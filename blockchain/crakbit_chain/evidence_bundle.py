from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Iterable

from .crypto import KeyPair, address_from_public_key, canonical_json, sha256_hex, verify_signature
from .genesis import Genesis


EVIDENCE_FORMAT = "crakbit-public-testnet-evidence/1"


class EvidenceBundleError(ValueError):
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


def build_evidence_bundle(
    *,
    genesis_path: str | Path,
    signing_key_path: str | Path,
    source_commit: str,
    cometbft_version: str,
    evidence_paths: Iterable[str | Path],
    release_manifest_path: str | Path | None = None,
) -> dict:
    commit = source_commit.strip().lower()
    if not _valid_commit(commit):
        raise EvidenceBundleError("source_commit must be an exact hexadecimal Git commit SHA")
    if not str(cometbft_version).strip():
        raise EvidenceBundleError("cometbft_version is required")

    genesis_file = Path(genesis_path)
    genesis = Genesis.load(genesis_file)
    key = KeyPair.load(signing_key_path)

    files: list[dict] = []
    seen: set[str] = set()
    for raw in evidence_paths:
        path = Path(raw)
        if not path.is_file():
            raise EvidenceBundleError(f"evidence file not found: {path}")
        name = path.name
        if name in seen:
            raise EvidenceBundleError(f"duplicate evidence file name: {name}")
        seen.add(name)
        files.append({"name": name, "size": path.stat().st_size, "sha256": _file_sha256(path)})
    files.sort(key=lambda item: item["name"])

    release_manifest = None
    if release_manifest_path is not None:
        release_path = Path(release_manifest_path)
        if not release_path.is_file():
            raise EvidenceBundleError("release manifest was not found")
        release_manifest = {
            "name": release_path.name,
            "size": release_path.stat().st_size,
            "sha256": _file_sha256(release_path),
        }

    manifest = {
        "format": EVIDENCE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": commit,
        "cometbft_version": str(cometbft_version).strip(),
        "chain_id": genesis.chain_id,
        "network_name": genesis.network_name,
        "genesis_fingerprint": genesis.fingerprint(),
        "genesis_file_sha256": _file_sha256(genesis_file),
        "release_manifest": release_manifest,
        "evidence": files,
        "claims": {
            "independent_host_operation_verified": False,
            "independent_security_review_completed": False,
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


def verify_evidence_bundle(
    envelope: dict,
    *,
    genesis_path: str | Path,
    evidence_directory: str | Path | None = None,
    expected_signer: str | None = None,
) -> dict:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("manifest"), dict):
        raise EvidenceBundleError("invalid evidence bundle")
    manifest = envelope["manifest"]
    if manifest.get("format") != EVIDENCE_FORMAT:
        raise EvidenceBundleError("unsupported evidence bundle format")
    if not _valid_commit(str(manifest.get("source_commit", ""))):
        raise EvidenceBundleError("evidence bundle source commit is invalid")

    payload = canonical_json(manifest)
    if str(envelope.get("manifest_sha256")) != sha256_hex(payload):
        raise EvidenceBundleError("evidence bundle manifest hash mismatch")
    public_key = str(envelope.get("public_key", ""))
    signer = str(envelope.get("signer", ""))
    if not public_key or address_from_public_key(public_key) != signer:
        raise EvidenceBundleError("evidence signer identity mismatch")
    if expected_signer and signer != expected_signer:
        raise EvidenceBundleError("evidence signer does not match expected signer")
    if not verify_signature(public_key, payload, str(envelope.get("signature", ""))):
        raise EvidenceBundleError("invalid evidence bundle signature")

    genesis_file = Path(genesis_path)
    genesis = Genesis.load(genesis_file)
    if manifest.get("chain_id") != genesis.chain_id:
        raise EvidenceBundleError("evidence chain_id does not match genesis")
    if manifest.get("genesis_fingerprint") != genesis.fingerprint():
        raise EvidenceBundleError("evidence genesis fingerprint mismatch")
    if manifest.get("genesis_file_sha256") != _file_sha256(genesis_file):
        raise EvidenceBundleError("evidence genesis file hash mismatch")

    verified = 0
    if evidence_directory is not None:
        root = Path(evidence_directory)
        for item in manifest.get("evidence", []):
            name = str(item.get("name", ""))
            if not name or Path(name).name != name:
                raise EvidenceBundleError("invalid evidence artifact name")
            path = root / name
            if not path.is_file():
                raise EvidenceBundleError(f"evidence artifact missing: {name}")
            if path.stat().st_size != int(item.get("size", -1)):
                raise EvidenceBundleError(f"evidence artifact size mismatch: {name}")
            if _file_sha256(path) != str(item.get("sha256", "")):
                raise EvidenceBundleError(f"evidence artifact hash mismatch: {name}")
            verified += 1

    return {
        "valid": True,
        "format": EVIDENCE_FORMAT,
        "source_commit": manifest["source_commit"],
        "cometbft_version": manifest["cometbft_version"],
        "chain_id": manifest["chain_id"],
        "signer": signer,
        "declared_evidence_files": len(manifest.get("evidence", [])),
        "verified_evidence_files": verified,
        "production_mainnet_ready": False,
    }


def save_evidence_bundle(envelope: dict, path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise EvidenceBundleError(f"evidence bundle already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    return target


def load_evidence_bundle(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
