from __future__ import annotations

import json
from pathlib import Path

from crakbit_chain.comet_state_sync import CometStateSyncManager
from crakbit_chain.crypto import KeyPair
from crakbit_chain.external_commit_v16 import ExternalExecutionStoreV16
from crakbit_chain.genesis import Genesis
from crakbit_chain.models import ATOMIC_UNITS, Transaction
from crakbit_chain.storage import Ledger


def make_env(tmp_path: Path):
    validator = KeyPair.generate()
    treasury = KeyPair.generate()
    recipient = KeyPair.generate()
    data = {
        "chain_id": "crakbit-v17-test-1",
        "network_name": "Crakbit v0.17 Test",
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
        "allocations": {treasury.address: 100 * ATOMIC_UNITS},
    }
    genesis_path = tmp_path / "genesis.json"
    genesis_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return Genesis.load(genesis_path), treasury, recipient


def signed_tx(genesis: Genesis, sender: KeyPair, recipient: str, nonce: int = 1):
    tx = Transaction(
        chain_id=genesis.chain_id,
        sender=sender.address,
        recipient=recipient,
        amount=ATOMIC_UNITS,
        fee=genesis.min_fee,
        nonce=nonce,
        public_key=sender.public_key_b64,
        memo="v17-state-sync",
    )
    tx.signature = sender.sign(tx.signing_bytes())
    return tx


def committed_source(tmp_path: Path):
    genesis, treasury, recipient = make_env(tmp_path)
    source = tmp_path / "source"
    ledger = Ledger(source / "chain.sqlite3", genesis)
    store = ExternalExecutionStoreV16(ledger)
    tx = signed_tx(genesis, treasury, recipient.address)
    store.stage_finalize(
        height=1,
        consensus_block_hash="44" * 32,
        transactions=[tx.to_dict()],
    )
    committed = store.commit_pending()
    return genesis, source, committed


def test_comet_snapshot_materialization_is_deterministic(tmp_path):
    genesis, source, committed = committed_source(tmp_path)
    manager = CometStateSyncManager(genesis=genesis, data_dir=source, chunk_bytes=256)
    first = manager.materialize_latest()
    second = manager.materialize_latest()
    assert first["descriptor"] == second["descriptor"]
    assert first["metadata"]["application_hash"] == committed["application_hash"]
    assert first["descriptor"]["chunks"] >= 1
    assert manager.list_snapshots()[0]["hash_hex"] == first["descriptor"]["hash_hex"]


def test_comet_snapshot_offer_apply_and_restore(tmp_path):
    genesis, source, committed = committed_source(tmp_path)
    source_manager = CometStateSyncManager(genesis=genesis, data_dir=source, chunk_bytes=200)
    materialized = source_manager.materialize_latest()
    descriptor = materialized["descriptor"]

    target = tmp_path / "target"
    target_store = ExternalExecutionStoreV16(Ledger(target / "chain.sqlite3", genesis))
    assert target_store.status()["height"] == 0
    target_manager = CometStateSyncManager(genesis=genesis, data_dir=target, chunk_bytes=200)

    rejected = target_manager.offer_snapshot(
        descriptor,
        trusted_app_hash_hex="00" * 32,
    )
    assert rejected["result"] == "REJECT"

    offered = target_manager.offer_snapshot(
        descriptor,
        trusted_app_hash_hex=committed["application_hash"],
    )
    assert offered["result"] == "ACCEPT"

    last = None
    for index in range(descriptor["chunks"]):
        chunk = source_manager.load_chunk(
            height=descriptor["height"],
            format_id=descriptor["format"],
            chunk=index,
        )
        last = target_manager.apply_chunk(index=index, chunk=chunk, sender="source-peer")
        assert last["result"] == "ACCEPT"

    assert last is not None and "completed" in last
    restored = ExternalExecutionStoreV16(Ledger(target / "chain.sqlite3", genesis)).status()
    assert restored["height"] == 1
    assert restored["application_hash"] == committed["application_hash"]
    assert restored["snapshot_base"]["height"] == 1


def test_bad_chunk_requests_refetch(tmp_path):
    genesis, source, committed = committed_source(tmp_path)
    source_manager = CometStateSyncManager(genesis=genesis, data_dir=source, chunk_bytes=200)
    descriptor = source_manager.materialize_latest()["descriptor"]

    target = tmp_path / "bad-target"
    ExternalExecutionStoreV16(Ledger(target / "chain.sqlite3", genesis))
    target_manager = CometStateSyncManager(genesis=genesis, data_dir=target, chunk_bytes=200)
    assert target_manager.offer_snapshot(
        descriptor,
        trusted_app_hash_hex=committed["application_hash"],
    )["result"] == "ACCEPT"

    result = target_manager.apply_chunk(index=0, chunk=b"tampered", sender="bad-peer")
    assert result["result"] == "RETRY"
    assert result["refetch_chunks"] == [0]
    assert result["reject_senders"] == ["bad-peer"]
