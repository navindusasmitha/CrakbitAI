from __future__ import annotations

import json

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.genesis import Genesis
from crakbit_chain.history_archive import (
    export_history_archive,
    import_history_archive,
    verify_history_archive,
)
from crakbit_chain.models import ATOMIC_UNITS, Block, PhaseVote, Transaction, merkle_root, now_ms
from crakbit_chain.monitoring_auth import MonitoringAuthConfig
from crakbit_chain.storage import Ledger, LedgerError
from crakbit_chain.transport_security import load_pin_sets


def make_genesis(tmp_path):
    validator = KeyPair.generate()
    treasury = KeyPair.generate()
    receiver = KeyPair.generate()
    data = {
        "chain_id": "crakbit-v12-test-1",
        "network_name": "Crakbit v0.12 Test",
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
    path = tmp_path / "genesis.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return Genesis.load(path), validator, treasury, receiver


def phase_vote(key: KeyPair, block: Block, phase: str) -> PhaseVote:
    vote = PhaseVote(
        chain_id=block.chain_id,
        height=block.height,
        round=block.round,
        phase=phase,
        block_hash=block.block_hash,
        voter=key.address,
        public_key=key.public_key_b64,
    )
    vote.signature = key.sign(vote.signing_bytes())
    return vote


def add_one_block(ledger: Ledger, validator: KeyPair, treasury: KeyPair, receiver: KeyPair) -> Block:
    tx = Transaction(
        chain_id=ledger.genesis.chain_id,
        sender=treasury.address,
        recipient=receiver.address,
        amount=5 * ATOMIC_UNITS,
        fee=ledger.genesis.min_fee,
        nonce=1,
        public_key=treasury.public_key_b64,
        memo="archive-test",
    )
    tx.signature = treasury.sign(tx.signing_bytes())
    block = Block(
        chain_id=ledger.genesis.chain_id,
        height=1,
        previous_hash="0" * 64,
        timestamp=now_ms(),
        proposer=validator.address,
        proposer_public_key=validator.public_key_b64,
        transactions=[tx],
        tx_root=merkle_root([tx.txid]),
        state_root=ledger.simulate_state_root([tx], validator.address),
        round=0,
    )
    block.signature = validator.sign(block.signing_bytes())
    block.prevote_votes = [phase_vote(validator, block, "prevote")]
    block.precommit_votes = [phase_vote(validator, block, "precommit")]
    ledger.apply_block(block)
    return block


def test_history_archive_export_and_verify(tmp_path):
    genesis, validator, treasury, receiver = make_genesis(tmp_path)
    ledger = Ledger(tmp_path / "full" / "chain.sqlite3", genesis)
    block = add_one_block(ledger, validator, treasury, receiver)

    output = tmp_path / "history.json"
    exported = export_history_archive(ledger, output)
    artifact = json.loads(output.read_text(encoding="utf-8"))
    verified = verify_history_archive(artifact, genesis)

    assert exported["end_height"] == 1
    assert verified["valid"] is True
    assert verified["tip_hash"] == block.block_hash


def test_history_archive_rejects_payload_tamper(tmp_path):
    genesis, validator, treasury, receiver = make_genesis(tmp_path)
    ledger = Ledger(tmp_path / "full" / "chain.sqlite3", genesis)
    add_one_block(ledger, validator, treasury, receiver)
    output = tmp_path / "history.json"
    export_history_archive(ledger, output)
    artifact = json.loads(output.read_text(encoding="utf-8"))
    artifact["blocks"][0]["state_root"] = "f" * 64
    with pytest.raises(LedgerError):
        verify_history_archive(artifact, genesis)


def test_snapshot_node_can_backfill_verified_history_without_state_change(tmp_path):
    genesis, validator, treasury, receiver = make_genesis(tmp_path)
    source = Ledger(tmp_path / "source" / "chain.sqlite3", genesis)
    block = add_one_block(source, validator, treasury, receiver)
    archive_path = tmp_path / "history.json"
    export_history_archive(source, archive_path)
    artifact = json.loads(archive_path.read_text(encoding="utf-8"))

    recovered = Ledger(tmp_path / "recovered" / "chain.sqlite3", genesis)
    with source.connect() as src, recovered.connect() as dst:
        rows = src.execute("SELECT address,balance,nonce FROM accounts").fetchall()
        dst.execute("BEGIN IMMEDIATE")
        dst.execute("DELETE FROM accounts")
        for row in rows:
            dst.execute(
                "INSERT INTO accounts(address,balance,nonce) VALUES(?,?,?)",
                (row["address"], int(row["balance"]), int(row["nonce"])),
            )
        dst.execute("UPDATE metadata SET value='1' WHERE key='height'")
        dst.execute("UPDATE metadata SET value=? WHERE key='last_hash'", (block.block_hash,))
        dst.execute("INSERT INTO metadata(key,value) VALUES('snapshot_base_height','1')")
        dst.execute("INSERT INTO metadata(key,value) VALUES('snapshot_base_hash',?)", (block.block_hash,))
        dst.execute("INSERT INTO metadata(key,value) VALUES('snapshot_accounts_root',?)", (block.state_root,))
        dst.execute("COMMIT")

    before = recovered.account(treasury.address)
    result = import_history_archive(recovered, artifact)
    after = recovered.account(treasury.address)

    assert result["state_mutated"] is False
    assert result["inserted_blocks"] == 1
    assert before == after
    assert recovered.get_block(1)["hash"] == block.block_hash


def test_dual_pin_overlap_accepts_two_fingerprints(tmp_path):
    pins = tmp_path / "pins.json"
    first = "a" * 64
    second = "b" * 64
    pins.write_text(json.dumps({"crk1validator": [first, second]}), encoding="utf-8")
    loaded = load_pin_sets(pins)
    assert loaded["crk1validator"] == (first, second)


def test_monitoring_bearer_auth_comparison():
    config = MonitoringAuthConfig(token="x" * 32)
    assert config.accepts("Bearer " + ("x" * 32)) is True
    assert config.accepts("Bearer wrong") is False
    assert config.accepts(None) is False
