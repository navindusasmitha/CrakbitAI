from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, cli_v23
from .ops_hardening_v24 import (
    build_fault_plan,
    build_fault_result,
    build_readiness,
    build_recovery_record,
    build_remote_signer_record,
    build_signed_evidence,
    probe_redundancy,
    run_host_preflight,
    save_json,
    verify_signed_evidence,
)


def _read(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.24 operational fault, recovery, signer and long-soak hardening tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("host-preflight-v24")
    preflight.add_argument("--node-name", required=True)
    preflight.add_argument("--application-genesis", required=True)
    preflight.add_argument("--application-genesis-sha256", required=True)
    preflight.add_argument("--consensus-genesis", required=True)
    preflight.add_argument("--consensus-genesis-sha256", required=True)
    preflight.add_argument("--data", required=True)
    preflight.add_argument("--token-file", required=True)
    preflight.add_argument("--execution-bind", default="127.0.0.1:26659")
    preflight.add_argument("--abci-bind", default="tcp://127.0.0.1:26658")
    preflight.add_argument("--expected-package-version", default="0.24.0a1")
    preflight.add_argument("--cometbft", default="cometbft")
    preflight.add_argument("--expected-cometbft-version", default="v0.40.0")
    preflight.add_argument("--minimum-free-bytes", type=int, default=5 * 1024 * 1024 * 1024)
    preflight.add_argument("--output", required=True)
    preflight.add_argument("--overwrite", action="store_true")

    plan = sub.add_parser("fault-v24-plan-build")
    plan.add_argument("--spec", required=True, help="JSON object with name and steps; each step needs kind, command argv and recovery_command argv")
    plan.add_argument("--output", required=True)
    plan.add_argument("--overwrite", action="store_true")

    fault_result = sub.add_parser("fault-v24-result-build")
    fault_result.add_argument("--plan", required=True)
    fault_result.add_argument("--campaign-result", required=True)
    fault_result.add_argument("--output", required=True)
    fault_result.add_argument("--overwrite", action="store_true")

    recovery = sub.add_parser("recovery-v24-record")
    recovery.add_argument("--kind", required=True, choices=["backup-restore", "clean-host-state-sync"])
    recovery.add_argument("--source-height", required=True, type=int)
    recovery.add_argument("--restored-height", required=True, type=int)
    recovery.add_argument("--source-app-hash", required=True)
    recovery.add_argument("--restored-app-hash", required=True)
    recovery.add_argument("--source-state-root", default="")
    recovery.add_argument("--restored-state-root", default="")
    recovery.add_argument("--clean-host", action="store_true")
    recovery.add_argument("--notes", default="")
    recovery.add_argument("--output", required=True)
    recovery.add_argument("--overwrite", action="store_true")

    signer = sub.add_parser("remote-signer-v24-record")
    signer.add_argument("--validator", required=True)
    signer.add_argument("--signer-type", required=True)
    signer.add_argument("--key-exported", action="store_true")
    signer.add_argument("--double-sign-protection", action="store_true")
    signer.add_argument("--restart-recovery-drilled", action="store_true")
    signer.add_argument("--failover-drilled", action="store_true")
    signer.add_argument("--signer-endpoint-private", action="store_true")
    signer.add_argument("--operator-note", default="")
    signer.add_argument("--output", required=True)
    signer.add_argument("--overwrite", action="store_true")

    redundancy = sub.add_parser("redundancy-v24-check")
    redundancy.add_argument("--chain-id", required=True)
    redundancy.add_argument("--rpc", action="append", required=True)
    redundancy.add_argument("--explorer", action="append", required=True)
    redundancy.add_argument("--timeout-seconds", type=float, default=4.0)
    redundancy.add_argument("--output", required=True)
    redundancy.add_argument("--overwrite", action="store_true")

    readiness = sub.add_parser("readiness-v24-build")
    readiness.add_argument("--soak-24h", default=None)
    readiness.add_argument("--soak-72h", default=None)
    readiness.add_argument("--soak-7d", default=None)
    readiness.add_argument("--fault-result", action="append", default=[])
    readiness.add_argument("--recovery", action="append", default=[])
    readiness.add_argument("--signer-record", action="append", default=[])
    readiness.add_argument("--redundancy", default=None)
    readiness.add_argument("--output", required=True)
    readiness.add_argument("--overwrite", action="store_true")

    sign = sub.add_parser("ops-v24-sign")
    sign.add_argument("--key", required=True)
    sign.add_argument("--source-commit", required=True)
    sign.add_argument("--package-version", default="0.24.0a1")
    sign.add_argument("--cometbft-version", default="v0.40.0")
    sign.add_argument("--artifact", action="append", required=True)
    sign.add_argument("--operator-note", default="")
    sign.add_argument("--output", required=True)
    sign.add_argument("--overwrite", action="store_true")

    verify = sub.add_parser("ops-v24-verify")
    verify.add_argument("--evidence", required=True)
    verify.add_argument("--artifact-dir", default=None)
    verify.add_argument("--expected-signer", default=None)
    verify.add_argument("--expected-source-commit", default=None)
    return parser


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "host-preflight-v24":
        result = run_host_preflight(
            node_name=args.node_name,
            application_genesis=args.application_genesis,
            expected_application_genesis_sha256=args.application_genesis_sha256,
            consensus_genesis=args.consensus_genesis,
            expected_consensus_genesis_sha256=args.consensus_genesis_sha256,
            data_dir=args.data,
            token_file=args.token_file,
            execution_bind=args.execution_bind,
            abci_bind=args.abci_bind,
            package_version=__version__,
            expected_package_version=args.expected_package_version,
            cometbft_binary=args.cometbft,
            expected_cometbft_version=args.expected_cometbft_version,
            minimum_free_bytes=args.minimum_free_bytes,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, **result}, indent=2))
        return 0 if result["ready_to_start"] else 2

    if args.command == "fault-v24-plan-build":
        spec = _read(args.spec)
        result = build_fault_plan(name=str(spec.get("name", "")), steps=list(spec.get("steps") or []))
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, **result}, indent=2))
        return 0

    if args.command == "fault-v24-result-build":
        result = build_fault_result(plan=_read(args.plan), campaign_result=_read(args.campaign_result))
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, **result}, indent=2))
        return 0 if result["all_steps_recovered"] else 2

    if args.command == "recovery-v24-record":
        result = build_recovery_record(
            kind=args.kind,
            source_height=args.source_height,
            restored_height=args.restored_height,
            source_application_hash=args.source_app_hash,
            restored_application_hash=args.restored_app_hash,
            source_state_root=args.source_state_root,
            restored_state_root=args.restored_state_root,
            clean_host=bool(args.clean_host),
            notes=args.notes,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, **result}, indent=2))
        return 0 if result["success"] else 2

    if args.command == "remote-signer-v24-record":
        result = build_remote_signer_record(
            validator_name=args.validator,
            signer_type=args.signer_type,
            key_exported=bool(args.key_exported),
            double_sign_protection=bool(args.double_sign_protection),
            restart_recovery_drilled=bool(args.restart_recovery_drilled),
            failover_drilled=bool(args.failover_drilled),
            signer_endpoint_private=bool(args.signer_endpoint_private),
            operator_note=args.operator_note,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, **result}, indent=2))
        return 0 if result["protected_signer_gate_satisfied"] else 2

    if args.command == "redundancy-v24-check":
        result = probe_redundancy(
            rpc_urls=list(args.rpc),
            explorer_urls=list(args.explorer),
            expected_chain_id=args.chain_id,
            timeout_seconds=args.timeout_seconds,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, **result}, indent=2))
        return 0 if result["redundancy_gate_satisfied"] else 2

    if args.command == "readiness-v24-build":
        result = build_readiness(
            soak_24h=_read(args.soak_24h) if args.soak_24h else None,
            soak_72h=_read(args.soak_72h) if args.soak_72h else None,
            soak_7d=_read(args.soak_7d) if args.soak_7d else None,
            fault_results=[_read(path) for path in args.fault_result],
            recovery_records=[_read(path) for path in args.recovery],
            signer_records=[_read(path) for path in args.signer_record],
            redundancy_report=_read(args.redundancy) if args.redundancy else None,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, **result}, indent=2))
        return 0 if result["operational_review_candidate"] else 2

    if args.command == "ops-v24-sign":
        result = build_signed_evidence(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            package_version=args.package_version,
            cometbft_version=args.cometbft_version,
            artifact_paths=list(args.artifact),
            operator_note=args.operator_note,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "manifest_sha256": result["manifest_sha256"], "signer": result["signer"], "production_mainnet_ready": False}, indent=2))
        return 0

    result = verify_signed_evidence(
        _read(args.evidence),
        artifact_directory=args.artifact_dir,
        expected_signer=args.expected_signer,
        expected_source_commit=args.expected_source_commit,
    )
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    commands = {
        "host-preflight-v24",
        "fault-v24-plan-build",
        "fault-v24-result-build",
        "recovery-v24-record",
        "remote-signer-v24-record",
        "redundancy-v24-check",
        "readiness-v24-build",
        "ops-v24-sign",
        "ops-v24-verify",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        return _run(sys.argv[1:])
    return int(cli_v23.main())


if __name__ == "__main__":
    raise SystemExit(main())
