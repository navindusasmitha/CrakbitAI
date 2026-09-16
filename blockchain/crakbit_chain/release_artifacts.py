from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Iterable

from .crypto import KeyPair, address_from_public_key, canonical_json, sha256_hex, verify_signature
from .genesis import Genesis


RELEASE_FORMAT = "crakbit-signed-release/1"


class ReleaseArtifactError(ValueError):
    pass


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_release_envelope(
    *,
    genesis_path: str | Path,
    signing_key_path: str | Path,
    version: str,
    artifact_paths: Iterable[str | Path] = (),
) -> dict:
    genesis_file = Path(genesis_path)
    genesis = Genesis.load(genesis_file)
    key = KeyPair.load(signing_key_path)

    artifacts: list[dict] = []
    seen_names: set[str] = set()
    for raw_path in artifact_paths:
        path = Path(raw_path)
        if not path.is_file():
            raise ReleaseArtifactError(f"release artifact not found: {path}")
        name = path.name
        if name in seen_names:
            raise ReleaseArtifactError(f"duplicate release artifact name: {name}")
        seen_names.add(name)
        artifacts.append(
            {
                "name": name,
                "size": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        )
    artifacts.sort(key=lambda item: item["name"])

    manifest = {
        "format": RELEASE_FORMAT,
        "version": str(version),
        "created_at_ms": int(time.time() * 1000),
        "chain_id": genesis.chain_id,
        "network_name": genesis.network_name,
        "genesis_fingerprint": genesis.fingerprint(),
        "genesis_file_sha256": file_sha256(genesis_file),
        "artifacts": artifacts,
    }
    payload = canonical_json(manifest)
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_hex(payload),
        "signer": key.address,
        "public_key": key.public_key_b64,
        "signature": key.sign(payload),
    }


def verify_release_envelope(
    envelope: dict,
    *,
    genesis_path: str | Path | None = None,
    expected_signer: str | None = None,
    artifact_directory: str | Path | None = None,
) -> dict:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("manifest"), dict):
        raise ReleaseArtifactError("invalid release envelope")
    manifest = envelope["manifest"]
    if manifest.get("format") != RELEASE_FORMAT:
        raise ReleaseArtifactError("unsupported release artifact format")
    payload = canonical_json(manifest)
    if envelope.get("manifest_sha256") != sha256_hex(payload):
        raise ReleaseArtifactError("release manifest hash mismatch")

    public_key = str(envelope.get("public_key", ""))
    signer = str(envelope.get("signer", ""))
    if not public_key or address_from_public_key(public_key) != signer:
        raise ReleaseArtifactError("release signer identity mismatch")
    if expected_signer and signer != expected_signer:
        raise ReleaseArtifactError("release signer does not match expected signer")
    if not verify_signature(public_key, payload, str(envelope.get("signature", ""))):
        raise ReleaseArtifactError("invalid release signature")

    if genesis_path is not None:
        genesis_file = Path(genesis_path)
        genesis = Genesis.load(genesis_file)
        if genesis.chain_id != manifest.get("chain_id"):
            raise ReleaseArtifactError("release chain_id does not match genesis")
        if genesis.fingerprint() != manifest.get("genesis_fingerprint"):
            raise ReleaseArtifactError("release genesis fingerprint mismatch")
        if file_sha256(genesis_file) != manifest.get("genesis_file_sha256"):
            raise ReleaseArtifactError("release genesis file hash mismatch")

    verified_artifacts = 0
    if artifact_directory is not None:
        root = Path(artifact_directory)
        for item in manifest.get("artifacts", []):
            name = str(item.get("name", ""))
            if not name or Path(name).name != name:
                raise ReleaseArtifactError("invalid release artifact name")
            path = root / name
            if not path.is_file():
                raise ReleaseArtifactError(f"release artifact missing: {name}")
            if path.stat().st_size != int(item.get("size", -1)):
                raise ReleaseArtifactError(f"release artifact size mismatch: {name}")
            if file_sha256(path) != str(item.get("sha256", "")):
                raise ReleaseArtifactError(f"release artifact hash mismatch: {name}")
            verified_artifacts += 1

    return {
        "valid": True,
        "format": RELEASE_FORMAT,
        "version": str(manifest.get("version", "")),
        "chain_id": str(manifest.get("chain_id", "")),
        "signer": signer,
        "manifest_sha256": envelope["manifest_sha256"],
        "declared_artifacts": len(manifest.get("artifacts", [])),
        "verified_artifacts": verified_artifacts,
        "genesis_verified": genesis_path is not None,
    }


def save_release_envelope(envelope: dict, path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise ReleaseArtifactError(f"release manifest already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    return target
