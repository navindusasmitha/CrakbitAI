from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any

from .crypto import canonical_json, sha256_hex
from .storage import LedgerError


SCHEMA_VERSION_KEY = "application_schema_version"
CURRENT_SCHEMA_VERSION = 20
BASELINE_EXTERNAL_SCHEMA_VERSION = 19
MIGRATION_ID_19_TO_20 = "external-app-19-to-20"
_V20_TABLES = {"crakbit_schema_migrations", "validator_lifecycle_drills"}


class SchemaMigrationError(LedgerError):
    pass


def resolve_db_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_dir():
        path = path / "chain.sqlite3"
    if not path.is_file():
        raise FileNotFoundError(f"application database not found: {path}")
    return path


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


def _metadata(conn: sqlite3.Connection, key: str) -> str | None:
    try:
        row = conn.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
    except sqlite3.OperationalError as exc:
        raise SchemaMigrationError("database does not contain Crakbit metadata") from exc
    return str(row["value"]) if row is not None else None


def detect_schema_version(path: str | Path) -> int:
    db = resolve_db_path(path)
    with _connect(db) as conn:
        owner = _metadata(conn, "execution_owner")
        if owner != "crakbit-execution/2":
            raise SchemaMigrationError("database is not a Crakbit external execution database")
        raw = _metadata(conn, SCHEMA_VERSION_KEY)
        if raw is None:
            # v0.19 and earlier external-application databases did not persist an
            # explicit schema version. Treat that exact owner as the v19 baseline.
            return BASELINE_EXTERNAL_SCHEMA_VERSION
        try:
            version = int(raw)
        except ValueError as exc:
            raise SchemaMigrationError("invalid application schema version metadata") from exc
        if version < 1:
            raise SchemaMigrationError("invalid application schema version")
        return version


