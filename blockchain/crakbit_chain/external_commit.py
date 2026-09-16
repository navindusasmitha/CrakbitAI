from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Any

from .crypto import canonical_json, sha256_hex
from .models import Transaction, merkle_root
from .storage import Ledger, LedgerError


COMMIT_PROTOCOL_VERSION = "crakbit-execution/2"


def _is_hex64(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in value)


def deterministic_fee_recipient(chain_id: str) -> str:
    """Return a deterministic test-network fee pool address for external consensus.

    The address intentionally has no corresponding private key. v0.14 does not define
    production validator rewards; fees collected by the external-consensus PoC are
    parked in this deterministic application account until economics are reviewed.
    """

    digest = sha256_hex(f"{chain_id}:external-consensus-fee-pool".encode("utf-8"))
    return "crk1" + digest[:40]


@dataclass(frozen=True)
class PendingFinalize:
    height: int
    request_hash: str
    previous_application_hash: str
    next_application_hash: str
    consensus_block_hash: str
    transaction_root: str
    transaction_count: int
    fee_recipient: str


class ExternalExecutionStore:
    """Crash-safe application state boundary for an external BFT engine.

    This store is intended to use a dedicated data directory. It deliberately keeps
    external consensus commits separate from the research Python consensus block table.
    `stage_finalize` is non-mutating and persisted. `commit_pending` applies the staged
    transition in one SQLite transaction and is idempotent across replay/restart.
    """

    def __init__(self, ledger: Ledger):
        self.ledger = ledger
        self._lock = threading.Lock()
        self._init_schema()

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
                raise LedgerError("external execution database must not contain research-consensus blocks")
            if self.ledger.height != external_count:
                raise LedgerError(
                    "external execution commit count does not match application height; "
                    "run integrity/recovery procedures before continuing"
                )

    def _state_from_conn(self, conn) -> dict[str, list[int]]:
        return {
            str(row["address"]): [int(row["balance"]), int(row["nonce"])]
            for row in conn.execute(
                "SELECT address,balance,nonce FROM accounts ORDER BY address ASC"
            ).fetchall()
        }

    def _application_hash_from_state(
        self,
        *,
        height: int,
        consensus_block_hash: str,
        state: dict[str, list[int]],
    ) -> str:
        payload = {
            "protocol": COMMIT_PROTOCOL_VERSION,
            "chain_id": self.ledger.genesis.chain_id,
            "height": int(height),
            "consensus_block_hash": str(consensus_block_hash),
            "accounts": sorted(
                (address, int(values[0]), int(values[1]))
                for address, values in state.items()
            ),
        }
        return sha256_hex(canonical_json(payload))

    def application_hash(self) -> str:
        with self.ledger.connect() as conn:
            state = self._state_from_conn(conn)
            height = int(
                conn.execute("SELECT value FROM metadata WHERE key='height'").fetchone()["value"]
            )
            last_hash = str(
                conn.execute("SELECT value FROM metadata WHERE key='last_hash'").fetchone()["value"]
            )
            return self._application_hash_from_state(
                height=height,
                consensus_block_hash=last_hash,
                state=state,
            )

    def _simulate(
        self,
        state: dict[str, list[int]],
        txs: list[Transaction],
        fee_recipient: str,
    ) -> tuple[dict[str, list[int]], str]:
        working = {address: [values[0], values[1]] for address, values in state.items()}
        for tx in txs:
            self.ledger._validate_transaction_fields(tx)
            sender = working.setdefault(tx.sender, [0, 0])
            recipient = working.setdefault(tx.recipient, [0, 0])
            fees = working.setdefault(fee_recipient, [0, 0])
            if tx.nonce != sender[1] + 1:
                raise LedgerError(
                    f"invalid nonce in external execution batch: expected {sender[1] + 1}"
                )
            if sender[0] < tx.amount + tx.fee:
                raise LedgerError("insufficient balance in external execution batch")
            sender[0] -= tx.amount + tx.fee
            sender[1] += 1
            recipient[0] += tx.amount
            fees[0] += tx.fee
        state_root = sha256_hex(
            canonical_json(
                sorted(
                    (address, int(values[0]), int(values[1]))
                    for address, values in working.items()
                )
            )
        )
        return working, state_root

    def _request_hash(
        self,
        *,
        height: int,
        previous_application_hash: str,
        consensus_block_hash: str,
        txs: list[Transaction],
        fee_recipient: str,
    ) -> str:
        return sha256_hex(
            canonical_json(
                {
                    "protocol": COMMIT_PROTOCOL_VERSION,
                    "chain_id": self.ledger.genesis.chain_id,
                    "height": int(height),
                    "previous_application_hash": previous_application_hash,
                    "consensus_block_hash": consensus_block_hash.lower(),
                    "transaction_ids": [tx.txid for tx in txs],
                    "transaction_root": merkle_root([tx.txid for tx in txs]),
                    "fee_recipient": fee_recipient,
                }
            )
        )

    def preview_finalize(
        self,
        *,
        height: int,
        consensus_block_hash: str,
        transactions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if height < 1:
            raise LedgerError("external consensus height must be at least 1")
        if not _is_hex64(consensus_block_hash):
            raise LedgerError("consensus block hash must be 64 hexadecimal characters")
        txs = [Transaction.from_dict(item) for item in transactions]
        if len({tx.txid for tx in txs}) != len(txs):
            raise LedgerError("duplicate transaction in external finalize batch")
        fee_recipient = deterministic_fee_recipient(self.ledger.genesis.chain_id)
        with self.ledger.connect() as conn:
            current_height = int(
                conn.execute("SELECT value FROM metadata WHERE key='height'").fetchone()["value"]
            )
            last_hash = str(
                conn.execute("SELECT value FROM metadata WHERE key='last_hash'").fetchone()["value"]
            )
            if height != current_height + 1:
                raise LedgerError(
                    f"unexpected external consensus height: expected {current_height + 1}"
                )
            current_state = self._state_from_conn(conn)
            previous_application_hash = self._application_hash_from_state(
                height=current_height,
                consensus_block_hash=last_hash,
                state=current_state,
            )
            next_state, next_state_root = self._simulate(current_state, txs, fee_recipient)
            next_application_hash = self._application_hash_from_state(
                height=height,
                consensus_block_hash=consensus_block_hash.lower(),
                state=next_state,
            )
            request_hash = self._request_hash(
                height=height,
                previous_application_hash=previous_application_hash,
                consensus_block_hash=consensus_block_hash,
                txs=txs,
                fee_recipient=fee_recipient,
            )
            return {
                "protocol": COMMIT_PROTOCOL_VERSION,
                "chain_id": self.ledger.genesis.chain_id,
                "height": height,
                "previous_application_hash": previous_application_hash,
                "next_application_hash": next_application_hash,
                "next_state_root": next_state_root,
                "consensus_block_hash": consensus_block_hash.lower(),
                "transaction_root": merkle_root([tx.txid for tx in txs]),
                "transaction_ids": [tx.txid for tx in txs],
                "transaction_count": len(txs),
                "fee_recipient": fee_recipient,
                "total_fees": sum(tx.fee for tx in txs),
                "request_hash": request_hash,
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
            txs = [Transaction.from_dict(item) for item in transactions]
            if len({tx.txid for tx in txs}) != len(txs):
                raise LedgerError("duplicate transaction in external finalize batch")
            if not _is_hex64(consensus_block_hash):
                raise LedgerError("consensus block hash must be 64 hexadecimal characters")
            fee_recipient = deterministic_fee_recipient(self.ledger.genesis.chain_id)
            with self.ledger.connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    current_height = int(
                        conn.execute("SELECT value FROM metadata WHERE key='height'").fetchone()["value"]
                    )
                    last_hash = str(
                        conn.execute("SELECT value FROM metadata WHERE key='last_hash'").fetchone()["value"]
                    )
                    current_state = self._state_from_conn(conn)
                    previous_application_hash = self._application_hash_from_state(
                        height=current_height,
                        consensus_block_hash=last_hash,
                        state=current_state,
                    )
                    request_hash = self._request_hash(
                        height=height,
                        previous_application_hash=previous_application_hash,
                        consensus_block_hash=consensus_block_hash,
                        txs=txs,
                        fee_recipient=fee_recipient,
                    )

                    committed = conn.execute(
                        "SELECT * FROM external_commits WHERE height=?",
                        (height,),
                    ).fetchone()
                    if committed is not None:
                        if str(committed["request_hash"]) != request_hash:
                            raise LedgerError("conflicting external finalize replay at committed height")
                        conn.execute("COMMIT")
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

                    if height != current_height + 1:
                        raise LedgerError(
                            f"unexpected external consensus height: expected {current_height + 1}"
                        )

                    next_state, next_state_root = self._simulate(current_state, txs, fee_recipient)
                    next_application_hash = self._application_hash_from_state(
                        height=height,
                        consensus_block_hash=consensus_block_hash.lower(),
                        state=next_state,
                    )
                    transaction_root = merkle_root([tx.txid for tx in txs])
                    pending = conn.execute(
                        "SELECT * FROM external_pending_finalizes WHERE height=?",
                        (height,),
                    ).fetchone()
                    if pending is not None:
                        if str(pending["request_hash"]) != request_hash:
                            raise LedgerError("conflicting external finalize request for pending height")
                        conn.execute("COMMIT")
                        return {
                            "protocol": COMMIT_PROTOCOL_VERSION,
                            "height": height,
                            "request_hash": request_hash,
                            "previous_application_hash": previous_application_hash,
                            "next_application_hash": str(pending["next_application_hash"]),
                            "next_state_root": next_state_root,
                            "consensus_block_hash": str(pending["consensus_block_hash"]),
                            "transaction_root": str(pending["transaction_root"]),
                            "transaction_count": int(pending["transaction_count"]),
                            "fee_recipient": str(pending["fee_recipient"]),
                            "staged": True,
                            "already_committed": False,
                            "idempotent": True,
                            "state_mutated": False,
                        }

                    conn.execute(
                        """
                        INSERT INTO external_pending_finalizes(
                            height,request_hash,previous_application_hash,next_application_hash,
                            consensus_block_hash,transaction_root,transaction_count,fee_recipient,
                            transactions_json,created_at_ms
                        ) VALUES(?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            height,
                            request_hash,
                            previous_application_hash,
                            next_application_hash,
                            consensus_block_hash.lower(),
                            transaction_root,
                            len(txs),
                            fee_recipient,
                            json.dumps([tx.to_dict() for tx in txs], separators=(",", ":")),
                            int(time.time() * 1000),
                        ),
                    )
                    conn.execute("COMMIT")
                    return {
                        "protocol": COMMIT_PROTOCOL_VERSION,
                        "height": height,
                        "request_hash": request_hash,
                        "previous_application_hash": previous_application_hash,
                        "next_application_hash": next_application_hash,
                        "next_state_root": next_state_root,
                        "consensus_block_hash": consensus_block_hash.lower(),
                        "transaction_root": transaction_root,
                        "transaction_count": len(txs),
                        "fee_recipient": fee_recipient,
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
                        state = self._state_from_conn(conn)
                        last_hash = str(
                            conn.execute("SELECT value FROM metadata WHERE key='last_hash'").fetchone()["value"]
                        )
                        app_hash = self._application_hash_from_state(
                            height=current_height,
                            consensus_block_hash=last_hash,
                            state=state,
                        )
                        conn.execute("COMMIT")
                        return {
                            "protocol": COMMIT_PROTOCOL_VERSION,
                            "height": current_height,
                            "application_hash": app_hash,
                            "committed": False,
                            "idempotent": True,
                            "reason": "no_pending_finalize",
                        }

                    height = int(pending["height"])
                    if height != current_height + 1:
                        raise LedgerError("pending external finalize is not the next application height")
                    current_state = self._state_from_conn(conn)
                    last_hash = str(
                        conn.execute("SELECT value FROM metadata WHERE key='last_hash'").fetchone()["value"]
                    )
                    previous_application_hash = self._application_hash_from_state(
                        height=current_height,
                        consensus_block_hash=last_hash,
                        state=current_state,
                    )
                    if previous_application_hash != str(pending["previous_application_hash"]):
                        raise LedgerError("pending external finalize no longer matches committed application state")

                    txs = [
                        Transaction.from_dict(item)
                        for item in json.loads(str(pending["transactions_json"]))
                    ]
                    fee_recipient = str(pending["fee_recipient"])
                    next_state, _ = self._simulate(current_state, txs, fee_recipient)
                    expected_app_hash = self._application_hash_from_state(
                        height=height,
                        consensus_block_hash=str(pending["consensus_block_hash"]),
                        state=next_state,
                    )
                    if expected_app_hash != str(pending["next_application_hash"]):
                        raise LedgerError("pending external finalize application hash mismatch")

                    for tx in txs:
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
                        conn.execute(
                            "INSERT INTO transactions(txid,height,body) VALUES(?,?,?)",
                            (
                                tx.txid,
                                height,
                                json.dumps(tx.to_dict(), separators=(",", ":")),
                            ),
                        )

                    conn.execute(
                        "UPDATE metadata SET value=? WHERE key='height'",
                        (str(height),),
                    )
                    conn.execute(
                        "UPDATE metadata SET value=? WHERE key='last_hash'",
                        (str(pending["consensus_block_hash"]),),
                    )
                    final_state = self._state_from_conn(conn)
                    application_hash = self._application_hash_from_state(
                        height=height,
                        consensus_block_hash=str(pending["consensus_block_hash"]),
                        state=final_state,
                    )
                    if application_hash != expected_app_hash:
                        raise LedgerError("committed application hash differs from staged finalize hash")

                    committed_at_ms = int(time.time() * 1000)
                    conn.execute(
                        """
                        INSERT INTO external_commits(
                            height,request_hash,previous_application_hash,application_hash,
                            consensus_block_hash,transaction_root,transaction_count,fee_recipient,
                            committed_at_ms
                        ) VALUES(?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            height,
                            str(pending["request_hash"]),
                            str(pending["previous_application_hash"]),
                            application_hash,
                            str(pending["consensus_block_hash"]),
                            str(pending["transaction_root"]),
                            int(pending["transaction_count"]),
                            fee_recipient,
                            committed_at_ms,
                        ),
                    )
                    conn.execute(
                        "DELETE FROM external_pending_finalizes WHERE height=?",
                        (height,),
                    )
                    conn.execute("COMMIT")
                    return {
                        "protocol": COMMIT_PROTOCOL_VERSION,
                        "height": height,
                        "application_hash": application_hash,
                        "consensus_block_hash": str(pending["consensus_block_hash"]),
                        "transaction_root": str(pending["transaction_root"]),
                        "transaction_count": int(pending["transaction_count"]),
                        "request_hash": str(pending["request_hash"]),
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
            pending = conn.execute(
                "SELECT height,request_hash,next_application_hash,consensus_block_hash,transaction_count,created_at_ms "
                "FROM external_pending_finalizes ORDER BY height ASC LIMIT 1"
            ).fetchone()
            commits = int(
                conn.execute("SELECT COUNT(*) AS n FROM external_commits").fetchone()["n"]
            )
        return {
            "protocol": COMMIT_PROTOCOL_VERSION,
            "chain_id": self.ledger.genesis.chain_id,
            "height": current_height,
            "application_hash": self.application_hash(),
            "last_consensus_block_hash": self.ledger.last_hash,
            "external_commit_count": commits,
            "pending_finalize": (
                {
                    "height": int(pending["height"]),
                    "request_hash": str(pending["request_hash"]),
                    "next_application_hash": str(pending["next_application_hash"]),
                    "consensus_block_hash": str(pending["consensus_block_hash"]),
                    "transaction_count": int(pending["transaction_count"]),
                    "created_at_ms": int(pending["created_at_ms"]),
                }
                if pending is not None
                else None
            ),
            "crash_safe_sqlite_commit": True,
            "idempotent_finalize_replay": True,
            "production_ready": False,
        }
