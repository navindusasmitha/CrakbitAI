from __future__ import annotations

import os
import time
from dataclasses import dataclass
from threading import Lock

from .crypto import canonical_json
from .storage import LedgerError


@dataclass(frozen=True)
class LimitConfig:
    max_public_body_bytes: int = 256 * 1024
    max_internal_body_bytes: int = 2 * 1024 * 1024
    public_tx_requests_per_minute: int = 60
    max_mempool_transactions: int = 5000
    max_block_transactions: int = 1000
    max_transaction_bytes: int = 64 * 1024

    @classmethod
    def from_env(cls) -> "LimitConfig":
        values = cls(
            max_public_body_bytes=int(os.environ.get("CRAKBIT_MAX_PUBLIC_BODY_BYTES", 256 * 1024)),
            max_internal_body_bytes=int(os.environ.get("CRAKBIT_MAX_INTERNAL_BODY_BYTES", 2 * 1024 * 1024)),
            public_tx_requests_per_minute=int(os.environ.get("CRAKBIT_PUBLIC_TX_RPM", 60)),
            max_mempool_transactions=int(os.environ.get("CRAKBIT_MAX_MEMPOOL_TXS", 5000)),
            max_block_transactions=int(os.environ.get("CRAKBIT_MAX_BLOCK_TXS", 1000)),
            max_transaction_bytes=int(os.environ.get("CRAKBIT_MAX_TX_BYTES", 64 * 1024)),
        )
        values.validate()
        return values

    def validate(self) -> None:
        for name, value in self.__dict__.items():
            if int(value) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.max_block_transactions > self.max_mempool_transactions:
            raise ValueError("max_block_transactions cannot exceed max_mempool_transactions")
        if self.max_transaction_bytes > self.max_public_body_bytes:
            raise ValueError("max_transaction_bytes cannot exceed max_public_body_bytes")


class FixedWindowLimiter:
    """Small per-process fixed-window limiter for the development RPC.

    This is intentionally a node-local protection layer. A public deployment should also
    enforce connection/request limits at a reverse proxy or load balancer.
    """

    def __init__(self, limit: int, window_seconds: int = 60):
        if limit <= 0 or window_seconds <= 0:
            raise ValueError("rate-limit values must be positive")
        self.limit = int(limit)
        self.window_seconds = int(window_seconds)
        self._entries: dict[str, tuple[int, int]] = {}
        self._lock = Lock()

    def allow(self, key: str, now: float | None = None) -> tuple[bool, int]:
        current = time.time() if now is None else float(now)
        window = int(current // self.window_seconds)
        with self._lock:
            existing_window, count = self._entries.get(key, (window, 0))
            if existing_window != window:
                existing_window, count = window, 0
            count += 1
            self._entries[key] = (existing_window, count)
            remaining = max(0, self.limit - count)
            return count <= self.limit, remaining


def install_node_limits(node, config: LimitConfig) -> None:
    """Install bounded transaction/mempool selection behavior on the current devnet node."""

    original_select = node._select_transactions

    def bounded_submit(tx):
        encoded_size = len(canonical_json(tx.to_dict()))
        if encoded_size > config.max_transaction_bytes:
            raise LedgerError(
                f"transaction exceeds maximum serialized size ({config.max_transaction_bytes} bytes)"
            )
        node.ledger.validate_transaction(tx)
        with node.lock:
            if len(node.mempool) >= config.max_mempool_transactions:
                raise LedgerError("mempool capacity reached")
            if any(item.sender == tx.sender for item in node.mempool.values()):
                raise LedgerError("sender already has a pending transaction")
            node.mempool[tx.txid] = tx
        return tx.txid

    def bounded_select(limit: int = 1000):
        return original_select(min(int(limit), config.max_block_transactions))

    node.submit_transaction = bounded_submit
    node._select_transactions = bounded_select