def inspect_schema(path: str | Path) -> dict[str, Any]:
    db = resolve_db_path(path)
    with _connect(db) as conn:
        version = detect_schema_version(db)
        height = int(_metadata(conn, "height") or "0")
        fingerprint = _metadata(conn, "genesis_fingerprint") or ""
        owner = _metadata(conn, "execution_owner") or ""
        tables = [
            str(row["name"])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
    return {
        "database": str(db),
        "execution_owner": owner,
        "schema_version": version,
        "current_supported_schema_version": CURRENT_SCHEMA_VERSION,
        "height": height,
        "genesis_fingerprint": fingerprint,
        "tables": tables,
        "migration_required": version != CURRENT_SCHEMA_VERSION,
        "production_ready": False,
    }


def _normalize_cell(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"bytes_hex": value.hex()}
    if value is None or isinstance(value, (str, int, float)):
        return value
    return str(value)


def logical_database_fingerprint(path: str | Path) -> str:
    """Fingerprint pre-v20 application state without depending on SQLite file layout.

    v0.20 metadata/tables are intentionally excluded so a migration + rollback can be
    checked for logical preservation of the pre-upgrade database.
    """

    db = resolve_db_path(path)
    payload: list[dict[str, Any]] = []
    with _connect(db) as conn:
        tables = conn.execute(
            "SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        for table in tables:
            name = str(table["name"])
            if name in _V20_TABLES:
                continue
            columns = [
                str(row["name"])
                for row in conn.execute(f'PRAGMA table_info("{name}")').fetchall()
            ]
            quoted = ",".join('"' + col.replace('"', '""') + '"' for col in columns)
            rows = conn.execute(f'SELECT {quoted} FROM "{name}"').fetchall()
            encoded_rows: list[str] = []
            for row in rows:
                item = {col: _normalize_cell(row[col]) for col in columns}
                if name == "metadata" and item.get("key") == SCHEMA_VERSION_KEY:
                    continue
                encoded_rows.append(
                    json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                )
            encoded_rows.sort()
            payload.append(
                {
                    "table": name,
                    "schema": str(table["sql"] or ""),
                    "rows": encoded_rows,
                }
            )
    return sha256_hex(canonical_json(payload))


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sqlite_backup(source: Path, target: Path) -> None:
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


def _apply_19_to_20(conn: sqlite3.Connection, source_fingerprint: str) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS crakbit_schema_migrations (
            migration_id TEXT PRIMARY KEY,
            from_version INTEGER NOT NULL,
            to_version INTEGER NOT NULL,
            source_fingerprint TEXT NOT NULL,
            applied_at_ms INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS validator_lifecycle_drills (
            plan_hash TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            source_set_hash TEXT NOT NULL,
            target_set_hash TEXT NOT NULL,
            artifact_json TEXT NOT NULL,
            status TEXT NOT NULL,
            recorded_at_ms INTEGER NOT NULL
        );
        """
    )
    conn.execute(
        "INSERT INTO metadata(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (SCHEMA_VERSION_KEY, str(CURRENT_SCHEMA_VERSION)),
    )
    conn.execute(
        "INSERT OR REPLACE INTO crakbit_schema_migrations("
        "migration_id,from_version,to_version,source_fingerprint,applied_at_ms"
        ") VALUES(?,?,?,?,?)",
        (
            MIGRATION_ID_19_TO_20,
            BASELINE_EXTERNAL_SCHEMA_VERSION,
            CURRENT_SCHEMA_VERSION,
            source_fingerprint,
            int(time.time() * 1000),
        ),
    )


def _rollback_20_to_19(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM metadata WHERE key=?", (SCHEMA_VERSION_KEY,))
    conn.execute("DROP TABLE IF EXISTS validator_lifecycle_drills")
    conn.execute("DROP TABLE IF EXISTS crakbit_schema_migrations")


def migrate_database_copy(
    *,
    source: str | Path,
    output: str | Path,
    target_version: int = CURRENT_SCHEMA_VERSION,
    overwrite: bool = False,
    verify_rollback: bool = True,
) -> dict[str, Any]:
    source_db = resolve_db_path(source)
    output_db = Path(output)
    if output_db.exists() and not overwrite:
        raise SchemaMigrationError(f"migration output already exists: {output_db}")
    if target_version != CURRENT_SCHEMA_VERSION:
        raise SchemaMigrationError(f"v0.20 supports target schema {CURRENT_SCHEMA_VERSION} only")
    source_version = detect_schema_version(source_db)
    if source_version not in {BASELINE_EXTERNAL_SCHEMA_VERSION, CURRENT_SCHEMA_VERSION}:
        raise SchemaMigrationError(
            f"unsupported source schema {source_version}; expected 19 or 20"
        )

    source_fingerprint_before = logical_database_fingerprint(source_db)
    _sqlite_backup(source_db, output_db)
    source_fingerprint_after = logical_database_fingerprint(source_db)
    if source_fingerprint_before != source_fingerprint_after:
        output_db.unlink(missing_ok=True)
        raise SchemaMigrationError("source database changed while migration copy was created; retry offline")

    migrated = False
    if source_version == BASELINE_EXTERNAL_SCHEMA_VERSION:
        with _connect(output_db) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                _apply_19_to_20(conn, source_fingerprint_before)
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        migrated = True

    output_version = detect_schema_version(output_db)
    if output_version != target_version:
        raise SchemaMigrationError("migration output schema version mismatch")
    migrated_fingerprint = logical_database_fingerprint(output_db)
    if migrated_fingerprint != source_fingerprint_before:
        raise SchemaMigrationError("migration changed pre-existing logical application state")

    rollback_verified = False
    if verify_rollback:
        with tempfile.TemporaryDirectory(prefix="crakbit-v20-rollback-") as tmp:
            rollback_db = Path(tmp) / "rollback.sqlite3"
            _sqlite_backup(output_db, rollback_db)
            with _connect(rollback_db) as conn:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    _rollback_20_to_19(conn)
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
            rollback_verified = (
                detect_schema_version(rollback_db) == BASELINE_EXTERNAL_SCHEMA_VERSION
                and logical_database_fingerprint(rollback_db) == source_fingerprint_before
            )
            if not rollback_verified:
                raise SchemaMigrationError("rollback verification failed")

    return {
        "source": str(source_db),
        "output": str(output_db),
        "source_schema_version": source_version,
        "target_schema_version": target_version,
        "migration_applied": migrated,
        "source_logical_fingerprint": source_fingerprint_before,
        "output_logical_fingerprint": migrated_fingerprint,
        "output_file_sha256": _file_sha256(output_db),
        "rollback_verified": rollback_verified,
        "source_modified": False,
        "production_ready": False,
    }


def dry_run_migration(
    *,
    source: str | Path,
    target_version: int = CURRENT_SCHEMA_VERSION,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="crakbit-v20-migration-") as tmp:
        output = Path(tmp) / "migrated.sqlite3"
        report = migrate_database_copy(
            source=source,
            output=output,
            target_version=target_version,
            overwrite=False,
            verify_rollback=True,
        )
        report["dry_run"] = True
        report["temporary_output_removed"] = True
        report.pop("output", None)
        report.pop("output_file_sha256", None)
        return report
