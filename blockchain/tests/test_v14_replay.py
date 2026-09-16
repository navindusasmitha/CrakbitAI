from __future__ import annotations

import json

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.external_commit import ExternalExecutionStore
from crakbit_chain.external_replay import replay_safe_stage_finalize
from crakbit_chain.genesis import Genesis
from crakbit_chain.models import ATOMIC_UNITS, Transaction
from crakbit_chain.storage import Ledger, LedgerError


def test_identical_finalize_replay_after_commit_is_idempotent(tmp_path):
    validator = KeyPair.generate()
    treasury = KeyPair.generate()
    receiver = KeyPair.generate()
    genesis_raw = {
        "chain_id": "crakbit-v14-replay-test",
        "network_name": "Crakbit v0.14 Replay Test",
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
                "peer_url": "https://validator.example:9101",
            }
        ],
        "allocations": {treasury.address: 20 * ATOMIC_UNITS},
    }
    genesis_path = tmp_path / "genesis.json"
    genesis_path.write_text(json.dumps(genesis_raw), encoding="utf-8")
    genesis = Genesis.load(genesis_path)
    ledger = Ledger(tmp_path / "external" / "chain.sqlite3", genesis)
    store = ExternalExecutionStore(ledger)

    tx = Transaction(
        chain_id=genesis.chain_id,
        sender=treasury.address,
        recipient=receiver.address,
        amount=ATOMIC_UNITS,
        fee=genesis.min_fee,
        nonce=1,
        public_key=treasury.public_key_b64,
        memo="replay",
    )
    tx.signature = treasury.sign(tx.signing_bytes())
    block_hash = "42" * 32

    first = replay_safe_stage_finalize(
        store,
        height=1,
        consensus_block_hash=block_hash,
        transactions=[tx.to_dict()],
    )
    store.commit_pending()

    replay = replay_safe_stage_finalize(
        store,
        height=1,
        consensus_block_hash=block_hash,
        transactions=[tx.to_dict()],
    )
    assert replay["already_committed"] is True
    assert replay["idempotent"] is True
    assert replay["request_hash"] == first["request_hash"]
    assert ledger.height == 1

    with pytest.raises(LedgerError, match="conflicting external finalize replay"):
        replay_safe_stage_finalize(
            store,
            height=1,
            consensus_block_hash="43" * 32,
            transactions=[tx.to_dict()],
        )
