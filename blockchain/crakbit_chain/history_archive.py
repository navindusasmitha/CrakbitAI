from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .crypto import canonical_json, sha256_hex
from .genesis import Genesis
from .models import Block, PhaseVote, ViewChange, merkle_root
from .storage import Ledger, LedgerError

ARCHIVE_FORMAT = "crakbit-history-archive-v1"


def _state_root(state: dict[str, list[int]]) -> str:
    return sha256_hex(
        canonical_json(sorted((address, values[0], values[1]) for address, values in state.items()))
    )


def _verify_view_changes(block: Block, genesis: Genesis) -> None:
    if block.round == 0:
        if block.view_changes:
            raise LedgerError("round-zero archived block contains view-change messages")
        return
    seen: set[str] = set()
    for change in block.view_changes:
        if not isinstance(change, ViewChange):
            raise LedgerError("invalid archived view-change message")
        if change.voter in seen:
            raise LedgerError("duplicate archived view-change validator")
        seen.add(change.voter)
        validator = genesis.validator_by_address(change.voter)
        if validator is None or validator.public_key != change.public_key:
            raise LedgerError("archived view-change validator identity mismatch")
        if change.chain_id != genesis.chain_id or change.height != block.height:
            raise LedgerError("archived view-change chain/height mismatch")
        if change.from_round != block.round - 1 or change.to_round != block.round:
            raise LedgerError("archived view-change round mismatch")
        if not change.verify_signature():
            raise LedgerError("invalid archived view-change signature")
    if len(seen) < genesis.quorum_size:
        raise LedgerError("archived view-change certificate lacks quorum")


def _verify_phase(block: Block, phase: str, votes: list[PhaseVote], genesis: Genesis) -> None:
    seen: set[str] = set()
    for vote in votes:
        if vote.voter in seen:
            raise LedgerError(f"duplicate archived {phase} validator")
        seen.add(vote.voter)
        validator = genesis.validator_by_address(vote.voter)
        if validator is None or validator.public_key != vote.public_key:
            raise LedgerError(f"archived {phase} validator identity mismatch")
        if (
            vote.phase != phase
            or vote.chain_id != genesis.chain_id
            or vote.height != block.height
            or vote.round != block.round
            or vote.block_hash != block.block_hash
        ):
            raise LedgerError(f"archived {phase} certificate metadata mismatch")
        if not vote.verify_signature():
            raise LedgerError(f"invalid archived {phase} signature")
    if len(seen) < genesis.quorum_size:
        raise LedgerError(f"archived {phase} certificate lacks quorum")


def verify_history_archive(artifact: dict[str, Any], genesis: Genesis) -> dict[str, Any]:
    """Fully verify a genesis-anchored history archive by replaying account state.

    v1 deliberately requires a complete archive beginning at height 1. That keeps archive
    verification independent of a trusted checkpoint: signatures, quorum certificates,
    transaction nonces/balances, state roots and the hash chain are replayed from genesis.
    """

    if artifact.get("format") != ARCHIVE_FORMAT:
        raise LedgerError("unsupported history archive format")
    manifest = artifact.get("manifest")
    blocks_raw = artifact.get("blocks")
    if not isinstance(manifest, dict) or not isinstance(blocks_raw, list):
        raise LedgerError("invalid history archive structure")
    if manifest.get("chain_id") != genesis.chain_id:
        raise LedgerError("history archive chain_id mismatch")
    if manifest.get("genesis_fingerprint") != genesis.fingerprint():
        raise LedgerError("history archive genesis fingerprint mismatch")
    if int(manifest.get("start_height", 0)) != 1:
        raise LedgerError("history archive v1 must begin at height 1")
    if int(manifest.get("block_count", -1)) != len(blocks_raw):
        raise LedgerError("history archive block count mismatch")

    expected_archive_hash = sha256_hex(canonical_json(blocks_raw))
    if manifest.get("blocks_sha256") != expected_archive_hash:
        raise LedgerError("history archive payload hash mismatch")

    state: dict[str, list[int]] = {
        address: [int(amount), 0] for address, amount in genesis.allocations.items()
    }
    previous_hash = "0" * 64
    last_hash = previous_hash

    for expected_height, raw in enumerate(blocks_raw, start=1):
        if not isinstance(raw, dict):
            raise LedgerError("history archive block entry must be an object")
        block = Block.from_dict(raw)
        if block.height != expected_height:
            raise LedgerError("history archive heights are not contiguous from genesis")
        if block.chain_id != genesis.chain_id:
            raise LedgerError("archived block chain_id mismatch")
        if block.previous_hash != previous_hash:
            raise LedgerError("archived block previous-hash continuity failure")
        proposer = genesis.proposer_for_height_round(block.height, block.round)
        if block.proposer != proposer.address or block.proposer_public_key != proposer.public_key:
            raise LedgerError("archived block proposer mismatch")
        if not block.verify_signature():
            raise LedgerError("invalid archived block proposer signature")
        if raw.get("hash") and str(raw["hash"]) != block.block_hash:
            raise LedgerError("archived block hash field mismatch")
        if block.tx_root != merkle_root([tx.txid for tx in block.transactions]):
            raise LedgerError("archived transaction Merkle root mismatch")

        _verify_view_changes(block, genesis)
        _verify_phase(block, "prevote", block.prevote_votes, genesis)
        _verify_phase(block, "precommit", block.precommit_votes, genesis)

        for tx in block.transactions:
            if tx.chain_id != genesis.chain_id or tx.amount <= 0 or tx.fee < genesis.min_fee:
                raise LedgerError("invalid archived transaction fields")
            if tx.sender == tx.recipient or not tx.verify_signature():
                raise LedgerError("invalid archived transaction signature or recipient")
            sender = state.setdefault(tx.sender, [0, 0])
            recipient = state.setdefault(tx.recipient, [0, 0])
            fees = state.setdefault(block.proposer, [0, 0])
            if tx.nonce != sender[1] + 1:
                raise LedgerError("archived transaction nonce replay failure")
            if sender[0] < tx.amount + tx.fee:
                raise LedgerError("archived transaction exceeds replayed balance")
            sender[0] -= tx.amount + tx.fee
            sender[1] += 1
            recipient[0] += tx.amount
            fees[0] += tx.fee

        replayed_root = _state_root(state)
        if block.state_root != replayed_root:
            raise LedgerError("archived block state root mismatch")
        previous_hash = block.block_hash
        last_hash = block.block_hash

    end_height = len(blocks_raw)
    if int(manifest.get("end_height", -1)) != end_height:
        raise LedgerError("history archive end height mismatch")
    if str(manifest.get("tip_hash") or "") != last_hash:
        raise LedgerError("history archive tip hash mismatch")

    return {
        "valid": True,
        "format": ARCHIVE_FORMAT,
        "chain_id": genesis.chain_id,
        "start_height": 1,
        "end_height": end_height,
        "block_count": len(blocks_raw),
        "tip_hash": last_hash,
        "blocks_sha256": expected_archive_hash,
        "replayed_state_root": _state_root(state),
    }


