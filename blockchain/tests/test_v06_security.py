from __future__ import annotations

import json

import pytest

from crakbit_chain.crypto import KeyPair, canonical_json
from crakbit_chain.genesis import Genesis
from crakbit_chain.peer_auth import (
    PeerAuthError,
    PeerAuthenticator,
    build_hello_payload,
    sign_peer_request,
    verify_hello_response,
)
from crakbit_chain.snapshots import sign_snapshot, verify_snapshot
from crakbit_chain.storage import Ledger, LedgerError


def make_genesis(tmp_path, validator_count: int = 2):
    validators = [KeyPair.generate() for _ in range(validator_count)]
    treasury = KeyPair.generate()
    data = {
        "chain_id": "crakbit-v06-test-1",
        "network_name": "Crakbit v0.6 Test",
        "symbol": "CRKBIT",
        "decimals": 8,
        "max_supply": 21_000_000 * 100_000_000,
        "block_time_ms": 100,
        "view_timeout_ms": 200,
        "min_fee": 1000,
        "validators": [
            {
                "name": f"validator-{index + 1}",
                "address": key.address,
                "public_key": key.public_key_b64,
                "peer_url": f"http://127.0.0.1:{9101 + index}",
            }
            for index, key in enumerate(validators)
        ],
        "allocations": {treasury.address: 100 * 100_000_000},
    }
    path = tmp_path / "genesis.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return Genesis.load(path), validators


def test_signed_peer_request_authentication_and_replay_rejection(tmp_path):
    genesis, validators = make_genesis(tmp_path)
    key = validators[0]
    body = canonical_json({"block": {"height": 1}})
    now = 1_700_000_000_000
    headers = sign_peer_request(
        key,
        method="POST",
        path="/internal/prevote",
        body=body,
        timestamp_ms=now,
        nonce="0123456789abcdef0123456789abcdef",
    )
    authenticator = PeerAuthenticator(genesis)
    peer = authenticator.verify(
        headers,
        method="POST",
        path="/internal/prevote",
        body=body,
        now_ms=now,
    )
    assert peer.address == key.address

    with pytest.raises(PeerAuthError, match="replayed peer request"):
        authenticator.verify(
            headers,
            method="POST",
            path="/internal/prevote",
            body=body,
            now_ms=now,
        )


def test_peer_request_body_tamper_and_stale_timestamp_rejected(tmp_path):
    genesis, validators = make_genesis(tmp_path)
    key = validators[0]
    body = canonical_json({"hello": "world"})
    now = 1_700_000_000_000
    headers = sign_peer_request(
        key,
        method="POST",
        path="/internal/block",
        body=body,
        timestamp_ms=now,
        nonce="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )

    with pytest.raises(PeerAuthError, match="invalid peer request signature"):
        PeerAuthenticator(genesis).verify(
            headers,
            method="POST",
            path="/internal/block",
            body=canonical_json({"hello": "tampered"}),
            now_ms=now,
        )

    with pytest.raises(PeerAuthError, match="timestamp outside accepted window"):
        PeerAuthenticator(genesis).verify(
            headers,
            method="POST",
            path="/internal/block",
            body=body,
            now_ms=now + 31_000,
        )


def test_mutual_identity_hello_is_signed(tmp_path):
    genesis, validators = make_genesis(tmp_path)
    peer_key = validators[1]
    peer = genesis.validator_by_address(peer_key.address)
    assert peer is not None
    now = 1_700_000_000_000
    response = build_hello_payload(
        peer_key,
        chain_id=genesis.chain_id,
        challenge="challenge-123",
        timestamp_ms=now,
    )
    hello = verify_hello_response(
        peer,
        response,
        chain_id=genesis.chain_id,
        challenge="challenge-123",
        now_ms=now,
    )
    assert hello["address"] == peer_key.address

    response["hello"]["challenge"] = "other"
    with pytest.raises(PeerAuthError):
        verify_hello_response(
            peer,
            response,
            chain_id=genesis.chain_id,
            challenge="challenge-123",
            now_ms=now,
        )


def test_signed_state_snapshot_verification_and_tamper_detection(tmp_path):
    genesis, validators = make_genesis(tmp_path)
    ledger = Ledger(tmp_path / "chain.db", genesis)
    envelope = sign_snapshot(ledger, validators[0])
    snapshot = verify_snapshot(envelope, genesis)
    assert snapshot["height"] == 0
    assert snapshot["chain_id"] == genesis.chain_id
    assert len(snapshot["accounts_root"]) == 64

    envelope["snapshot"]["accounts"][0]["balance"] += 1
    with pytest.raises(LedgerError, match="accounts root mismatch"):
        verify_snapshot(envelope, genesis)
