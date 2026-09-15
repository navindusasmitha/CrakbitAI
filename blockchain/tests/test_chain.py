from __future__ import annotations

import json

from crakbit_chain.crypto import KeyPair
from crakbit_chain.genesis import Genesis
from crakbit_chain.models import ATOMIC_UNITS, Block, Transaction, merkle_root, now_ms
from crakbit_chain.storage import Ledger


def make_genesis(tmp_path):
    validator = KeyPair.generate()
    treasury = KeyPair.generate()
    receiver = KeyPair.generate()
    data = {
        "chain_id": "crakbit-test-1",
        "network_name": "Crakbit Test",
        "symbol": "CRKBIT",
        "decimals": 8,
        "max_supply": 21_000_000 * ATOMIC_UNITS,
        "block_time_ms": 100,
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


def test_signed_transfer_and_block(tmp_path):
    genesis, validator, treasury, receiver = make_genesis(tmp_path)
    ledger = Ledger(tmp_path / "chain.db", genesis)
    tx = Transaction(
        chain_id=genesis.chain_id,
        sender=treasury.address,
        recipient=receiver.address,
        amount=5 * ATOMIC_UNITS,
        fee=1000,
        nonce=1,
        public_key=treasury.public_key_b64,
        memo="test",
    )
    tx.signature = treasury.sign(tx.signing_bytes())
    ledger.validate_transaction(tx)

    block = Block(
        chain_id=genesis.chain_id,
        height=1,
        previous_hash=ledger.last_hash,
        timestamp=now_ms(),
        proposer=validator.address,
        proposer_public_key=validator.public_key_b64,
        transactions=[tx],
        tx_root=merkle_root([tx.txid]),
        state_root=ledger.simulate_state_root([tx], validator.address),
    )
    block.signature = validator.sign(block.signing_bytes())
    ledger.apply_block(block)

    assert ledger.height == 1
    assert ledger.account(receiver.address)["balance"] == 5 * ATOMIC_UNITS
    assert ledger.account(treasury.address)["nonce"] == 1
    assert ledger.account(validator.address)["balance"] == 1000


def test_tampered_transaction_signature_rejected(tmp_path):
    genesis, _, treasury, receiver = make_genesis(tmp_path)
    ledger = Ledger(tmp_path / "chain.db", genesis)
    tx = Transaction(
        chain_id=genesis.chain_id,
        sender=treasury.address,
        recipient=receiver.address,
        amount=ATOMIC_UNITS,
        fee=1000,
        nonce=1,
        public_key=treasury.public_key_b64,
    )
    tx.signature = treasury.sign(tx.signing_bytes())
    tx.amount += 1

    try:
        ledger.validate_transaction(tx)
        assert False, "tampered transaction should fail"
    except ValueError:
        pass
