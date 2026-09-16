from __future__ import annotations

import json

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.genesis import Genesis
from crakbit_chain.models import ATOMIC_UNITS, Block, PhaseVote, merkle_root, now_ms
from crakbit_chain.storage import Ledger, LedgerError


def make_context(tmp_path):
    validators = [KeyPair.generate() for _ in range(4)]
    treasury = KeyPair.generate()
    data = {
        "chain_id": "crakbit-v12-byzantine",
        "network_name": "Crakbit v0.12 Byzantine Fixtures",
        "symbol": "CRKBIT",
        "decimals": 8,
        "max_supply": 21_000_000 * ATOMIC_UNITS,
        "block_time_ms": 100,
        "view_timeout_ms": 200,
        "min_fee": 1000,
        "validators": [
            {
                "name": f"validator-{i + 1}",
                "address": key.address,
                "public_key": key.public_key_b64,
                "peer_url": f"http://127.0.0.1:{9101 + i}",
            }
            for i, key in enumerate(validators)
        ],
        "allocations": {treasury.address: 100 * ATOMIC_UNITS},
    }
    path = tmp_path / "genesis.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    genesis = Genesis.load(path)
    ledger = Ledger(tmp_path / "chain.sqlite3", genesis)
    proposer = validators[0]
    block = Block(
        chain_id=genesis.chain_id,
        height=1,
        previous_hash="0" * 64,
        timestamp=now_ms(),
        proposer=proposer.address,
        proposer_public_key=proposer.public_key_b64,
        transactions=[],
        tx_root=merkle_root([]),
        state_root=ledger.simulate_state_root([], proposer.address),
        round=0,
    )
    block.signature = proposer.sign(block.signing_bytes())
    return genesis, ledger, validators, block


def vote(key: KeyPair, block: Block, phase: str, *, block_hash: str | None = None) -> PhaseVote:
    item = PhaseVote(
        chain_id=block.chain_id,
        height=block.height,
        round=block.round,
        phase=phase,
        block_hash=block_hash or block.block_hash,
        voter=key.address,
        public_key=key.public_key_b64,
    )
    item.signature = key.sign(item.signing_bytes())
    return item


def test_duplicate_validator_vote_does_not_count_twice(tmp_path):
    _, ledger, validators, block = make_context(tmp_path)
    duplicated = vote(validators[0], block, "prevote")
    votes = [duplicated, duplicated, vote(validators[1], block, "prevote"), vote(validators[2], block, "prevote")]
    with pytest.raises(LedgerError, match="duplicate validator prevote vote"):
        ledger.validate_phase_certificate(block, "prevote", votes)


def test_vote_for_conflicting_block_hash_is_rejected(tmp_path):
    _, ledger, validators, block = make_context(tmp_path)
    votes = [
        vote(validators[0], block, "prevote"),
        vote(validators[1], block, "prevote"),
        vote(validators[2], block, "prevote", block_hash="f" * 64),
    ]
    with pytest.raises(LedgerError, match="prevote vote block hash mismatch"):
        ledger.validate_phase_certificate(block, "prevote", votes)


def test_forged_validator_identity_is_rejected(tmp_path):
    _, ledger, validators, block = make_context(tmp_path)
    outsider = KeyPair.generate()
    forged = vote(outsider, block, "precommit")
    votes = [
        vote(validators[0], block, "precommit"),
        vote(validators[1], block, "precommit"),
        forged,
    ]
    with pytest.raises(LedgerError, match="precommit vote from unknown validator"):
        ledger.validate_phase_certificate(block, "precommit", votes)
