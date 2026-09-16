from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Iterable

from .crypto import KeyPair, address_from_public_key, canonical_json, sha256_hex, verify_signature
from .genesis import Genesis
from .reproducible_build import REPRO_FORMAT


PROVENANCE_FORMAT = "crakbit-release-provenance/1"


class ReleaseProvenanceError(ValueError):
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


def _artifact_record(role: str, path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ReleaseProvenanceError(f"release artifact not found: {path}")
    return {
        "role": role,
        "name": path.name,
        "size": path.stat().st_size,
        "sha256": _file_sha256(path),
    }


def build_release_provenance(
    *,
    genesis_path: str | Path,
    signing_key_path: str | Path,
    source_commit: str,
    package_version: str,
    cometbft_version: str,
    artifacts: Iterable[tuple[str, str | Path]] = (),
    sbom_path: str | Path | None = None,
    reproducibility_report_path: str | Path | None = None,
) -> dict[str, Any]:
    commit = str(source_commit).strip().lower()
    if not _valid_commit(commit):
        raise ReleaseProvenanceError("source_commit must be an exact hexadecimal Git commit SHA")
    package_version = str(package_version).strip()
    cometbft_version = str(cometbft_version).strip()
    if not package_version or not cometbft_version:
        raise ReleaseProvenanceError("package_version and cometbft_version are required")

    genesis_file = Path(genesis_path)
    genesis = Genesis.load(genesis_file)
    key = KeyPair.load(signing_key_path)

    records: list[dict[str, Any]] = []
    seen_roles: set[str] = set()
    seen_names: set[str] = set()
    for raw_role, raw_path in artifacts:
        role = str(raw_role).strip()
        path = Path(raw_path)
        if not role:
            raise ReleaseProvenanceError("artifact role cannot be empty")
        if role in seen_roles:
            raise ReleaseProvenanceError(f"duplicate artifact role: {role}")
        if path.name in seen_names:
            raise ReleaseProvenanceError(f"duplicate artifact filename: {path.name}")
        seen_roles.add(role)
        seen_names.add(path.name)
        records.append(_artifact_record(role, path))

    sbom = None
    if sbom_path is not None:
        path = Path(sbom_path)
        sbom = _artifact_record("sbom", path)

    repro = None
    reproducible_verified = False
    if reproducibility_report_path is not None:
        path = Path(reproducibility_report_path)
        repro = _artifact_record("reproducibility-report", path)
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ReleaseProvenanceError("reproducibility report is not valid JSON") from exc
        if report.get("format") != REPRO_FORMAT:
            raise ReleaseProvenanceError("unsupported reproducibility report format")
        reproducible_verified = bool(report.get("reproducible"))

    manifest = {
        "format": PROVENANCE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": commit,
        "package_version": package_version,
        "cometbft_version": cometbft_version,
        "chain_id": genesis.chain_id,
        "network_name": genesis.network_name,
        "genesis_fingerprint": genesis.fingerprint(),
        "genesis_file_sha256": _file_sha256(genesis_file),
        "artifacts": sorted(records, key=lambda item: item["role"]),
        "sbom": sbom,
        "reproducibility_report": repro,
        "claims": {
            "supplied_artifacts_hash_bound": True,
            "supplied_artifacts_reproducible": reproducible_verified,
            "independent_security_review_completed": False,
            "production_mainnet_ready": False,
            "production_crkbit_launched": False,
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


def verify_release_provenance(
    envelope: dict[str, Any],
    *,
    genesis_path: str | Path,
    artifact_directory: str | Path | None = None,
    expected_signer: str | None = None,
    expected_source_commit: str | None = None,
) -> dict[str, Any]:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("manifest"), dict):
        raise ReleaseProvenanceError("invalid release provenance envelope")
    manifest = envelope["manifest"]
    if manifest.get("format") != PROVENANCE_FORMAT:
        raise ReleaseProvenanceError("unsupported release provenance format")
    payload = canonical_json(manifest)
    if str(envelope.get("manifest_sha256", "")) != sha256_hex(payload):
        raise ReleaseProvenanceError("release provenance manifest hash mismatch")

    public_key = str(envelope.get("public_key", ""))
    signer = str(envelope.get("signer", ""))
    if not public_key or address_from_public_key(public_key) != signer:
        raise ReleaseProvenanceError("release provenance signer identity mismatch")
    if expected_signer and signer != expected_signer:
        raise ReleaseProvenanceError("release provenance signer does not match expected signer")
    if not verify_signature(public_key, payload, str(envelope.get("signature", ""))):
        raise ReleaseProvenanceError("invalid release provenance signature")

    source_commit = str(manifest.get("source_commit", ""))
    if not _valid_commit(source_commit):
        raise ReleaseProvenanceError("release provenance source commit is invalid")
    if expected_source_commit and source_commit != str(expected_source_commit).strip().lower():
        raise ReleaseProvenanceError("release provenance source commit mismatch")

    genesis_file = Path(genesis_path)
    genesis = Genesis.load(genesis_file)
    if manifest.get("chain_id") != genesis.chain_id:
        raise ReleaseProvenanceError("release provenance chain_id does not match genesis")
    if manifest.get("genesis_fingerprint") != genesis.fingerprint():
        raise ReleaseProvenanceError("release provenance genesis fingerprint mismatch")
    if manifest.get("genesis_file_sha256") != _file_sha256(genesis_file):
        raise ReleaseProvenanceError("release provenance genesis file hash mismatch")

    verified_artifacts = 0
    if artifact_directory is not None:
        root = Path(artifact_directory)
        records = list(manifest.get("artifacts", []))
        for optional_name in ("sbom", "reproducibility_report"):
            value = manifest.get(optional_name)
            if isinstance(value, dict):
                records.append(value)
        for record in records:
            name = str(record.get("name", ""))
            if not name or Path(name).name != name:
                raise ReleaseProvenanceError("invalid provenance artifact filename")
            path = root / name
            if not path.is_file():
                raise ReleaseProvenanceError(f"provenance artifact missing: {name}")
            if path.stat().st_size != int(record.get("size", -1)):
                raise ReleaseProvenanceError(f"provenance artifact size mismatch: {name}")
            if _file_sha256(path) != str(record.get("sha256", "")):
                raise ReleaseProvenanceError(f"provenance artifact hash mismatch: {name}")
            verified_artifacts += 1

    claims = manifest.get("claims", {})
    return {
        "valid": True,
        "source_commit": source_commit,
        "package_version": str(manifest.get("package_version", "")),
        "cometbft_version": str(manifest.get("cometbft_version", "")),
        "signer": signer,
        "verified_artifacts": verified_artifacts,
        "supplied_artifacts_reproducible": bool(claims.get("supplied_artifacts_reproducible", False)),
        "independent_security_review_completed": False,
        "production_mainnet_ready": False,
    }


def save_release_provenance(envelope: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise ReleaseProvenanceError(f"release provenance already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    return target


def load_release_provenance(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
