from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path
from typing import Any

from .crypto import canonical_json, sha256_hex
from .external_state_sync import (
    export_external_snapshot,
    import_external_snapshot,
    verify_external_snapshot,
)
from .genesis import Genesis
from .storage import Ledger, LedgerError


COMET_SNAPSHOT_FORMAT = 1
DEFAULT_CHUNK_BYTES = 1024 * 1024
MAX_CHUNK_BYTES = 8 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 512 * 1024 * 1024
STATE_SYNC_PROTOCOL = "crakbit-comet-state-sync/1"


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(value: str) -> bytes:
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except Exception as exc:  # noqa: BLE001
        raise LedgerError("invalid base64 in CometBFT snapshot request") from exc


def _hex64(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in value)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LedgerError(f"invalid state-sync metadata: {path}") from exc


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class CometStateSyncManager:
    """Materialize and restore deterministic application snapshots for CometBFT ABCI state sync.

    Snapshot metadata is untrusted until CometBFT supplies a light-client-verified app hash.
    Restoration therefore requires the offered app hash to match the deterministic Crakbit
    application hash embedded in the snapshot metadata and again verifies the full state before
    importing it into a pristine external application database.
    """

    def __init__(
        self,
        *,
        genesis: Genesis,
        data_dir: str | Path,
        chunk_bytes: int = DEFAULT_CHUNK_BYTES,
    ):
        self.genesis = genesis
        self.data_dir = Path(data_dir)
        self.chunk_bytes = int(chunk_bytes)
        if self.chunk_bytes <= 0 or self.chunk_bytes > MAX_CHUNK_BYTES:
            raise ValueError(f"state-sync chunk size must be between 1 and {MAX_CHUNK_BYTES} bytes")
        self.root = self.data_dir / "state-sync"
        self.snapshots_dir = self.root / "snapshots"
        self.incoming_dir = self.root / "incoming"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.incoming_dir.mkdir(parents=True, exist_ok=True)

    @property
    def ledger(self) -> Ledger:
        return Ledger(self.data_dir / "chain.sqlite3", self.genesis)

    @property
    def session_path(self) -> Path:
        return self.incoming_dir / "session.json"

    def _deterministic_envelope(self) -> dict[str, Any]:
        envelope = export_external_snapshot(self.ledger)
        snapshot = dict(envelope["snapshot"])
        # v0.16 included an export timestamp for operator artifacts. ABCI snapshots must be
        # byte-identical at the same state, so omit non-deterministic wall-clock metadata here.
        snapshot.pop("created_at_ms", None)
        deterministic = {
            "snapshot": snapshot,
            "artifact_hash": sha256_hex(canonical_json(snapshot)),
            "trust_model": "CometBFT light-client-verified application hash",
        }
        verify_external_snapshot(
            deterministic,
            self.genesis,
            expected_height=int(snapshot["height"]),
            expected_application_hash=str(snapshot["application_hash"]),
        )
        return deterministic

    def materialize_latest(self) -> dict[str, Any]:
        envelope = self._deterministic_envelope()
        snapshot = envelope["snapshot"]
        height = int(snapshot["height"])
        if height <= 0:
            raise LedgerError("CometBFT state-sync snapshots require a committed height greater than zero")

        payload = canonical_json(envelope)
        if len(payload) > MAX_SNAPSHOT_BYTES:
            raise LedgerError("state-sync snapshot exceeds configured maximum size")
        transport_hash = sha256_hex(payload)
        chunks = [
            payload[offset : offset + self.chunk_bytes]
            for offset in range(0, len(payload), self.chunk_bytes)
        ]
        if not chunks:
            chunks = [b""]
        chunk_hashes = [sha256_hex(item) for item in chunks]
        metadata = {
            "protocol": STATE_SYNC_PROTOCOL,
            "chain_id": self.genesis.chain_id,
            "genesis_fingerprint": self.genesis.fingerprint(),
            "height": height,
            "application_hash": str(snapshot["application_hash"]),
            "artifact_hash": str(envelope["artifact_hash"]),
            "transport_hash": transport_hash,
            "byte_length": len(payload),
            "chunk_bytes": self.chunk_bytes,
            "chunk_hashes": chunk_hashes,
        }
        metadata_bytes = canonical_json(metadata)
        descriptor = {
            "height": height,
            "format": COMET_SNAPSHOT_FORMAT,
            "chunks": len(chunks),
            "hash_hex": transport_hash,
            "metadata_base64": _b64(metadata_bytes),
        }

        target = self.snapshots_dir / f"{height}-{transport_hash}"
        temp = self.snapshots_dir / f".{height}-{transport_hash}.tmp"
        if temp.exists():
            shutil.rmtree(temp)
        temp.mkdir(parents=True, exist_ok=True)
        for index, chunk in enumerate(chunks):
            (temp / f"chunk-{index:06d}.bin").write_bytes(chunk)
        _write_json(
            temp / "manifest.json",
            {
                "descriptor": descriptor,
                "metadata": metadata,
                "format_name": "canonical-json-envelope",
                "production_ready": False,
            },
        )
        if target.exists():
            shutil.rmtree(temp)
        else:
            temp.replace(target)
        return {"materialized": True, "descriptor": descriptor, "metadata": metadata, "path": str(target)}

    def list_snapshots(self, *, limit: int = 2) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for manifest in self.snapshots_dir.glob("*/manifest.json"):
            try:
                body = _read_json(manifest)
                descriptor = dict(body["descriptor"])
                if int(descriptor.get("format", -1)) != COMET_SNAPSHOT_FORMAT:
                    continue
                if not _hex64(str(descriptor.get("hash_hex", ""))):
                    continue
                found.append(descriptor)
            except (KeyError, TypeError, ValueError, LedgerError):
                continue
        found.sort(key=lambda item: int(item["height"]), reverse=True)
        return found[: max(1, int(limit))]

    def _find_snapshot_dir(self, *, height: int, format_id: int) -> Path:
        if int(format_id) != COMET_SNAPSHOT_FORMAT:
            raise LedgerError("unsupported CometBFT snapshot format")
        candidates = sorted(self.snapshots_dir.glob(f"{int(height)}-*/manifest.json"))
        for manifest in candidates:
            body = _read_json(manifest)
            descriptor = body.get("descriptor", {})
            if int(descriptor.get("height", -1)) == int(height) and int(
                descriptor.get("format", -1)
            ) == int(format_id):
                return manifest.parent
        raise LedgerError("requested CometBFT snapshot is not available")

    def load_chunk(self, *, height: int, format_id: int, chunk: int) -> bytes:
        directory = self._find_snapshot_dir(height=height, format_id=format_id)
        manifest = _read_json(directory / "manifest.json")
        descriptor = manifest["descriptor"]
        index = int(chunk)
        if index < 0 or index >= int(descriptor["chunks"]):
            raise LedgerError("state-sync chunk index is out of range")
        path = directory / f"chunk-{index:06d}.bin"
        if not path.is_file():
            raise LedgerError("state-sync chunk is missing")
        data = path.read_bytes()
        metadata = manifest["metadata"]
        hashes = list(metadata.get("chunk_hashes", []))
        if index >= len(hashes) or sha256_hex(data) != str(hashes[index]):
            raise LedgerError("local state-sync chunk hash mismatch")
        return data

    def _decode_offered_metadata(self, descriptor: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
        raw = _unb64(str(descriptor.get("metadata_base64", "")))
        if len(raw) > 4 * 1024 * 1024:
            raise LedgerError("CometBFT snapshot metadata exceeds safe limit")
        try:
            metadata = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LedgerError("offered snapshot metadata is invalid JSON") from exc
        if not isinstance(metadata, dict):
            raise LedgerError("offered snapshot metadata must be an object")
        return metadata, raw

    def _is_pristine(self) -> bool:
        ledger = self.ledger
        if ledger.height != 0:
            return False
        with ledger.connect() as conn:
            external_commits = conn.execute(
                "SELECT COUNT(*) AS n FROM external_commits"
            ).fetchone()
            pending = conn.execute(
                "SELECT COUNT(*) AS n FROM external_pending_finalizes"
            ).fetchone()
            accounts = {
                str(row["address"]): (int(row["balance"]), int(row["nonce"]))
                for row in conn.execute("SELECT address,balance,nonce FROM accounts").fetchall()
            }
        expected = {
            str(address): (int(amount), 0) for address, amount in self.genesis.allocations.items()
        }
        return int(external_commits["n"]) == 0 and int(pending["n"]) == 0 and accounts == expected

    def offer_snapshot(self, descriptor: dict[str, Any], *, trusted_app_hash_hex: str) -> dict[str, Any]:
        try:
            height = int(descriptor["height"])
            format_id = int(descriptor["format"])
            chunks = int(descriptor["chunks"])
            hash_hex = str(descriptor["hash_hex"]).lower()
        except (KeyError, TypeError, ValueError):
            return {"result": "REJECT"}
        if format_id != COMET_SNAPSHOT_FORMAT:
            return {"result": "REJECT_FORMAT"}
        if height <= 0 or chunks <= 0 or chunks > 10000 or not _hex64(hash_hex):
            return {"result": "REJECT"}
        if not _hex64(str(trusted_app_hash_hex)):
            return {"result": "ABORT"}
        if not self._is_pristine():
            return {"result": "ABORT", "reason": "state-sync restore requires pristine application state"}

        try:
            metadata, raw_metadata = self._decode_offered_metadata(descriptor)
        except LedgerError:
            return {"result": "REJECT"}
        if metadata.get("protocol") != STATE_SYNC_PROTOCOL:
            return {"result": "REJECT_FORMAT"}
        if str(metadata.get("chain_id")) != self.genesis.chain_id:
            return {"result": "REJECT"}
        if str(metadata.get("genesis_fingerprint")) != self.genesis.fingerprint():
            return {"result": "REJECT"}
        if int(metadata.get("height", -1)) != height:
            return {"result": "REJECT"}
        if str(metadata.get("transport_hash", "")).lower() != hash_hex:
            return {"result": "REJECT"}
        expected_app_hash = str(metadata.get("application_hash", "")).lower()
        if expected_app_hash != str(trusted_app_hash_hex).lower():
            return {"result": "REJECT", "reason": "snapshot app hash does not match trusted CometBFT app hash"}
        hashes = list(metadata.get("chunk_hashes", []))
        if len(hashes) != chunks or any(not _hex64(str(item)) for item in hashes):
            return {"result": "REJECT"}
        byte_length = int(metadata.get("byte_length", -1))
        if byte_length < 0 or byte_length > MAX_SNAPSHOT_BYTES:
            return {"result": "REJECT"}

        if self.incoming_dir.exists():
            for path in self.incoming_dir.glob("chunk-*.bin"):
                path.unlink(missing_ok=True)
        session = {
            "descriptor": {
                "height": height,
                "format": format_id,
                "chunks": chunks,
                "hash_hex": hash_hex,
                "metadata_base64": _b64(raw_metadata),
            },
            "metadata": metadata,
            "trusted_app_hash": str(trusted_app_hash_hex).lower(),
            "received": [],
        }
        _write_json(self.session_path, session)
        return {"result": "ACCEPT"}

    def apply_chunk(self, *, index: int, chunk: bytes, sender: str = "") -> dict[str, Any]:
        if not self.session_path.is_file():
            return {"result": "ABORT", "refetch_chunks": [], "reject_senders": []}
        session = _read_json(self.session_path)
        descriptor = session["descriptor"]
        metadata = session["metadata"]
        total = int(descriptor["chunks"])
        index = int(index)
        if index < 0 or index >= total:
            return {"result": "REJECT_SNAPSHOT", "refetch_chunks": [], "reject_senders": []}
        hashes = list(metadata["chunk_hashes"])
        if sha256_hex(chunk) != str(hashes[index]):
            result = {"result": "RETRY", "refetch_chunks": [index], "reject_senders": []}
            if sender:
                result["reject_senders"] = [sender]
            return result

        target = self.incoming_dir / f"chunk-{index:06d}.bin"
        target.write_bytes(chunk)
        received = sorted(
            {
                int(item)
                for item in list(session.get("received", [])) + [index]
                if 0 <= int(item) < total
            }
        )
        session["received"] = received
        _write_json(self.session_path, session)
        if len(received) < total:
            return {"result": "ACCEPT", "refetch_chunks": [], "reject_senders": []}

        try:
            parts = [
                (self.incoming_dir / f"chunk-{item:06d}.bin").read_bytes()
                for item in range(total)
            ]
            payload = b"".join(parts)
            if len(payload) != int(metadata["byte_length"]):
                raise LedgerError("restored snapshot byte length mismatch")
            if sha256_hex(payload) != str(descriptor["hash_hex"]):
                raise LedgerError("restored snapshot transport hash mismatch")
            envelope = json.loads(payload.decode("utf-8"))
            verified = verify_external_snapshot(
                envelope,
                self.genesis,
                expected_height=int(descriptor["height"]),
                expected_application_hash=str(session["trusted_app_hash"]),
            )
            if str(envelope.get("artifact_hash")) != str(metadata.get("artifact_hash")):
                raise LedgerError("restored snapshot artifact hash does not match offered metadata")
            imported = import_external_snapshot(
                envelope=envelope,
                genesis=self.genesis,
                data_dir=self.data_dir,
                expected_height=verified["height"],
                expected_application_hash=verified["application_hash"],
            )
        except Exception:  # noqa: BLE001
            return {"result": "REJECT_SNAPSHOT", "refetch_chunks": [], "reject_senders": []}

        receipt = {
            "completed": True,
            "height": imported["height"],
            "application_hash": imported["application_hash"],
            "transport_hash": descriptor["hash_hex"],
            "historical_commits_recreated": False,
        }
        _write_json(self.incoming_dir / "last-completed.json", receipt)
        self.session_path.unlink(missing_ok=True)
        for path in self.incoming_dir.glob("chunk-*.bin"):
            path.unlink(missing_ok=True)
        return {"result": "ACCEPT", "refetch_chunks": [], "reject_senders": [], "completed": receipt}

    def status(self) -> dict[str, Any]:
        snapshots = self.list_snapshots(limit=10)
        incoming = _read_json(self.session_path) if self.session_path.is_file() else None
        completed_path = self.incoming_dir / "last-completed.json"
        completed = _read_json(completed_path) if completed_path.is_file() else None
        return {
            "protocol": STATE_SYNC_PROTOCOL,
            "format": COMET_SNAPSHOT_FORMAT,
            "chunk_bytes": self.chunk_bytes,
            "available_snapshots": snapshots,
            "incoming": incoming,
            "last_completed": completed,
            "native_abci_lifecycle_supported": True,
            "trust_anchor": "CometBFT light-client verified application hash",
            "production_ready": False,
        }
