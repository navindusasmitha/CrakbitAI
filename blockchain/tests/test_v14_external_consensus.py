from __future__ import annotations

import json

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.external_commit import ExternalExecutionStore, deterministic_fee_recipient
from crakbit_chain.genesis import Genesis
from crakbit_chain.genesis_ceremony import add_attestation, build_ceremony, verify_ceremony
from crakbit_chain.models import ATOMIC_UNITS, Transaction
from crakbit_chain.storage import Ledger, LedgerError


def make_genesis(tmp_path):
    validators = [KeyPair.generate() for _ in range(4)]
    treasury = KeyPair.generate()
    receiver = KeyPair.generate()
    data = {
        "chain_id": "crakbit-v14-test-1",
        "network_name": "Crakbit v0.14 Test",
        "symbol": "CRKBIT",
        "decimals": 8,
        "max_supply": 21_000_000 * ATOMIC_UNITS,
        "block_time_ms": 100,
        "view_timeout_ms": 200,
        "min_fee": 1000,
        "validators": [
            {
                "name": f"validator-{index + 1}",
                "address": key.address,
                "public_key": key.public_key_b64,
                "peer_url": f"https://validator-{index + 1}.example:9101",
            }
            for index, key in enumerate(validators)
        ],
        "allocations": {treasury.address: 100 * ATOMIC_UNITS},
    }
    path = tmp_path / "genesis.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, Genesis.load(path), validators, treasury, receiver


def signed_tx(genesis, sender, receiver, nonce, amount=5 * ATOMIC_UNITS):
    tx = Transaction(
        chain_id=genesis.chain_id,
        sender=sender.address,
        recipient=receiver.address,
        amount=amount,
        fee=genesis.min_fee,
        nonce=nonce,
        public_key=sender.public_key_b64,
        memo="external-consensus-test",
    )
    tx.signature = sender.sign(tx.signing_bytes())
    return tx


def test_external_finalize_is_staged_then_atomically_committed(tmp_path):
    _, genesis, _, treasury, receiver = make_genesis(tmp_path)
    ledger = Ledger(tmp_path / "external" / "chain.sqlite3", genesis)
    store = ExternalExecutionStore(ledger)
    tx = signed_tx(genesis, treasury, receiver, 1)
    block_hash = "ab" * 32

    staged = store.stage_finalize(
        height=1,
        consensus_block_hash=block_hash,
        transactions=[tx.to_dict()],
    )
    assert staged["staged"] is True
    assert staged["state_mutated"] is False
    assert ledger.height == 0
    assert ledger.account(receiver.address)["balance"] == 0

    replay = store.stage_finalize(
        height=1,
        consensus_block_hash=block_hash,
        transactions=[tx.to_dict()],
    )
    assert replay["idempotent"] is True
    assert replay["request_hash"] == staged["request_hash"]

    with pytest.raises(LedgerError, match="conflicting external finalize"):
        store.stage_finalize(
            height=1,
            consensus_block_hash="cd" * 32,
            transactions=[tx.to_dict()],
        )

    committed = store.commit_pending()
    assert committed["committed"] is True
    assert committed["application_hash"] == staged["next_application_hash"]
    assert ledger.height == 1
    assert ledger.last_hash == block_hash
    assert ledger.account(receiver.address)["balance"] == 5 * ATOMIC_UNITS
    fee_pool = deterministic_fee_recipient(genesis.chain_id)
    assert ledger.account(fee_pool)["balance"] == genesis.min_fee

    second_commit = store.commit_pending()
    assert second_commit["committed"] is False
    assert second_commit["idempotent"] is True
    assert second_commit["height"] == 1


def test_pending_finalize_survives_process_restart(tmp_path):
    _, genesis, _, treasury, receiver = make_genesis(tmp_path)
    db_path = tmp_path / "external" / "chain.sqlite3"
    ledger = Ledger(db_path, genesis)
    store = ExternalExecutionStore(ledger)
    tx1 = signed_tx(genesis, treasury, receiver, 1)
    store.stage_finalize(
        height=1,
        consensus_block_hash="11" * 32,
        transactions=[tx1.to_dict()],
    )

    restarted_ledger = Ledger(db_path, genesis)
    restarted_store = ExternalExecutionStore(restarted_ledger)
    assert restarted_store.status()["pending_finalize"]["height"] == 1
    result = restarted_store.commit_pending()
    assert result["committed"] is True
    assert restarted_ledger.height == 1


def test_external_execution_refuses_existing_research_chain_db(tmp_path):
    _, genesis, validators, treasury, receiver = make_genesis(tmp_path)
    ledger = Ledger(tmp_path / "mixed" / "chain.sqlite3", genesis)
    with ledger.connect() as conn:
        conn.execute("UPDATE metadata SET value='1' WHERE key='height'")
    with pytest.raises(LedgerError, match="dedicated fresh data directory"):
        ExternalExecutionStore(ledger)


def test_genesis_ceremony_requires_validator_quorum(tmp_path):
    genesis_path, genesis, validators, _, _ = make_genesis(tmp_path)
    ceremony = build_ceremony(genesis_path)
    key_paths = []
    for index, key in enumerate(validators):
        path = tmp_path / f"validator-{index + 1}.json"
        key.save(path)
        key_paths.append(path)

    ceremony = add_attestation(ceremony, key_paths[0])
    ceremony = add_attestation(ceremony, key_paths[1])
    with pytest.raises(ValueError, match="insufficient ceremony quorum"):
        verify_ceremony(ceremony, genesis_path=genesis_path)

    ceremony = add_attestation(ceremony, key_paths[2])
    verified = verify_ceremony(ceremony, genesis_path=genesis_path)
    assert verified["valid"] is True
    assert verified["valid_attestations"] == 3
    assert verified["required_quorum"] == genesis.quorum_size == 3
    assert verified["quorum_reached"] is True
