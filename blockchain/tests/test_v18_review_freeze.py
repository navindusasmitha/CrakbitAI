from __future__ import annotations

import json
from pathlib import Path

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.explorer_index import ExternalExplorerIndex
from crakbit_chain.explorer_reconcile import reconcile_explorer_index
from crakbit_chain.external_commit_v16 import ExternalExecutionStoreV16
from crakbit_chain.genesis import Genesis
from crakbit_chain.review_freeze import (
    ReviewFreezeError,
    build_review_freeze,
    verify_review_freeze,
)
from crakbit_chain.soak_evidence import summarize_soak
from crakbit_chain.storage import Ledger


def _genesis(tmp_path: Path) -> tuple[Path, Genesis, KeyPair]:
    validator = KeyPair.generate()
    path = tmp_path / "genesis.json"
    path.write_text(
        json.dumps(
            {
                "chain_id": "crakbit-v18-test",
                "network_name": "Crakbit v0.18 Test",
                "symbol": "CRKBIT",
                "decimals": 8,
                "max_supply": 1_000_000,
                "block_time_ms": 1000,
                "view_timeout_ms": 2000,
                "min_fee": 1,
                "validators": [
                    {
                        "address": validator.address,
                        "public_key": validator.public_key_b64,
                        "name": "validator-1",
                        "peer_url": "http://127.0.0.1:9101",
                    }
                ],
                "allocations": {validator.address: 1_000_000},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path, Genesis.load(path), validator


def test_review_freeze_signature_and_tamper_detection(tmp_path: Path):
    genesis_path, _genesis_obj, _validator = _genesis(tmp_path)
    signer = KeyPair.generate()
    key_path = tmp_path / "review-key.json"
    signer.save(key_path)
    evidence = tmp_path / "health.json"
    evidence.write_text('{"healthy":true}\n', encoding="utf-8")

    envelope = build_review_freeze(
        genesis_path=genesis_path,
        signing_key_path=key_path,
        source_commit="a" * 40,
        package_version="0.18.0a1",
        cometbft_version="v0.40.0",
        artifacts=[("health", evidence)],
    )
    verified = verify_review_freeze(
        envelope,
        genesis_path=genesis_path,
        artifact_directory=tmp_path,
        expected_signer=signer.address,
        expected_source_commit="a" * 40,
    )
    assert verified["valid"] is True
    assert verified["production_mainnet_ready"] is False
    assert verified["verified_artifacts"] == 1

    tampered = json.loads(json.dumps(envelope))
    tampered["manifest"]["package_version"] = "9.9.9"
    with pytest.raises(ReviewFreezeError):
        verify_review_freeze(tampered, genesis_path=genesis_path)


def test_explorer_reconcile_matches_clean_rebuild(tmp_path: Path):
    _genesis_path, genesis, _validator = _genesis(tmp_path)
    source_dir = tmp_path / "external-app"
    source_dir.mkdir()
    ledger = Ledger(source_dir / "chain.sqlite3", genesis)
    ExternalExecutionStoreV16(ledger)

    index_path = tmp_path / "explorer.sqlite3"
    index = ExternalExplorerIndex(index_path, genesis)
    index.sync_from_source(source_dir)

    result = reconcile_explorer_index(
        genesis=genesis,
        source_data_dir=source_dir,
        index_path=index_path,
    )
    assert result["matches_clean_rebuild"] is True
    assert result["mismatched_tables"] == []


def test_soak_summary_is_conservative():
    result = summarize_soak(
        [
            {"healthy": True, "height_spread": 0},
            {"healthy": False, "height_spread": 3},
        ]
    )
    assert result["sample_count"] == 2
    assert result["healthy_samples"] == 1
    assert result["unhealthy_samples"] == 1
    assert result["all_samples_healthy"] is False
    assert result["max_height_spread_observed"] == 3
