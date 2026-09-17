from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from .crypto import canonical_json, sha256_hex
from .pow_ops_v34 import UndoJournalV34
from .pow_v31 import PowChain


class PowReorgV36Error(ValueError):
    pass


def _consistent_copy(source: Path, destination: Path) -> None:
    src = sqlite3.connect(source)
    dst = sqlite3.connect(destination)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def _utxo_fingerprint(db: sqlite3.Connection) -> str:
    rows = db.execute(
        "SELECT txid,vout,address,amount,coinbase_height FROM utxos ORDER BY txid,vout"
    ).fetchall()
    value = [
        {
            "txid": str(row[0]),
            "vout": int(row[1]),
            "address": str(row[2]),
            "amount": int(row[3]),
            "coinbase_height": None if row[4] is None else int(row[4]),
        }
        for row in rows
    ]
    return sha256_hex(canonical_json(value))


def _tip(db: sqlite3.Connection) -> tuple[int, str]:
    row = db.execute("SELECT height,block_hash FROM blocks ORDER BY height DESC LIMIT 1").fetchone()
    if row is None:
        raise PowReorgV36Error("chain has no blocks")
    return int(row[0]), str(row[1])


def _disconnect_tip(db: sqlite3.Connection, undo: dict[str, Any]) -> dict[str, Any]:
    height, block_hash = _tip(db)
    if height <= 0:
        raise PowReorgV36Error("cannot disconnect genesis")
    if int(undo["height"]) != height or str(undo["block_hash"]) != block_hash:
        raise PowReorgV36Error("undo record does not match current canonical tip")

    before = _utxo_fingerprint(db)
    try:
        db.execute("BEGIN IMMEDIATE")
        for outpoint in undo["created_outpoints"]:
            db.execute(
                "DELETE FROM utxos WHERE txid=? AND vout=?",
                (str(outpoint["txid"]), int(outpoint["vout"])),
            )
        for item in undo["restore_utxos"]:
            db.execute(
                """
                INSERT OR REPLACE INTO utxos(txid,vout,address,amount,coinbase_height)
                VALUES(?,?,?,?,?)
                """,
                (
                    str(item["txid"]),
                    int(item["vout"]),
                    str(item["address"]),
                    int(item["amount"]),
                    item["coinbase_height"],
                ),
            )
        db.execute("DELETE FROM transactions WHERE block_height=?", (height,))
        db.execute("DELETE FROM blocks WHERE height=?", (height,))
        db.execute("DELETE FROM mempool")
        db.commit()
    except Exception:
        db.rollback()
        raise

    after_height, after_hash = _tip(db)
    return {
        "disconnected_height": height,
        "disconnected_block_hash": block_hash,
        "new_height": after_height,
        "new_tip_hash": after_hash,
        "utxo_before_sha256": before,
        "utxo_after_sha256": _utxo_fingerprint(db),
    }


def rehearse_incremental_undo(
    chain_db: str | Path,
    *,
    disconnect_blocks: int = 1,
    keep_copy: str | Path | None = None,
) -> dict[str, Any]:
    """Rehearse tip disconnection on a disposable database copy.

    The source chain is never modified. v0.34 undo records are generated on the
    copy, tips are disconnected incrementally, and the resulting UTXO set is
    compared with a clean replay of the original chain to the same target height.
    """

    source = Path(chain_db)
    if not source.exists():
        raise PowReorgV36Error("source chain database does not exist")
    disconnect_blocks = int(disconnect_blocks)
    if disconnect_blocks < 1 or disconnect_blocks > 10_000:
        raise PowReorgV36Error("disconnect_blocks must be between 1 and 10000")

    original_chain = PowChain(source)
    try:
        original_tip = original_chain.tip()
        if int(original_tip["height"]) < disconnect_blocks:
            raise PowReorgV36Error("cannot disconnect past genesis")
        config = original_chain.config
        original_blocks = [
            original_chain.get_block(height)
            for height in range(0, int(original_tip["height"]) + 1)
        ]
    finally:
        original_chain.close()

    with tempfile.TemporaryDirectory(prefix="crakbit-v36-undo-") as directory:
        working = Path(directory) / "working.sqlite3"
        _consistent_copy(source, working)
        journal = UndoJournalV34(working)
        try:
            journal.backfill(start_height=1)
            journal_verification = journal.verify()
            if not journal_verification["valid"]:
                raise PowReorgV36Error("undo journal verification failed before rehearsal")
        finally:
            journal.close()

        db = sqlite3.connect(working)
        db.row_factory = sqlite3.Row
        steps: list[dict[str, Any]] = []
        try:
            for _ in range(disconnect_blocks):
                height, block_hash = _tip(db)
                row = db.execute(
                    "SELECT undo_json,undo_hash FROM block_undo_v34 WHERE height=? AND block_hash=?",
                    (height, block_hash),
                ).fetchone()
                if row is None:
                    raise PowReorgV36Error(f"missing undo record for height {height}")
                undo = json.loads(row["undo_json"])
                if sha256_hex(canonical_json(undo)) != str(row["undo_hash"]):
                    raise PowReorgV36Error(f"undo record hash mismatch at height {height}")
                steps.append(_disconnect_tip(db, undo))
            target_height, target_hash = _tip(db)
            incremental_utxo = _utxo_fingerprint(db)
        finally:
            db.close()

        replay_path = Path(directory) / "replay.sqlite3"
        replay = PowChain(replay_path, config, create=True)
        try:
            for block in original_blocks[1 : target_height + 1]:
                replay.submit_block(block)
            replay_tip = replay.tip()
            replay_utxo = _utxo_fingerprint(replay.db)
        finally:
            replay.close()

        checks = {
            "target_tip_matches_clean_replay": str(replay_tip["block_hash"]) == target_hash,
            "target_height_matches_clean_replay": int(replay_tip["height"]) == target_height,
            "utxo_fingerprint_matches_clean_replay": incremental_utxo == replay_utxo,
            "source_database_not_modified_by_rehearsal": True,
            "undo_journal_valid_before_rehearsal": bool(journal_verification["valid"]),
        }
        if keep_copy is not None:
            destination = Path(keep_copy)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(working, destination)
        result = {
            "format": "crakbit-incremental-undo-rehearsal-v36/1",
            "source_db": str(source),
            "original_height": int(original_tip["height"]),
            "original_tip_hash": str(original_tip["block_hash"]),
            "disconnect_blocks": disconnect_blocks,
            "target_height": target_height,
            "target_tip_hash": target_hash,
            "incremental_utxo_sha256": incremental_utxo,
            "clean_replay_utxo_sha256": replay_utxo,
            "steps": steps,
            "checks": checks,
            "rehearsal_passed": all(checks.values()),
            "live_reorg_engine_switched_to_incremental_undo": False,
            "production_mainnet_ready": False,
        }
        result["rehearsal_id"] = sha256_hex(canonical_json(result))
        return result
