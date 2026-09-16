from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Iterable

from .crypto import KeyPair, address_from_public_key, canonical_json, sha256_hex, verify_signature
from .genesis import Genesis


REVIEW_FREEZE_FORMAT = "crakbit-review-candidate-freeze/1"


class ReviewFreezeError(ValueError):
    pass


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_commit(value: str) -> bool:
    value = value.strip().lower()
    return len(value) in {40, 64} and all(ch in "0123456789abcdef" for ch in value)


def build_review_freeze(
    *,
    genesis_path: str | Path,
    signing_key_path: str | Path,
    source_commit: str,
    package_version: str,
    cometbft_version: str,
    artifacts: Iterable[tuple[str, str | Path]] = (),
) -> dict:
    commit = str(source_commit).strip().lower()
    if not _valid_commit(commit):
        raise ReviewFreezeError("source_commit must be an exact hexadecimal Git commit SHA")
    if not str(package_version).strip():
        raise ReviewFreezeError("package_version is required")
    if not str(cometbft_version).strip():
        raise ReviewFreezeError("cometbft_version is required")

    genesis_file = Path(genesis_path)
    genesis = Genesis.load(genesis_file)
    key = KeyPair.load(signing_key_path)

    entries: list[dict] = []
    seen_roles: set[str] = set()
    seen_names: set[str] = set()
    for role, raw_path in artifacts:
        normalized_role = str(role).strip()
        if not normalized_role or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for ch in normalized_role.lower()):
            raise ReviewFreezeError(f"invalid review artifact role: {role}")
        if normalized_role in seen_roles:
            raise ReviewFreezeError(f"duplicate review artifact role: {normalized_role}")
        path = Path(raw_path)
        if not path.is_file():
            raise ReviewFreezeError(f"review artifact not found: {path}")
        name = path.name
        if name in seen_names:
            raise ReviewFreezeError(f"duplicate review artifact file name: {name}")
        seen_roles.add(normalized_role)
        seen_names.add(name)
        entries.append(
            {
                "role": normalized_role,
                "name": name,
                "size": path.stat().st_size,
                "sha256": _file_sha256(path),
            }
        )
    entries.sort(key=lambda item: (item["role"], item["name"]))

    manifest = {
        "format": REVIEW_FREEZE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": commit,
        "package_version": str(package_version).strip(),
        "cometbft_version": str(cometbft_version).strip(),
        "chain_id": genesis.chain_id,
        "network_name": genesis.network_name,
        "genesis_fingerprint": genesis.fingerprint(),
        "genesis_file_sha256": _file_sha256(genesis_file),
        "artifacts": entries,
        "claims": {
            "candidate_frozen_for_review": True,
            "independent_review_completed": False,
            "production_mainnet_ready": False,
            "production_crkbit_launched": False,
        },
        "required_external_gates": [
            "independent-host sustained operation",
            "live clean-host state-sync recovery evidence",
            "real fault/load campaign evidence",
            "protected validator signer deployment and drill",
            "independent consensus/application/network/wallet review",
            "final economics/incentives and applicable legal review",
        ],
    }
    payload = canonical_json(manifest)
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_hex(payload),
        "signer": key.address,
        "public_key": key.public_key_b64,
        "signature": key.sign(payload),
    }


def verify_review_freeze(
    envelope: dict,
    *,
    genesis_path: str | Path,
    artifact_directory: str | Path | None = None,
    expected_signer: str | None = None,
    expected_source_commit: str | None = None,
) -> dict:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("manifest"), dict):
        raise ReviewFreezeError("invalid review-freeze envelope")
    manifest = envelope["manifest"]
    if manifest.get("format") != REVIEW_FREEZE_FORMAT:
        raise ReviewFreezeError("unsupported review-freeze format")
    source_commit = str(manifest.get("source_commit", "")).lower()
    if not _valid_commit(source_commit):
        raise ReviewFreezeError("review-freeze source commit is invalid")
    if expected_source_commit and source_commit != str(expected_source_commit).strip().lower():
        raise ReviewFreezeError("review-freeze source commit does not match expected commit")

    claims = manifest.get("claims")
    if not isinstance(claims, dict):
        raise ReviewFreezeError("review-freeze claims are missing")
    if claims.get("production_mainnet_ready") is not False:
        raise ReviewFreezeError("review-freeze may not claim production mainnet readiness")
    if claims.get("independent_review_completed") is not False:
        raise ReviewFreezeError("review-freeze may not claim completed independent review")
    if claims.get("production_crkbit_launched") is not False:
        raise ReviewFreezeError("review-freeze may not claim production CRKBIT launch")

    payload = canonical_json(manifest)
    if str(envelope.get("manifest_sha256")) != sha256_hex(payload):
        raise ReviewFreezeError("review-freeze manifest hash mismatch")
    public_key = str(envelope.get("public_key", ""))
    signer = str(envelope.get("signer", ""))
    if not public_key or address_from_public_key(public_key) != signer:
        raise ReviewFreezeError("review-freeze signer identity mismatch")
    if expected_signer and signer != expected_signer:
        raise ReviewFreezeError("review-freeze signer does not match expected signer")
    if not verify_signature(public_key, payload, str(envelope.get("signature", ""))):
        raise ReviewFreezeError("invalid review-freeze signature")

    genesis_file = Path(genesis_path)
    genesis = Genesis.load(genesis_file)
    if manifest.get("chain_id") != genesis.chain_id:
        raise ReviewFreezeError("review-freeze chain_id does not match genesis")
    if manifest.get("genesis_fingerprint") != genesis.fingerprint():
        raise ReviewFreezeError("review-freeze genesis fingerprint mismatch")
    if manifest.get("genesis_file_sha256") != _file_sha256(genesis_file):
        raise ReviewFreezeError("review-freeze genesis file hash mismatch")

    verified_artifacts = 0
    if artifact_directory is not None:
        root = Path(artifact_directory)
        for item in manifest.get("artifacts", []):
            name = str(item.get("name", ""))
            if not name or Path(name).name != name:
                raise ReviewFreezeError("invalid review artifact file name")
            path = root / name
            if not path.is_file():
                raise ReviewFreezeError(f"review artifact missing: {name}")
            if path.stat().st_size != int(item.get("size", -1)):
                raise ReviewFreezeError(f"review artifact size mismatch: {name}")
            if _file_sha256(path) != str(item.get("sha256", "")):
                raise ReviewFreezeError(f"review artifact hash mismatch: {name}")
            verified_artifacts += 1

    return {
        "valid": True,
        "format": REVIEW_FREEZE_FORMAT,
        "source_commit": source_commit,
        "package_version": str(manifest.get("package_version", "")),
        "cometbft_version": str(manifest.get("cometbft_version", "")),
        "chain_id": manifest["chain_id"],
        "signer": signer,
        "declared_artifacts": len(manifest.get("artifacts", [])),
        "verified_artifacts": verified_artifacts,
        "candidate_frozen_for_review": True,
        "independent_review_completed": False,
        "production_mainnet_ready": False,
    }


def save_review_freeze(envelope: dict, path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise ReviewFreezeError(f"review-freeze file already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    return target


def load_review_freeze(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
