from __future__ import annotations

import json
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any

from .crypto import canonical_json, sha256_hex
from .genesis import Genesis
from .schema_migrations_v20 import (
    SCHEMA_VERSION_KEY,
    detect_schema_version,
    migrate_database_copy,
    resolve_db_path,
)
from .storage import LedgerError
from .validator_governance_v21 import SCHEMA_VERSION, genesis_validator_set

MIGRATION_ID_20_TO_21 = "external-app-20-to-21-validator-governance"
GOVERNANCE_TABLES = {
    "validator_governance_validators",
    "validator_governance_pending",
    "validator_governance_history",
    "validator_governance_emissions",
}


class SchemaMigrationV21Error(LedgerError):
    pass


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


def _backup(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    src = sqlite3.connect(source, timeout=30)
    dst = sqlite3.connect(target, timeout=30)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def _normalize(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"bytes_hex": value.hex()}
    if value is None or isinstance(value, (str, int, float)):
        return value
    return str(value)


def core_state_fingerprint(path: str | Path) -> str:
    db = resolve_db_path(path)
    included_tables = [
        "accounts",
        "transactions",
        "external_commits",
        "external_pending_finalizes",
    ]
    payload: dict[str, Any] = {"tables": [], "metadata": []}
    with _connect(db) as conn:
        metadata = conn.execute(
            "SELECT key,value FROM metadata WHERE key<>? ORDER BY key", (SCHEMA_VERSION_KEY,)
        ).fetchall()
        payload["metadata"] = [(str(row["key"]), str(row["value"])) for row in metadata]
        for table in included_tables:
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            if exists is None:
                continue
            columns = [str(row["name"]) for row in conn.execute(f'PRAGMA table_info("{table}")')]
            quoted = ",".join('"' + item.replace('"', '""') + '"' for item in columns)
            rows = conn.execute(f'SELECT {quoted} FROM "{table}"').fetchall()
            encoded = [
                json.dumps(
                    {column: _normalize(row[column]) for column in columns},
                    sort_keys=True,
                    separators=(",", ":"),
                )
                for row in rows
            ]
            encoded.sort()
            payload["tables"].append({"name": table, "rows": encoded})
    return sha256_hex(canonical_json(payload))


def _apply_v21_schema(conn: sqlite3.Connection, genesis: Genesis, source_fingerprint: str) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS validator_governance_validators (
            address TEXT PRIMARY KEY,
            public_key TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            power INTEGER NOT NULL,
            activated_height INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS validator_governance_pending (
            change_id TEXT PRIMARY KEY,
            emit_height INTEGER UNIQUE NOT NULL,
            effective_height INTEGER UNIQUE NOT NULL,
            source_set_hash TEXT NOT NULL,
            target_set_hash TEXT NOT NULL,
            envelope_json TEXT NOT NULL,
            target_validators_json TEXT NOT NULL,
            updates_json TEXT NOT NULL,
            created_at_ms INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS validator_governance_history (
            change_id TEXT PRIMARY KEY,
            emit_height INTEGER NOT NULL,
            effective_height INTEGER NOT NULL,
            source_set_hash TEXT NOT NULL,
            target_set_hash TEXT NOT NULL,
            envelope_json TEXT NOT NULL,
            target_validators_json TEXT NOT NULL,
            updates_json TEXT NOT NULL,
            applied_height INTEGER NOT NULL,
            applied_at_ms INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS validator_governance_emissions (
            height INTEGER PRIMARY KEY,
            change_id TEXT UNIQUE NOT NULL,
            updates_json TEXT NOT NULL
        );
        """
    )
    count = int(
        conn.execute("SELECT COUNT(*) AS n FROM validator_governance_validators").fetchone()["n"]
    )
    if count != 0:
        raise SchemaMigrationV21Error("v0.21 migration target already contains governance validator state")
    for item in genesis_validator_set(genesis):
        conn.execute(
            "INSERT INTO validator_governance_validators(address,public_key,name,power,activated_height) "
            "VALUES(?,?,?,?,0)",
            (item["address"], item["public_key"], item["name"], int(item["power"])),
        )
    conn.execute(
        "INSERT INTO metadata(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (SCHEMA_VERSION_KEY, str(SCHEMA_VERSION)),
    )
    conn.execute(
        "INSERT OR REPLACE INTO crakbit_schema_migrations("
        "migration_id,from_version,to_version,source_fingerprint,applied_at_ms) VALUES(?,?,?,?,?)",
        (MIGRATION_ID_20_TO_21, 20, 21, source_fingerprint, int(time.time() * 1000)),
    )


def _rollback_to_v20(conn: sqlite3.Connection) -> None:
    for table in sorted(GOVERNANCE_TABLES):
        conn.execute(f'DROP TABLE IF EXISTS "{table}"')
    conn.execute(
        "INSERT INTO metadata(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (SCHEMA_VERSION_KEY, "20"),
    )
    conn.execute(
        "DELETE FROM crakbit_schema_migrations WHERE migration_id=?", (MIGRATION_ID_20_TO_21,)
    )


def migrate_to_v21_copy(
    *,
    genesis_path: str | Path,
    source: str | Path,
    output: str | Path,
    overwrite: bool = False,
    verify_rollback: bool = True,
) -> dict[str, Any]:
    genesis = Genesis.load(genesis_path)
    source_db = resolve_db_path(source)
    output_db = Path(output)
    if output_db.exists() and not overwrite:
        raise SchemaMigrationV21Error(f"migration output already exists: {output_db}")

    source_version = detect_schema_version(source_db)
    if source_version not in {19, 20, 21}:
        raise SchemaMigrationV21Error(f"unsupported source schema {source_version}; expected 19, 20, or 21")
    source_fingerprint = core_state_fingerprint(source_db)

    if source_version == 19:
        migrate_database_copy(
            source=source_db,
            output=output_db,
            target_version=20,
            overwrite=overwrite,
            verify_rollback=True,
        )
        base_version = 20
    else:
        _backup(source_db, output_db)
        base_version = source_version

    migrated = False
    if base_version == 20:
        with _connect(output_db) as conn:
            _apply_v21_schema(conn, genesis, source_fingerprint)
        migrated = True

    if detect_schema_version(output_db) != 21:
        raise SchemaMigrationV21Error("v0.21 migration output schema mismatch")
    if core_state_fingerprint(output_db) != source_fingerprint:
        raise SchemaMigrationV21Error("v0.21 migration changed pre-existing core application state")

    with _connect(output_db) as conn:
        stored_genesis = conn.execute(
            "SELECT value FROM metadata WHERE key='genesis_fingerprint'"
        ).fetchone()
        if stored_genesis is None or str(stored_genesis["value"]) != genesis.fingerprint():
            raise SchemaMigrationV21Error("v0.21 migration genesis fingerprint mismatch")
        active = int(
            conn.execute("SELECT COUNT(*) AS n FROM validator_governance_validators").fetchone()["n"]
        )
    if active < 1:
        raise SchemaMigrationV21Error("v0.21 migration did not initialize validator governance state")

    rollback_verified = False
    if verify_rollback and source_version in {19, 20}:
        with tempfile.TemporaryDirectory(prefix="crakbit-v21-rollback-") as tmp:
            rollback_db = Path(tmp) / "rollback.sqlite3"
            _backup(output_db, rollback_db)
            with _connect(rollback_db) as conn:
                _rollback_to_v20(conn)
            rollback_verified = (
                detect_schema_version(rollback_db) == 20
                and core_state_fingerprint(rollback_db) == source_fingerprint
            )
            if not rollback_verified:
                raise SchemaMigrationV21Error("v0.21 rollback verification failed")

    return {
        "source": str(source_db),
        "output": str(output_db),
        "source_schema_version": source_version,
        "target_schema_version": 21,
        "migration_applied": migrated,
        "core_state_fingerprint": source_fingerprint,
        "rollback_verified": rollback_verified,
        "source_modified": False,
        "live_node_upgraded": False,
        "production_mainnet_ready": False,
    }


def dry_run_v21_migration(
    *, genesis_path: str | Path, source: str | Path
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="crakbit-v21-migration-") as tmp:
        report = migrate_to_v21_copy(
            genesis_path=genesis_path,
            source=source,
            output=Path(tmp) / "chain.sqlite3",
            overwrite=False,
            verify_rollback=True,
        )
        report.pop("output", None)
        report["dry_run"] = True
        report["temporary_output_removed"] = True
        return report
