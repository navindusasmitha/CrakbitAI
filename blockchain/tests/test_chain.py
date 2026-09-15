from __future__ import annotations

import json

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.genesis import Genesis
from crakbit_chain.models import (
    ATOMIC_UNITS,
    Block,
    PhaseVote,
    Transaction,
    ViewChange,
    merkle_root,
    now_ms,
)
from crakbit_chain.storage import Ledger, LedgerError


def make_genesis(tmp_path, validator_count: int = 1):
    validators = [KeyPair.generate() for _ in range(validator_count)]
    treasury = KeyPair.generate()
    receiver = KeyPair.generate()
    data = {
        "chain_id": "crakbit-test-1",
        "network_name": "Crakbit Test",
        "symbol": "CRKBIT",
        "decimals": 8,
        "max_supply": 21_000_000 * ATOMIC_UNITS,
        "block_time_ms": 100,
        "view_timeout_ms": 200,
        "min_fee": 1000,
        "validators": [
            {
                "name": f"validator-{index + 1}",
                "address": validator.address,
                "public_key": validator.public_key_b64,
                "peer_url": f"http://127.0.0.1:{9101 + index}",
            }
            for index, validator in enumerate(validators)
        ],
        "allocations": {treasury.address: 100 * ATOMIC_UNITS},
    }
    path = tmp_path / "genesis.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return Genesis.load(path), validators, treasury, receiver


def sign_phase_vote(key: KeyPair, block: Block, phase: str) -> PhaseVote:
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


def sign_view_change(
    key: KeyPair,
    genesis: Genesis,
    *,
    height: int,
    from_round: int,
    to_round: int,
    locked_round: int = -1,
    locked_block_hash: str = "",
) -> ViewChange:
    change = ViewChange(
        chain_id=genesis.chain_id,
        height=height,
        from_round=from_round,
        to_round=to_round,
        voter=key.address,
        public_key=key.public_key_b64,
        locked_round=locked_round,
        locked_block_hash=locked_block_hash,
    )
    change.signature = key.sign(change.signing_bytes())
    return change


def build_block(
    ledger: Ledger,
    genesis: Genesis,
    proposer: KeyPair,
    txs: list[Transaction],
    round_number: int = 0,
    view_changes: list[ViewChange] | None = None,
) -> Block:
    block = Block(
        chain_id=genesis.chain_id,
        height=ledger.height + 1,
        previous_hash=ledger.last_hash,
        timestamp=now_ms(),
        proposer=proposer.address,
        proposer_public_key=proposer.public_key_b64,
        transactions=txs,
        tx_root=merkle_root([tx.txid for tx in txs]),
        state_root=ledger.simulate_state_root(txs, proposer.address),
        round=round_number,
        view_changes=list(view_changes or []),
    )
    block.signature = proposer.sign(block.signing_bytes())
    return block


def finalize_for_test(block: Block, validators: list[KeyPair]) -> None:
    block.prevote_votes = [sign_phase_vote(key, block, "prevote") for key in validators]
    block.precommit_votes = [sign_phase_vote(key, block, "precommit") for key in validators]


def test_signed_transfer_requires_multiphase_finality(tmp_path):
    genesis, validators, treasury, receiver = make_genesis(tmp_path)
    validator = validators[0]
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

    block = build_block(ledger, genesis, validator, [tx])
    finalize_for_test(block, validators)
    ledger.apply_block(block)

    assert ledger.height == 1
    assert ledger.account(receiver.address)["balance"] == 5 * ATOMIC_UNITS
    assert ledger.account(treasury.address)["nonce"] == 1
    assert ledger.account(validator.address)["balance"] == 1000
    stored = ledger.get_block(1)
    assert len(stored["prevote_votes"]) == 1
    assert len(stored["precommit_votes"]) == 1


def test_three_validator_block_requires_prevote_quorum(tmp_path):
    genesis, validators, _, _ = make_genesis(tmp_path, validator_count=3)
    ledger = Ledger(tmp_path / "chain.db", genesis)
    block = build_block(ledger, genesis, validators[0], [])

    assert genesis.quorum_size == 3
    block.prevote_votes = [
        sign_phase_vote(validators[0], block, "prevote"),
        sign_phase_vote(validators[1], block, "prevote"),
    ]
    block.precommit_votes = [sign_phase_vote(key, block, "precommit") for key in validators]

    with pytest.raises(LedgerError, match="insufficient prevote quorum"):
        ledger.apply_block(block)


def test_three_validator_block_requires_precommit_quorum(tmp_path):
    genesis, validators, _, _ = make_genesis(tmp_path, validator_count=3)
    ledger = Ledger(tmp_path / "chain.db", genesis)
    block = build_block(ledger, genesis, validators[0], [])
    block.prevote_votes = [sign_phase_vote(key, block, "prevote") for key in validators]
    block.precommit_votes = [
        sign_phase_vote(validators[0], block, "precommit"),
        sign_phase_vote(validators[1], block, "precommit"),
    ]

    with pytest.raises(LedgerError, match="insufficient precommit quorum"):
        ledger.apply_block(block)


def test_wrong_phase_in_certificate_rejected(tmp_path):
    genesis, validators, _, _ = make_genesis(tmp_path, validator_count=3)
    ledger = Ledger(tmp_path / "chain.db", genesis)
    block = build_block(ledger, genesis, validators[0], [])
    block.prevote_votes = [sign_phase_vote(key, block, "prevote") for key in validators]
    block.prevote_votes[0].phase = "precommit"
    block.prevote_votes[0].signature = validators[0].sign(block.prevote_votes[0].signing_bytes())

    with pytest.raises(LedgerError, match="wrong vote phase"):
        ledger.validate_prevote_certificate(block)


