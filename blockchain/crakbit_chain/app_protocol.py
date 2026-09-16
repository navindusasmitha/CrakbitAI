from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .crypto import canonical_json, sha256_hex
from .models import Transaction, merkle_root
from .storage import Ledger, LedgerError


PROTOCOL_VERSION = "crakbit-execution/1"


def deterministic_application_hash(ledger: Ledger) -> str:
    """Return a deterministic hash of application-visible state.

    This hash intentionally excludes consensus-local metadata such as votes, rounds and
    peer health. It is suitable as the application-state commitment exposed across a
    future external-consensus boundary.
    """

    with ledger.connect() as conn:
        accounts = [
            (str(row["address"]), int(row["balance"]), int(row["nonce"]))
            for row in conn.execute(
                "SELECT address,balance,nonce FROM accounts ORDER BY address ASC"
            ).fetchall()
        ]
    payload = {
        "protocol": PROTOCOL_VERSION,
        "chain_id": ledger.genesis.chain_id,
        "height": ledger.height,
        "last_hash": ledger.last_hash,
        "accounts": accounts,
    }
    return sha256_hex(canonical_json(payload))


@dataclass
class ExecutionProtocolAdapter:
    """Deterministic, non-network boundary for external-consensus experiments.

    v0.13 deliberately exposes preview/check semantics only. Finalized-block mutation
    still goes through the existing ledger path until a reviewed BFT integration owns
    ordering/finality. This prevents the PoC boundary from becoming an unauthenticated
    alternate consensus path.
    """

    ledger: Ledger

    def info(self) -> dict[str, Any]:
        return {
            "protocol": PROTOCOL_VERSION,
            "chain_id": self.ledger.genesis.chain_id,
            "height": self.ledger.height,
            "last_hash": self.ledger.last_hash,
            "application_hash": deterministic_application_hash(self.ledger),
            "mutating_external_consensus_enabled": False,
            "production_ready": False,
        }

    def check_transaction(self, raw: dict[str, Any]) -> dict[str, Any]:
        try:
            tx = Transaction.from_dict(raw)
            self.ledger.validate_transaction(tx)
            return {
                "accepted": True,
                "txid": tx.txid,
                "sender": tx.sender,
                "nonce": tx.nonce,
            }
        except (KeyError, TypeError, ValueError, LedgerError) as exc:
            return {
                "accepted": False,
                "error": type(exc).__name__,
                "detail": str(exc),
            }

    def preview_batch(
        self,
        transactions: list[dict[str, Any]],
        *,
        fee_recipient: str,
    ) -> dict[str, Any]:
        if not fee_recipient:
            raise LedgerError("fee_recipient is required")
        txs = [Transaction.from_dict(item) for item in transactions]
        seen: set[str] = set()
        for tx in txs:
            if tx.txid in seen:
                raise LedgerError("duplicate transaction in execution batch")
            seen.add(tx.txid)
        next_state_root = self.ledger.simulate_state_root(txs, fee_recipient)
        return {
            "protocol": PROTOCOL_VERSION,
            "chain_id": self.ledger.genesis.chain_id,
            "expected_height": self.ledger.height + 1,
            "previous_block_hash": self.ledger.last_hash,
            "previous_application_hash": deterministic_application_hash(self.ledger),
            "transaction_count": len(txs),
            "transaction_ids": [tx.txid for tx in txs],
            "transaction_root": merkle_root([tx.txid for tx in txs]),
            "next_state_root": next_state_root,
            "fee_recipient": fee_recipient,
            "total_fees": sum(tx.fee for tx in txs),
            "deterministic_preview": True,
            "state_mutated": False,
        }
