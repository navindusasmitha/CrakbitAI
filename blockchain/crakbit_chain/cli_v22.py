from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import cli_v21
from .cluster_monitor_v22 import collect_and_evaluate
from .comet_broadcast_v22 import guarded_broadcast_governance
from .governance_campaign_v22 import (
    build_campaign_evidence,
    build_campaign_plan,
    load_campaign_evidence,
    save_campaign_evidence,
    save_campaign_plan,
    verify_campaign_evidence,
)
from .governance_history_v22 import governance_history_from_paths
from .governed_lab_v22 import generate_governed_lab
from .validator_governance_v21 import load_governance_request


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.22 governed multi-node testnet campaign and evidence tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    lab = sub.add_parser("governed-lab-create")
    lab.add_argument("--output", default="runtime/governed-v22-lab")
    lab.add_argument("--chain-id", default="crakbit-v22-local")
    lab.add_argument("--nodes", type=int, default=4)
    lab.add_argument("--cometbft", default="cometbft")
    lab.add_argument("--bridge", default="./cometbft-app/crakbit-cometbft-bridge")
    lab.add_argument("--force", action="store_true")

    cluster = sub.add_parser("cluster-v22-check")
    cluster.add_argument("--inventory", required=True)
    cluster.add_argument("--timeout-seconds", type=float, default=3.0)
    cluster.add_argument("--max-height-spread", type=int, default=1)
    cluster.add_argument("--output", default=None)

    history = sub.add_parser("governance-history-v22")
    history.add_argument("--genesis", required=True)
    history.add_argument("--data", required=True)
    history.add_argument("--limit", type=int, default=100)
    history.add_argument("--output", default=None)

    broadcast = sub.add_parser("governance-v22-broadcast")
    broadcast.add_argument("--request", required=True)
    broadcast.add_argument("--rpc", required=True)
    broadcast.add_argument("--wait-for-preheight", action="store_true")
    broadcast.add_argument("--wait-timeout-seconds", type=float, default=60.0)
    broadcast.add_argument("--poll-seconds", type=float, default=0.5)
    broadcast.add_argument("--output", default=None)

    plan = sub.add_parser("campaign-v22-plan-build")
    plan.add_argument("--genesis", required=True)
    plan.add_argument("--kind", required=True, choices=["join", "remove", "replace"])
    plan.add_argument("--emit-height", type=int, required=True)
    plan.add_argument("--change-request", required=True)
    plan.add_argument("--output", required=True)
    plan.add_argument("--no-restart-boundaries", action="store_true")
    plan.add_argument("--overwrite", action="store_true")

    evidence = sub.add_parser("campaign-v22-evidence-build")
    evidence.add_argument("--genesis", required=True)
    evidence.add_argument("--key", required=True)
    evidence.add_argument("--source-commit", required=True)
    evidence.add_argument("--plan", required=True)
    evidence.add_argument("--observation", action="append", default=[])
    evidence.add_argument("--executed", action="store_true")
    evidence.add_argument("--operator-note", default="")
    evidence.add_argument("--output", required=True)
    evidence.add_argument("--overwrite", action="store_true")

    verify = sub.add_parser("campaign-v22-evidence-verify")
    verify.add_argument("--genesis", required=True)
    verify.add_argument("--evidence", required=True)
    verify.add_argument("--artifact-dir", default=None)
    verify.add_argument("--expected-signer", default=None)
    verify.add_argument("--expected-source-commit", default=None)
    return parser


def _write_json(payload: dict, path: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "governed-lab-create":
        result = generate_governed_lab(
            output=args.output,
            chain_id=args.chain_id,
            nodes=args.nodes,
            cometbft_binary=args.cometbft,
            bridge_binary=args.bridge,
            force=bool(args.force),
        )
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "cluster-v22-check":
        result = collect_and_evaluate(
            args.inventory,
            timeout_seconds=args.timeout_seconds,
            max_height_spread=args.max_height_spread,
        )
        if args.output:
            _write_json(result, args.output)
        print(json.dumps(result, indent=2))
        return 0 if result["divergence_free"] else 2

    if args.command == "governance-history-v22":
        result = governance_history_from_paths(
            genesis_path=args.genesis,
            data_dir=args.data,
            limit=args.limit,
        )
        if args.output:
            _write_json(result, args.output)
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "governance-v22-broadcast":
        result = guarded_broadcast_governance(
            load_governance_request(args.request),
            rpc_url=args.rpc,
            wait_for_preheight=bool(args.wait_for_preheight),
            wait_timeout_seconds=args.wait_timeout_seconds,
            poll_seconds=args.poll_seconds,
        )
        if args.output:
            _write_json(result, args.output)
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "campaign-v22-plan-build":
        plan = build_campaign_plan(
            genesis_path=args.genesis,
            kind=args.kind,
            emit_height=args.emit_height,
            change_request_path=args.change_request,
            restart_boundaries=not bool(args.no_restart_boundaries),
        )
        target = save_campaign_plan(plan, args.output, overwrite=bool(args.overwrite))
        print(
            json.dumps(
                {
                    "saved": str(target),
                    "change_id": plan["change_id"],
                    "emit_height": plan["emit_height"],
                    "effective_height": plan["effective_height"],
                    "restart_heights": plan["restart_heights"],
                    "campaign_executed": False,
                    "production_mainnet_ready": False,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "campaign-v22-evidence-build":
        envelope = build_campaign_evidence(
            genesis_path=args.genesis,
            signing_key_path=args.key,
            source_commit=args.source_commit,
            plan_path=args.plan,
            observation_paths=list(args.observation),
            executed=bool(args.executed),
            operator_note=args.operator_note,
        )
        target = save_campaign_evidence(envelope, args.output, overwrite=bool(args.overwrite))
        print(
            json.dumps(
                {
                    "saved": str(target),
                    "manifest_sha256": envelope["manifest_sha256"],
                    "signer": envelope["signer"],
                    "campaign_executed": bool(envelope["manifest"]["claims"]["campaign_executed"]),
                    "production_mainnet_ready": False,
                },
                indent=2,
            )
        )
        return 0

    result = verify_campaign_evidence(
        load_campaign_evidence(args.evidence),
        genesis_path=args.genesis,
        artifact_directory=args.artifact_dir,
        expected_signer=args.expected_signer,
        expected_source_commit=args.expected_source_commit,
    )
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    commands = {
        "governed-lab-create",
        "cluster-v22-check",
        "governance-history-v22",
        "governance-v22-broadcast",
        "campaign-v22-plan-build",
        "campaign-v22-evidence-build",
        "campaign-v22-evidence-verify",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        return _run(sys.argv[1:])
    return int(cli_v21.main())


if __name__ == "__main__":
    raise SystemExit(main())
