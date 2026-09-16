from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import cli_v33
from .algorithm_gate_v34 import (
    AlgorithmGateV34Error,
    build_algorithm_decision,
    build_benchmark_gate,
    build_benchmark_record,
    load_json as load_algorithm_json,
    verify_algorithm_decision,
    verify_benchmark_gate,
    verify_benchmark_record,
)
from .pool_payout_v34 import (
    PoolPayoutV34Error,
    atomic_to_crk,
    build_payout_plan,
    list_payout_plans,
    mark_submitted,
    payout_transaction,
    reconcile_payout_plan,
)
from .pow_ops_v34 import (
    PeerBookV34,
    PowOpsV34Error,
    UndoJournalV34,
    build_watch_only,
    chain_statistics,
    fee_estimate,
    transaction_confirmations,
)
from .pow_v31 import COIN


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.34 PoW operations: benchmark evidence, undo journal, peer book, explorer stats and mature pool payouts",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    benchmark = sub.add_parser("pow-benchmark-v34-build")
    benchmark.add_argument("--key", required=True)
    benchmark.add_argument("--machine-id", required=True)
    benchmark.add_argument("--cpu-model", required=True)
    benchmark.add_argument("--logical-threads", type=int, required=True)
    benchmark.add_argument("--ram-mib", type=int, required=True)
    benchmark.add_argument("--scrypt-hps", type=float, required=True)
    benchmark.add_argument("--randomx-hps", type=float, default=None)
    benchmark.add_argument("--randomx-mode", choices=["light", "fast"], default=None)
    benchmark.add_argument("--randomx-selftest-passed", action="store_true")
    benchmark.add_argument("--randomx-library-sha256", default=None)
    benchmark.add_argument("--gpu-model", default=None)
    benchmark.add_argument("--gpu-randomx-hps", type=float, default=None)
    benchmark.add_argument("--notes", default="")
    benchmark.add_argument("--output", required=True)
    benchmark.add_argument("--overwrite", action="store_true")

    benchmark_verify = sub.add_parser("pow-benchmark-v34-verify")
    benchmark_verify.add_argument("--record", required=True)

    gate = sub.add_parser("pow-benchmark-gate-v34-build")
    gate.add_argument("--key", required=True)
    gate.add_argument("--record", action="append", required=True)
    gate.add_argument("--minimum-unique-machines", type=int, default=2)
    gate.add_argument("--allow-missing-randomx", action="store_true")
    gate.add_argument("--output", required=True)
    gate.add_argument("--overwrite", action="store_true")

    gate_verify = sub.add_parser("pow-benchmark-gate-v34-verify")
    gate_verify.add_argument("--record", required=True)

    decision = sub.add_parser("pow-algorithm-decision-v34-build")
    decision.add_argument("--key", required=True)
    decision.add_argument("--benchmark-gate", required=True)
    decision.add_argument("--decision", choices=["hold", "scrypt", "randomx"], required=True)
    decision.add_argument("--rationale", required=True)
    decision.add_argument("--output", required=True)
    decision.add_argument("--overwrite", action="store_true")

    decision_verify = sub.add_parser("pow-algorithm-decision-v34-verify")
    decision_verify.add_argument("--record", required=True)

    undo = sub.add_parser("pow-undo-v34-backfill")
    undo.add_argument("--db", required=True)
    undo.add_argument("--start-height", type=int, default=1)
    undo.add_argument("--end-height", type=int, default=None)
    undo.add_argument("--output", default=None)
    undo.add_argument("--overwrite", action="store_true")

    undo_verify = sub.add_parser("pow-undo-v34-verify")
    undo_verify.add_argument("--db", required=True)

    peer_note = sub.add_parser("pow-peer-v34-note")
    peer_note.add_argument("--db", required=True)
    peer_note.add_argument("--endpoint", required=True)
    peer_note.add_argument("--node-id", default=None)
    peer_note.add_argument("--source", default="manual")
    state = peer_note.add_mutually_exclusive_group()
    state.add_argument("--success", action="store_true")
    state.add_argument("--failure", action="store_true")
    peer_note.add_argument("--score-delta", type=int, default=0)

    peer_list = sub.add_parser("pow-peer-v34-list")
    peer_list.add_argument("--db", required=True)
    peer_list.add_argument("--limit", type=int, default=500)

    peer_select = sub.add_parser("pow-peer-v34-select")
    peer_select.add_argument("--db", required=True)
    peer_select.add_argument("--limit", type=int, default=16)
    peer_select.add_argument("--max-per-bucket", type=int, default=2)

    stats = sub.add_parser("pow-stats-v34")
    stats.add_argument("--db", required=True)
    stats.add_argument("--window", type=int, default=120)

    tx_status = sub.add_parser("pow-tx-status-v34")
    tx_status.add_argument("--db", required=True)
    tx_status.add_argument("--txid", required=True)

    fees = sub.add_parser("pow-fee-estimate-v34")
    fees.add_argument("--db", required=True)
    fees.add_argument("--fallback-atomic-per-byte", type=int, default=1)

    watch = sub.add_parser("pow-watch-only-v34-build")
    watch.add_argument("--address", required=True)
    watch.add_argument("--label", default="")
    watch.add_argument("--output", required=True)
    watch.add_argument("--overwrite", action="store_true")

    payout = sub.add_parser("pow-payout-v34-build")
    payout.add_argument("--chain-db", required=True)
    payout.add_argument("--pool-db", required=True)
    payout.add_argument("--wallet", required=True, help="pool hot-wallet key file; keep private and never commit")
    payout.add_argument("--minimum-payout-crk", type=float, default=0.1)
    payout.add_argument("--fee-crk", type=float, default=0.0001)
    payout.add_argument("--max-recipients", type=int, default=100)
    payout.add_argument("--max-total-payout-crk", type=float, default=None)
    payout.add_argument("--output", required=True)
    payout.add_argument("--overwrite", action="store_true")

    payout_list = sub.add_parser("pow-payout-v34-list")
    payout_list.add_argument("--pool-db", required=True)

    payout_tx = sub.add_parser("pow-payout-v34-export-tx")
    payout_tx.add_argument("--pool-db", required=True)
    payout_tx.add_argument("--plan-id", required=True)
    payout_tx.add_argument("--output", required=True)
    payout_tx.add_argument("--overwrite", action="store_true")

    payout_mark = sub.add_parser("pow-payout-v34-mark-submitted")
    payout_mark.add_argument("--pool-db", required=True)
    payout_mark.add_argument("--plan-id", required=True)

    payout_reconcile = sub.add_parser("pow-payout-v34-reconcile")
    payout_reconcile.add_argument("--chain-db", required=True)
    payout_reconcile.add_argument("--pool-db", required=True)
    payout_reconcile.add_argument("--plan-id", required=True)
    payout_reconcile.add_argument("--minimum-confirmations", type=int, default=2)

    return parser


