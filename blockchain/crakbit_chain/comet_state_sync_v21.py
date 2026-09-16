from __future__ import annotations

import json
from typing import Any

from .comet_state_sync import (
    CometStateSyncManager,
    _read_json,
    _write_json,
)
from .crypto import canonical_json, sha256_hex
from .external_commit_v21 import ExternalExecutionStoreV21
from .external_state_sync_v21 import (
    export_external_snapshot_v21,
    import_external_snapshot_v21,
    verify_external_snapshot_v21,
)
from .storage import LedgerError
from .validator_governance_v21 import genesis_validator_set


class CometStateSyncManagerV21(CometStateSyncManager):
    """ABCI state sync that preserves v0.21 validator-governance consensus state."""

    def _deterministic_envelope(self) -> dict[str, Any]:
        envelope = export_external_snapshot_v21(self.ledger)
        snapshot = dict(envelope["snapshot"])
        snapshot.pop("created_at_ms", None)
        deterministic = {
            "snapshot": snapshot,
            "artifact_hash": sha256_hex(canonical_json(snapshot)),
            "trust_model": "CometBFT light-client-verified v0.21 application hash",
        }
        verify_external_snapshot_v21(
            deterministic,
            self.genesis,
            expected_height=int(snapshot["height"]),
            expected_application_hash=str(snapshot["application_hash"]),
        )
        return deterministic

    def _is_pristine(self) -> bool:
        ledger = self.ledger
        if ledger.height != 0:
            return False
        try:
            store = ExternalExecutionStoreV21(ledger)
        except Exception:  # noqa: BLE001
            return False
        with ledger.connect() as conn:
            external_commits = int(
                conn.execute("SELECT COUNT(*) AS n FROM external_commits").fetchone()["n"]
            )
            pending = int(
                conn.execute("SELECT COUNT(*) AS n FROM external_pending_finalizes").fetchone()["n"]
            )
            history = int(
                conn.execute("SELECT COUNT(*) AS n FROM validator_governance_history").fetchone()["n"]
            )
            emissions = int(
                conn.execute("SELECT COUNT(*) AS n FROM validator_governance_emissions").fetchone()["n"]
            )
            accounts = {
                str(row["address"]): (int(row["balance"]), int(row["nonce"]))
                for row in conn.execute("SELECT address,balance,nonce FROM accounts").fetchall()
            }
        expected_accounts = {
            str(address): (int(amount), 0)
            for address, amount in self.genesis.allocations.items()
        }
        governance = store.governance.state()
        return (
            external_commits == 0
            and pending == 0
            and history == 0
            and emissions == 0
            and accounts == expected_accounts
            and governance["active_validators"] == genesis_validator_set(self.genesis)
            and not governance["pending"]
        )

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
                raise LedgerError("restored v0.21 snapshot byte length mismatch")
            if sha256_hex(payload) != str(descriptor["hash_hex"]):
                raise LedgerError("restored v0.21 snapshot transport hash mismatch")
            envelope = json.loads(payload.decode("utf-8"))
            verified = verify_external_snapshot_v21(
                envelope,
                self.genesis,
                expected_height=int(descriptor["height"]),
                expected_application_hash=str(session["trusted_app_hash"]),
            )
            if str(envelope.get("artifact_hash")) != str(metadata.get("artifact_hash")):
                raise LedgerError("restored v0.21 snapshot artifact hash does not match offered metadata")
            imported = import_external_snapshot_v21(
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
            "governance_history_recreated": False,
            "active_validator_count": imported["active_validator_count"],
            "pending_validator_changes": imported["pending_validator_changes"],
        }
        _write_json(self.incoming_dir / "last-completed.json", receipt)
        self.session_path.unlink(missing_ok=True)
        for path in self.incoming_dir.glob("chunk-*.bin"):
            path.unlink(missing_ok=True)
        return {
            "result": "ACCEPT",
            "refetch_chunks": [],
            "reject_senders": [],
            "completed": receipt,
        }
