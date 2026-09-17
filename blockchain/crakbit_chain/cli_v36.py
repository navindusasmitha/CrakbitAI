from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import cli_v35
from .pow_activation_v36 import PowActivationV36Error, build_activation_proposal, load_json as load_activation_json, verify_activation_proposal
from .pow_campaign_v36 import CampaignLogV36, PowCampaignV36Error, load_campaign_log, summarize_campaign, verify_campaign_log
from .pow_node_v36 import PowNodeV36Error, run_node_v36, select_seed_peers_v36
from .pow_reorg_v36 import PowReorgV36Error, rehearse_incremental_undo


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.36 controlled PoW testnet integration, campaign evidence and reorg rehearsal tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    campaign_probe = sub.add_parser("pow-campaign-v36-probe")
    campaign_probe.add_argument("--key", required=True)
    campaign_probe.add_argument("--log", required=True)
    campaign_probe.add_argument("--rpc-url", action="append", required=True)
    campaign_probe.add_argument("--timeout-seconds", type=float, default=8.0)
    campaign_probe.add_argument("--label", default="")

    campaign_verify = sub.add_parser("pow-campaign-v36-verify")
    campaign_verify.add_argument("--log", required=True)

    campaign_summary = sub.add_parser("pow-campaign-v36-summarize")
    campaign_summary.add_argument("--log", required=True)
    campaign_summary.add_argument("--required-level", choices=["24h", "72h", "7d"], default="24h")
    campaign_summary.add_argument("--minimum-nodes", type=int, default=4)
    campaign_summary.add_argument("--minimum-sample-success-ratio", type=float, default=0.99)
    campaign_summary.add_argument("--maximum-height-lag", type=int, default=2)
    campaign_summary.add_argument("--output", required=True)
    campaign_summary.add_argument("--overwrite", action="store_true")

    undo = sub.add_parser("pow-undo-v36-rehearse")
    undo.add_argument("--db", required=True)
    undo.add_argument("--disconnect-blocks", type=int, default=1)
    undo.add_argument("--keep-copy", default=None)
    undo.add_argument("--output", required=True)
    undo.add_argument("--overwrite", action="store_true")

    seeds = sub.add_parser("pow-peer-seeds-v36-select")
    seeds.add_argument("--peer-db", default=None)
    seeds.add_argument("--peer", action="append", default=[])
    seeds.add_argument("--limit", type=int, default=16)
    seeds.add_argument("--max-per-bucket", type=int, default=2)
    seeds.add_argument("--output", default=None)
    seeds.add_argument("--overwrite", action="store_true")

    node = sub.add_parser("pow-node-v36-run")
    node.add_argument("--db", required=True)
    node.add_argument("--network-key", required=True)
    node.add_argument("--peer-db", default=None)
    node.add_argument("--peer", action="append", default=[])
    node.add_argument("--rpc-host", default="127.0.0.1")
    node.add_argument("--rpc-port", type=int, default=28443)
    node.add_argument("--p2p-host", default="0.0.0.0")
    node.add_argument("--p2p-port", type=int, default=28444)
    node.add_argument("--advertised-endpoint", default=None)
    node.add_argument("--max-peers", type=int, default=32)
    node.add_argument("--seed-limit", type=int, default=16)
    node.add_argument("--max-per-bucket", type=int, default=2)

    activation = sub.add_parser("pow-activation-v36-build")
    activation.add_argument("--key", required=True)
    activation.add_argument("--algorithm-decision", required=True)
    activation.add_argument("--source-commit", required=True)
    activation.add_argument("--chain-id", required=True)
    activation.add_argument("--genesis-hash", required=True)
    activation.add_argument("--current-height", type=int, required=True)
    activation.add_argument("--activation-height", type=int, default=None)
    activation.add_argument("--consensus-vectors-sha256", default=None)
    activation.add_argument("--randomx-library-sha256", default=None)
    activation.add_argument("--minimum-notice-blocks", type=int, default=1000)
    activation.add_argument("--notes", default="")
    activation.add_argument("--output", required=True)
    activation.add_argument("--overwrite", action="store_true")

    activation_verify = sub.add_parser("pow-activation-v36-verify")
    activation_verify.add_argument("--record", required=True)
    return parser


