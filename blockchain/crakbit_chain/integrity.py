from __future__ import annotations

import json
from typing import Any

from .models import Block, Transaction, merkle_root
from .storage import Ledger


def _metadata(ledger: Ledger, key: str) -> str | None:
    with ledger.connect() as conn:
        row = conn.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        return str(row["value"]) if row is not None else None


def verify_ledger_integrity(ledger: Ledger, *, full: bool = True) -> dict[str, Any]:
    """Verify local database, chain continuity and snapshot-base semantics.

    This is an operational integrity checker, not a replacement for consensus validation.
    In full mode it verifies every locally stored block body, proposer signature, view-change
    certificate, prevote/precommit certificates, transaction roots and transaction index.
    Snapshot-bootstrapped nodes are checked only from their certified local history base.
    """

    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    # SQLite-level corruption check.
    try:
        with ledger.connect() as conn:
            rows = conn.execute("PRAGMA quick_check").fetchall()
        quick = [str(row[0]) for row in rows]
        checks["sqlite_quick_check"] = quick
        if quick != ["ok"]:
            errors.append("SQLite quick_check did not return ok")
    except Exception as exc:
        checks["sqlite_quick_check"] = [f"error:{type(exc).__name__}"]
        errors.append(f"SQLite quick_check failed: {type(exc).__name__}: {exc}")

    expected_fingerprint = ledger.genesis.fingerprint()
    actual_fingerprint = _metadata(ledger, "genesis_fingerprint")
    checks["genesis_fingerprint"] = {
        "expected": expected_fingerprint,
        "actual": actual_fingerprint,
    }
    if actual_fingerprint != expected_fingerprint:
        errors.append("database genesis fingerprint does not match configured genesis")

    try:
        current_height = ledger.height
        last_hash = ledger.last_hash
    except Exception as exc:
        errors.append(f"failed to read chain tip metadata: {type(exc).__name__}: {exc}")
        return {
            "ok": False,
            "full": bool(full),
            "checks": checks,
            "errors": errors,
            "warnings": warnings,
        }

    checks["tip"] = {"height": current_height, "last_hash": last_hash}
    if current_height < 0:
        errors.append("negative chain height")
    if len(last_hash) != 64:
        errors.append("last_hash is not a 64-character hash")

    # Accounting conservation. Fees move between accounts, so issued supply should remain fixed.
    try:
        with ledger.connect() as conn:
            row = conn.execute("SELECT COALESCE(SUM(balance),0) AS total FROM accounts").fetchone()
            total_supply = int(row["total"])
        issued_supply = sum(ledger.genesis.allocations.values())
        checks["issued_supply"] = {
            "expected": issued_supply,
            "actual": total_supply,
        }
        if total_supply != issued_supply:
            errors.append("account balances do not conserve genesis-issued supply")
    except Exception as exc:
        errors.append(f"failed to verify account supply: {type(exc).__name__}: {exc}")

    base_raw = _metadata(ledger, "snapshot_base_height")
    base_height = int(base_raw) if base_raw is not None else None
    base_hash = _metadata(ledger, "snapshot_base_hash") if base_height is not None else None
    base_root = _metadata(ledger, "snapshot_accounts_root") if base_height is not None else None
    checks["snapshot_base"] = {
        "bootstrapped": base_height is not None,
        "height": base_height,
        "hash": base_hash,
        "accounts_root": base_root,
    }

    if base_height is not None:
        if base_height < 0 or base_height > current_height:
            errors.append("snapshot base height is outside the local chain height")
        if not base_hash or len(base_hash) != 64:
            errors.append("snapshot base hash is missing or invalid")
        if not base_root or len(base_root) != 64:
            errors.append("snapshot accounts root is missing or invalid")
        if current_height == base_height and base_hash and last_hash != base_hash:
            errors.append("chain tip hash does not match snapshot base hash")

    if not full:
        return {
            "ok": not errors,
            "full": False,
            "checks": checks,
            "errors": errors,
            "warnings": warnings,
        }

    local_start = (base_height + 1) if base_height is not None else 1
    expected_previous = base_hash if base_height is not None else "0" * 64
    local_blocks: dict[int, Block] = {}
    block_txids: dict[str, int] = {}

    try:
        with ledger.connect() as conn:
            rows = conn.execute(
                "SELECT height,hash,body FROM blocks ORDER BY height ASC"
            ).fetchall()

        expected_heights = list(range(local_start, current_height + 1)) if current_height >= local_start else []
        actual_heights = [int(row["height"]) for row in rows]
        checks["local_history"] = {
            "start": local_start,
            "end": current_height,
            "stored_blocks": len(rows),
            "expected_blocks": len(expected_heights),
        }
        if actual_heights != expected_heights:
            errors.append(
                f"local block heights are not contiguous: expected {expected_heights[:4]}...{expected_heights[-4:] if expected_heights else []}, "
                f"got {actual_heights[:4]}...{actual_heights[-4:] if actual_heights else []}"
            )

        for row in rows:
            height = int(row["height"])
            stored_hash = str(row["hash"])
            try:
                body = json.loads(str(row["body"]))
                block = Block.from_dict(body)
            except Exception as exc:
                errors.append(f"block {height} body could not be parsed: {type(exc).__name__}: {exc}")
                continue

            local_blocks[height] = block
            if block.height != height:
                errors.append(f"block row height {height} disagrees with body height {block.height}")
            if block.chain_id != ledger.genesis.chain_id:
                errors.append(f"block {height} has wrong chain_id")
            if stored_hash != block.block_hash:
                errors.append(f"block {height} stored hash does not match reconstructed block hash")
            if body.get("hash") and str(body.get("hash")) != block.block_hash:
                errors.append(f"block {height} body hash field is inconsistent")
            if expected_previous is not None and block.previous_hash != expected_previous:
                errors.append(f"block {height} previous_hash breaks local chain continuity")

            expected_proposer = ledger.genesis.proposer_for_height_round(block.height, block.round)
            if block.proposer != expected_proposer.address:
                errors.append(f"block {height} proposer does not match configured schedule")
            if block.proposer_public_key != expected_proposer.public_key:
                errors.append(f"block {height} proposer public key does not match genesis")
            if not block.verify_signature():
                errors.append(f"block {height} proposer signature is invalid")

            expected_tx_root = merkle_root([tx.txid for tx in block.transactions])
            if block.tx_root != expected_tx_root:
                errors.append(f"block {height} transaction Merkle root is invalid")

            try:
                ledger.validate_view_change_certificate(block)
            except Exception as exc:
                errors.append(f"block {height} view-change certificate invalid: {exc}")
            try:
                ledger.validate_phase_certificate(block, "prevote", block.prevote_votes)
            except Exception as exc:
                errors.append(f"block {height} prevote certificate invalid: {exc}")
            try:
                ledger.validate_phase_certificate(block, "precommit", block.precommit_votes)
            except Exception as exc:
                errors.append(f"block {height} precommit certificate invalid: {exc}")

            for tx in block.transactions:
                block_txids[tx.txid] = height
            expected_previous = stored_hash

        if expected_heights:
            if rows and str(rows[-1]["hash"]) != last_hash:
                errors.append("metadata last_hash does not match highest locally stored block")
        elif base_height is None and current_height == 0 and last_hash != "0" * 64:
            errors.append("genesis-height database has non-zero last_hash")
    except Exception as exc:
        errors.append(f"local block-history verification failed: {type(exc).__name__}: {exc}")

    # Transaction index must correspond exactly to locally stored block transactions.
    try:
        with ledger.connect() as conn:
            tx_rows = conn.execute(
                "SELECT txid,height,body FROM transactions ORDER BY height,txid"
            ).fetchall()
        indexed: dict[str, int] = {}
        for row in tx_rows:
            txid = str(row["txid"])
            height = int(row["height"])
            indexed[txid] = height
            try:
                tx = Transaction.from_dict(json.loads(str(row["body"])))
                if tx.txid != txid:
                    errors.append(f"transaction index entry {txid} has inconsistent transaction body")
            except Exception as exc:
                errors.append(f"transaction index entry {txid} could not be parsed: {exc}")
        checks["transaction_index"] = {
            "indexed_transactions": len(indexed),
            "local_block_transactions": len(block_txids),
        }
        if indexed != block_txids:
            errors.append("transaction index does not match transactions in locally stored blocks")
    except Exception as exc:
        errors.append(f"transaction-index verification failed: {type(exc).__name__}: {exc}")

    if base_height is not None:
        warnings.append(
            "pre-snapshot block/transaction bodies are intentionally unavailable unless restored from an archive"
        )

    return {
        "ok": not errors,
        "full": True,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }
