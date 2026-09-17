from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import cli_v36_entry
from .pow_execution_v37 import (
    PowExecutionV37Error,
    build_algorithm_review_gate,
    build_deployment_plan,
    build_payout_policy,
    build_review_bundle,
    load_json,
    verify_algorithm_review_gate,
    verify_deployment_plan,
    verify_payout_policy,
    verify_review_bundle,
)


COMMANDS = {
    "pow-deployment-v37-build",
    "pow-deployment-v37-verify",
    "pow-payout-policy-v37-build",
    "pow-payout-policy-v37-verify",
    "pow-algorithm-review-v37-build",
    "pow-algorithm-review-v37-verify",
    "pow-review-bundle-v37-build",
    "pow-review-bundle-v37-verify",
}


def _save(path: str | Path, value: dict[str, Any], overwrite: bool) -> None:
    target = Path(path)
    if target.exists() and not overwrite:
        raise PowExecutionV37Error(f"file exists: {target}; pass --overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_nodes(path: str | Path) -> list[dict[str, Any]]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(value, dict):
        value = value.get("nodes")
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise PowExecutionV37Error("nodes JSON must be an array or an object containing a nodes array")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.37 public-testnet execution and independent-review preparation tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    deployment = sub.add_parser("pow-deployment-v37-build")
    deployment.add_argument("--key", required=True)
    deployment.add_argument("--source-commit", required=True)
    deployment.add_argument("--package-version", default="0.37.0a1")
    deployment.add_argument("--chain-id", required=True)
    deployment.add_argument("--genesis-hash", required=True)
    deployment.add_argument("--nodes", required=True)
    deployment.add_argument("--minimum-nodes", type=int, default=4)
    deployment.add_argument("--minimum-providers", type=int, default=2)
    deployment.add_argument("--minimum-regions", type=int, default=2)
    deployment.add_argument("--minimum-network-groups", type=int, default=2)
    deployment.add_argument("--minimum-miner-operators", type=int, default=2)
    deployment.add_argument("--notes", default="")
    deployment.add_argument("--output", required=True)
    deployment.add_argument("--overwrite", action="store_true")

    deployment_verify = sub.add_parser("pow-deployment-v37-verify")
    deployment_verify.add_argument("--record", required=True)

    payout = sub.add_parser("pow-payout-policy-v37-build")
    payout.add_argument("--key", required=True)
    payout.add_argument("--hot-wallet-address", required=True)
    payout.add_argument("--cold-wallet-address", required=True)
    payout.add_argument("--maximum-single-payout-atomic", type=int, required=True)
    payout.add_argument("--maximum-batch-payout-atomic", type=int, required=True)
    payout.add_argument("--daily-payout-limit-atomic", type=int, required=True)
    payout.add_argument("--manual-hold-above-atomic", type=int, required=True)
    payout.add_argument("--approvals-required", type=int, default=2)
    payout.add_argument("--minimum-confirmations", type=int, default=6)
    payout.add_argument("--notes", default="")
    payout.add_argument("--output", required=True)
    payout.add_argument("--overwrite", action="store_true")

    payout_verify = sub.add_parser("pow-payout-policy-v37-verify")
    payout_verify.add_argument("--record", required=True)

    algorithm = sub.add_parser("pow-algorithm-review-v37-build")
    algorithm.add_argument("--key", required=True)
    algorithm.add_argument("--benchmark-gate", required=True)
    algorithm.add_argument("--algorithm-decision", required=True)
    algorithm.add_argument("--v36-handoff", required=True)
    algorithm.add_argument("--activation-proposal", default=None)
    algorithm.add_argument("--external-benchmark-review-asserted", action="store_true")
    algorithm.add_argument("--external-consensus-review-asserted", action="store_true")
    algorithm.add_argument("--notes", default="")
    algorithm.add_argument("--output", required=True)
    algorithm.add_argument("--overwrite", action="store_true")

    algorithm_verify = sub.add_parser("pow-algorithm-review-v37-verify")
    algorithm_verify.add_argument("--record", required=True)

    bundle = sub.add_parser("pow-review-bundle-v37-build")
    bundle.add_argument("--key", required=True)
    bundle.add_argument("--source-commit", required=True)
    bundle.add_argument("--package-version", default="0.37.0a1")
    bundle.add_argument("--deployment-plan", required=True)
    bundle.add_argument("--payout-policy", required=True)
    bundle.add_argument("--algorithm-review-gate", required=True)
    bundle.add_argument("--v36-handoff", required=True)
    bundle.add_argument("--notes", default="")
    bundle.add_argument("--output", required=True)
    bundle.add_argument("--overwrite", action="store_true")

    bundle_verify = sub.add_parser("pow-review-bundle-v37-verify")
    bundle_verify.add_argument("--record", required=True)
    return parser


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "pow-deployment-v37-build":
        value = build_deployment_plan(
            key_path=args.key,
            source_commit=args.source_commit,
            package_version=args.package_version,
            chain_id=args.chain_id,
            genesis_hash=args.genesis_hash,
            nodes=_load_nodes(args.nodes),
            minimum_nodes=args.minimum_nodes,
            minimum_providers=args.minimum_providers,
            minimum_regions=args.minimum_regions,
            minimum_network_groups=args.minimum_network_groups,
            minimum_miner_operators=args.minimum_miner_operators,
            notes=args.notes,
        )
        _save(args.output, value, args.overwrite)
        result = verify_deployment_plan(value)
        print(json.dumps({"saved": args.output, **result}, indent=2))
        return 0 if result["deployment_gate_satisfied"] else 2

    if args.command == "pow-deployment-v37-verify":
        result = verify_deployment_plan(load_json(args.record))
        print(json.dumps(result, indent=2))
        return 0 if result["deployment_gate_satisfied"] else 2

    if args.command == "pow-payout-policy-v37-build":
        value = build_payout_policy(
            key_path=args.key,
            hot_wallet_address=args.hot_wallet_address,
            cold_wallet_address=args.cold_wallet_address,
            maximum_single_payout_atomic=args.maximum_single_payout_atomic,
            maximum_batch_payout_atomic=args.maximum_batch_payout_atomic,
            daily_payout_limit_atomic=args.daily_payout_limit_atomic,
            manual_hold_above_atomic=args.manual_hold_above_atomic,
            approvals_required=args.approvals_required,
            minimum_confirmations=args.minimum_confirmations,
            notes=args.notes,
        )
        _save(args.output, value, args.overwrite)
        result = verify_payout_policy(value)
        print(json.dumps({"saved": args.output, **result}, indent=2))
        return 0 if result["payout_policy_gate_satisfied"] else 2

    if args.command == "pow-payout-policy-v37-verify":
        result = verify_payout_policy(load_json(args.record))
        print(json.dumps(result, indent=2))
        return 0 if result["payout_policy_gate_satisfied"] else 2

    if args.command == "pow-algorithm-review-v37-build":
        value = build_algorithm_review_gate(
            key_path=args.key,
            benchmark_gate=load_json(args.benchmark_gate),
            algorithm_decision=load_json(args.algorithm_decision),
            v36_handoff=load_json(args.v36_handoff),
            activation_proposal=None if args.activation_proposal is None else load_json(args.activation_proposal),
            external_benchmark_review_asserted=args.external_benchmark_review_asserted,
            external_consensus_review_asserted=args.external_consensus_review_asserted,
            notes=args.notes,
        )
        _save(args.output, value, args.overwrite)
        result = verify_algorithm_review_gate(value)
        print(json.dumps({"saved": args.output, **result}, indent=2))
        return 0 if result["algorithm_review_gate_satisfied"] else 2

    if args.command == "pow-algorithm-review-v37-verify":
        result = verify_algorithm_review_gate(load_json(args.record))
        print(json.dumps(result, indent=2))
        return 0 if result["algorithm_review_gate_satisfied"] else 2

    if args.command == "pow-review-bundle-v37-build":
        value = build_review_bundle(
            key_path=args.key,
            source_commit=args.source_commit,
            package_version=args.package_version,
            deployment_plan=load_json(args.deployment_plan),
            payout_policy=load_json(args.payout_policy),
            algorithm_review_gate=load_json(args.algorithm_review_gate),
            v36_handoff=load_json(args.v36_handoff),
            notes=args.notes,
        )
        _save(args.output, value, args.overwrite)
        result = verify_review_bundle(value)
        print(json.dumps({"saved": args.output, **result}, indent=2))
        return 0 if result["public_testnet_review_candidate_ready"] else 2

    if args.command == "pow-review-bundle-v37-verify":
        result = verify_review_bundle(load_json(args.record))
        print(json.dumps(result, indent=2))
        return 0 if result["public_testnet_review_candidate_ready"] else 2

    raise PowExecutionV37Error("unknown v0.37 command")


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in COMMANDS:
        try:
            return _run(sys.argv[1:])
        except (PowExecutionV37Error, ValueError, OSError) as exc:
            print(json.dumps({"error": str(exc), "production_mainnet_ready": False}), file=sys.stderr)
            return 2
    return cli_v36_entry.main()


if __name__ == "__main__":
    raise SystemExit(main())
