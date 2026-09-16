from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path


class DurableFixedWindowLimiter:
    """SQLite-backed fixed-window limiter with the same interface as FixedWindowLimiter.

    The limiter survives process restarts and can be shared by processes that can safely
    access the same SQLite file. It is still a single-site protection layer; a real
    horizontally scaled public deployment should additionally use a shared upstream
    limiter (for example at a load balancer/API gateway) rather than treating SQLite as
    a distributed rate-limit database.
    """

    def __init__(
        self,
        limit: int,
        window_seconds: int = 60,
        *,
        path: str | Path | None = None,
        namespace: str | None = None,
    ):
        if int(limit) <= 0 or int(window_seconds) <= 0:
            raise ValueError("rate-limit values must be positive")
        self.limit = int(limit)
        self.window_seconds = int(window_seconds)
        self.path = Path(
            path
            or os.environ.get(
                "CRAKBIT_RATE_LIMIT_DB",
                "runtime/public-rate-limits.sqlite3",
            )
        )
        self.namespace = (
            namespace
            or os.environ.get("CRAKBIT_RATE_LIMIT_NAMESPACE", "crakbit-public")
        ).strip() or "crakbit-public"
        self.path.parent.mkdir(parents=True, exist_ok=True)
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
                CREATE TABLE IF NOT EXISTS durable_rate_limits (
                    namespace TEXT NOT NULL,
                    client_key TEXT NOT NULL,
                    window_id INTEGER NOT NULL,
                    count INTEGER NOT NULL,
                    updated_at_ms INTEGER NOT NULL,
                    PRIMARY KEY(namespace, client_key)
                );
                CREATE INDEX IF NOT EXISTS idx_durable_rate_limits_window
                    ON durable_rate_limits(namespace, window_id);
                """
            )

    def allow(self, key: str, now: float | None = None) -> tuple[bool, int]:
        current = time.time() if now is None else float(now)
        window_id = int(current // self.window_seconds)
        now_ms = int(current * 1000)
        client_key = str(key or "unknown")[:256]

        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT window_id,count FROM durable_rate_limits "
                    "WHERE namespace=? AND client_key=?",
                    (self.namespace, client_key),
                ).fetchone()
                if row is None or int(row["window_id"]) != window_id:
                    count = 1
                    conn.execute(
                        "INSERT INTO durable_rate_limits(namespace,client_key,window_id,count,updated_at_ms) "
                        "VALUES(?,?,?,?,?) "
                        "ON CONFLICT(namespace,client_key) DO UPDATE SET "
                        "window_id=excluded.window_id,count=excluded.count,updated_at_ms=excluded.updated_at_ms",
                        (self.namespace, client_key, window_id, count, now_ms),
                    )
                else:
                    count = int(row["count"]) + 1
                    conn.execute(
                        "UPDATE durable_rate_limits SET count=?,updated_at_ms=? "
                        "WHERE namespace=? AND client_key=?",
                        (count, now_ms, self.namespace, client_key),
                    )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

        remaining = max(0, self.limit - count)
        return count <= self.limit, remaining

    def prune(self, *, keep_windows: int = 3, now: float | None = None) -> int:
        if keep_windows < 1:
            raise ValueError("keep_windows must be at least 1")
        current = time.time() if now is None else float(now)
        current_window = int(current // self.window_seconds)
        cutoff = current_window - int(keep_windows)
        with self.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM durable_rate_limits WHERE namespace=? AND window_id<?",
                (self.namespace, cutoff),
            )
            return int(cursor.rowcount if cursor.rowcount is not None else 0)

    def status(self) -> dict:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS clients, COALESCE(SUM(count),0) AS requests "
                "FROM durable_rate_limits WHERE namespace=?",
                (self.namespace,),
            ).fetchone()
        return {
            "backend": "sqlite",
            "path": str(self.path),
            "namespace": self.namespace,
            "limit": self.limit,
            "window_seconds": self.window_seconds,
            "tracked_clients": int(row["clients"]),
            "tracked_requests_in_retained_windows": int(row["requests"]),
            "survives_process_restart": True,
            "horizontally_distributed": False,
        }
