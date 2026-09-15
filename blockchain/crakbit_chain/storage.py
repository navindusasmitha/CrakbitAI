from __future__ import annotations

import json
import sqlite3
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

    def simulate_state_root(self, txs: list[Transaction], fee_recipient: str) -> str:
        with self.connect() as conn:
            state = {
                row["address"]: [int(row["balance"]), int(row["nonce"])]
                for row in conn.execute("SELECT address,balance,nonce FROM accounts")
            }
        for tx in txs:
            sender = state.setdefault(tx.sender, [0, 0])
            recipient = state.setdefault(tx.recipient, [0, 0])
            fees = state.setdefault(fee_recipient, [0, 0])
            if tx.nonce != sender[1] + 1 or sender[0] < tx.amount + tx.fee:
                raise LedgerError("transaction invalid against simulated state")
            sender[0] -= tx.amount + tx.fee
            sender[1] += 1
            recipient[0] += tx.amount
            fees[0] += tx.fee
        return sha256_hex(canonical_json(sorted((addr, bal, nonce) for addr, (bal, nonce) in state.items())))

    def apply_block(self, block: Block) -> None:
        expected_height = self.height + 1
        if block.chain_id != self.genesis.chain_id:
            raise LedgerError("wrong block chain_id")
        if block.height != expected_height:
            raise LedgerError(f"unexpected block height: expected {expected_height}")
        if block.previous_hash != self.last_hash:
            raise LedgerError("previous hash mismatch")
        expected_validator = self.genesis.proposer_for_height(block.height)
        if block.proposer != expected_validator.address or block.proposer_public_key != expected_validator.public_key:
            raise LedgerError("unexpected proposer")
        if not block.verify_signature():
            raise LedgerError("invalid block signature")
        expected_tx_root = merkle_root([tx.txid for tx in block.transactions])
        if block.tx_root != expected_tx_root:
            raise LedgerError("transaction Merkle root mismatch")
        expected_root = self.simulate_state_root(block.transactions, block.proposer)
        if block.state_root != expected_root:
            raise LedgerError("state root mismatch")

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
