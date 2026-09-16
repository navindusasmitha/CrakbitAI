from __future__ import annotations

import json
from threading import Lock

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.genesis import Genesis
from crakbit_chain.limits import FixedWindowLimiter, LimitConfig, install_node_limits
from crakbit_chain.models import ATOMIC_UNITS, Transaction
from crakbit_chain.storage import Ledger, LedgerError


class FakeNode:
    """Minimal node surface required by install_node_limits, without API import side effects."""

    def __init__(self, ledger: Ledger):
        self.ledger = ledger
        self.genesis = ledger.genesis
        self.mempool: dict[str, Transaction] = {}
        self.lock = Lock()

    def _select_transactions(self, limit: int = 1000) -> list[Transaction]:
        with self.lock:
            txs = list(self.mempool.values())[:limit]
        valid: list[Transaction] = []
        for tx in txs:
            try:
                self.ledger.validate_transaction(tx)
                valid.append(tx)
            except LedgerError:
                with self.lock:
                    self.mempool.pop(tx.txid, None)
        return valid


def make_node(tmp_path):
    validator = KeyPair.generate()
    sender1 = KeyPair.generate()
    sender2 = KeyPair.generate()
    receiver = KeyPair.generate()

    genesis_path = tmp_path / "genesis.json"
    genesis_path.write_text(
        json.dumps(
            {
                "chain_id": "crakbit-v10-test",
                "network_name": "Crakbit v0.10 Test",
                "symbol": "CRKBIT",
                "decimals": 8,
                "max_supply": 21_000_000 * ATOMIC_UNITS,
                "block_time_ms": 100,
                "view_timeout_ms": 200,
                "min_fee": 1000,
                "validators": [
                    {
                        "name": "validator-1",
                        "address": validator.address,
                        "public_key": validator.public_key_b64,
                        "peer_url": "http://127.0.0.1:9101",
                    }
                ],
                "allocations": {
                    sender1.address: 10 * ATOMIC_UNITS,
                    sender2.address: 10 * ATOMIC_UNITS,
                },
            }
        ),
        encoding="utf-8",
    )
    genesis = Genesis.load(genesis_path)
    ledger = Ledger(tmp_path / "data" / "chain.sqlite3", genesis)
    return FakeNode(ledger), sender1, sender2, receiver


def signed_tx(node, sender, receiver, *, memo=""):
    tx = Transaction(
        chain_id=node.genesis.chain_id,
        sender=sender.address,
        recipient=receiver.address,
        amount=ATOMIC_UNITS,
        fee=node.genesis.min_fee,
        nonce=1,
        public_key=sender.public_key_b64,
        memo=memo,
    )
    tx.signature = sender.sign(tx.signing_bytes())
    return tx


def test_fixed_window_rate_limiter_resets():
    limiter = FixedWindowLimiter(2, window_seconds=60)
    assert limiter.allow("client", now=1)[0] is True
    assert limiter.allow("client", now=2)[0] is True
    assert limiter.allow("client", now=3)[0] is False
    assert limiter.allow("client", now=61)[0] is True


def test_limit_config_rejects_block_limit_above_mempool():
    with pytest.raises(ValueError):
        LimitConfig(max_mempool_transactions=10, max_block_transactions=11).validate()


def test_mempool_capacity_is_enforced(tmp_path):
    node, sender1, sender2, receiver = make_node(tmp_path)
    config = LimitConfig(
        max_public_body_bytes=4096,
        max_internal_body_bytes=8192,
        public_tx_requests_per_minute=10,
        max_mempool_transactions=1,
        max_block_transactions=1,
        max_transaction_bytes=2048,
    )
    install_node_limits(node, config)

    node.submit_transaction(signed_tx(node, sender1, receiver))
    with pytest.raises(LedgerError, match="mempool capacity reached"):
        node.submit_transaction(signed_tx(node, sender2, receiver))


def test_transaction_serialized_size_is_bounded(tmp_path):
    node, sender1, _, receiver = make_node(tmp_path)
    config = LimitConfig(
        max_public_body_bytes=4096,
        max_internal_body_bytes=8192,
        public_tx_requests_per_minute=10,
        max_mempool_transactions=10,
        max_block_transactions=10,
        max_transaction_bytes=512,
    )
    install_node_limits(node, config)

    with pytest.raises(LedgerError, match="transaction exceeds maximum serialized size"):
        node.submit_transaction(signed_tx(node, sender1, receiver, memo="x" * 2000))
