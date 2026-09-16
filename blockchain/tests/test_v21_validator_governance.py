from __future__ import annotations

import json
from pathlib import Path

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.external_commit_v16 import ExternalExecutionStoreV16
from crakbit_chain.external_commit_v21 import ExternalExecutionStoreV21
from crakbit_chain.external_state_sync_v21 import (
    export_external_snapshot_v21,
    import_external_snapshot_v21,
    verify_external_snapshot_v21,
)
from crakbit_chain.genesis import Genesis
from crakbit_chain.schema_migrations_v20 import detect_schema_version, migrate_database_copy
from crakbit_chain.schema_migrations_v21 import migrate_to_v21_copy
from crakbit_chain.storage import Ledger
from crakbit_chain.validator_governance_v21 import (
    ValidatorGovernanceError,
    build_governance_request,
    sign_governance_request,
)


def _fixture(tmp_path: Path):
    validators = [KeyPair.generate() for _ in range(4)]
    treasury = KeyPair.generate()
    genesis_path = tmp_path / "genesis.json"
    genesis_path.write_text(
        json.dumps(
            {
                "chain_id": "crakbit-v21-test",
                "network_name": "Crakbit v0.21 Test",
                "symbol": "CRKBIT",
                "decimals": 8,
                "max_supply": 1_000_000,
                "block_time_ms": 1000,
                "view_timeout_ms": 2000,
                "min_fee": 1,
                "validators": [
                    {
                        "address": key.address,
                        "public_key": key.public_key_b64,
                        "name": f"validator-{index + 1}",
                        "peer_url": f"http://127.0.0.1:{9101 + index}",
                    }
                    for index, key in enumerate(validators)
                ],
                "allocations": {treasury.address: 1_000_000},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    key_paths: list[Path] = []
    for index, key in enumerate(validators):
        path = tmp_path / f"validator-{index + 1}.json"
        key.save(path)
        key_paths.append(path)
    genesis = Genesis.load(genesis_path)
    data_dir = tmp_path / "app"
    data_dir.mkdir()
    ledger = Ledger(data_dir / "chain.sqlite3", genesis)
    store = ExternalExecutionStoreV21(ledger)
    return genesis_path, genesis, validators, key_paths, treasury, data_dir, store


def _signed_join(tmp_path: Path, genesis_path: Path, data_dir: Path, key_paths: list[Path]):
    joining = KeyPair.generate()
    envelope = build_governance_request(
        genesis_path=genesis_path,
        data_dir=data_dir,
        kind="join",
        emit_height=1,
        new_public_key=joining.public_key_b64,
        new_name="validator-5",
        new_power=1,
    )
    for path in key_paths[:3]:
        envelope = sign_governance_request(
            envelope,
            genesis_path=genesis_path,
            data_dir=data_dir,
            signing_key_path=path,
        )
    return joining, envelope


def test_v21_governance_requires_strict_quorum(tmp_path: Path):
    genesis_path, _genesis, _validators, key_paths, _treasury, data_dir, store = _fixture(tmp_path)
    joining = KeyPair.generate()
    envelope = build_governance_request(
        genesis_path=genesis_path,
        data_dir=data_dir,
        kind="join",
        emit_height=1,
        new_public_key=joining.public_key_b64,
    )
    for path in key_paths[:2]:
        envelope = sign_governance_request(
            envelope,
            genesis_path=genesis_path,
            data_dir=data_dir,
            signing_key_path=path,
        )
    with pytest.raises(ValidatorGovernanceError):
        store.governance.verify_envelope(envelope, expected_emit_height=1, require_quorum=True)


def test_v21_governance_emits_and_activates_validator_update(tmp_path: Path):
    genesis_path, _genesis, _validators, key_paths, _treasury, data_dir, store = _fixture(tmp_path)
    joining, envelope = _signed_join(tmp_path, genesis_path, data_dir, key_paths)

    verified = store.governance.verify_envelope(
        envelope, expected_emit_height=1, require_quorum=True
    )
    assert verified["quorum"] is True
    assert verified["approved_power"] == 3
    assert verified["total_power"] == 4

    block1 = "11" * 32
    staged = store.stage_finalize(height=1, consensus_block_hash=block1, transactions=[envelope])
    assert staged["staged"] is True
    assert len(staged["validator_updates"]) == 1
    assert staged["validator_updates"][0]["public_key"] == joining.public_key_b64
    committed = store.commit_pending()
    assert committed["height"] == 1
    status = store.governance.status()
    assert status["active_validator_count"] == 4
    assert len(status["pending"]) == 1
    assert status["pending"][0]["effective_height"] == 3

    replay = store.stage_finalize(height=1, consensus_block_hash=block1, transactions=[envelope])
    assert replay["already_committed"] is True
    assert len(replay["validator_updates"]) == 1

    store.stage_finalize(height=2, consensus_block_hash="22" * 32, transactions=[])
    store.commit_pending()
    assert store.governance.status()["active_validator_count"] == 4

    store.stage_finalize(height=3, consensus_block_hash="33" * 32, transactions=[])
    store.commit_pending()
    final = store.governance.status()
    assert final["active_validator_count"] == 5
    assert final["pending"] == []
    assert any(item["address"] == joining.address for item in final["active_validators"])


def test_v21_snapshot_preserves_pending_governance_state(tmp_path: Path):
    genesis_path, genesis, _validators, key_paths, _treasury, data_dir, store = _fixture(tmp_path)
    _joining, envelope = _signed_join(tmp_path, genesis_path, data_dir, key_paths)
    store.stage_finalize(height=1, consensus_block_hash="44" * 32, transactions=[envelope])
    store.commit_pending()

    snapshot = export_external_snapshot_v21(store.ledger)
    verified = verify_external_snapshot_v21(
        snapshot,
        genesis,
        expected_height=1,
        expected_application_hash=store.application_hash(),
    )
    assert verified["pending_validator_changes"] == 1

    restored_dir = tmp_path / "restored"
    restored = import_external_snapshot_v21(
        envelope=snapshot,
        genesis=genesis,
        data_dir=restored_dir,
        expected_height=1,
        expected_application_hash=store.application_hash(),
    )
    assert restored["application_hash"] == store.application_hash()
    restored_store = ExternalExecutionStoreV21(
        Ledger(restored_dir / "chain.sqlite3", genesis)
    )
    assert len(restored_store.governance.status()["pending"]) == 1


def test_v21_offline_schema_migration_from_v20(tmp_path: Path):
    genesis_path, genesis, _validators, _key_paths, _treasury, _data_dir, _store = _fixture(tmp_path)

    legacy_dir = tmp_path / "legacy-v19"
    legacy_dir.mkdir()
    legacy_ledger = Ledger(legacy_dir / "chain.sqlite3", genesis)
    ExternalExecutionStoreV16(legacy_ledger)
    v20_db = tmp_path / "v20.sqlite3"
    migrate_database_copy(source=legacy_dir, output=v20_db)
    assert detect_schema_version(v20_db) == 20

    v21_db = tmp_path / "v21.sqlite3"
    report = migrate_to_v21_copy(
        genesis_path=genesis_path,
        source=v20_db,
        output=v21_db,
    )
    assert report["migration_applied"] is True
    assert report["rollback_verified"] is True
    assert detect_schema_version(v21_db) == 21
    migrated_store = ExternalExecutionStoreV21(Ledger(v21_db, genesis))
    assert migrated_store.governance.status()["active_validator_count"] == 4
