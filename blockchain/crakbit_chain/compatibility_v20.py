from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema_migrations_v20 import CURRENT_SCHEMA_VERSION, detect_schema_version, resolve_db_path


COMPATIBILITY_FORMAT = "crakbit-compatibility-matrix/1"
PACKAGE_VERSION = "0.20.0a1"
EXECUTION_PROTOCOL = "crakbit-execution/2"
SUPPORTED_COMETBFT = {"v0.40.0"}
SUPPORTED_SCHEMA_VERSIONS = {19, 20}
RECOMMENDED_SCHEMA_VERSION = 20


def compatibility_matrix() -> dict[str, Any]:
    return {
        "format": COMPATIBILITY_FORMAT,
        "package_version": PACKAGE_VERSION,
        "execution_protocol": EXECUTION_PROTOCOL,
        "supported_cometbft_versions": sorted(SUPPORTED_COMETBFT),
        "supported_application_schema_versions": sorted(SUPPORTED_SCHEMA_VERSIONS),
        "recommended_application_schema_version": RECOMMENDED_SCHEMA_VERSION,
        "native_state_sync_minimum_package": "0.17.0a1",
        "review_freeze_minimum_package": "0.18.0a1",
        "release_provenance_minimum_package": "0.19.0a1",
        "validator_lifecycle_mode": "offline-signed-drill-plan-only",
        "live_validator_updates_enabled": False,
        "production_mainnet_ready": False,
    }


def check_compatibility(
    *,
    data: str | Path,
    cometbft_version: str,
    expected_genesis_fingerprint: str | None = None,
) -> dict[str, Any]:
    db = resolve_db_path(data)
    schema_version = detect_schema_version(db)
    with __import__("sqlite3").connect(db) as conn:
        conn.row_factory = __import__("sqlite3").Row
        owner_row = conn.execute(
            "SELECT value FROM metadata WHERE key='execution_owner'"
        ).fetchone()
        genesis_row = conn.execute(
            "SELECT value FROM metadata WHERE key='genesis_fingerprint'"
        ).fetchone()
    owner = str(owner_row["value"]) if owner_row is not None else ""
    genesis_fingerprint = str(genesis_row["value"]) if genesis_row is not None else ""

    checks = {
        "execution_owner": owner == EXECUTION_PROTOCOL,
        "schema_supported": schema_version in SUPPORTED_SCHEMA_VERSIONS,
        "schema_recommended": schema_version == RECOMMENDED_SCHEMA_VERSION,
        "cometbft_supported": cometbft_version in SUPPORTED_COMETBFT,
        "genesis_matches_expected": (
            True
            if expected_genesis_fingerprint is None
            else genesis_fingerprint == expected_genesis_fingerprint
        ),
    }
    compatible = all(
        checks[name]
        for name in (
            "execution_owner",
            "schema_supported",
            "cometbft_supported",
            "genesis_matches_expected",
        )
    )
    return {
        "format": COMPATIBILITY_FORMAT,
        "package_version": PACKAGE_VERSION,
        "database": str(db),
        "execution_protocol": owner,
        "schema_version": schema_version,
        "cometbft_version": cometbft_version,
        "genesis_fingerprint": genesis_fingerprint,
        "checks": checks,
        "compatible_for_v020_testnet_rehearsal": compatible,
        "migration_recommended": schema_version != RECOMMENDED_SCHEMA_VERSION,
        "live_validator_updates_enabled": False,
        "production_mainnet_ready": False,
    }


def save_matrix(path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"compatibility matrix already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(compatibility_matrix(), indent=2) + "\n", encoding="utf-8")
    return target