def export_history_archive(
    ledger: Ledger,
    output: str | Path,
    *,
    end_height: int | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    end = ledger.height if end_height is None else int(end_height)
    if end < 0 or end > ledger.height:
        raise LedgerError("history archive end height is outside the local finalized range")

    blocks: list[dict[str, Any]] = []
    for height in range(1, end + 1):
        block = ledger.get_block(height)
        if block is None:
            raise LedgerError(
                "cannot export a genesis-anchored archive because local historical blocks are missing"
            )
        blocks.append(block)

    manifest = {
        "chain_id": ledger.genesis.chain_id,
        "genesis_fingerprint": ledger.genesis.fingerprint(),
        "start_height": 1,
        "end_height": end,
        "block_count": len(blocks),
        "tip_hash": (str(blocks[-1].get("hash")) if blocks else "0" * 64),
        "blocks_sha256": sha256_hex(canonical_json(blocks)),
        "created_at_ms": int(time.time() * 1000),
    }
    artifact = {"format": ARCHIVE_FORMAT, "manifest": manifest, "blocks": blocks}
    verify_history_archive(artifact, ledger.genesis)

    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        raise LedgerError(f"history archive target already exists: {target}")
    target.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return {"archive": str(target), **manifest}


def import_history_archive(ledger: Ledger, artifact: dict[str, Any]) -> dict[str, Any]:
    """Backfill pre-snapshot history without mutating the snapshot-restored account state."""

    summary = verify_history_archive(artifact, ledger.genesis)
    with ledger.connect() as conn:
        base_row = conn.execute(
            "SELECT value FROM metadata WHERE key='snapshot_base_height'"
        ).fetchone()
        base_hash_row = conn.execute(
            "SELECT value FROM metadata WHERE key='snapshot_base_hash'"
        ).fetchone()
    if base_row is None or base_hash_row is None:
        raise LedgerError("history backfill is only allowed on a snapshot-bootstrapped node")

    base_height = int(base_row["value"])
    base_hash = str(base_hash_row["value"])
    if summary["end_height"] < base_height:
        raise LedgerError("history archive does not reach the local snapshot base height")
    base_raw = artifact["blocks"][base_height - 1]
    base_block = Block.from_dict(base_raw)
    if base_block.block_hash != base_hash:
        raise LedgerError("history archive snapshot-base hash does not match local snapshot metadata")

    inserted_blocks = 0
    inserted_transactions = 0
    with ledger.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            for raw in artifact["blocks"][:base_height]:
                block = Block.from_dict(raw)
                body = json.dumps(block.to_dict(), separators=(",", ":"))
                existing = conn.execute(
                    "SELECT hash,body FROM blocks WHERE height=?", (block.height,)
                ).fetchone()
                if existing is not None:
                    if str(existing["hash"]) != block.block_hash:
                        raise LedgerError("local historical block conflicts with archive")
                else:
                    conn.execute(
                        "INSERT INTO blocks(height,hash,body) VALUES(?,?,?)",
                        (block.height, block.block_hash, body),
                    )
                    inserted_blocks += 1
                for tx in block.transactions:
                    tx_body = json.dumps(tx.to_dict(), separators=(",", ":"))
                    existing_tx = conn.execute(
                        "SELECT height,body FROM transactions WHERE txid=?", (tx.txid,)
                    ).fetchone()
                    if existing_tx is not None:
                        if int(existing_tx["height"]) != block.height:
                            raise LedgerError("local transaction index conflicts with archive")
                    else:
                        conn.execute(
                            "INSERT INTO transactions(txid,height,body) VALUES(?,?,?)",
                            (tx.txid, block.height, tx_body),
                        )
                        inserted_transactions += 1
            conn.execute(
                "INSERT OR REPLACE INTO metadata(key,value) VALUES('archive_history_imported_to',?)",
                (str(base_height),),
            )
            conn.execute(
                "INSERT OR REPLACE INTO metadata(key,value) VALUES('archive_history_hash',?)",
                (str(summary["blocks_sha256"]),),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    return {
        "imported": True,
        "snapshot_base_height": base_height,
        "snapshot_base_hash": base_hash,
        "inserted_blocks": inserted_blocks,
        "inserted_transactions": inserted_transactions,
        "archive_tip_height": summary["end_height"],
        "archive_hash": summary["blocks_sha256"],
        "state_mutated": False,
    }