def _save(path: str | Path, value: dict, *, overwrite: bool = False) -> None:
    target = Path(path)
    if target.exists() and not overwrite:
        raise ValueError(f"file exists: {target}; pass --overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "pow-campaign-v36-probe":
        log = CampaignLogV36(args.log, args.key)
        value = log.probe_and_append(args.rpc_url, timeout_seconds=args.timeout_seconds, label=args.label)
        print(json.dumps(value, indent=2))
        return 0 if not value["probe_errors"] else 2

    if args.command == "pow-campaign-v36-verify":
        value = verify_campaign_log(load_campaign_log(args.log))
        print(json.dumps(value, indent=2))
        return 0

    if args.command == "pow-campaign-v36-summarize":
        value = summarize_campaign(
            load_campaign_log(args.log),
            required_level=args.required_level,
            minimum_nodes=args.minimum_nodes,
            minimum_sample_success_ratio=args.minimum_sample_success_ratio,
            maximum_height_lag=args.maximum_height_lag,
        )
        _save(args.output, value, overwrite=args.overwrite)
        print(json.dumps(value, indent=2))
        return 0 if value["campaign_gate_satisfied"] else 2

    if args.command == "pow-undo-v36-rehearse":
        value = rehearse_incremental_undo(
            args.db,
            disconnect_blocks=args.disconnect_blocks,
            keep_copy=args.keep_copy,
        )
        _save(args.output, value, overwrite=args.overwrite)
        print(json.dumps(value, indent=2))
        return 0 if value["rehearsal_passed"] else 2

    if args.command == "pow-peer-seeds-v36-select":
        value = select_seed_peers_v36(
            peer_db=args.peer_db,
            explicit_peers=args.peer,
            limit=args.limit,
            max_per_bucket=args.max_per_bucket,
        )
        if args.output:
            _save(args.output, value, overwrite=args.overwrite)
        print(json.dumps(value, indent=2))
        return 0

    if args.command == "pow-node-v36-run":
        run_node_v36(
            db_path=args.db,
            network_key_path=args.network_key,
            peer_db=args.peer_db,
            explicit_peers=args.peer,
            rpc_host=args.rpc_host,
            rpc_port=args.rpc_port,
            p2p_host=args.p2p_host,
            p2p_port=args.p2p_port,
            advertised_endpoint=args.advertised_endpoint,
            max_peers=args.max_peers,
            seed_limit=args.seed_limit,
            max_per_bucket=args.max_per_bucket,
        )
        return 0

    if args.command == "pow-activation-v36-build":
        value = build_activation_proposal(
            key_path=args.key,
            algorithm_decision=load_activation_json(args.algorithm_decision),
            source_commit=args.source_commit,
            chain_id=args.chain_id,
            genesis_hash=args.genesis_hash,
            current_height=args.current_height,
            activation_height=args.activation_height,
            consensus_vectors_sha256=args.consensus_vectors_sha256,
            randomx_library_sha256=args.randomx_library_sha256,
            minimum_notice_blocks=args.minimum_notice_blocks,
            notes=args.notes,
        )
        _save(args.output, value, overwrite=args.overwrite)
        print(json.dumps({
            "saved": args.output,
            "proposal_id": value["manifest"]["proposal_id"],
            "decision": value["manifest"]["decision"],
            "consensus_activated": False,
            "production_mainnet_ready": False,
        }, indent=2))
        return 0

    if args.command == "pow-activation-v36-verify":
        print(json.dumps(verify_activation_proposal(load_activation_json(args.record)), indent=2))
        return 0

    raise ValueError("unknown v0.36 command")


def main() -> int:
    commands = {
        "pow-campaign-v36-probe",
        "pow-campaign-v36-verify",
        "pow-campaign-v36-summarize",
        "pow-undo-v36-rehearse",
        "pow-peer-seeds-v36-select",
        "pow-node-v36-run",
        "pow-activation-v36-build",
        "pow-activation-v36-verify",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        try:
            return _run(sys.argv[1:])
        except (PowCampaignV36Error, PowReorgV36Error, PowNodeV36Error, PowActivationV36Error, ValueError, OSError) as exc:
            print(json.dumps({"error": str(exc), "production_mainnet_ready": False}), file=sys.stderr)
            return 2
    return cli_v35.main()


if __name__ == "__main__":
    raise SystemExit(main())
