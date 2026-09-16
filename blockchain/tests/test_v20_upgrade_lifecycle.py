from __future__ import annotations

import json
from pathlib import Path

import pytest

from crakbit_chain.compatibility_v20 import check_compatibility
from crakbit_chain.crypto import KeyPair
from crakbit_chain.external_commit_v16 import ExternalExecutionStoreV16
from crakbit_chain.genesis import Genesis
from crakbit_chain.migration_evidence_v20 import (
    MigrationEvidenceError,
    build_migration_evidence,
    verify_migration_evidence,
)
from crakbit_chain.schema_migrations_v20 import (
    detect_schema_version,
    dry_run_migration,
    logical_database_fingerprint,
    migrate_database_copy,
)
from crakbit_chain.storage import Ledger
from crakbit_chain.upgrade_rehearsal_v20 import rehearse_upgrade, save_upgrade_rehearsal
from crakbit_chain.validator_lifecycle_v20 import (
    ValidatorLifecycleError,
    build_validator_lifecycle_plan,
    verify_validator_lifecycle_plan,
)


def _fixture(tmp_path: Path):
    validator = KeyPair.generate()
    treasury = KeyPair.generate()
    genesis_path = tmp_path / "genesis.json"
    genesis_path.write_text(
        json.dumps(
            {
                "chain_id": "crakbit-v20-test",
                "network_name": "Crakbit v0.20 Test",
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
                "allocations": {treasury.address: 1_000_000},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    genesis = Genesis.load(genesis_path)
    data_dir = tmp_path / "app-v19"
    data_dir.mkdir()
    ledger = Ledger(data_dir / "chain.sqlite3", genesis)
    ExternalExecutionStoreV16(ledger)
    return genesis_path, genesis, validator, treasury, data_dir


def test_v20_migration_copy_preserves_state_and_verifies_rollback(tmp_path: Path):
    _genesis_path, _genesis, _validator, _treasury, data_dir = _fixture(tmp_path)
    source = data_dir / "chain.sqlite3"
    assert detect_schema_version(source) == 19
    before = logical_database_fingerprint(source)

    output = tmp_path / "migrated.sqlite3"
    report = migrate_database_copy(source=source, output=output)
    assert report["migration_applied"] is True
    assert report["rollback_verified"] is True
    assert report["source_modified"] is False
    assert detect_schema_version(output) == 20
    assert detect_schema_version(source) == 19
    assert logical_database_fingerprint(source) == before
    assert logical_database_fingerprint(output) == before

    dry = dry_run_migration(source=source)
    assert dry["dry_run"] is True
    assert dry["rollback_verified"] is True


def test_v20_compatibility_and_upgrade_rehearsal(tmp_path: Path):
    genesis_path, genesis, _validator, _treasury, data_dir = _fixture(tmp_path)
    migrated = tmp_path / "migrated.sqlite3"
    migrate_database_copy(source=data_dir, output=migrated)

    good = check_compatibility(
        data=migrated,
        cometbft_version="v0.40.0",
        expected_genesis_fingerprint=genesis.fingerprint(),
    )
    assert good["compatible_for_v020_testnet_rehearsal"] is True
    assert good["checks"]["schema_recommended"] is True

    bad = check_compatibility(data=migrated, cometbft_version="v9.9.9")
    assert bad["compatible_for_v020_testnet_rehearsal"] is False

    rehearsal_dir = tmp_path / "rehearsed"
    report = rehearse_upgrade(
        genesis_path=genesis_path,
        source_data=data_dir,
        output_data=rehearsal_dir,
    )
    assert report["testnet_rehearsal_passed"] is True
    assert report["rollback_verified"] is True
    assert report["live_node_upgraded"] is False
    assert detect_schema_version(rehearsal_dir) == 20


def test_v20_signed_migration_evidence_detects_tamper(tmp_path: Path):
    genesis_path, _genesis, _validator, _treasury, data_dir = _fixture(tmp_path)
    report = rehearse_upgrade(
        genesis_path=genesis_path,
        source_data=data_dir,
        output_data=tmp_path / "rehearsed",
    )
    report_path = tmp_path / "upgrade-report.json"
    save_upgrade_rehearsal(report, report_path)

    signer = KeyPair.generate()
    key_path = tmp_path / "migration-signer.json"
    signer.save(key_path)
    envelope = build_migration_evidence(
        signing_key_path=key_path,
        source_commit="a" * 40,
        report_path=report_path,
    )
    verified = verify_migration_evidence(
        envelope,
        report_directory=tmp_path,
        expected_signer=signer.address,
    )
    assert verified["valid"] is True
    assert verified["rollback_verified"] is True
    assert verified["report_verified"] is True

    tampered = json.loads(json.dumps(envelope))
    tampered["manifest"]["target_schema_version"] = 99
    with pytest.raises(MigrationEvidenceError):
        verify_migration_evidence(tampered)


def test_v20_validator_lifecycle_plan_is_signed_and_non_live(tmp_path: Path):
    genesis_path, genesis, _validator, _treasury, _data_dir = _fixture(tmp_path)
    signer = KeyPair.generate()
    signer_path = tmp_path / "lifecycle-signer.json"
    signer.save(signer_path)
    joining = KeyPair.generate()

    envelope = build_validator_lifecycle_plan(
        genesis_path=genesis_path,
        signing_key_path=signer_path,
        source_commit="b" * 40,
        kind="join",
        effective_height=12,
        new_public_key=joining.public_key_b64,
        new_name="validator-2",
        new_power=1,
    )
    result = verify_validator_lifecycle_plan(
        envelope,
        genesis_path=genesis_path,
        expected_signer=signer.address,
        expected_source_commit="b" * 40,
    )
    assert result["valid"] is True
    assert result["emit_height"] == 10
    assert result["effective_height"] == 12
    assert result["before_validator_count"] == 1
    assert result["after_validator_count"] == 2
    assert result["consensus_change_applied"] is False

    with pytest.raises(ValidatorLifecycleError):
        build_validator_lifecycle_plan(
            genesis_path=genesis_path,
            signing_key_path=signer_path,
            source_commit="b" * 40,
            kind="remove",
            effective_height=12,
            existing_address=genesis.validators[0].address,
        )
