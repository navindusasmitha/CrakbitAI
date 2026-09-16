from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .crypto import KeyPair, address_from_public_key, canonical_json, sha256_hex, verify_signature


FORMAT = "crakbit-migration-evidence/1"


class MigrationEvidenceError(ValueError):
    pass


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_commit(value: str) -> str:
    commit = value.strip().lower()
    if len(commit) not in {40, 64} or any(ch not in "0123456789abcdef" for ch in commit):
        raise MigrationEvidenceError("source_commit must be an exact hexadecimal Git commit SHA")
    return commit


def build_migration_evidence(
    *,
    signing_key_path: str | Path,
    source_commit: str,
    report_path: str | Path,
) -> dict[str, Any]:
    report_file = Path(report_path)
    if not report_file.is_file():
        raise MigrationEvidenceError("upgrade rehearsal report was not found")
    report = json.loads(report_file.read_text(encoding="utf-8"))
    if report.get("format") != "crakbit-upgrade-rehearsal/1":
        raise MigrationEvidenceError("unsupported upgrade rehearsal report")
    migration = report.get("migration") or {}
    if migration.get("rollback_verified") is not True:
        raise MigrationEvidenceError("upgrade rehearsal did not verify rollback")
    if report.get("source_modified") is not False:
        raise MigrationEvidenceError("upgrade rehearsal must preserve the source database")

    signer = KeyPair.load(signing_key_path)
    manifest = {
        "format": FORMAT,
        "source_commit": _valid_commit(source_commit),
        "chain_id": str(report.get("chain_id", "")),
        "genesis_fingerprint": str(report.get("genesis_fingerprint", "")),
        "source_schema_version": int(migration.get("source_schema_version", 0)),
        "target_schema_version": int(migration.get("target_schema_version", 0)),
        "source_logical_fingerprint": str(migration.get("source_logical_fingerprint", "")),
        "output_logical_fingerprint": str(migration.get("output_logical_fingerprint", "")),
        "rollback_verified": True,
        "report": {
            "name": report_file.name,
            "size": report_file.stat().st_size,
            "sha256": _file_sha256(report_file),
        },
        "claims": {
            "offline_copy_migration_rehearsed": True,
            "live_production_upgrade_performed": False,
            "independent_review_completed": False,
            "production_mainnet_ready": False,
        },
    }
    payload = canonical_json(manifest)
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_hex(payload),
        "signer": signer.address,
        "public_key": signer.public_key_b64,
        "signature": signer.sign(payload),
    }


def verify_migration_evidence(
    envelope: dict[str, Any],
    *,
    report_directory: str | Path | None = None,
    expected_signer: str | None = None,
) -> dict[str, Any]:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("manifest"), dict):
        raise MigrationEvidenceError("invalid migration evidence")
    manifest = envelope["manifest"]
    if manifest.get("format") != FORMAT:
        raise MigrationEvidenceError("unsupported migration evidence format")
    payload = canonical_json(manifest)
    if str(envelope.get("manifest_sha256", "")) != sha256_hex(payload):
        raise MigrationEvidenceError("migration evidence manifest hash mismatch")
    public_key = str(envelope.get("public_key", ""))
    signer = str(envelope.get("signer", ""))
    if not public_key or address_from_public_key(public_key) != signer:
        raise MigrationEvidenceError("migration evidence signer identity mismatch")
    if expected_signer and signer != expected_signer:
        raise MigrationEvidenceError("migration evidence signer does not match expected signer")
    if not verify_signature(public_key, payload, str(envelope.get("signature", ""))):
        raise MigrationEvidenceError("invalid migration evidence signature")
    if manifest.get("rollback_verified") is not True:
        raise MigrationEvidenceError("migration evidence does not include rollback verification")

    report_verified = False
    if report_directory is not None:
        item = manifest.get("report") or {}
        name = str(item.get("name", ""))
        if not name or Path(name).name != name:
            raise MigrationEvidenceError("invalid migration report name")
        path = Path(report_directory) / name
        if not path.is_file():
            raise MigrationEvidenceError("migration report artifact missing")
        if path.stat().st_size != int(item.get("size", -1)):
            raise MigrationEvidenceError("migration report artifact size mismatch")
        if _file_sha256(path) != str(item.get("sha256", "")):
            raise MigrationEvidenceError("migration report artifact hash mismatch")
        report_verified = True

    return {
        "valid": True,
        "format": FORMAT,
        "source_commit": manifest["source_commit"],
        "source_schema_version": int(manifest["source_schema_version"]),
        "target_schema_version": int(manifest["target_schema_version"]),
        "rollback_verified": True,
        "report_verified": report_verified,
        "signer": signer,
        "production_mainnet_ready": False,
    }


def save_migration_evidence(envelope: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise MigrationEvidenceError(f"migration evidence already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    return target


def load_migration_evidence(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
