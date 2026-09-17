from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

from . import cli_v34
from .pow_testnet_v35 import (
    PowTestnetV35Error,
    build_fault_campaign,
    build_host_attestation,
    build_public_testnet_gate,
    build_testnet_freeze,
    evaluate_convergence,
    load_json,
    probe_node,
    summarize_soak,
    verify_host_attestation,
    verify_public_testnet_gate,
    verify_testnet_freeze,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crakchain", description="Crakbit v0.35 public PoW testnet evidence and review-freeze tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    host = sub.add_parser("pow-host-v35-attest")
    host.add_argument("--key", required=True)
    host.add_argument("--operator-id", required=True)
    host.add_argument("--node-id", required=True)
    host.add_argument("--provider", required=True)
    host.add_argument("--region", required=True)
    host.add_argument("--rpc-url", required=True)
    host.add_argument("--p2p-endpoint", required=True)
    host.add_argument("--source-commit", required=True)
    host.add_argument("--package-version", default="0.35.0a1")
    host.add_argument("--chain-id", required=True)
    host.add_argument("--genesis-hash", required=True)
    host.add_argument("--independently-managed", action="store_true")
    host.add_argument("--miner-role", action="store_true")
    host.add_argument("--pool-role", action="store_true")
    host.add_argument("--output", required=True)
    host.add_argument("--overwrite", action="store_true")

    verify_host = sub.add_parser("pow-host-v35-verify")
    verify_host.add_argument("--record", required=True)

    probe = sub.add_parser("pow-node-v35-probe")
    probe.add_argument("--rpc-url", required=True)
    probe.add_argument("--timeout-seconds", type=float, default=8.0)
    probe.add_argument("--output", default=None)
    probe.add_argument("--overwrite", action="store_true")

    converge = sub.add_parser("pow-convergence-v35-check")
    converge.add_argument("--observation", action="append", required=True)
    converge.add_argument("--maximum-height-lag", type=int, default=2)
    converge.add_argument("--output", required=True)
    converge.add_argument("--overwrite", action="store_true")

    soak = sub.add_parser("pow-soak-v35-summarize")
    soak.add_argument("--sample", action="append", required=True)
    soak.add_argument("--required-level", choices=["24h", "72h", "7d"], default="24h")
    soak.add_argument("--output", required=True)
    soak.add_argument("--overwrite", action="store_true")

    fault = sub.add_parser("pow-fault-v35-record")
    fault.add_argument("--kind", action="append", required=True)
    fault.add_argument("--recovered", action="store_true")
    fault.add_argument("--higher-work-reorg-observed", action="store_true")
    fault.add_argument("--partition-convergence-observed", action="store_true")
    fault.add_argument("--invalid-work-rejected", action="store_true")
    fault.add_argument("--notes", default="")
    fault.add_argument("--output", required=True)
    fault.add_argument("--overwrite", action="store_true")

    gate = sub.add_parser("pow-testnet-gate-v35-build")
    gate.add_argument("--key", required=True)
    gate.add_argument("--host-attestation", action="append", required=True)
    gate.add_argument("--convergence", required=True)
    gate.add_argument("--soak", required=True)
    gate.add_argument("--fault-campaign", required=True)
    gate.add_argument("--minimum-hosts", type=int, default=4)
    gate.add_argument("--output", required=True)
    gate.add_argument("--overwrite", action="store_true")

    gate_verify = sub.add_parser("pow-testnet-gate-v35-verify")
    gate_verify.add_argument("--record", required=True)

    freeze = sub.add_parser("pow-testnet-freeze-v35-build")
    freeze.add_argument("--key", required=True)
    freeze.add_argument("--gate", required=True)
    freeze.add_argument("--source-commit", required=True)
    freeze.add_argument("--notes", default="")
    freeze.add_argument("--output", required=True)
    freeze.add_argument("--overwrite", action="store_true")

    freeze_verify = sub.add_parser("pow-testnet-freeze-v35-verify")
    freeze_verify.add_argument("--record", required=True)
    return parser


def _save(path: str | Path, value: dict, overwrite: bool) -> None:
    target = Path(path)
    if target.exists() and not overwrite:
        raise ValueError(f"file exists: {target}; pass --overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)
    if args.command == "pow-host-v35-attest":
        value = build_host_attestation(key_path=args.key, operator_id=args.operator_id, node_id=args.node_id, provider=args.provider, region=args.region, rpc_url=args.rpc_url, p2p_endpoint=args.p2p_endpoint, source_commit=args.source_commit, package_version=args.package_version, chain_id=args.chain_id, genesis_hash=args.genesis_hash, independently_managed=args.independently_managed, miner_role=args.miner_role, pool_role=args.pool_role)
        _save(args.output, value, args.overwrite); print(json.dumps({"saved": args.output, "attestation_id": value["manifest"]["attestation_id"], "production_mainnet_ready": False}, indent=2)); return 0
    if args.command == "pow-host-v35-verify":
        print(json.dumps(verify_host_attestation(load_json(args.record)), indent=2)); return 0
    if args.command == "pow-node-v35-probe":
        value = probe_node(args.rpc_url, timeout_seconds=args.timeout_seconds)
        if args.output: _save(args.output, value, args.overwrite)
        print(json.dumps(value, indent=2)); return 0
    if args.command == "pow-convergence-v35-check":
        value = evaluate_convergence([load_json(p) for p in args.observation], maximum_height_lag=args.maximum_height_lag)
        _save(args.output, value, args.overwrite); print(json.dumps(value, indent=2)); return 0 if value["converged"] else 2
    if args.command == "pow-soak-v35-summarize":
        value = summarize_soak([load_json(p) for p in args.sample], required_level=args.required_level)
        _save(args.output, value, args.overwrite); print(json.dumps(value, indent=2)); return 0 if value["soak_gate_satisfied"] else 2
    if args.command == "pow-fault-v35-record":
        value = build_fault_campaign(kinds=args.kind, recovered=args.recovered, higher_work_reorg_observed=args.higher_work_reorg_observed, partition_convergence_observed=args.partition_convergence_observed, invalid_work_rejected=args.invalid_work_rejected, notes=args.notes)
        _save(args.output, value, args.overwrite); print(json.dumps(value, indent=2)); return 0 if value["fault_gate_satisfied"] else 2
    if args.command == "pow-testnet-gate-v35-build":
        value = build_public_testnet_gate(key_path=args.key, host_attestations=[load_json(p) for p in args.host_attestation], convergence=load_json(args.convergence), soak=load_json(args.soak), fault_campaign=load_json(args.fault_campaign), minimum_hosts=args.minimum_hosts)
        _save(args.output, value, args.overwrite); print(json.dumps({"saved": args.output, "gate_id": value["manifest"]["gate_id"], "public_testnet_gate_satisfied": value["manifest"]["public_testnet_gate_satisfied"], "production_mainnet_ready": False}, indent=2)); return 0 if value["manifest"]["public_testnet_gate_satisfied"] else 2
    if args.command == "pow-testnet-gate-v35-verify":
        value = verify_public_testnet_gate(load_json(args.record)); print(json.dumps(value, indent=2)); return 0 if value["public_testnet_gate_satisfied"] else 2
    if args.command == "pow-testnet-freeze-v35-build":
        value = build_testnet_freeze(key_path=args.key, gate_record=load_json(args.gate), source_commit=args.source_commit, notes=args.notes)
        _save(args.output, value, args.overwrite); print(json.dumps({"saved": args.output, "freeze_id": value["manifest"]["freeze_id"], "production_mainnet_ready": False}, indent=2)); return 0
    if args.command == "pow-testnet-freeze-v35-verify":
        print(json.dumps(verify_testnet_freeze(load_json(args.record)), indent=2)); return 0
    raise ValueError("unknown v0.35 command")


def main() -> int:
    commands = {"pow-host-v35-attest", "pow-host-v35-verify", "pow-node-v35-probe", "pow-convergence-v35-check", "pow-soak-v35-summarize", "pow-fault-v35-record", "pow-testnet-gate-v35-build", "pow-testnet-gate-v35-verify", "pow-testnet-freeze-v35-build", "pow-testnet-freeze-v35-verify"}
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        try: return _run(sys.argv[1:])
        except (PowTestnetV35Error, ValueError, OSError, httpx.HTTPError) as exc:
            print(json.dumps({"error": str(exc), "production_mainnet_ready": False}), file=sys.stderr); return 2
    return cli_v34.main()


if __name__ == "__main__": raise SystemExit(main())
