from __future__ import annotations

import json
import time
from typing import Any

from .crypto import canonical_json, sha256_hex
from .external_commit import deterministic_fee_recipient
from .external_commit_v16 import ExternalExecutionStoreV16
from .models import Transaction, merkle_root
from .storage import LedgerError
from .validator_governance_v21 import (
    ValidatorGovernanceError,
    ValidatorGovernanceStore,
    governance_txid,
)

COMMIT_PROTOCOL_VERSION_V21 = "crakbit-execution/3"


def _is_hex64(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in value)


def _is_governance_tx(item: dict[str, Any]) -> bool:
    return str(item.get("type", "")) == "validator_governance"


class ExternalExecutionStoreV21(ExternalExecutionStoreV16):
    """External execution v3 with deterministic validator-governance state.

    The v0.21 store preserves the v0.14-v0.20 crash-safe staged FinalizeBlock -> Commit
    structure while extending the deterministic application state with an active validator
    set and at most one pending validator-set change. Governance approvals are replicated as
    transactions and ABCI validator updates are derived only from committed/validated state.
    """

    def _init_schema(self) -> None:
        super()._init_schema()
        self.governance = ValidatorGovernanceStore(self.ledger, allow_pristine_initialize=True)

    def _application_hash_v21(
        self,
        *,
        height: int,
        consensus_block_hash: str,
        account_state: dict[str, list[int]],
        governance_state: dict[str, Any],
    ) -> str:
        payload = {
            "protocol": COMMIT_PROTOCOL_VERSION_V21,
            "chain_id": self.ledger.genesis.chain_id,
            "height": int(height),
            "consensus_block_hash": str(consensus_block_hash).lower(),
            "accounts": sorted(
                (address, int(values[0]), int(values[1]))
                for address, values in account_state.items()
            ),
            "validator_governance": {
                "active_validators": list(governance_state["active_validators"]),
                "pending": list(governance_state.get("pending") or []),
            },
        }
        return sha256_hex(canonical_json(payload))

    def application_hash(self) -> str:
        with self.ledger.connect() as conn:
            accounts = self._state_from_conn(conn)
            governance = self.governance.state_from_conn(conn)
            height = int(
                conn.execute("SELECT value FROM metadata WHERE key='height'").fetchone()["value"]
            )
            last_hash = str(
                conn.execute("SELECT value FROM metadata WHERE key='last_hash'").fetchone()["value"]
            )
            return self._application_hash_v21(
                height=height,
                consensus_block_hash=last_hash,
                account_state=accounts,
                governance_state=governance,
            )

    def _split_transactions(
        self, transactions: list[dict[str, Any]]
    ) -> tuple[list[Transaction], dict[str, Any] | None, list[str]]:
        transfers: list[Transaction] = []
        governance: dict[str, Any] | None = None
        txids: list[str] = []
        for item in transactions:
            if not isinstance(item, dict):
                raise LedgerError("external transaction must be a JSON object")
            if _is_governance_tx(item):
                if governance is not None:
                    raise LedgerError("only one validator-governance transaction is allowed per block")
                governance = item
                txids.append(governance_txid(item))
            else:
                tx = Transaction.from_dict(item)
                transfers.append(tx)
                txids.append(tx.txid)
        if len(set(txids)) != len(txids):
            raise LedgerError("duplicate transaction in external finalize batch")
        return transfers, governance, txids

    def _request_hash_v21(
        self,
        *,
        height: int,
        consensus_block_hash: str,
        txids: list[str],
    ) -> str:
        return sha256_hex(
            canonical_json(
                {
                    "protocol": COMMIT_PROTOCOL_VERSION_V21,
                    "chain_id": self.ledger.genesis.chain_id,
                    "height": int(height),
                    "consensus_block_hash": str(consensus_block_hash).lower(),
                    "transaction_ids": list(txids),
                    "transaction_root": merkle_root(txids),
                }
            )
        )

    def check_transaction(self, item: dict[str, Any]) -> dict[str, Any]:
        if _is_governance_tx(item):
            with self.ledger.connect() as conn:
                current_height = int(
                    conn.execute("SELECT value FROM metadata WHERE key='height'").fetchone()["value"]
                )
                state = self.governance.state_from_conn(conn)
                # Mempool admission is intentionally narrow: governance changes are admitted
                # only for the immediately next height. FinalizeBlock validates again.
                result = self.governance.verify_envelope(
                    item,
                    active_validators=list(state["active_validators"]),
                    expected_emit_height=current_height + 1,
                    require_quorum=True,
                )
                if state["pending"]:
                    raise ValidatorGovernanceError(
                        "a validator governance change is already pending activation"
                    )
                return {
                    "accepted": True,
                    "txid": result["txid"],
                    "kind": "validator_governance",
                    "change_id": result["change_id"],
                    "emit_height": result["emit_height"],
                    "effective_height": result["effective_height"],
                }
        tx = Transaction.from_dict(item)
        self.ledger.validate_transaction(tx)
        return {"accepted": True, "txid": tx.txid, "kind": "transfer"}

    def preview_finalize(
        self,
        *,
        height: int,
        consensus_block_hash: str,
        transactions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if int(height) < 1:
            raise LedgerError("external consensus height must be at least 1")
        if not _is_hex64(consensus_block_hash):
            raise LedgerError("consensus block hash must be 64 hexadecimal characters")
        transfers, governance_tx, txids = self._split_transactions(transactions)
        fee_recipient = deterministic_fee_recipient(self.ledger.genesis.chain_id)
        with self.ledger.connect() as conn:
            current_height = int(
                conn.execute("SELECT value FROM metadata WHERE key='height'").fetchone()["value"]
            )
            if int(height) != current_height + 1:
                raise LedgerError(
                    f"unexpected external consensus height: expected {current_height + 1}"
                )
            last_hash = str(
                conn.execute("SELECT value FROM metadata WHERE key='last_hash'").fetchone()["value"]
            )
            current_accounts = self._state_from_conn(conn)
            current_governance = self.governance.state_from_conn(conn)
            previous_application_hash = self._application_hash_v21(
                height=current_height,
                consensus_block_hash=last_hash,
                account_state=current_accounts,
                governance_state=current_governance,
            )
            next_accounts, next_state_root = self._simulate(current_accounts, transfers, fee_recipient)
            governance_result = self.governance.simulate_height(
                conn,
                height=int(height),
                envelope=governance_tx,
            )
            next_application_hash = self._application_hash_v21(
                height=int(height),
                consensus_block_hash=consensus_block_hash,
                account_state=next_accounts,
                governance_state=governance_result["state"],
            )
            return {
                "protocol": COMMIT_PROTOCOL_VERSION_V21,
                "chain_id": self.ledger.genesis.chain_id,
                "height": int(height),
                "previous_application_hash": previous_application_hash,
                "next_application_hash": next_application_hash,
                "next_state_root": next_state_root,
                "next_governance_hash": governance_result["governance_hash"],
                "consensus_block_hash": consensus_block_hash.lower(),
                "transaction_root": merkle_root(txids),
                "transaction_ids": txids,
                "transaction_count": len(txids),
                "transfer_count": len(transfers),
                "governance_transaction_count": 1 if governance_tx is not None else 0,
                "fee_recipient": fee_recipient,
                "total_fees": sum(tx.fee for tx in transfers),
                "request_hash": self._request_hash_v21(
                    height=int(height),
                    consensus_block_hash=consensus_block_hash,
                    txids=txids,
                ),
                "validator_updates": list(governance_result["validator_updates"]),
                "state_mutated": False,
            }

    def stage_finalize(
        self,
        *,
        height: int,
        consensus_block_hash: str,
        transactions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        with self._lock:
            if not _is_hex64(consensus_block_hash):
                raise LedgerError("consensus block hash must be 64 hexadecimal characters")
            transfers, governance_tx, txids = self._split_transactions(transactions)
            request_hash = self._request_hash_v21(
                height=int(height),
                consensus_block_hash=consensus_block_hash,
                txids=txids,
            )
            fee_recipient = deterministic_fee_recipient(self.ledger.genesis.chain_id)
            with self.ledger.connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    current_height = int(
                        conn.execute("SELECT value FROM metadata WHERE key='height'").fetchone()["value"]
                    )
                    if int(height) <= current_height:
                        committed = conn.execute(
                            "SELECT * FROM external_commits WHERE height=?", (int(height),)
                        ).fetchone()
                        if committed is None:
                            raise LedgerError("stale external finalize has no matching committed record")
                        if str(committed["request_hash"]) != request_hash:
                            raise LedgerError("conflicting external finalize replay at committed height")
                        updates = self.governance.emission_for_height(conn, int(height))
                        conn.execute("COMMIT")
                        return {
                            "protocol": COMMIT_PROTOCOL_VERSION_V21,
                            "height": int(height),
                            "request_hash": request_hash,
                            "previous_application_hash": str(committed["previous_application_hash"]),
                            "next_application_hash": str(committed["application_hash"]),
                            "consensus_block_hash": str(committed["consensus_block_hash"]),
                            "transaction_root": str(committed["transaction_root"]),
                            "transaction_count": int(committed["transaction_count"]),
                            "fee_recipient": str(committed["fee_recipient"]),
                            "validator_updates": updates,
                            "staged": False,
                            "already_committed": True,
                            "idempotent": True,
                            "state_mutated": False,
                        }
                    if int(height) != current_height + 1:
                        raise LedgerError(
                            f"unexpected external consensus height: expected {current_height + 1}"
                        )

                    current_accounts = self._state_from_conn(conn)
                    last_hash = str(
                        conn.execute("SELECT value FROM metadata WHERE key='last_hash'").fetchone()["value"]
                    )
                    current_governance = self.governance.state_from_conn(conn)
                    previous_application_hash = self._application_hash_v21(
                        height=current_height,
                        consensus_block_hash=last_hash,
                        account_state=current_accounts,
                        governance_state=current_governance,
                    )
                    next_accounts, next_state_root = self._simulate(
                        current_accounts, transfers, fee_recipient
                    )
                    governance_result = self.governance.simulate_height(
                        conn,
                        height=int(height),
                        envelope=governance_tx,
                    )
                    next_application_hash = self._application_hash_v21(
                        height=int(height),
                        consensus_block_hash=consensus_block_hash,
                        account_state=next_accounts,
                        governance_state=governance_result["state"],
                    )
                    transaction_root = merkle_root(txids)
                    pending = conn.execute(
                        "SELECT * FROM external_pending_finalizes WHERE height=?", (int(height),)
                    ).fetchone()
                    if pending is not None:
                        if str(pending["request_hash"]) != request_hash:
                            raise LedgerError("conflicting external finalize request for pending height")
                        conn.execute("COMMIT")
                        return {
                            "protocol": COMMIT_PROTOCOL_VERSION_V21,
                            "height": int(height),
                            "request_hash": request_hash,
                            "previous_application_hash": previous_application_hash,
                            "next_application_hash": str(pending["next_application_hash"]),
                            "next_state_root": next_state_root,
                            "next_governance_hash": governance_result["governance_hash"],
                            "consensus_block_hash": str(pending["consensus_block_hash"]),
                            "transaction_root": str(pending["transaction_root"]),
                            "transaction_count": int(pending["transaction_count"]),
                            "fee_recipient": str(pending["fee_recipient"]),
                            "validator_updates": list(governance_result["validator_updates"]),
                            "staged": True,
                            "already_committed": False,
                            "idempotent": True,
                            "state_mutated": False,
                        }

                    conn.execute(
                        "INSERT INTO external_pending_finalizes("
                        "height,request_hash,previous_application_hash,next_application_hash,"
                        "consensus_block_hash,transaction_root,transaction_count,fee_recipient,"
                        "transactions_json,created_at_ms) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (
                            int(height),
                            request_hash,
                            previous_application_hash,
                            next_application_hash,
                            consensus_block_hash.lower(),
                            transaction_root,
                            len(txids),
                            fee_recipient,
                            json.dumps(transactions, separators=(",", ":"), sort_keys=True),
                            int(time.time() * 1000),
                        ),
                    )
                    conn.execute("COMMIT")
                    return {
                        "protocol": COMMIT_PROTOCOL_VERSION_V21,
                        "height": int(height),
                        "request_hash": request_hash,
                        "previous_application_hash": previous_application_hash,
                        "next_application_hash": next_application_hash,
                        "next_state_root": next_state_root,
                        "next_governance_hash": governance_result["governance_hash"],
                        "consensus_block_hash": consensus_block_hash.lower(),
                        "transaction_root": transaction_root,
                        "transaction_count": len(txids),
                        "fee_recipient": fee_recipient,
                        "validator_updates": list(governance_result["validator_updates"]),
                        "staged": True,
                        "already_committed": False,
                        "idempotent": False,
                        "state_mutated": False,
                    }
                except Exception:
                    conn.execute("ROLLBACK")
                    raise

    def commit_pending(self) -> dict[str, Any]:
        with self._lock:
            with self.ledger.connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    current_height = int(
                        conn.execute("SELECT value FROM metadata WHERE key='height'").fetchone()["value"]
                    )
                    pending = conn.execute(
                        "SELECT * FROM external_pending_finalizes ORDER BY height ASC LIMIT 1"
                    ).fetchone()
                    if pending is None:
                        current_accounts = self._state_from_conn(conn)
                        current_governance = self.governance.state_from_conn(conn)
                        last_hash = str(
                            conn.execute("SELECT value FROM metadata WHERE key='last_hash'").fetchone()["value"]
                        )
                        app_hash = self._application_hash_v21(
                            height=current_height,
                            consensus_block_hash=last_hash,
                            account_state=current_accounts,
                            governance_state=current_governance,
                        )
                        conn.execute("COMMIT")
                        return {
                            "protocol": COMMIT_PROTOCOL_VERSION_V21,
                            "height": current_height,
                            "application_hash": app_hash,
                            "committed": False,
                            "idempotent": True,
                            "reason": "no_pending_finalize",
                        }

                    height = int(pending["height"])
                    if height != current_height + 1:
                        raise LedgerError("pending external finalize is not the next application height")
                    raw_transactions = json.loads(str(pending["transactions_json"]))
                    transfers, governance_tx, txids = self._split_transactions(raw_transactions)
                    request_hash = self._request_hash_v21(
                        height=height,
                        consensus_block_hash=str(pending["consensus_block_hash"]),
                        txids=txids,
                    )
                    if request_hash != str(pending["request_hash"]):
                        raise LedgerError("pending v0.21 finalize request hash mismatch")

                    current_accounts = self._state_from_conn(conn)
                    current_governance = self.governance.state_from_conn(conn)
                    last_hash = str(
                        conn.execute("SELECT value FROM metadata WHERE key='last_hash'").fetchone()["value"]
                    )
                    previous_application_hash = self._application_hash_v21(
                        height=current_height,
                        consensus_block_hash=last_hash,
                        account_state=current_accounts,
                        governance_state=current_governance,
                    )
                    if previous_application_hash != str(pending["previous_application_hash"]):
                        raise LedgerError("pending finalize no longer matches committed v0.21 application state")

                    fee_recipient = str(pending["fee_recipient"])
                    next_accounts, _ = self._simulate(current_accounts, transfers, fee_recipient)
                    governance_preview = self.governance.simulate_height(
                        conn,
                        height=height,
                        envelope=governance_tx,
                    )
                    expected_application_hash = self._application_hash_v21(
                        height=height,
                        consensus_block_hash=str(pending["consensus_block_hash"]),
                        account_state=next_accounts,
                        governance_state=governance_preview["state"],
                    )
                    if expected_application_hash != str(pending["next_application_hash"]):
                        raise LedgerError("pending v0.21 finalize application hash mismatch")

                    for tx in transfers:
                        self.ledger.validate_transaction(tx, conn)
                        conn.execute(
                            "INSERT OR IGNORE INTO accounts(address,balance,nonce) VALUES(?,0,0)",
                            (tx.sender,),
                        )
                        conn.execute(
                            "INSERT OR IGNORE INTO accounts(address,balance,nonce) VALUES(?,0,0)",
                            (tx.recipient,),
                        )
                        conn.execute(
                            "INSERT OR IGNORE INTO accounts(address,balance,nonce) VALUES(?,0,0)",
                            (fee_recipient,),
                        )
                        conn.execute(
                            "UPDATE accounts SET balance=balance-?, nonce=nonce+1 WHERE address=?",
                            (tx.amount + tx.fee, tx.sender),
                        )
                        conn.execute(
                            "UPDATE accounts SET balance=balance+? WHERE address=?",
                            (tx.amount, tx.recipient),
                        )
                        conn.execute(
                            "UPDATE accounts SET balance=balance+? WHERE address=?",
                            (tx.fee, fee_recipient),
                        )

                    governance_committed = self.governance.commit_height(
                        conn,
                        height=height,
                        envelope=governance_tx,
                    )

                    for item, txid in zip(raw_transactions, txids, strict=True):
                        conn.execute(
                            "INSERT INTO transactions(txid,height,body) VALUES(?,?,?)",
                            (
                                txid,
                                height,
                                json.dumps(item, separators=(",", ":"), sort_keys=True),
                            ),
                        )

                    conn.execute("UPDATE metadata SET value=? WHERE key='height'", (str(height),))
                    conn.execute(
                        "UPDATE metadata SET value=? WHERE key='last_hash'",
                        (str(pending["consensus_block_hash"]),),
                    )
                    final_accounts = self._state_from_conn(conn)
                    final_governance = self.governance.state_from_conn(conn)
                    application_hash = self._application_hash_v21(
                        height=height,
                        consensus_block_hash=str(pending["consensus_block_hash"]),
                        account_state=final_accounts,
                        governance_state=final_governance,
                    )
                    if application_hash != expected_application_hash:
                        raise LedgerError("committed v0.21 application hash differs from staged hash")

                    committed_at_ms = int(time.time() * 1000)
                    conn.execute(
                        "INSERT INTO external_commits("
                        "height,request_hash,previous_application_hash,application_hash,"
                        "consensus_block_hash,transaction_root,transaction_count,fee_recipient,"
                        "committed_at_ms) VALUES(?,?,?,?,?,?,?,?,?)",
                        (
                            height,
                            request_hash,
                            previous_application_hash,
                            application_hash,
                            str(pending["consensus_block_hash"]),
                            str(pending["transaction_root"]),
                            int(pending["transaction_count"]),
                            fee_recipient,
                            committed_at_ms,
                        ),
                    )
                    conn.execute("DELETE FROM external_pending_finalizes WHERE height=?", (height,))
                    conn.execute("COMMIT")
                    return {
                        "protocol": COMMIT_PROTOCOL_VERSION_V21,
                        "height": height,
                        "application_hash": application_hash,
                        "consensus_block_hash": str(pending["consensus_block_hash"]),
                        "transaction_root": str(pending["transaction_root"]),
                        "transaction_count": int(pending["transaction_count"]),
                        "request_hash": request_hash,
                        "governance_hash": governance_committed["governance_hash"],
                        "validator_updates": list(governance_committed["validator_updates"]),
                        "committed": True,
                        "idempotent": False,
                    }
                except Exception:
                    conn.execute("ROLLBACK")
                    raise

    def status(self) -> dict[str, Any]:
        with self.ledger.connect() as conn:
            current_height = int(
                conn.execute("SELECT value FROM metadata WHERE key='height'").fetchone()["value"]
            )
            pending_finalize = conn.execute(
                "SELECT height,request_hash,next_application_hash,consensus_block_hash,transaction_count,created_at_ms "
                "FROM external_pending_finalizes ORDER BY height ASC LIMIT 1"
            ).fetchone()
            commits = int(conn.execute("SELECT COUNT(*) AS n FROM external_commits").fetchone()["n"])
            governance_state = self.governance.state_from_conn(conn)
        base = self.snapshot_base()
        return {
            "protocol": COMMIT_PROTOCOL_VERSION_V21,
            "chain_id": self.ledger.genesis.chain_id,
            "height": current_height,
            "application_hash": self.application_hash(),
            "last_consensus_block_hash": self.ledger.last_hash,
            "external_commit_count": commits,
            "pending_finalize": (
                {
                    "height": int(pending_finalize["height"]),
                    "request_hash": str(pending_finalize["request_hash"]),
                    "next_application_hash": str(pending_finalize["next_application_hash"]),
                    "consensus_block_hash": str(pending_finalize["consensus_block_hash"]),
                    "transaction_count": int(pending_finalize["transaction_count"]),
                    "created_at_ms": int(pending_finalize["created_at_ms"]),
                }
                if pending_finalize is not None
                else None
            ),
            "snapshot_base": base,
            "state_sync_checkpoint_supported": True,
            "post_snapshot_commit_count": commits,
            "historical_commits_complete": base["height"] == 0,
            "validator_governance": {
                "active_validator_count": len(governance_state["active_validators"]),
                "active_validator_set_hash": governance_state["active_validator_set_hash"],
                "pending": governance_state["pending"],
                "governance_hash": self.governance.governance_hash_from_state(governance_state),
            },
            "crash_safe_sqlite_commit": True,
            "idempotent_finalize_replay": True,
            "live_abci_validator_updates_enabled": True,
            "production_ready": False,
        }
