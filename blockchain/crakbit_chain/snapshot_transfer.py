from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Iterable

from .crypto import canonical_json, sha256_hex
from .storage import LedgerError

BUNDLE_FORMAT = "crakbit-snapshot-bundle-v1"
DEFAULT_CHUNK_SIZE = 64 * 1024
MAX_CHUNK_SIZE = 1024 * 1024
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_CHUNKS = 4096


def build_snapshot_bundle(
    artifact: dict[str, Any],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    max_total_bytes: int = MAX_ARTIFACT_BYTES,
) -> tuple[dict[str, Any], list[bytes]]:
    """Split a signed snapshot artifact into independently hashed chunks.

    The serialized artifact is canonical JSON so all nodes derive the same byte stream for
    the same signed envelope/certificate. The manifest commits to every chunk and to the
    complete artifact. This is transport framing only; snapshot trust still comes from the
    validator signatures verified by the snapshot layer.
    """

    chunk_size = int(chunk_size)
    max_total_bytes = int(max_total_bytes)
    if chunk_size < 1024 or chunk_size > MAX_CHUNK_SIZE:
        raise LedgerError(f"snapshot chunk size must be between 1024 and {MAX_CHUNK_SIZE} bytes")

    raw = canonical_json(artifact)
    if len(raw) > max_total_bytes:
        raise LedgerError("snapshot artifact exceeds configured transfer size limit")

    chunks = [raw[offset : offset + chunk_size] for offset in range(0, len(raw), chunk_size)]
    if not chunks:
        chunks = [b"{}"]
    if len(chunks) > MAX_CHUNKS:
        raise LedgerError("snapshot artifact requires too many transfer chunks")

    entries = [
        {
            "index": index,
            "size": len(chunk),
            "sha256": sha256_hex(chunk),
        }
        for index, chunk in enumerate(chunks)
    ]
    manifest = {
        "format": BUNDLE_FORMAT,
        "artifact_sha256": sha256_hex(raw),
        "total_bytes": len(raw),
        "chunk_size": chunk_size,
        "total_chunks": len(chunks),
        "chunks": entries,
    }
    return manifest, chunks


def validate_manifest(manifest: dict[str, Any], *, max_total_bytes: int = MAX_ARTIFACT_BYTES) -> None:
    if manifest.get("format") != BUNDLE_FORMAT:
        raise LedgerError("unsupported snapshot bundle format")
    try:
        total_bytes = int(manifest["total_bytes"])
        chunk_size = int(manifest["chunk_size"])
        total_chunks = int(manifest["total_chunks"])
    except (KeyError, TypeError, ValueError) as exc:
        raise LedgerError("invalid snapshot bundle manifest") from exc

    if total_bytes < 2 or total_bytes > int(max_total_bytes):
        raise LedgerError("snapshot bundle total size outside accepted limits")
    if chunk_size < 1024 or chunk_size > MAX_CHUNK_SIZE:
        raise LedgerError("snapshot bundle chunk size outside accepted limits")
    if total_chunks < 1 or total_chunks > MAX_CHUNKS:
        raise LedgerError("snapshot bundle chunk count outside accepted limits")

    entries = list(manifest.get("chunks") or [])
    if len(entries) != total_chunks:
        raise LedgerError("snapshot bundle manifest chunk count mismatch")
    expected_indices = list(range(total_chunks))
    actual_indices = [int(item.get("index", -1)) for item in entries]
    if actual_indices != expected_indices:
        raise LedgerError("snapshot bundle chunk indices are not contiguous")
    if sum(int(item.get("size", -1)) for item in entries) != total_bytes:
        raise LedgerError("snapshot bundle manifest byte count mismatch")
    if len(str(manifest.get("artifact_sha256") or "")) != 64:
        raise LedgerError("invalid snapshot bundle artifact hash")
    for item in entries:
        size = int(item.get("size", -1))
        if size < 1 or size > chunk_size:
            raise LedgerError("snapshot bundle chunk size entry invalid")
        if len(str(item.get("sha256") or "")) != 64:
            raise LedgerError("snapshot bundle chunk hash invalid")