def test_persistent_phase_vote_survives_restart_and_blocks_conflict(tmp_path):
    genesis, _, _, _ = make_genesis(tmp_path, validator_count=4)
    db_path = tmp_path / "chain.db"
    ledger = Ledger(db_path, genesis)
    first_hash = "a" * 64
    second_hash = "b" * 64

    ledger.record_phase_vote(1, 0, "prevote", first_hash)
    ledger.record_phase_vote(1, 0, "precommit", first_hash)

    reopened = Ledger(db_path, genesis)
    assert reopened.phase_vote_hash(1, 0, "prevote") == first_hash
    assert reopened.phase_vote_hash(1, 0, "precommit") == first_hash
    assert reopened.phase_vote_count("prevote") == 1
    assert reopened.phase_vote_count("precommit") == 1

    with pytest.raises(LedgerError, match="persistent prevote anti-double-vote"):
        reopened.record_phase_vote(1, 0, "prevote", second_hash)
    with pytest.raises(LedgerError, match="persistent precommit anti-double-vote"):
        reopened.record_phase_vote(1, 0, "precommit", second_hash)


def test_consensus_lock_persists_and_rejects_conflict(tmp_path):
    genesis, _, _, _ = make_genesis(tmp_path, validator_count=4)
    db_path = tmp_path / "chain.db"
    ledger = Ledger(db_path, genesis)
    first_hash = "a" * 64
    second_hash = "b" * 64

    ledger.set_consensus_lock(1, 0, first_hash)
    reopened = Ledger(db_path, genesis)
    assert reopened.consensus_lock(1) == (0, first_hash)
    reopened.set_consensus_lock(1, 1, first_hash)
    assert reopened.consensus_lock(1) == (1, first_hash)

    with pytest.raises(LedgerError, match="consensus lock prevents conflicting block"):
        reopened.set_consensus_lock(1, 2, second_hash)


def test_certified_view_change_still_required_for_round_one(tmp_path):
    genesis, validators, _, _ = make_genesis(tmp_path, validator_count=3)
    ledger = Ledger(tmp_path / "chain.db", genesis)
    block = build_block(ledger, genesis, validators[1], [], round_number=1)

    with pytest.raises(LedgerError, match="insufficient view-change quorum"):
        ledger.validate_block_proposal(block)

    certificate = [
        sign_view_change(key, genesis, height=1, from_round=0, to_round=1)
        for key in validators
    ]
    block = build_block(
        ledger,
        genesis,
        validators[1],
        [],
        round_number=1,
        view_changes=certificate,
    )
    finalize_for_test(block, validators)
    ledger.apply_block(block)
    assert ledger.height == 1
    assert ledger.get_block(1)["round"] == 1


def test_invalid_precommit_signature_rejected(tmp_path):
    genesis, validators, _, _ = make_genesis(tmp_path, validator_count=3)
    ledger = Ledger(tmp_path / "chain.db", genesis)
    block = build_block(ledger, genesis, validators[0], [])
    block.prevote_votes = [sign_phase_vote(key, block, "prevote") for key in validators]
    block.precommit_votes = [sign_phase_vote(key, block, "precommit") for key in validators]
    block.precommit_votes[1].signature = block.precommit_votes[0].signature

    with pytest.raises(LedgerError, match="invalid validator precommit signature"):
        ledger.validate_precommit_certificate(block)


def test_conflicting_signed_proposals_create_equivocation_evidence(tmp_path):
    genesis, validators, _, _ = make_genesis(tmp_path, validator_count=4)
    ledger = Ledger(tmp_path / "chain.db", genesis)
    proposer = validators[0]

    first = build_block(ledger, genesis, proposer, [], round_number=0)
    ledger.validate_block_proposal(first)
    assert ledger.record_seen_proposal(first) is None

    second = build_block(ledger, genesis, proposer, [], round_number=0)
    second.timestamp = first.timestamp + 1
    second.signature = proposer.sign(second.signing_bytes())
    ledger.validate_block_proposal(second)
    evidence = ledger.record_seen_proposal(second)

    assert evidence is not None
    assert evidence["offender"] == proposer.address
    assert evidence["first_hash"] != evidence["second_hash"]
    assert ledger.evidence_count() == 1


def test_consensus_event_journal_records_votes_locks_and_finalization(tmp_path):
    genesis, validators, _, _ = make_genesis(tmp_path)
    ledger = Ledger(tmp_path / "chain.db", genesis)
    block = build_block(ledger, genesis, validators[0], [])

    ledger.record_phase_vote(1, 0, "prevote", block.block_hash)
    ledger.record_phase_vote(1, 0, "precommit", block.block_hash)
    ledger.set_consensus_lock(1, 0, block.block_hash)
    finalize_for_test(block, validators)
    ledger.apply_block(block)

    events = ledger.list_consensus_events(20)
    event_types = {item["event_type"] for item in events}
    assert "local_prevote" in event_types
    assert "local_precommit" in event_types
    assert "lock" in event_types
    assert "finalized" in event_types


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

    with pytest.raises(ValueError):
        ledger.validate_transaction(tx)