def _save_json(path: str | Path, value: dict, *, overwrite: bool = False) -> None:
    target = Path(path)
    if target.exists() and not overwrite:
        raise ValueError(f"file exists: {target}; pass --overwrite to replace")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "pow-benchmark-v34-build":
        record = build_benchmark_record(
            signing_key_path=args.key,
            machine_id=args.machine_id,
            cpu_model=args.cpu_model,
            logical_threads=args.logical_threads,
            ram_mib=args.ram_mib,
            scrypt_hps=args.scrypt_hps,
            randomx_hps=args.randomx_hps,
            randomx_mode=args.randomx_mode,
            randomx_selftest_passed=args.randomx_selftest_passed,
            randomx_library_sha256=args.randomx_library_sha256,
            gpu_model=args.gpu_model,
            gpu_randomx_hps=args.gpu_randomx_hps,
            notes=args.notes,
        )
        _save_json(args.output, record, overwrite=args.overwrite)
        print(json.dumps({"saved": args.output, "benchmark_id": record["manifest"]["benchmark_id"], "production_mainnet_ready": False}, indent=2))
        return 0

    if args.command == "pow-benchmark-v34-verify":
        print(json.dumps(verify_benchmark_record(load_algorithm_json(args.record)), indent=2))
        return 0

    if args.command == "pow-benchmark-gate-v34-build":
        record = build_benchmark_gate(
            signing_key_path=args.key,
            records=[load_algorithm_json(path) for path in args.record],
            minimum_unique_machines=args.minimum_unique_machines,
            require_randomx_on_every_machine=not args.allow_missing_randomx,
        )
        _save_json(args.output, record, overwrite=args.overwrite)
        print(json.dumps({
            "saved": args.output,
            "gate_id": record["manifest"]["gate_id"],
            "benchmark_gate_satisfied": record["manifest"]["benchmark_gate_satisfied"],
            "human_algorithm_decision_required": True,
            "production_mainnet_ready": False,
        }, indent=2))
        return 0 if record["manifest"]["benchmark_gate_satisfied"] else 2

    if args.command == "pow-benchmark-gate-v34-verify":
        result = verify_benchmark_gate(load_algorithm_json(args.record))
        print(json.dumps(result, indent=2))
        return 0 if result["benchmark_gate_satisfied"] else 2

    if args.command == "pow-algorithm-decision-v34-build":
        record = build_algorithm_decision(
            signing_key_path=args.key,
            benchmark_gate=load_algorithm_json(args.benchmark_gate),
            decision=args.decision,
            rationale=args.rationale,
        )
        _save_json(args.output, record, overwrite=args.overwrite)
        print(json.dumps({
            "saved": args.output,
            "decision_id": record["manifest"]["decision_id"],
            "decision": record["manifest"]["decision"],
            "consensus_activation_authorized": False,
            "production_mainnet_ready": False,
        }, indent=2))
        return 0

    if args.command == "pow-algorithm-decision-v34-verify":
        print(json.dumps(verify_algorithm_decision(load_algorithm_json(args.record)), indent=2))
        return 0

    if args.command == "pow-undo-v34-backfill":
        journal = UndoJournalV34(args.db)
        try:
            result = journal.backfill(start_height=args.start_height, end_height=args.end_height)
        finally:
            journal.close()
        if args.output:
            _save_json(args.output, result, overwrite=args.overwrite)
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "pow-undo-v34-verify":
        journal = UndoJournalV34(args.db)
        try:
            result = journal.verify()
        finally:
            journal.close()
        print(json.dumps(result, indent=2))
        return 0 if result["valid"] else 2

    if args.command == "pow-peer-v34-note":
        book = PeerBookV34(args.db)
        try:
            success = True if args.success else False if args.failure else None
            result = book.note(
                args.endpoint,
                node_id=args.node_id,
                source=args.source,
                success=success,
                score_delta=args.score_delta,
            )
        finally:
            book.close()
        print(json.dumps({**result, "production_mainnet_ready": False}, indent=2))
        return 0

    if args.command == "pow-peer-v34-list":
        book = PeerBookV34(args.db)
        try:
            peers = book.list(limit=args.limit)
        finally:
            book.close()
        print(json.dumps({"peers": peers, "production_mainnet_ready": False}, indent=2))
        return 0

    if args.command == "pow-peer-v34-select":
        book = PeerBookV34(args.db)
        try:
            peers = book.select(limit=args.limit, max_per_bucket=args.max_per_bucket)
        finally:
            book.close()
        print(json.dumps({"selected_peers": peers, "coarse_diversity_only": True, "production_mainnet_ready": False}, indent=2))
        return 0

    if args.command == "pow-stats-v34":
        print(json.dumps(chain_statistics(args.db, window=args.window), indent=2))
        return 0

    if args.command == "pow-tx-status-v34":
        print(json.dumps(transaction_confirmations(args.db, args.txid), indent=2))
        return 0

    if args.command == "pow-fee-estimate-v34":
        print(json.dumps(fee_estimate(args.db, fallback_atomic_per_byte=args.fallback_atomic_per_byte), indent=2))
        return 0

    if args.command == "pow-watch-only-v34-build":
        value = build_watch_only(args.address, label=args.label)
        _save_json(args.output, value, overwrite=args.overwrite)
        print(json.dumps({"saved": args.output, "address": value["address"], "contains_private_key": False, "production_mainnet_ready": False}, indent=2))
        return 0

    if args.command == "pow-payout-v34-build":
        max_total = None if args.max_total_payout_crk is None else int(round(args.max_total_payout_crk * COIN))
        plan = build_payout_plan(
            chain_db=args.chain_db,
            pool_db=args.pool_db,
            wallet_path=args.wallet,
            minimum_payout=int(round(args.minimum_payout_crk * COIN)),
            fee=int(round(args.fee_crk * COIN)),
            max_recipients=args.max_recipients,
            max_total_payout=max_total,
        )
        _save_json(args.output, plan, overwrite=args.overwrite)
        print(json.dumps({
            "saved": args.output,
            "plan_id": plan["plan_id"],
            "txid": plan["txid"],
            "recipients": len(plan["payouts"]),
            "total_payout_crk": atomic_to_crk(plan["total_payout"]),
            "automatic_submit": False,
            "production_mainnet_ready": False,
        }, indent=2))
        return 0

    if args.command == "pow-payout-v34-list":
        print(json.dumps({"plans": list_payout_plans(args.pool_db), "production_mainnet_ready": False}, indent=2))
        return 0

    if args.command == "pow-payout-v34-export-tx":
        tx = payout_transaction(args.pool_db, args.plan_id)
        _save_json(args.output, tx, overwrite=args.overwrite)
        print(json.dumps({"saved": args.output, "plan_id": args.plan_id, "production_mainnet_ready": False}, indent=2))
        return 0

    if args.command == "pow-payout-v34-mark-submitted":
        print(json.dumps(mark_submitted(args.pool_db, args.plan_id), indent=2))
        return 0

    if args.command == "pow-payout-v34-reconcile":
        result = reconcile_payout_plan(
            chain_db=args.chain_db,
            pool_db=args.pool_db,
            plan_id=args.plan_id,
            minimum_confirmations=args.minimum_confirmations,
        )
        print(json.dumps(result, indent=2))
        return 0

    raise ValueError("unknown v0.34 command")


def main() -> int:
    commands = {
        "pow-benchmark-v34-build", "pow-benchmark-v34-verify",
        "pow-benchmark-gate-v34-build", "pow-benchmark-gate-v34-verify",
        "pow-algorithm-decision-v34-build", "pow-algorithm-decision-v34-verify",
        "pow-undo-v34-backfill", "pow-undo-v34-verify",
        "pow-peer-v34-note", "pow-peer-v34-list", "pow-peer-v34-select",
        "pow-stats-v34", "pow-tx-status-v34", "pow-fee-estimate-v34", "pow-watch-only-v34-build",
        "pow-payout-v34-build", "pow-payout-v34-list", "pow-payout-v34-export-tx",
        "pow-payout-v34-mark-submitted", "pow-payout-v34-reconcile",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        try:
            return _run(sys.argv[1:])
        except (AlgorithmGateV34Error, PoolPayoutV34Error, PowOpsV34Error, ValueError, OSError) as exc:
            print(json.dumps({"error": str(exc), "production_mainnet_ready": False}), file=sys.stderr)
            return 2
    return cli_v33.main()


if __name__ == "__main__":
    raise SystemExit(main())
