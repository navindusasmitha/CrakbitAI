from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from .genesis import Genesis
from .integrity import verify_ledger_integrity
from .storage import Ledger, LedgerError

BACKUP_MANIFEST_FORMAT = "crakbit-ledger-backup-v1"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _metadata_from_db(path: Path, key: str) -> str | None:
    with sqlite3.connect(path, timeout=30) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        return str(row["value"]) if row is not None else None


def create_ledger_backup(
    ledger: Ledger,
    output: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create an online SQLite backup plus a cryptographic manifest.

    SQLite's backup API captures a consistent database image while the source remains live.
    The resulting copy is integrity-checked before its manifest is emitted.
    """

    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        raise LedgerError(f"backup target already exists: {target}")

    tmp = target.with_name(target.name + ".tmp")
    manifest_path = target.with_name(target.name + ".manifest.json")
    if tmp.exists():
        tmp.unlink()

    source = sqlite3.connect(ledger.db_path, timeout=30)
    destination = sqlite3.connect(tmp, timeout=30)
    try:
        source.backup(destination)
        destination.commit()
    finally:
        destination.close()
        source.close()

    # Open through Ledger so the same schema/genesis checks used by a node are applied.
    backup_ledger = Ledger(tmp, ledger.genesis)
    integrity = verify_ledger_integrity(backup_ledger, full=True)
    if not integrity["ok"]:
        tmp.unlink(missing_ok=True)
        raise LedgerError("refusing to publish backup that failed integrity verification")

    if target.exists():
        target.unlink()
    os.replace(tmp, target)

    height_raw = _metadata_from_db(target, "height")
    last_hash = _metadata_from_db(target, "last_hash")
    snapshot_base_height = _metadata_from_db(target, "snapshot_base_height")
    manifest = {
        "format": BACKUP_MANIFEST_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "chain_id": ledger.genesis.chain_id,
        "genesis_fingerprint": ledger.genesis.fingerprint(),
        "height": int(height_raw or 0),
        "last_hash": last_hash,
        "snapshot_base_height": int(snapshot_base_height) if snapshot_base_height is not None else None,
        "database_file": target.name,
        "database_bytes": target.stat().st_size,
        "database_sha256": sha256_file(target),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"backup": str(target), "manifest": str(manifest_path), **manifest}


def verify_ledger_backup(
    backup: str | Path,
    manifest: str | Path,
    genesis: Genesis,
    *,
    full: bool = True,
) -> dict[str, Any]:
    backup_path = Path(backup)
    manifest_path = Path(manifest)
    errors: list[str] = []

    if not backup_path.is_file():
        raise LedgerError(f"backup file not found: {backup_path}")
    if not manifest_path.is_file():
        raise LedgerError(f"backup manifest not found: {manifest_path}")

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise LedgerError(f"invalid backup manifest: {exc}") from exc

    if data.get("format") != BACKUP_MANIFEST_FORMAT:
        errors.append("unsupported backup manifest format")
    if data.get("chain_id") != genesis.chain_id:
        errors.append("backup manifest chain_id mismatch")
    if data.get("genesis_fingerprint") != genesis.fingerprint():
        errors.append("backup manifest genesis fingerprint mismatch")

    actual_size = backup_path.stat().st_size
    actual_hash = sha256_file(backup_path)
    if int(data.get("database_bytes", -1)) != actual_size:
        errors.append("backup file size does not match manifest")
    if str(data.get("database_sha256") or "") != actual_hash:
        errors.append("backup SHA-256 does not match manifest")

    integrity: dict[str, Any] | None = None
    if not errors:
        try:
            ledger = Ledger(backup_path, genesis)
            integrity = verify_ledger_integrity(ledger, full=full)
            if not integrity["ok"]:
                errors.extend(f"integrity: {item}" for item in integrity["errors"])
            if int(data.get("height", -1)) != ledger.height:
                errors.append("backup manifest height does not match database")
            if str(data.get("last_hash") or "") != ledger.last_hash:
                errors.append("backup manifest last_hash does not match database")
        except Exception as exc:
            errors.append(f"backup database validation failed: {type(exc).__name__}: {exc}")

    return {
        "ok": not errors,
        "backup": str(backup_path),
        "manifest": str(manifest_path),
        "database_bytes": actual_size,
        "database_sha256": actual_hash,
        "errors": errors,
        "integrity": integrity,
    }
