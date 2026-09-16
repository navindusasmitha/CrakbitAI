from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .compatibility_v20 import check_compatibility
from .genesis import Genesis
from .schema_migrations_v20 import migrate_database_copy, resolve_db_path


class UpgradeRehearsalError(ValueError):
    pass


def rehearse_upgrade(
    *,
    genesis_path: str | Path,
    source_data: str | Path,
    output_data: str | Path,
    cometbft_version: str = "v0.40.0",
    overwrite: bool = False,
) -> dict[str, Any]:
    genesis = Genesis.load(genesis_path)
    source_db = resolve_db_path(source_data)
    target_dir = Path(output_data)
    target_db = target_dir / "chain.sqlite3"
    if target_dir.exists() and any(target_dir.iterdir()) and not overwrite:
        raise UpgradeRehearsalError(
            f"upgrade rehearsal output directory is not empty: {target_dir}"
        )
    target_dir.mkdir(parents=True, exist_ok=True)

    migration = migrate_database_copy(
        source=source_db,
        output=target_db,
        target_version=20,
        overwrite=overwrite,
        verify_rollback=True,
    )
    with sqlite3.connect(target_db) as conn:
        row = conn.execute("PRAGMA integrity_check").fetchone()
        integrity = str(row[0]) if row else "unknown"
        fingerprint_row = conn.execute(
            "SELECT value FROM metadata WHERE key='genesis_fingerprint'"
        ).fetchone()
        fingerprint = str(fingerprint_row[0]) if fingerprint_row else ""
    if integrity.lower() != "ok":
        raise UpgradeRehearsalError(f"migrated database integrity check failed: {integrity}")
    if fingerprint != genesis.fingerprint():
        raise UpgradeRehearsalError("migrated database genesis fingerprint mismatch")

    compatibility = check_compatibility(
        data=target_db,
        cometbft_version=cometbft_version,
        expected_genesis_fingerprint=genesis.fingerprint(),
    )
    if not compatibility["compatible_for_v020_testnet_rehearsal"]:
        raise UpgradeRehearsalError("migrated database failed v0.20 compatibility checks")

    return {
        "format": "crakbit-upgrade-rehearsal/1",
        "source_database": str(source_db),
        "target_database": str(target_db),
        "chain_id": genesis.chain_id,
        "genesis_fingerprint": genesis.fingerprint(),
        "migration": migration,
        "sqlite_integrity_check": integrity,
        "compatibility": compatibility,
        "rollback_verified": bool(migration["rollback_verified"]),
        "source_modified": False,
        "live_node_upgraded": False,
        "testnet_rehearsal_passed": True,
        "production_mainnet_ready": False,
    }


def save_upgrade_rehearsal(report: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise UpgradeRehearsalError(f"upgrade rehearsal report already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return target
