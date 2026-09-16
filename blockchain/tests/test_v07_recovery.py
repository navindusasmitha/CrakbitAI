from __future__ import annotations

import json

import pytest

from crakbit_chain.crypto import KeyPair, canonical_json
from crakbit_chain.genesis import Genesis
from crakbit_chain.peer_auth import PeerAuthError, PeerAuthenticator, sign_peer_request
from crakbit_chain.snapshots import (
    build_snapshot_certificate,
    import_snapshot_certificate,
    sign_snapshot,
    verify_snapshot_certificate,
)
from crakbit_chain.storage import Ledger, LedgerError


def make_genesis(tmp_path, validator_count: int = 4):
    validators = [KeyPair.generate() for _ in range(validator_count)]
    treasury = KeyPair.generate()
    data = {
        "chain_id": "crakbit-v07-test-1",
        "network_name": "Crakbit v0.7 Test",
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
    return Genesis.load(path), validators, treasury


def test_peer_replay_cache_survives_authenticator_restart(tmp_path):
    genesis, validators, _ = make_genesis(tmp_path)
    key = validators[0]
    body = canonical_json({"height": 7, "phase": "prevote"})
    now = 1_700_000_000_000
    headers = sign_peer_request(
        key,
        method="POST",
        path="/internal/prevote",
        body=body,
        timestamp_ms=now,
        nonce="v07-persistent-replay-nonce-0001",
    )
    replay_db = tmp_path / "peer-replay.sqlite3"

    first = PeerAuthenticator(genesis, replay_store_path=replay_db)
    assert first.replay_store_mode == "sqlite"
    first.verify(
        headers,
        method="POST",
        path="/internal/prevote",
        body=body,
        now_ms=now,
    )

    restarted = PeerAuthenticator(genesis, replay_store_path=replay_db)
    with pytest.raises(PeerAuthError, match="replayed peer request"):
        restarted.verify(
            headers,
            method="POST",
            path="/internal/prevote",
            body=body,
            now_ms=now,
        )


def test_quorum_snapshot_certificate_and_import(tmp_path):
    genesis, validators, treasury = make_genesis(tmp_path)
    source = Ledger(tmp_path / "source.sqlite3", genesis)
    receiver = KeyPair.generate()

    with source.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "UPDATE accounts SET balance=? WHERE address=?",
            (75 * 100_000_000, treasury.address),
        )
        conn.execute(
            "INSERT INTO accounts(address,balance,nonce) VALUES(?,?,?)",
            (receiver.address, 25 * 100_000_000, 2),
        )
        conn.execute("UPDATE metadata SET value='5' WHERE key='height'")
        conn.execute("UPDATE metadata SET value=? WHERE key='last_hash'", ("ab" * 32,))
        conn.execute("COMMIT")

    envelopes = [sign_snapshot(source, key) for key in validators[:3]]
    certificate = build_snapshot_certificate(envelopes, genesis)
    snapshot = verify_snapshot_certificate(certificate, genesis)

    assert snapshot["height"] == 5
    assert len(certificate["signatures"]) == genesis.quorum_size == 3

    target = Ledger(tmp_path / "target.sqlite3", genesis)
    imported = import_snapshot_certificate(target, certificate)
    assert imported["height"] == 5
    assert target.height == 5
    assert target.last_hash == "ab" * 32
    assert target.account(receiver.address)["balance"] == 25 * 100_000_000
    assert target.account(receiver.address)["nonce"] == 2

    with target.connect() as conn:
        row = conn.execute(
            "SELECT value FROM metadata WHERE key='snapshot_base_height'"
        ).fetchone()
        assert row is not None and row["value"] == "5"


def test_snapshot_certificate_rejects_split_state_without_quorum(tmp_path):
    genesis, validators, treasury = make_genesis(tmp_path)
    ledger_a = Ledger(tmp_path / "a.sqlite3", genesis)
    ledger_b = Ledger(tmp_path / "b.sqlite3", genesis)
    receiver = KeyPair.generate()

    with ledger_b.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "UPDATE accounts SET balance=? WHERE address=?",
            (99 * 100_000_000, treasury.address),
        )
        conn.execute(
            "INSERT INTO accounts(address,balance,nonce) VALUES(?,?,0)",
            (receiver.address, 1 * 100_000_000),
        )
        conn.execute("COMMIT")

    envelopes = [
        sign_snapshot(ledger_a, validators[0]),
        sign_snapshot(ledger_a, validators[1]),
        sign_snapshot(ledger_b, validators[2]),
        sign_snapshot(ledger_b, validators[3]),
    ]
    with pytest.raises(LedgerError, match="no snapshot hash has validator quorum"):
        build_snapshot_certificate(envelopes, genesis)


def test_snapshot_import_refuses_nonempty_local_history(tmp_path):
    genesis, validators, _ = make_genesis(tmp_path)
    source = Ledger(tmp_path / "source.sqlite3", genesis)
    with source.connect() as conn:
        conn.execute("UPDATE metadata SET value='1' WHERE key='height'")
        conn.execute("UPDATE metadata SET value=? WHERE key='last_hash'", ("cd" * 32,))
    certificate = build_snapshot_certificate(
        [sign_snapshot(source, key) for key in validators[:3]],
        genesis,
    )

    target = Ledger(tmp_path / "target.sqlite3", genesis)
    with target.connect() as conn:
        conn.execute("UPDATE metadata SET value='1' WHERE key='height'")
        conn.execute("UPDATE metadata SET value=? WHERE key='last_hash'", ("ef" * 32,))

    with pytest.raises(LedgerError, match="fresh height-zero database"):
        import_snapshot_certificate(target, certificate)