def verify_snapshot_bundle(
    manifest: dict[str, Any],
    chunks: Iterable[bytes],
    *,
    max_total_bytes: int = MAX_ARTIFACT_BYTES,
) -> dict[str, Any]:
    validate_manifest(manifest, max_total_bytes=max_total_bytes)
    chunk_list = list(chunks)
    entries = list(manifest["chunks"])
    if len(chunk_list) != len(entries):
        raise LedgerError("snapshot bundle is incomplete")

    for entry, chunk in zip(entries, chunk_list):
        if len(chunk) != int(entry["size"]):
            raise LedgerError(f"snapshot bundle chunk {entry['index']} size mismatch")
        if sha256_hex(chunk) != str(entry["sha256"]):
            raise LedgerError(f"snapshot bundle chunk {entry['index']} hash mismatch")

    raw = b"".join(chunk_list)
    if len(raw) != int(manifest["total_bytes"]):
        raise LedgerError("snapshot bundle reconstructed size mismatch")
    if sha256_hex(raw) != str(manifest["artifact_sha256"]):
        raise LedgerError("snapshot bundle artifact hash mismatch")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LedgerError("snapshot bundle payload is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise LedgerError("snapshot bundle payload must be a JSON object")
    return value


def chunk_response(manifest: dict[str, Any], chunks: list[bytes], index: int) -> dict[str, Any]:
    validate_manifest(manifest)
    index = int(index)
    if index < 0 or index >= len(chunks):
        raise LedgerError("snapshot chunk index out of range")
    entry = manifest["chunks"][index]
    chunk = chunks[index]
    return {
        "artifact_sha256": manifest["artifact_sha256"],
        "index": index,
        "size": len(chunk),
        "sha256": entry["sha256"],
        "data_b64": base64.b64encode(chunk).decode("ascii"),
    }


def decode_chunk_response(payload: dict[str, Any], expected: dict[str, Any], artifact_sha256: str) -> bytes:
    if str(payload.get("artifact_sha256") or "") != artifact_sha256:
        raise LedgerError("snapshot chunk belongs to a different artifact")
    if int(payload.get("index", -1)) != int(expected["index"]):
        raise LedgerError("snapshot chunk index mismatch")
    try:
        chunk = base64.b64decode(str(payload.get("data_b64") or ""), validate=True)
    except Exception as exc:
        raise LedgerError("snapshot chunk base64 is invalid") from exc
    if len(chunk) != int(expected["size"]):
        raise LedgerError("snapshot chunk response size mismatch")
    if sha256_hex(chunk) != str(expected["sha256"]):
        raise LedgerError("snapshot chunk response hash mismatch")
    return chunk


def save_bundle_cache(cache_dir: str | Path, manifest: dict[str, Any], chunks: list[bytes]) -> Path:
    validate_manifest(manifest)
    target = Path(cache_dir) / str(manifest["artifact_sha256"])
    target.mkdir(parents=True, exist_ok=True)
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for entry, chunk in zip(manifest["chunks"], chunks):
        (target / f"{int(entry['index']):06d}.part").write_bytes(chunk)
    return target


def load_cached_chunks(bundle_dir: str | Path, manifest: dict[str, Any]) -> tuple[list[bytes | None], int]:
    """Return verified cached chunks and a count of chunks that can be resumed."""

    validate_manifest(manifest)
    root = Path(bundle_dir)
    cached: list[bytes | None] = []
    valid = 0
    for entry in manifest["chunks"]:
        path = root / f"{int(entry['index']):06d}.part"
        if not path.exists():
            cached.append(None)
            continue
        chunk = path.read_bytes()
        if len(chunk) == int(entry["size"]) and sha256_hex(chunk) == str(entry["sha256"]):
            cached.append(chunk)
            valid += 1
        else:
            cached.append(None)
    return cached, valid
