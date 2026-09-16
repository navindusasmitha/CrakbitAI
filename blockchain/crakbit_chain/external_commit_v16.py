from __future__ import annotations

from .external_commit import COMMIT_PROTOCOL_VERSION, ExternalExecutionStore
from .storage import LedgerError


SNAPSHOT_BASE_HEIGHT_KEY = "external_snapshot_base_height"
SNAPSHOT_BASE_APP_HASH_KEY = "external_snapshot_base_application_hash"
SNAPSHOT_BASE_STATE_HASH_KEY = "external_snapshot_artifact_hash"


class ExternalExecutionStoreV16(ExternalExecutionStore):
    """v0.16 external execution store with explicit state-sync checkpoint support.

    A restored checkpoint may start the application at height N without recreating all
    historical external_commits rows 1..N. Commits after the checkpoint remain fully
    recorded and the invariant becomes:

        application height == snapshot base height + post-snapshot commit count

    This keeps checkpoint restoration explicit instead of fabricating historical commits.
    """

    def _init_schema(self) -> None:
        with self.ledger.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS external_pending_finalizes (
                    height INTEGER PRIMARY KEY,
                    request_hash TEXT UNIQUE NOT NULL,
                    previous_application_hash TEXT NOT NULL,
                    next_application_hash TEXT NOT NULL,
                    consensus_block_hash TEXT NOT NULL,
                    transaction_root TEXT NOT NULL,
                    transaction_count INTEGER NOT NULL,
                    fee_recipient TEXT NOT NULL,
                    transactions_json TEXT NOT NULL,
                    created_at_ms INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS external_commits (
                    height INTEGER PRIMARY KEY,
                    request_hash TEXT UNIQUE NOT NULL,
                    previous_application_hash TEXT NOT NULL,
                    application_hash TEXT NOT NULL,
                    consensus_block_hash TEXT NOT NULL,
                    transaction_root TEXT NOT NULL,
                    transaction_count INTEGER NOT NULL,
                    fee_recipient TEXT NOT NULL,
                    committed_at_ms INTEGER NOT NULL
                );
                """
            )
            mode = conn.execute(
                "SELECT value FROM metadata WHERE key='execution_owner'"
            ).fetchone()
            block_count = int(
                conn.execute("SELECT COUNT(*) AS n FROM blocks").fetchone()["n"]
            )
            external_count = int(
                conn.execute("SELECT COUNT(*) AS n FROM external_commits").fetchone()["n"]
            )
            if mode is None:
                if self.ledger.height != 0 or block_count != 0:
                    raise LedgerError(
                        "external execution requires a dedicated fresh data directory; "
                        "refusing to attach to an existing research-consensus ledger"
                    )
                conn.execute(
                    "INSERT INTO metadata(key,value) VALUES('execution_owner',?)",
                    (COMMIT_PROTOCOL_VERSION,),
                )
            elif str(mode["value"]) != COMMIT_PROTOCOL_VERSION:
                raise LedgerError("database belongs to a different execution owner")

            if block_count != 0:
                raise LedgerError(
                    "external execution database must not contain research-consensus blocks"
                )

            base_row = conn.execute(
                "SELECT value FROM metadata WHERE key=?",
                (SNAPSHOT_BASE_HEIGHT_KEY,),
            ).fetchone()
            base_height = int(base_row["value"]) if base_row is not None else 0
            if base_height < 0 or base_height > self.ledger.height:
                raise LedgerError("invalid external snapshot base height")
            if self.ledger.height != base_height + external_count:
                raise LedgerError(
                    "external execution commit count does not match application height "
                    "after accounting for snapshot base; run integrity/recovery procedures"
                )

    def snapshot_base(self) -> dict:
        with self.ledger.connect() as conn:
            height_row = conn.execute(
                "SELECT value FROM metadata WHERE key=?",
                (SNAPSHOT_BASE_HEIGHT_KEY,),
            ).fetchone()
            app_hash_row = conn.execute(
                "SELECT value FROM metadata WHERE key=?",
                (SNAPSHOT_BASE_APP_HASH_KEY,),
            ).fetchone()
            artifact_row = conn.execute(
                "SELECT value FROM metadata WHERE key=?",
                (SNAPSHOT_BASE_STATE_HASH_KEY,),
            ).fetchone()
        return {
            "height": int(height_row["value"]) if height_row is not None else 0,
            "application_hash": (
                str(app_hash_row["value"]) if app_hash_row is not None else None
            ),
            "artifact_hash": (
                str(artifact_row["value"]) if artifact_row is not None else None
            ),
        }

    def status(self) -> dict:
        status = super().status()
        base = self.snapshot_base()
        status.update(
            {
                "snapshot_base": base,
                "state_sync_checkpoint_supported": True,
                "post_snapshot_commit_count": status["external_commit_count"],
                "historical_commits_complete": base["height"] == 0,
            }
        )
        return status
