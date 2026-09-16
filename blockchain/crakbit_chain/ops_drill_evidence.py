from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .crypto import KeyPair, address_from_public_key, canonical_json, sha256_hex, verify_signature


DRILL_FORMAT = "crakbit-operations-drill-evidence/1"
DRILL_KINDS = {"upgrade", "rollback", "incident-response", "disaster-recovery", "validator-lifecycle"}


class OperationsDrillError(ValueError):
    pass


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_commit(value: str) -> bool:
    value = str(value).strip().lower()
    return len(value) in {40, 64} and all(ch in "0123456789abcdef" for ch in value)


def build_drill_evidence(
    *,
    signing_key_path: str | Path,
    source_commit: str,
    kind: str,
    started_at_ms: int,
    completed_at_ms: int,
    success: bool,
    summary: str,
    evidence_paths: Iterable[str | Path] = (),
) -> dict[str, Any]:
    commit = str(source_commit).strip().lower()
    if not _valid_commit(commit):
        raise OperationsDrillError("source_commit must be an exact hexadecimal Git commit SHA")
    kind = str(kind).strip().lower()
    if kind not in DRILL_KINDS:
        raise OperationsDrillError(f"unsupported drill kind: {kind}")
    if int(started_at_ms) < 0 or int(completed_at_ms) < int(started_at_ms):
        raise OperationsDrillError("invalid drill time range")
    if not str(summary).strip():
        raise OperationsDrillError("summary is required")

    artifacts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in evidence_paths:
        path = Path(raw)
        if not path.is_file():
            raise OperationsDrillError(f"drill evidence file not found: {path}")
        if path.name in seen:
            raise OperationsDrillError(f"duplicate drill evidence filename: {path.name}")
        seen.add(path.name)
        artifacts.append(
            {
                "name": path.name,
                "size": path.stat().st_size,
                "sha256": _file_sha256(path),
            }
        )
    artifacts.sort(key=lambda item: item["name"])

    key = KeyPair.load(signing_key_path)
    manifest = {
        "format": DRILL_FORMAT,
        "source_commit": commit,
        "kind": kind,
        "started_at_ms": int(started_at_ms),
        "completed_at_ms": int(completed_at_ms),
        "success": bool(success),
        "summary": str(summary).strip(),
        "evidence": artifacts,
        "claims": {
            "operator_reported_success": bool(success),
            "independently_verified": False,
            "production_mainnet_ready": False,
        },
    }
    payload = canonical_json(manifest)
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_hex(payload),
        "signer": key.address,
        "public_key": key.public_key_b64,
        "signature": key.sign(payload),
    }


def verify_drill_evidence(
    envelope: dict[str, Any],
    *,
    evidence_directory: str | Path | None = None,
    expected_signer: str | None = None,
) -> dict[str, Any]:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("manifest"), dict):
        raise OperationsDrillError("invalid drill evidence envelope")
    manifest = envelope["manifest"]
    if manifest.get("format") != DRILL_FORMAT:
        raise OperationsDrillError("unsupported drill evidence format")
    if manifest.get("kind") not in DRILL_KINDS:
        raise OperationsDrillError("unsupported drill evidence kind")
    if not _valid_commit(str(manifest.get("source_commit", ""))):
        raise OperationsDrillError("drill evidence source commit is invalid")

    payload = canonical_json(manifest)
    if str(envelope.get("manifest_sha256", "")) != sha256_hex(payload):
        raise OperationsDrillError("drill evidence manifest hash mismatch")
    public_key = str(envelope.get("public_key", ""))
    signer = str(envelope.get("signer", ""))
    if not public_key or address_from_public_key(public_key) != signer:
        raise OperationsDrillError("drill evidence signer identity mismatch")
    if expected_signer and signer != expected_signer:
        raise OperationsDrillError("drill evidence signer does not match expected signer")
    if not verify_signature(public_key, payload, str(envelope.get("signature", ""))):
        raise OperationsDrillError("invalid drill evidence signature")

    verified = 0
    if evidence_directory is not None:
        root = Path(evidence_directory)
        for item in manifest.get("evidence", []):
            name = str(item.get("name", ""))
            if not name or Path(name).name != name:
                raise OperationsDrillError("invalid drill evidence filename")
            path = root / name
            if not path.is_file():
                raise OperationsDrillError(f"drill evidence artifact missing: {name}")
            if path.stat().st_size != int(item.get("size", -1)):
                raise OperationsDrillError(f"drill evidence artifact size mismatch: {name}")
            if _file_sha256(path) != str(item.get("sha256", "")):
                raise OperationsDrillError(f"drill evidence artifact hash mismatch: {name}")
            verified += 1

    return {
        "valid": True,
        "kind": manifest["kind"],
        "success": bool(manifest.get("success")),
        "source_commit": manifest["source_commit"],
        "signer": signer,
        "verified_evidence_files": verified,
        "independently_verified": False,
        "production_mainnet_ready": False,
    }


def save_drill_evidence(envelope: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise OperationsDrillError(f"drill evidence already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    return target


def load_drill_evidence(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
