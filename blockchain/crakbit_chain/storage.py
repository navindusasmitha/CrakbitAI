from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .crypto import canonical_json, sha256_hex
from .genesis import Genesis
from .models import Block, Transaction, merkle_root


class LedgerError(ValueError):
    pass


class Ledger:
    def __init__(self, db_path: str | Path, genesis: Genesis):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.genesis = genesis
        self._init_db()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS accounts (
                    address TEXT PRIMARY KEY,
                    balance INTEGER NOT NULL,
                    nonce INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS blocks (
                    height INTEGER PRIMARY KEY,
                    hash TEXT UNIQUE NOT NULL,
                    body TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS transactions (
                    txid TEXT PRIMARY KEY,
                    height INTEGER NOT NULL,
                    body TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS local_votes (
                    height INTEGER NOT NULL,
                    round INTEGER NOT NULL,
                    block_hash TEXT NOT NULL,
                    PRIMARY KEY(height, round)
                );
                CREATE TABLE IF NOT EXISTS consensus_rounds (
                    height INTEGER PRIMARY KEY,
                    round INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS local_view_changes (
                    height INTEGER NOT NULL,
                    from_round INTEGER NOT NULL,
                    to_round INTEGER NOT NULL,
                    PRIMARY KEY(height, to_round)
                );
                CREATE TABLE IF NOT EXISTS seen_proposals (
                    height INTEGER NOT NULL,
                    round INTEGER NOT NULL,
                    proposer TEXT NOT NULL,
                    block_hash TEXT NOT NULL,
                    PRIMARY KEY(height, round, proposer)
                );
                CREATE TABLE IF NOT EXISTS equivocation_evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    height INTEGER NOT NULL,
                    round INTEGER NOT NULL,
                    offender TEXT NOT NULL,
                    first_hash TEXT NOT NULL,
                    second_hash TEXT NOT NULL,
                    observed_at_ms INTEGER NOT NULL,
                    UNIQUE(height, round, offender, first_hash, second_hash)
                );
                """
            )
            fingerprint = self.genesis.fingerprint()
            existing = conn.execute("SELECT value FROM metadata WHERE key='genesis_fingerprint'").fetchone()
            if existing is None:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    conn.execute("INSERT INTO metadata(key,value) VALUES('genesis_fingerprint', ?)", (fingerprint,))
                    conn.execute("INSERT INTO metadata(key,value) VALUES('height', '0')")
                    conn.execute("INSERT INTO metadata(key,value) VALUES('last_hash', ?)", ("0" * 64,))
                    for address, amount in self.genesis.allocations.items():
                        conn.execute(
                            "INSERT INTO accounts(address,balance,nonce) VALUES(?,?,0)",
                            (address, amount),
                        )
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
            elif existing["value"] != fingerprint:
                raise LedgerError("database genesis does not match configured genesis")

    @property
    def height(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT value FROM metadata WHERE key='height'").fetchone()["value"])

    @property
    def last_hash(self) -> str:
        with self.connect() as conn:
            return str(conn.execute("SELECT value FROM metadata WHERE key='last_hash'").fetchone()["value"])

    def account(self, address: str) -> dict[str, int | str]:
        with self.connect() as conn:
            row = conn.execute("SELECT balance, nonce FROM accounts WHERE address=?", (address,)).fetchone()
            if row is None:
                return {"address": address, "balance": 0, "nonce": 0}
            return {"address": address, "balance": int(row["balance"]), "nonce": int(row["nonce"])}

    def consensus_round(self, height: int) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT round FROM consensus_rounds WHERE height=?", (height,)).fetchone()
            return int(row["round"]) if row else 0

    def record_consensus_round(self, height: int, round_number: int) -> None:
        if height < 1 or round_number < 0:
            raise LedgerError("invalid consensus height/round")
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT round FROM consensus_rounds WHERE height=?",
                    (height,),
                ).fetchone()
                if row is None:
                    conn.execute(
                        "INSERT INTO consensus_rounds(height,round) VALUES(?,?)",
                        (height, round_number),
                    )
                elif round_number > int(row["round"]):
                    conn.execute(
                        "UPDATE consensus_rounds SET round=? WHERE height=?",
                        (round_number, height),
                    )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def local_vote_hash(self, height: int, round_number: int) -> str | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT block_hash FROM local_votes WHERE height=? AND round=?",
                (height, round_number),
            ).fetchone()
            return str(row["block_hash"]) if row else None

    def latest_local_vote(self, height: int) -> tuple[int, str] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT round, block_hash FROM local_votes WHERE height=? ORDER BY round DESC LIMIT 1",
                (height,),
            ).fetchone()
            if row is None:
                return None
            return int(row["round"]), str(row["block_hash"])

    def record_local_vote(self, height: int, round_number: int, block_hash: str) -> None:
        """Persist same-height/same-round anti-double-vote state before signing."""
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT block_hash FROM local_votes WHERE height=? AND round=?",
                    (height, round_number),
                ).fetchone()
                if row is not None and str(row["block_hash"]) != block_hash:
                    raise LedgerError("persistent anti-double-vote check rejected conflicting block")
                if row is None:
                    conn.execute(
                        "INSERT INTO local_votes(height,round,block_hash) VALUES(?,?,?)",
                        (height, round_number, block_hash),
                    )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def record_local_view_change(self, height: int, from_round: int, to_round: int) -> None:
        if to_round != from_round + 1:
            raise LedgerError("view change must advance exactly one round")
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT from_round FROM local_view_changes WHERE height=? AND to_round=?",
                    (height, to_round),
                ).fetchone()
                if row is not None and int(row["from_round"]) != from_round:
                    raise LedgerError("conflicting local view-change record")
                if row is None:
                    conn.execute(
                        "INSERT INTO local_view_changes(height,from_round,to_round) VALUES(?,?,?)",
                        (height, from_round, to_round),
                    )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def local_view_change_count(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) AS n FROM local_view_changes").fetchone()["n"])

    def record_seen_proposal(self, block: Block) -> dict | None:
        """Record a valid signed proposal and persist evidence if the proposer equivocates."""
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT block_hash FROM seen_proposals WHERE height=? AND round=? AND proposer=?",
                    (block.height, block.round, block.proposer),
                ).fetchone()
                if row is None:
                    conn.execute(
                        "INSERT INTO seen_proposals(height,round,proposer,block_hash) VALUES(?,?,?,?)",
                        (block.height, block.round, block.proposer, block.block_hash),
                    )
                    conn.execute("COMMIT")
                    return None

                first_hash = str(row["block_hash"])
                if first_hash == block.block_hash:
                    conn.execute("COMMIT")
                    return None

                first, second = sorted((first_hash, block.block_hash))
                observed_at_ms = int(time.time() * 1000)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO equivocation_evidence(
                        height,round,offender,first_hash,second_hash,observed_at_ms
                    ) VALUES(?,?,?,?,?,?)
                    """,
                    (block.height, block.round, block.proposer, first, second, observed_at_ms),
                )
                conn.execute("COMMIT")
                return {
                    "kind": "conflicting_block_proposal",
                    "height": block.height,
                    "round": block.round,
                    "offender": block.proposer,
                    "first_hash": first,
                    "second_hash": second,
                    "observed_at_ms": observed_at_ms,
                }
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def evidence_count(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) AS n FROM equivocation_evidence").fetchone()["n"])

    def list_evidence(self, limit: int = 100) -> list[dict]:
        limit = max(1, min(int(limit), 1000))
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT height,round,offender,first_hash,second_hash,observed_at_ms
                FROM equivocation_evidence
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [
                {
                    "kind": "conflicting_block_proposal",
                    "height": int(row["height"]),
                    "round": int(row["round"]),
                    "offender": str(row["offender"]),
                    "first_hash": str(row["first_hash"]),
                    "second_hash": str(row["second_hash"]),
                    "observed_at_ms": int(row["observed_at_ms"]),
                }
                for row in rows
            ]

    def prune_consensus_state(self, finalized_height: int) -> None:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("DELETE FROM local_votes WHERE height<=?", (finalized_height,))
                conn.execute("DELETE FROM local_view_changes WHERE height<=?", (finalized_height,))
                conn.execute("DELETE FROM consensus_rounds WHERE height<=?", (finalized_height,))
                conn.execute("DELETE FROM seen_proposals WHERE height<=?", (finalized_height,))
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def local_vote_count(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) AS n FROM local_votes").fetchone()["n"])

    def _ensure_account(self, conn: sqlite3.Connection, address: str) -> None:
        conn.execute(
            "INSERT OR IGNORE INTO accounts(address,balance,nonce) VALUES(?,0,0)",
            (address,),
        )

    def validate_transaction(self, tx: Transaction, conn: sqlite3.Connection | None = None) -> None:
        if tx.chain_id != self.genesis.chain_id:
            raise LedgerError("wrong chain_id")
        if tx.amount <= 0:
            raise LedgerError("amount must be positive")
        if tx.fee < self.genesis.min_fee:
            raise LedgerError("fee below network minimum")
        if tx.sender == tx.recipient:
            raise LedgerError("sender and recipient must differ")
        if not tx.verify_signature():
            raise LedgerError("invalid transaction signature")
        owns_conn = conn is None
        if conn is None:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT balance, nonce FROM accounts WHERE address=?", (tx.sender,)).fetchone()
            balance = int(row["balance"]) if row else 0
            nonce = int(row["nonce"]) if row else 0
            if tx.nonce != nonce + 1:
                raise LedgerError(f"invalid nonce: expected {nonce + 1}")
            if balance < tx.amount + tx.fee:
                raise LedgerError("insufficient balance")
        finally:
            if owns_conn:
                conn.close()

    def _validate_transaction_fields(self, tx: Transaction) -> None:
        if tx.chain_id != self.genesis.chain_id:
            raise LedgerError("wrong chain_id")
        if tx.amount <= 0:
            raise LedgerError("amount must be positive")
        if tx.fee < self.genesis.min_fee:
            raise LedgerError("fee below network minimum")
        if tx.sender == tx.recipient:
            raise LedgerError("sender and recipient must differ")
        if not tx.verify_signature():
            raise LedgerError("invalid transaction signature")

    def simulate_state_root(self, txs: list[Transaction], fee_recipient: str) -> str:
        with self.connect() as conn:
            state = {
                row["address"]: [int(row["balance"]), int(row["nonce"])]
                for row in conn.execute("SELECT address,balance,nonce FROM accounts")
            }
        for tx in txs:
            self._validate_transaction_fields(tx)
            sender = state.setdefault(tx.sender, [0, 0])
            recipient = state.setdefault(tx.recipient, [0, 0])
            fees = state.setdefault(fee_recipient, [0, 0])
            if tx.nonce != sender[1] + 1:
                raise LedgerError(f"invalid nonce in simulated state: expected {sender[1] + 1}")
            if sender[0] < tx.amount + tx.fee:
                raise LedgerError("insufficient balance in simulated state")
            sender[0] -= tx.amount + tx.fee
            sender[1] += 1
            recipient[0] += tx.amount
            fees[0] += tx.fee
        return sha256_hex(canonical_json(sorted((addr, bal, nonce) for addr, (bal, nonce) in state.items())))

    def validate_view_change_certificate(self, block: Block) -> None:
        if block.round == 0:
            if block.view_changes:
                raise LedgerError("round-zero block must not include a view-change certificate")
            return

        seen: set[str] = set()
        valid = 0
        for change in block.view_changes:
            if change.voter in seen:
                raise LedgerError("duplicate validator view-change message")
            seen.add(change.voter)
            if change.chain_id != block.chain_id:
                raise LedgerError("view-change chain_id mismatch")
            if change.height != block.height:
                raise LedgerError("view-change height mismatch")
            if change.from_round != block.round - 1 or change.to_round != block.round:
                raise LedgerError("view-change round transition mismatch")
            validator = self.genesis.validator_by_address(change.voter)
            if validator is None:
                raise LedgerError("view-change from unknown validator")
            if validator.public_key != change.public_key:
                raise LedgerError("view-change public key mismatch")
            if change.locked_round < -1 or change.locked_round >= change.to_round:
                raise LedgerError("invalid view-change lock round")
            if change.locked_round == -1 and change.locked_block_hash:
                raise LedgerError("unlocked view-change must not carry a block hash")
            if change.locked_round >= 0 and len(change.locked_block_hash) != 64:
                raise LedgerError("locked view-change must carry a 64-character block hash")
            if not change.verify_signature():
                raise LedgerError("invalid validator view-change signature")
            valid += 1

        if valid < self.genesis.quorum_size:
            raise LedgerError(
                f"insufficient view-change quorum: have {valid}, need {self.genesis.quorum_size}"
            )

    def validate_block_proposal(self, block: Block) -> None:
        """Validate a proposed block before a validator signs a commit vote."""
        expected_height = self.height + 1
        if block.chain_id != self.genesis.chain_id:
            raise LedgerError("wrong block chain_id")
        if block.height != expected_height:
            raise LedgerError(f"unexpected block height: expected {expected_height}")
        if block.previous_hash != self.last_hash:
            raise LedgerError("previous hash mismatch")
        if block.round < 0:
            raise LedgerError("invalid consensus round")
        expected_validator = self.genesis.proposer_for_height_round(block.height, block.round)
        if block.proposer != expected_validator.address or block.proposer_public_key != expected_validator.public_key:
            raise LedgerError("unexpected proposer for consensus round")
        if not block.verify_signature():
            raise LedgerError("invalid block signature")
        self.validate_view_change_certificate(block)
        expected_tx_root = merkle_root([tx.txid for tx in block.transactions])
        if block.tx_root != expected_tx_root:
            raise LedgerError("transaction Merkle root mismatch")
        expected_root = self.simulate_state_root(block.transactions, block.proposer)
        if block.state_root != expected_root:
            raise LedgerError("state root mismatch")

    def validate_commit_votes(self, block: Block) -> None:
        seen: set[str] = set()
        valid_votes = 0
        for vote in block.commit_votes:
            if vote.voter in seen:
                raise LedgerError("duplicate validator commit vote")
            seen.add(vote.voter)
            if vote.chain_id != block.chain_id:
                raise LedgerError("commit vote chain_id mismatch")
            if vote.height != block.height or vote.round != block.round:
                raise LedgerError("commit vote height/round mismatch")
            if vote.block_hash != block.block_hash:
                raise LedgerError("commit vote block hash mismatch")
            validator = self.genesis.validator_by_address(vote.voter)
            if validator is None:
                raise LedgerError("commit vote from unknown validator")
            if vote.public_key != validator.public_key:
                raise LedgerError("commit vote public key mismatch")
            if not vote.verify_signature():
                raise LedgerError("invalid validator commit signature")
            valid_votes += 1
        if valid_votes < self.genesis.quorum_size:
            raise LedgerError(
                f"insufficient commit quorum: have {valid_votes}, need {self.genesis.quorum_size}"
            )

    def apply_block(self, block: Block) -> None:
        self.validate_block_proposal(block)
        self.validate_commit_votes(block)

        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                for tx in block.transactions:
                    self.validate_transaction(tx, conn)
                    self._ensure_account(conn, tx.sender)
                    self._ensure_account(conn, tx.recipient)
                    self._ensure_account(conn, block.proposer)
                    conn.execute(
                        "UPDATE accounts SET balance=balance-?, nonce=nonce+1 WHERE address=?",
                        (tx.amount + tx.fee, tx.sender),
                    )
                    conn.execute("UPDATE accounts SET balance=balance+? WHERE address=?", (tx.amount, tx.recipient))
                    conn.execute("UPDATE accounts SET balance=balance+? WHERE address=?", (tx.fee, block.proposer))
                    conn.execute(
                        "INSERT INTO transactions(txid,height,body) VALUES(?,?,?)",
                        (tx.txid, block.height, json.dumps(tx.to_dict(), separators=(",", ":"))),
                    )
                body = json.dumps(block.to_dict(), separators=(",", ":"))
                conn.execute("INSERT INTO blocks(height,hash,body) VALUES(?,?,?)", (block.height, block.block_hash, body))
                conn.execute("UPDATE metadata SET value=? WHERE key='height'", (str(block.height),))
                conn.execute("UPDATE metadata SET value=? WHERE key='last_hash'", (block.block_hash,))
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def get_block(self, height: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT body FROM blocks WHERE height=?", (height,)).fetchone()
            return json.loads(row["body"]) if row else None

    def get_transaction(self, txid: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT body,height FROM transactions WHERE txid=?", (txid,)).fetchone()
            if not row:
                return None
            return {"height": int(row["height"]), "transaction": json.loads(row["body"])}
