from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from crakbit_chain.crypto import KeyPair, canonical_json, sha256_hex
from crakbit_chain.pow_network_v32 import PowNetworkChain
from crakbit_chain.pow_v31 import PowChain, mine_block


def _consistent_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(source)
    dst = sqlite3.connect(destination)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def _raw_tip(path: Path) -> tuple[int, str, str]:
    db = sqlite3.connect(path)
    try:
        row = db.execute(
            "SELECT height,block_hash,chainwork FROM blocks ORDER BY height DESC LIMIT 1"
        ).fetchone()
        if row is None:
            raise RuntimeError("chain database has no blocks")
        return int(row[0]), str(row[1]), str(row[2])
    finally:
        db.close()


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


def _coinbase_address(chain: PowChain, height: int) -> str:
    for candidate_height in range(max(1, int(height)), 0, -1):
        block = chain.get_block(candidate_height)
        txs = list(block.get("transactions", []))
        if not txs:
            continue
        outputs = list(txs[0].get("outputs", []))
        for output in outputs:
            address = str(output.get("address", ""))
            if address.startswith("crk1"):
                return address
    return KeyPair.generate().address


def _mine_next(chain: PowChain, miner_address: str, label: str) -> tuple[dict[str, Any], int]:
    template = chain.get_block_template(miner_address, message=label)
    candidate, hashes = mine_block(template["block"], chain.config)
    if candidate is None:
        raise RuntimeError("nonce space exhausted while mining rehearsal block")
    chain.submit_block(candidate)
    return candidate, int(hashes)


