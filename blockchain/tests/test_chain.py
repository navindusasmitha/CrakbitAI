from __future__ import annotations

import json

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.genesis import Genesis
from crakbit_chain.models import (
    ATOMIC_UNITS,
    Block,
    CommitVote,
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


def sign_vote(key: KeyPair, block: Block) -> CommitVote:
    vote = CommitVote(
        chain_id=block.chain_id,
        height=block.height,
        round=block.round,
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


def test_signed_transfer_and_finalized_block(tmp_path):
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
    block.commit_votes = [sign_vote(validator, block)]
    ledger.apply_block(block)

    assert ledger.height == 1
    assert ledger.account(receiver.address)["balance"] == 5 * ATOMIC_UNITS
    assert ledger.account(treasury.address)["nonce"] == 1
    assert ledger.account(validator.address)["balance"] == 1000


def test_three_validator_block_requires_supermajority_commit(tmp_path):
    genesis, validators, _, _ = make_genesis(tmp_path, validator_count=3)
    ledger = Ledger(tmp_path / "chain.db", genesis)
    proposer = validators[0]
    block = build_block(ledger, genesis, proposer, [])

    assert genesis.quorum_size == 3

    block.commit_votes = [sign_vote(validators[0], block), sign_vote(validators[1], block)]
    with pytest.raises(LedgerError, match="insufficient commit quorum"):
        ledger.apply_block(block)

    block.commit_votes = [sign_vote(key, block) for key in validators]
    ledger.apply_block(block)
    assert ledger.height == 1


def test_round_based_proposer_failover_requires_certified_view_change(tmp_path):
    genesis, validators, _, _ = make_genesis(tmp_path, validator_count=3)
    ledger = Ledger(tmp_path / "chain.db", genesis)

    assert genesis.proposer_for_height_round(1, 0).address == validators[0].address
    assert genesis.proposer_for_height_round(1, 1).address == validators[1].address
    assert genesis.proposer_for_height_round(1, 2).address == validators[2].address

    certificate = [
        sign_view_change(
            key,
            genesis,
            height=1,
            from_round=0,
            to_round=1,
        )
        for key in validators
    ]
    failover_block = build_block(
        ledger,
        genesis,
        validators[1],
        [],
        round_number=1,
        view_changes=certificate,
    )
    failover_block.commit_votes = [sign_vote(key, failover_block) for key in validators]
    ledger.apply_block(failover_block)

    assert ledger.height == 1
    assert ledger.get_block(1)["round"] == 1
    assert len(ledger.get_block(1)["view_changes"]) == 3


def test_round_one_without_view_change_quorum_rejected(tmp_path):
    genesis, validators, _, _ = make_genesis(tmp_path, validator_count=3)
    ledger = Ledger(tmp_path / "chain.db", genesis)
    block = build_block(ledger, genesis, validators[1], [], round_number=1)

    with pytest.raises(LedgerError, match="insufficient view-change quorum"):
        ledger.validate_block_proposal(block)


def test_invalid_view_change_signature_rejected(tmp_path):
    genesis, validators, _, _ = make_genesis(tmp_path, validator_count=3)
    ledger = Ledger(tmp_path / "chain.db", genesis)
    certificate = [
        sign_view_change(key, genesis, height=1, from_round=0, to_round=1)
        for key in validators
    ]
    certificate[1].signature = certificate[0].signature
    block = build_block(
        ledger,
        genesis,
        validators[1],
        [],
        round_number=1,
        view_changes=certificate,
    )

    with pytest.raises(LedgerError, match="invalid validator view-change signature"):
        ledger.validate_block_proposal(block)


def test_wrong_proposer_for_round_rejected(tmp_path):
    genesis, validators, _, _ = make_genesis(tmp_path, validator_count=3)
    ledger = Ledger(tmp_path / "chain.db", genesis)
    certificate = [
        sign_view_change(key, genesis, height=1, from_round=0, to_round=1)
        for key in validators
    ]
    wrong = build_block(
        ledger,
        genesis,
        validators[0],
        [],
        round_number=1,
        view_changes=certificate,
    )
    wrong.commit_votes = [sign_vote(key, wrong) for key in validators]

    with pytest.raises(LedgerError, match="unexpected proposer for consensus round"):
        ledger.apply_block(wrong)


def test_persistent_local_vote_and_consensus_round_survive_restart(tmp_path):
    genesis, _, _, _ = make_genesis(tmp_path, validator_count=4)
    db_path = tmp_path / "chain.db"
    ledger = Ledger(db_path, genesis)
    first_hash = "a" * 64
    second_hash = "b" * 64

    ledger.record_local_vote(1, 0, first_hash)
    ledger.record_consensus_round(1, 1)
    ledger.record_local_view_change(1, 0, 1)
    assert ledger.local_vote_hash(1, 0) == first_hash
    assert ledger.latest_local_vote(1) == (0, first_hash)

    reopened = Ledger(db_path, genesis)
    assert reopened.local_vote_hash(1, 0) == first_hash
    assert reopened.consensus_round(1) == 1
    assert reopened.local_view_change_count() == 1

    with pytest.raises(LedgerError, match="persistent anti-double-vote"):
        reopened.record_local_vote(1, 0, second_hash)


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
    assert ledger.list_evidence(10)[0]["height"] == 1


def test_duplicate_commit_vote_rejected(tmp_path):
    genesis, validators, _, _ = make_genesis(tmp_path, validator_count=3)
    ledger = Ledger(tmp_path / "chain.db", genesis)
    block = build_block(ledger, genesis, validators[0], [])
    vote = sign_vote(validators[0], block)
    block.commit_votes = [vote, vote, sign_vote(validators[1], block), sign_vote(validators[2], block)]

    with pytest.raises(LedgerError, match="duplicate validator commit vote"):
        ledger.apply_block(block)


def test_vote_for_wrong_block_rejected(tmp_path):
    genesis, validators, _, _ = make_genesis(tmp_path, validator_count=3)
    ledger = Ledger(tmp_path / "chain.db", genesis)
    block = build_block(ledger, genesis, validators[0], [])
    bad_vote = sign_vote(validators[1], block)
    bad_vote.block_hash = "0" * 64
    bad_vote.signature = validators[1].sign(bad_vote.signing_bytes())
    block.commit_votes = [sign_vote(validators[0], block), bad_vote, sign_vote(validators[2], block)]

    with pytest.raises(LedgerError, match="commit vote block hash mismatch"):
        ledger.apply_block(block)


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
