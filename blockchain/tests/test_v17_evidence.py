from __future__ import annotations

import json
from pathlib import Path

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.evidence_bundle import (
    EvidenceBundleError,
    build_evidence_bundle,
    verify_evidence_bundle,
)
from crakbit_chain.models import ATOMIC_UNITS


def make_files(tmp_path: Path):
    validator = KeyPair.generate()
    treasury = KeyPair.generate()
    signer = KeyPair.generate()
    data = {
        "chain_id": "crakbit-v17-evidence",
        "network_name": "Crakbit Evidence Test",
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
    genesis = tmp_path / "genesis.json"
    genesis.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    key = tmp_path / "evidence-key.json"
    signer.save(key)
    evidence = tmp_path / "health.json"
    evidence.write_text('{"healthy":true}\n', encoding="utf-8")
    return genesis, key, signer, evidence


def test_signed_evidence_bundle_verifies_files(tmp_path):
    genesis, key, signer, evidence = make_files(tmp_path)
    envelope = build_evidence_bundle(
        genesis_path=genesis,
        signing_key_path=key,
        source_commit="ab" * 20,
        cometbft_version="v0.40.0",
        evidence_paths=[evidence],
    )
    verified = verify_evidence_bundle(
        envelope,
        genesis_path=genesis,
        evidence_directory=tmp_path,
        expected_signer=signer.address,
    )
    assert verified["valid"] is True
    assert verified["verified_evidence_files"] == 1
    assert verified["production_mainnet_ready"] is False


def test_evidence_bundle_detects_artifact_tamper(tmp_path):
    genesis, key, signer, evidence = make_files(tmp_path)
    envelope = build_evidence_bundle(
        genesis_path=genesis,
        signing_key_path=key,
        source_commit="cd" * 20,
        cometbft_version="v0.40.0",
        evidence_paths=[evidence],
    )
    evidence.write_text('{"healthy":false}\n', encoding="utf-8")
    with pytest.raises(EvidenceBundleError):
        verify_evidence_bundle(
            envelope,
            genesis_path=genesis,
            evidence_directory=tmp_path,
            expected_signer=signer.address,
        )