def rehearse_controlled_reorg(
    source_db: str | Path,
    *,
    fork_depth: int = 1,
    extra_blocks: int = 1,
    output: str | Path | None = None,
    keep_working_copy: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_db)
    if not source.exists():
        raise RuntimeError(f"source chain database does not exist: {source}")
    fork_depth = int(fork_depth)
    extra_blocks = int(extra_blocks)
    if fork_depth < 1 or fork_depth > 100:
        raise RuntimeError("fork_depth must be between 1 and 100")
    if extra_blocks < 1 or extra_blocks > 100:
        raise RuntimeError("extra_blocks must be between 1 and 100")

    source_tip_before = _raw_tip(source)
    if source_tip_before[0] <= fork_depth:
        raise RuntimeError("source chain is not tall enough for requested fork depth")

    with tempfile.TemporaryDirectory(prefix="crakbit-phase3-reorg-") as directory:
        root = Path(directory)
        working_path = root / "network-working.sqlite3"
        branch_path = root / "side-branch.sqlite3"
        _consistent_copy(source, working_path)

        network = PowNetworkChain(working_path)
        branch: PowChain | None = None
        try:
            original_tip = network.chain.tip()
            original_height = int(original_tip["height"])
            original_tip_hash = str(original_tip["block_hash"])
            original_chainwork = int(original_tip["chainwork"])
            fork_height = original_height - fork_depth
            canonical_prefix = [
                network.chain.get_block(height)
                for height in range(0, fork_height + 1)
            ]
            miner_address = _coinbase_address(network.chain, fork_height)

            branch = PowChain(branch_path, network.config, create=True)
            for block in canonical_prefix[1:]:
                branch.submit_block(block)

            branch_blocks: list[dict[str, Any]] = []
            mining_hashes: list[int] = []
            blocks_to_mine = fork_depth + extra_blocks
            for index in range(blocks_to_mine):
                block, hashes = _mine_next(
                    branch,
                    miner_address,
                    f"Crakbit Phase 3 controlled side branch #{index + 1}",
                )
                branch_blocks.append(block)
                mining_hashes.append(hashes)

            branch_tip = branch.tip()
            branch_utxo = _utxo_fingerprint(branch.db)

            acceptance: list[dict[str, Any]] = []
            for block in branch_blocks:
                acceptance.append(
                    network.accept_block(block, source="phase3-controlled-reorg")
                )

            final_tip = network.chain.tip()
            network_utxo = _utxo_fingerprint(network.db)
            old_tip_row = network.db.execute(
                "SELECT status FROM block_graph WHERE block_hash=?",
                (original_tip_hash,),
            ).fetchone()
            new_tip_row = network.db.execute(
                "SELECT status FROM block_graph WHERE block_hash=?",
                (str(final_tip["block_hash"]),),
            ).fetchone()
            reorg_results = [item for item in acceptance if bool(item.get("reorg"))]
            reorg_result = reorg_results[-1] if reorg_results else None

            checks = {
                "first_side_block_did_not_replace_equal_work_tip": bool(acceptance)
                and not bool(acceptance[0].get("became_canonical")),
                "controlled_reorg_reported_true": reorg_result is not None,
                "reorg_result_became_canonical": reorg_result is not None
                and bool(reorg_result.get("became_canonical")),
                "fork_height_matches_plan": reorg_result is not None
                and int(reorg_result.get("fork_height", -999)) == fork_height,
                "higher_work_side_branch_became_tip": str(final_tip["block_hash"])
                == str(branch_tip["block_hash"])
                and int(final_tip["chainwork"]) > original_chainwork,
                "old_canonical_tip_is_now_side": old_tip_row is not None
                and str(old_tip_row[0]) == "side",
                "new_tip_is_marked_canonical": new_tip_row is not None
                and str(new_tip_row[0]) == "canonical",
                "utxo_state_matches_clean_side_branch": network_utxo == branch_utxo,
            }

            result: dict[str, Any] = {
                "format": "crakbit-controlled-reorg-rehearsal-v38/1",
                "network": network.config.network,
                "chain_id": network.config.chain_id,
                "source_db": str(source),
                "source_tip_before": {
                    "height": source_tip_before[0],
                    "block_hash": source_tip_before[1],
                    "chainwork": source_tip_before[2],
                },
                "original_snapshot_tip": {
                    "height": original_height,
                    "block_hash": original_tip_hash,
                    "chainwork": str(original_chainwork),
                },
                "fork_depth": fork_depth,
                "planned_fork_height": fork_height,
                "extra_blocks": extra_blocks,
                "branch_blocks_mined": len(branch_blocks),
                "mining_hashes_per_block": mining_hashes,
                "acceptance": acceptance,
                "reorg_result": reorg_result,
                "final_snapshot_tip": {
                    "height": int(final_tip["height"]),
                    "block_hash": str(final_tip["block_hash"]),
                    "chainwork": str(final_tip["chainwork"]),
                },
                "side_branch_tip": {
                    "height": int(branch_tip["height"]),
                    "block_hash": str(branch_tip["block_hash"]),
                    "chainwork": str(branch_tip["chainwork"]),
                },
                "network_utxo_sha256": network_utxo,
                "side_branch_utxo_sha256": branch_utxo,
                "checks": checks,
                "rehearsal_passed": all(checks.values()),
                "source_database_modified": False,
                "production_mainnet_ready": False,
                "production_crkbit_launched": False,
            }

            if keep_working_copy is not None:
                destination = Path(keep_working_copy)
                destination.parent.mkdir(parents=True, exist_ok=True)
                network.db.commit()
                shutil.copy2(working_path, destination)
                result["working_copy"] = str(destination)

        finally:
            if branch is not None:
                branch.close()
            network.close()

        source_tip_after = _raw_tip(source)
        source_unchanged = source_tip_after == source_tip_before
        result["source_tip_after"] = {
            "height": source_tip_after[0],
            "block_hash": source_tip_after[1],
            "chainwork": source_tip_after[2],
        }
        result["source_database_modified"] = not source_unchanged
        result["checks"]["source_database_tip_unchanged"] = source_unchanged
        result["rehearsal_passed"] = all(result["checks"].values())
        result["rehearsal_id"] = sha256_hex(canonical_json(result))

        if output is not None:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a controlled highest-chainwork reorg rehearsal on a disposable snapshot."
    )
    parser.add_argument("--source-db", required=True)
    parser.add_argument("--fork-depth", type=int, default=1)
    parser.add_argument("--extra-blocks", type=int, default=1)
    parser.add_argument("--output")
    parser.add_argument("--keep-working-copy")
    args = parser.parse_args()
    result = rehearse_controlled_reorg(
        args.source_db,
        fork_depth=args.fork_depth,
        extra_blocks=args.extra_blocks,
        output=args.output,
        keep_working_copy=args.keep_working_copy,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["rehearsal_passed"] else 2)


if __name__ == "__main__":
    main()
