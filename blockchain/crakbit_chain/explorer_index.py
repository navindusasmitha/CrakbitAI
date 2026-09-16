from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from .genesis import Genesis
from .storage import LedgerError


EXPLORER_INDEX_FORMAT = "crakbit-external-explorer-index-v1"


class ExternalExplorerIndex:
    """Dedicated read-optimized SQLite index for external-consensus history.

    The index is rebuilt/incrementally synchronized from the external application DB.
    It is intentionally separate from consensus/application state so public explorer
    queries do not need to scan or mutate the execution database.
    """

    def __init__(self, path: str | Path, genesis: Genesis):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.genesis = genesis
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS explorer_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS explorer_commits (
                    height INTEGER PRIMARY KEY,
                    consensus_block_hash TEXT NOT NULL,
                    application_hash TEXT NOT NULL,
                    transaction_root TEXT NOT NULL,
                    transaction_count INTEGER NOT NULL,
                    committed_at_ms INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS explorer_transactions (
                    txid TEXT PRIMARY KEY,
                    height INTEGER NOT NULL,
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    fee INTEGER NOT NULL,
                    nonce INTEGER NOT NULL,
                    memo TEXT NOT NULL,
                    body TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_explorer_transactions_height
                    ON explorer_transactions(height DESC);
                CREATE TABLE IF NOT EXISTS explorer_address_activity (
                    address TEXT NOT NULL,
                    txid TEXT NOT NULL,
                    height INTEGER NOT NULL,
                    direction TEXT NOT NULL,
                    counterparty TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    fee INTEGER NOT NULL,
                    PRIMARY KEY(address, txid)
                );
                CREATE INDEX IF NOT EXISTS idx_explorer_activity_address_height
                    ON explorer_address_activity(address, height DESC);
                CREATE TABLE IF NOT EXISTS explorer_accounts (
                    address TEXT PRIMARY KEY,
                    balance INTEGER NOT NULL,
                    nonce INTEGER NOT NULL
                );
                """
            )
            fingerprint = self.genesis.fingerprint()
            existing = conn.execute(
                "SELECT value FROM explorer_metadata WHERE key='genesis_fingerprint'"
            ).fetchone()
            if existing is None:
                conn.execute(
                    "INSERT INTO explorer_metadata(key,value) VALUES('format',?)",
                    (EXPLORER_INDEX_FORMAT,),
                )
                conn.execute(
                    "INSERT INTO explorer_metadata(key,value) VALUES('genesis_fingerprint',?)",
                    (fingerprint,),
                )
                conn.execute(
                    "INSERT INTO explorer_metadata(key,value) VALUES('chain_id',?)",
                    (self.genesis.chain_id,),
                )
                conn.execute(
                    "INSERT INTO explorer_metadata(key,value) VALUES('indexed_height','0')"
                )
                conn.execute(
                    "INSERT INTO explorer_metadata(key,value) VALUES('snapshot_base_height','0')"
                )
            elif str(existing["value"]) != fingerprint:
                raise LedgerError("explorer index genesis does not match configured genesis")

    def _metadata(self, conn: sqlite3.Connection, key: str, default: str = "") -> str:
        row = conn.execute(
            "SELECT value FROM explorer_metadata WHERE key=?", (key,)
        ).fetchone()
        return str(row["value"]) if row is not None else default

    def indexed_height(self) -> int:
        with self.connect() as conn:
            return int(self._metadata(conn, "indexed_height", "0"))

    def sync_from_source(self, source_data_dir: str | Path) -> dict[str, Any]:
        source_path = Path(source_data_dir) / "chain.sqlite3"
        if not source_path.is_file():
            raise FileNotFoundError(f"external application database not found: {source_path}")

        source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True, timeout=30)
        source.row_factory = sqlite3.Row
        try:
            fingerprint_row = source.execute(
                "SELECT value FROM metadata WHERE key='genesis_fingerprint'"
            ).fetchone()
            if fingerprint_row is None or str(fingerprint_row["value"]) != self.genesis.fingerprint():
                raise LedgerError("explorer source genesis fingerprint mismatch")
            owner = source.execute(
                "SELECT value FROM metadata WHERE key='execution_owner'"
            ).fetchone()
            if owner is None:
                raise LedgerError("explorer source is not an external execution database")
            height = int(
                source.execute("SELECT value FROM metadata WHERE key='height'").fetchone()["value"]
            )
            last_hash = str(
                source.execute("SELECT value FROM metadata WHERE key='last_hash'").fetchone()["value"]
            )
            base_row = source.execute(
                "SELECT value FROM metadata WHERE key='external_snapshot_base_height'"
            ).fetchone()
            snapshot_base = int(base_row["value"]) if base_row is not None else 0

            with self.connect() as index:
                index.execute("BEGIN IMMEDIATE")
                try:
                    current = int(self._metadata(index, "indexed_height", "0"))
                    rows = source.execute(
                        "SELECT height,consensus_block_hash,application_hash,transaction_root,"
                        "transaction_count,committed_at_ms FROM external_commits "
                        "WHERE height>? ORDER BY height ASC",
                        (current,),
                    ).fetchall()
                    new_commits = 0
                    new_transactions = 0
                    for commit in rows:
                        commit_height = int(commit["height"])
                        index.execute(
                            "INSERT OR REPLACE INTO explorer_commits("
                            "height,consensus_block_hash,application_hash,transaction_root,"
                            "transaction_count,committed_at_ms) VALUES(?,?,?,?,?,?)",
                            (
                                commit_height,
                                str(commit["consensus_block_hash"]),
                                str(commit["application_hash"]),
                                str(commit["transaction_root"]),
                                int(commit["transaction_count"]),
                                int(commit["committed_at_ms"]),
                            ),
                        )
                        tx_rows = source.execute(
                            "SELECT txid,body FROM transactions WHERE height=? ORDER BY rowid ASC",
                            (commit_height,),
                        ).fetchall()
                        for tx_row in tx_rows:
                            txid = str(tx_row["txid"])
                            body = json.loads(str(tx_row["body"]))
                            sender = str(body.get("sender", ""))
                            recipient = str(body.get("recipient", ""))
                            amount = int(body.get("amount", 0))
                            fee = int(body.get("fee", 0))
                            nonce = int(body.get("nonce", 0))
                            memo = str(body.get("memo", ""))
                            index.execute(
                                "INSERT OR REPLACE INTO explorer_transactions("
                                "txid,height,sender,recipient,amount,fee,nonce,memo,body) "
                                "VALUES(?,?,?,?,?,?,?,?,?)",
                                (
                                    txid,
                                    commit_height,
                                    sender,
                                    recipient,
                                    amount,
                                    fee,
                                    nonce,
                                    memo,
                                    json.dumps(body, separators=(",", ":")),
                                ),
                            )
                            if sender:
                                index.execute(
                                    "INSERT OR REPLACE INTO explorer_address_activity("
                                    "address,txid,height,direction,counterparty,amount,fee) "
                                    "VALUES(?,?,?,?,?,?,?)",
                                    (sender, txid, commit_height, "out", recipient, amount, fee),
                                )
                            if recipient:
                                index.execute(
                                    "INSERT OR REPLACE INTO explorer_address_activity("
                                    "address,txid,height,direction,counterparty,amount,fee) "
                                    "VALUES(?,?,?,?,?,?,?)",
                                    (recipient, txid, commit_height, "in", sender, amount, fee),
                                )
                            new_transactions += 1
                        new_commits += 1

                    index.execute("DELETE FROM explorer_accounts")
                    account_rows = source.execute(
                        "SELECT address,balance,nonce FROM accounts ORDER BY address ASC"
                    ).fetchall()
                    index.executemany(
                        "INSERT INTO explorer_accounts(address,balance,nonce) VALUES(?,?,?)",
                        [
                            (str(row["address"]), int(row["balance"]), int(row["nonce"]))
                            for row in account_rows
                        ],
                    )
                    effective_height = max(height, snapshot_base)
                    for key, value in (
                        ("indexed_height", str(effective_height)),
                        ("snapshot_base_height", str(snapshot_base)),
                        ("source_last_hash", last_hash),
                        ("last_sync_ms", str(int(time.time() * 1000))),
                    ):
                        index.execute(
                            "INSERT INTO explorer_metadata(key,value) VALUES(?,?) "
                            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                            (key, value),
                        )
                    index.execute("COMMIT")
                except Exception:
                    index.execute("ROLLBACK")
                    raise
        finally:
            source.close()

        return {
            "synced": True,
            "indexed_height": self.indexed_height(),
            "source_height": height,
            "snapshot_base_height": snapshot_base,
            "new_commits": new_commits,
            "new_transactions": new_transactions,
            "source_last_hash": last_hash,
        }

    def summary(self) -> dict[str, Any]:
        with self.connect() as conn:
            commits = int(conn.execute("SELECT COUNT(*) AS n FROM explorer_commits").fetchone()["n"])
            txs = int(conn.execute("SELECT COUNT(*) AS n FROM explorer_transactions").fetchone()["n"])
            accounts = int(conn.execute("SELECT COUNT(*) AS n FROM explorer_accounts").fetchone()["n"])
            issued = int(
                conn.execute("SELECT COALESCE(SUM(balance),0) AS n FROM explorer_accounts").fetchone()["n"]
            )
            return {
                "format": self._metadata(conn, "format", EXPLORER_INDEX_FORMAT),
                "chain_id": self.genesis.chain_id,
                "network": self.genesis.network_name,
                "symbol": self.genesis.symbol,
                "decimals": self.genesis.decimals,
                "indexed_height": int(self._metadata(conn, "indexed_height", "0")),
                "snapshot_base_height": int(self._metadata(conn, "snapshot_base_height", "0")),
                "source_last_hash": self._metadata(conn, "source_last_hash", ""),
                "last_sync_ms": int(self._metadata(conn, "last_sync_ms", "0") or 0),
                "indexed_commits": commits,
                "indexed_transactions": txs,
                "accounts": accounts,
                "issued_atomic_units": issued,
                "historical_commits_complete": int(
                    self._metadata(conn, "snapshot_base_height", "0")
                ) == 0,
            }

    def recent_commits(self, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM explorer_commits ORDER BY height DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def transaction(self, txid: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM explorer_transactions WHERE txid=?", (txid,)
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["body"] = json.loads(str(result["body"]))
        return result

    def account(self, address: str, limit: int = 50) -> dict[str, Any]:
        limit = max(1, min(int(limit), 100))
        with self.connect() as conn:
            state = conn.execute(
                "SELECT balance,nonce FROM explorer_accounts WHERE address=?", (address,)
            ).fetchone()
            rows = conn.execute(
                "SELECT txid,height,direction,counterparty,amount,fee "
                "FROM explorer_address_activity WHERE address=? "
                "ORDER BY height DESC, txid DESC LIMIT ?",
                (address, limit),
            ).fetchall()
        return {
            "account": {
                "address": address,
                "balance": int(state["balance"]) if state is not None else 0,
                "nonce": int(state["nonce"]) if state is not None else 0,
            },
            "activity": [dict(row) for row in rows],
            "fully_indexed_history": self.summary()["historical_commits_complete"],
        }
