from __future__ import annotations

from typing import Any

from .external_commit import COMMIT_PROTOCOL_VERSION, ExternalExecutionStore, deterministic_fee_recipient
from .models import Transaction
from .storage import LedgerError


def replay_safe_stage_finalize(
    store: ExternalExecutionStore,
    *,
    height: int,
    consensus_block_hash: str,
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Stage a finalize request while accepting an identical already-committed replay.

    This covers the important application-ahead recovery case where the application
    committed height H but the external consensus process replays FinalizeBlock(H)
    after restart. A conflicting replay is rejected.
    """

    txs = [Transaction.from_dict(item) for item in transactions]
    fee_recipient = deterministic_fee_recipient(store.ledger.genesis.chain_id)
    with store.ledger.connect() as conn:
        current_height = int(
            conn.execute("SELECT value FROM metadata WHERE key='height'").fetchone()["value"]
        )
        if height <= current_height:
            committed = conn.execute(
                "SELECT * FROM external_commits WHERE height=?",
                (height,),
            ).fetchone()
            if committed is None:
                raise LedgerError("stale external finalize has no matching committed record")
            request_hash = store._request_hash(
                height=height,
                previous_application_hash=str(committed["previous_application_hash"]),
                consensus_block_hash=consensus_block_hash,
                txs=txs,
                fee_recipient=fee_recipient,
            )
            if request_hash != str(committed["request_hash"]):
                raise LedgerError("conflicting external finalize replay at committed height")
            return {
                "protocol": COMMIT_PROTOCOL_VERSION,
                "height": height,
                "request_hash": request_hash,
                "previous_application_hash": str(committed["previous_application_hash"]),
                "next_application_hash": str(committed["application_hash"]),
                "consensus_block_hash": str(committed["consensus_block_hash"]),
                "transaction_root": str(committed["transaction_root"]),
                "transaction_count": int(committed["transaction_count"]),
                "fee_recipient": str(committed["fee_recipient"]),
                "staged": False,
                "already_committed": True,
                "idempotent": True,
                "state_mutated": False,
            }

    return store.stage_finalize(
        height=height,
        consensus_block_hash=consensus_block_hash,
        transactions=transactions,
    )
