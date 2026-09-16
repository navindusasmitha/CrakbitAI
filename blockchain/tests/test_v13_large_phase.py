from __future__ import annotations

import json

import pytest

from crakbit_chain.app_protocol import ExecutionProtocolAdapter, deterministic_application_hash
from crakbit_chain.crypto import KeyPair
from crakbit_chain.explorer_queries import explorer_summary, recent_blocks
from crakbit_chain.faucet_service import FaucetConfig, valid_crakbit_address
from crakbit_chain.genesis import Genesis
from crakbit_chain.models import ATOMIC_UNITS, Transaction
from crakbit_chain.release_artifacts import (
    ReleaseArtifactError,
    build_release_envelope,
    verify_release_envelope,
)
from crakbit_chain.storage import Ledger


def make_env(tmp_path):
    validator = KeyPair.generate()
    treasury = KeyPair.generate()
    recipient = KeyPair.generate()
    genesis_data = {
        "chain_id": "crakbit-v13-test-1",
        "network_name": "Crakbit v0.13 Test",
        "symbol": "CRKBIT",
        "decimals": 8,
        "max_supply": 21_000_000 * ATOMIC_UNITS,
        "block_time_ms": 100,
        "view_timeout_ms": 200,
        "min_fee": 1000,
        "validators": [
            {
                "name": "validator-1",
                "address": validator.address,
                "public_key": validator.public_key_b64,
                "peer_url": "http://127.0.0.1:9101",
            }
        ],
        "allocations": {treasury.address: 100 * ATOMIC_UNITS},
    }
    genesis_path = tmp_path / "genesis.json"
    genesis_path.write_text(json.dumps(genesis_data, indent=2) + "\n", encoding="utf-8")
    genesis = Genesis.load(genesis_path)
    ledger = Ledger(tmp_path / "node" / "chain.sqlite3", genesis)
    return genesis_path, genesis, ledger, validator, treasury, recipient


def signed_tx(genesis, treasury, recipient):
    tx = Transaction(
        chain_id=genesis.chain_id,
        sender=treasury.address,
        recipient=recipient.address,
        amount=ATOMIC_UNITS,
        fee=genesis.min_fee,
        nonce=1,
        public_key=treasury.public_key_b64,
        memo="v13-preview",
    )
    tx.signature = treasury.sign(tx.signing_bytes())
    return tx


def test_protocol_boundary_is_deterministic_and_non_mutating(tmp_path):
    _, genesis, ledger, validator, treasury, recipient = make_env(tmp_path)
    adapter = ExecutionProtocolAdapter(ledger)
    before_hash = deterministic_application_hash(ledger)
    tx = signed_tx(genesis, treasury, recipient)

    checked = adapter.check_transaction(tx.to_dict())
    preview = adapter.preview_batch([tx.to_dict()], fee_recipient=validator.address)

    assert checked["accepted"] is True
    assert preview["state_mutated"] is False
    assert preview["previous_application_hash"] == before_hash
    assert preview["transaction_count"] == 1
    assert ledger.height == 0
    assert deterministic_application_hash(ledger) == before_hash


def test_release_manifest_signature_and_genesis_binding(tmp_path):
    genesis_path, _, _, _, _, _ = make_env(tmp_path)
    release_key = KeyPair.generate()
    release_key_path = tmp_path / "release-key.json"
    release_key.save(release_key_path)
    artifact = tmp_path / "node-package.txt"
    artifact.write_text("test release payload", encoding="utf-8")

    envelope = build_release_envelope(
        genesis_path=genesis_path,
        signing_key_path=release_key_path,
        version="0.13.0a1",
        artifact_paths=[artifact],
    )
    verified = verify_release_envelope(
        envelope,
        genesis_path=genesis_path,
        expected_signer=release_key.address,
        artifact_directory=tmp_path,
    )

    assert verified["valid"] is True
    assert verified["verified_artifacts"] == 1
    assert verified["genesis_verified"] is True


def test_release_manifest_rejects_tamper(tmp_path):
    genesis_path, _, _, _, _, _ = make_env(tmp_path)
    release_key = KeyPair.generate()
    key_path = tmp_path / "release-key.json"
    release_key.save(key_path)
    envelope = build_release_envelope(
        genesis_path=genesis_path,
        signing_key_path=key_path,
        version="0.13.0a1",
    )
    envelope["manifest"]["version"] = "tampered"
    with pytest.raises(ReleaseArtifactError):
        verify_release_envelope(envelope, genesis_path=genesis_path)


def test_faucet_is_explicitly_bounded_and_address_validation_works(tmp_path):
    _, _, _, _, _, recipient = make_env(tmp_path)
    assert valid_crakbit_address(recipient.address) is True
    assert valid_crakbit_address("crk1bad") is False
    with pytest.raises(ValueError, match="at most 100"):
        FaucetConfig(amount_atomic=101 * ATOMIC_UNITS).validate()


def test_read_only_explorer_summary_is_bounded(tmp_path):
    _, _, ledger, _, _, _ = make_env(tmp_path)
    summary = explorer_summary(ledger)
    assert summary["height"] == 0
    assert summary["stored_blocks"] == 0
    assert recent_blocks(ledger, 500) == []
