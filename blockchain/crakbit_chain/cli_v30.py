from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import cli_v29
from .operations_v30 import (
    build_archive_manifest,
    build_edge_redundancy_gate,
    build_monitor_checkpoint,
    build_monitor_inventory,
    build_operator_checklist,
    build_public_evidence_bundle,
    build_signer_monitor_record,
    load_json,
    probe_and_build_edge_health_record,
    probe_monitor_sample,
    probe_signer_tcp,
    save_json,
    verify_archive_manifest,
    verify_edge_health_record,
    verify_edge_redundancy_gate,
    verify_monitor_checkpoint,
    verify_monitor_inventory,
    verify_monitor_sample,
    verify_operator_checklist,
    verify_public_evidence_bundle,
    verify_signer_monitor_record,
)


def _artifacts(values: list[str]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for value in values:
        if "=" not in value:
            raise SystemExit("artifact must use ROLE=PATH")
        role, path = value.split("=", 1)
        if not role.strip() or not path.strip():
            raise SystemExit("artifact must use non-empty ROLE=PATH")
        result.append((role.strip(), path.strip()))
    return result


def _load_hosts(path: str) -> list[dict]:
    body = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(body, list):
        return body
    if isinstance(body, dict) and isinstance(body.get("hosts"), list):
        return body["hosts"]
    raise SystemExit("host inventory input must be a JSON array or object with hosts array")


def _load_checks(path: str) -> dict[str, bool]:
    body = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(body, dict):
        raise SystemExit("checklist input must be a JSON object")
    return {str(key): bool(value) for key, value in body.items()}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.30 continuous operations, resumable evidence, edge monitoring and public evidence publication tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    inventory = sub.add_parser("monitor-inventory-v30-build")
    inventory.add_argument("--key", required=True)
    inventory.add_argument("--source-commit", required=True)
    inventory.add_argument("--candidate-identity-sha256", required=True)
    inventory.add_argument("--application-genesis-sha256", required=True)
    inventory.add_argument("--consensus-genesis-sha256", required=True)
    inventory.add_argument("--chain-id", required=True)
    inventory.add_argument("--input", required=True)
    inventory.add_argument("--output", required=True)
    inventory.add_argument("--overwrite", action="store_true")

    inventory_verify = sub.add_parser("monitor-inventory-v30-verify")
    inventory_verify.add_argument("--record", required=True)
    inventory_verify.add_argument("--expected-signer", default=None)

    sample = sub.add_parser("monitor-sample-v30-probe")
    sample.add_argument("--key", required=True)
    sample.add_argument("--inventory", required=True)
    sample.add_argument("--timeout-seconds", type=float, default=5.0)
    sample.add_argument("--maximum-height-spread", type=int, default=2)
    sample.add_argument("--output", required=True)
    sample.add_argument("--overwrite", action="store_true")

    sample_verify = sub.add_parser("monitor-sample-v30-verify")
    sample_verify.add_argument("--record", required=True)
    sample_verify.add_argument("--expected-signer", default=None)

    checkpoint = sub.add_parser("monitor-checkpoint-v30-build")
    checkpoint.add_argument("--key", required=True)
    checkpoint.add_argument("--session-id", required=True)
    checkpoint.add_argument("--sample", action="append", required=True)
    checkpoint.add_argument("--previous", default=None)
    checkpoint.add_argument("--target-duration-seconds", type=int, default=604800)
    checkpoint.add_argument("--minimum-success-ratio", type=float, default=0.99)
    checkpoint.add_argument("--output", required=True)
    checkpoint.add_argument("--overwrite", action="store_true")

    checkpoint_verify = sub.add_parser("monitor-checkpoint-v30-verify")
    checkpoint_verify.add_argument("--record", required=True)
    checkpoint_verify.add_argument("--expected-signer", default=None)

    archive = sub.add_parser("archive-v30-build")
    archive.add_argument("--key", required=True)
    archive.add_argument("--source-commit", required=True)
    archive.add_argument("--candidate-identity-sha256", required=True)
    archive.add_argument("--artifact", action="append", required=True, help="ROLE=PATH")
    archive.add_argument("--retention-days", type=int, default=90)
    archive.add_argument("--output", required=True)
    archive.add_argument("--overwrite", action="store_true")

    archive_verify = sub.add_parser("archive-v30-verify")
    archive_verify.add_argument("--record", required=True)
    archive_verify.add_argument("--expected-signer", default=None)
    archive_verify.add_argument("--artifact-dir", default=None)

    edge = sub.add_parser("edge-v30-probe")
    edge.add_argument("--key", required=True)
    edge.add_argument("--source-commit", required=True)
    edge.add_argument("--candidate-identity-sha256", required=True)
    edge.add_argument("--edge-id", required=True)
    edge.add_argument("--role", choices=["rpc", "explorer", "gateway"], required=True)
    edge.add_argument("--url", required=True)
    edge.add_argument("--timeout-seconds", type=float, default=5.0)
    edge.add_argument("--max-latency-ms", type=float, default=2000.0)
    edge.add_argument("--output", required=True)
    edge.add_argument("--overwrite", action="store_true")

    edge_verify = sub.add_parser("edge-v30-verify")
    edge_verify.add_argument("--record", required=True)
    edge_verify.add_argument("--expected-signer", default=None)

    edge_gate = sub.add_parser("edge-gate-v30-build")
    edge_gate.add_argument("--key", required=True)
    edge_gate.add_argument("--record", action="append", required=True)
    edge_gate.add_argument("--minimum-per-role", type=int, default=2)
    edge_gate.add_argument("--output", required=True)
    edge_gate.add_argument("--overwrite", action="store_true")

    edge_gate_verify = sub.add_parser("edge-gate-v30-verify")
    edge_gate_verify.add_argument("--record", required=True)
    edge_gate_verify.add_argument("--expected-signer", default=None)

    signer = sub.add_parser("signer-v30-probe")
    signer.add_argument("--key", required=True)
    signer.add_argument("--source-commit", required=True)
    signer.add_argument("--candidate-identity-sha256", required=True)
    signer.add_argument("--signer-id", required=True)
    signer.add_argument("--custody-type", choices=["hsm", "remote-signer", "hardware-backed", "equivalent-protected"], required=True)
    signer.add_argument("--host", required=True)
    signer.add_argument("--port", type=int, required=True)
    signer.add_argument("--timeout-seconds", type=float, default=3.0)
    signer.add_argument("--rotation-drill-manifest-sha256", required=True)
    signer.add_argument("--output", required=True)
    signer.add_argument("--overwrite", action="store_true")

    signer_verify = sub.add_parser("signer-v30-verify")
    signer_verify.add_argument("--record", required=True)
    signer_verify.add_argument("--expected-signer", default=None)

    bundle = sub.add_parser("public-evidence-v30-build")
    bundle.add_argument("--key", required=True)
    bundle.add_argument("--real-freeze-v29", required=True)
    bundle.add_argument("--monitor-checkpoint", required=True)
    bundle.add_argument("--archive-manifest", required=True)
    bundle.add_argument("--edge-gate", required=True)
    bundle.add_argument("--signer-record", action="append", required=True)
    bundle.add_argument("--artifact", action="append", default=[], help="ROLE=PATH")
    bundle.add_argument("--output", required=True)
    bundle.add_argument("--overwrite", action="store_true")

    bundle_verify = sub.add_parser("public-evidence-v30-verify")
    bundle_verify.add_argument("--record", required=True)
    bundle_verify.add_argument("--expected-signer", default=None)

    checklist = sub.add_parser("operator-checklist-v30-build")
    checklist.add_argument("--key", required=True)
    checklist.add_argument("--public-evidence-bundle", required=True)
    checklist.add_argument("--operator-id", required=True)
    checklist.add_argument("--input", required=True)
    checklist.add_argument("--notes", default="")
    checklist.add_argument("--output", required=True)
    checklist.add_argument("--overwrite", action="store_true")

    checklist_verify = sub.add_parser("operator-checklist-v30-verify")
    checklist_verify.add_argument("--record", required=True)
    checklist_verify.add_argument("--expected-signer", default=None)
    return parser


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "monitor-inventory-v30-build":
        result = build_monitor_inventory(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            candidate_identity_sha256=args.candidate_identity_sha256,
            application_genesis_sha256=args.application_genesis_sha256,
            consensus_genesis_sha256=args.consensus_genesis_sha256,
            chain_id=args.chain_id,
            hosts=_load_hosts(args.input),
        )
        save_json(result, args.output, overwrite=args.overwrite)
        print(json.dumps({"saved": args.output, "inventory_gate_satisfied": result["manifest"]["inventory_gate_satisfied"], "host_count": len(result["manifest"]["hosts"]), "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["inventory_gate_satisfied"] else 2

    if args.command == "monitor-inventory-v30-verify":
        print(json.dumps(verify_monitor_inventory(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "monitor-sample-v30-probe":
        result = probe_monitor_sample(
            signing_key_path=args.key,
            inventory=load_json(args.inventory),
            timeout_seconds=args.timeout_seconds,
            maximum_height_spread=args.maximum_height_spread,
        )
        save_json(result, args.output, overwrite=args.overwrite)
        print(json.dumps({"saved": args.output, "sample_gate_satisfied": result["manifest"]["sample_gate_satisfied"], "height_spread": result["manifest"]["height_spread"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["sample_gate_satisfied"] else 2

    if args.command == "monitor-sample-v30-verify":
        print(json.dumps(verify_monitor_sample(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "monitor-checkpoint-v30-build":
        result = build_monitor_checkpoint(
            signing_key_path=args.key,
            session_id=args.session_id,
            samples=[load_json(path) for path in args.sample],
            target_duration_seconds=args.target_duration_seconds,
            minimum_success_ratio=args.minimum_success_ratio,
            previous_checkpoint=load_json(args.previous) if args.previous else None,
        )
        save_json(result, args.output, overwrite=args.overwrite)
        print(json.dumps({"saved": args.output, "sample_count": result["manifest"]["sample_count"], "duration_seconds": result["manifest"]["duration_seconds"], "success_ratio": result["manifest"]["success_ratio"], "checkpoint_complete": result["manifest"]["checkpoint_complete"], "production_mainnet_ready": False}, indent=2))
        return 0

    if args.command == "monitor-checkpoint-v30-verify":
        print(json.dumps(verify_monitor_checkpoint(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "archive-v30-build":
        result = build_archive_manifest(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            candidate_identity_sha256=args.candidate_identity_sha256,
            artifacts=_artifacts(args.artifact),
            retention_days=args.retention_days,
        )
        save_json(result, args.output, overwrite=args.overwrite)
        print(json.dumps({"saved": args.output, "artifact_count": result["manifest"]["artifact_count"], "retention_days": result["manifest"]["retention_days"], "production_mainnet_ready": False}, indent=2))
        return 0

    if args.command == "archive-v30-verify":
        print(json.dumps(verify_archive_manifest(load_json(args.record), expected_signer=args.expected_signer, artifact_dir=args.artifact_dir), indent=2))
        return 0

    if args.command == "edge-v30-probe":
        result = probe_and_build_edge_health_record(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            candidate_identity_sha256=args.candidate_identity_sha256,
            edge_id=args.edge_id,
            role=args.role,
            url=args.url,
            timeout_seconds=args.timeout_seconds,
            max_latency_ms=args.max_latency_ms,
        )
        save_json(result, args.output, overwrite=args.overwrite)
        print(json.dumps({"saved": args.output, "edge_id": result["manifest"]["edge_id"], "role": result["manifest"]["role"], "edge_gate_satisfied": result["manifest"]["edge_gate_satisfied"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["edge_gate_satisfied"] else 2

    if args.command == "edge-v30-verify":
        print(json.dumps(verify_edge_health_record(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "edge-gate-v30-build":
        result = build_edge_redundancy_gate(
            signing_key_path=args.key,
            records=[load_json(path) for path in args.record],
            minimum_per_role=args.minimum_per_role,
        )
        save_json(result, args.output, overwrite=args.overwrite)
        print(json.dumps({"saved": args.output, "edge_redundancy_gate_satisfied": result["manifest"]["edge_redundancy_gate_satisfied"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["edge_redundancy_gate_satisfied"] else 2

    if args.command == "edge-gate-v30-verify":
        print(json.dumps(verify_edge_redundancy_gate(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "signer-v30-probe":
        reachable = probe_signer_tcp(args.host, args.port, timeout_seconds=args.timeout_seconds)
        result = build_signer_monitor_record(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            candidate_identity_sha256=args.candidate_identity_sha256,
            signer_id=args.signer_id,
            custody_type=args.custody_type,
            host=args.host,
            port=args.port,
            reachable=reachable,
            rotation_drill_manifest_sha256=args.rotation_drill_manifest_sha256,
            no_private_key_read=True,
        )
        save_json(result, args.output, overwrite=args.overwrite)
        print(json.dumps({"saved": args.output, "signer_id": result["manifest"]["signer_id"], "signer_monitor_gate_satisfied": result["manifest"]["signer_monitor_gate_satisfied"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["signer_monitor_gate_satisfied"] else 2

    if args.command == "signer-v30-verify":
        print(json.dumps(verify_signer_monitor_record(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "public-evidence-v30-build":
        result = build_public_evidence_bundle(
            signing_key_path=args.key,
            real_freeze_v29=load_json(args.real_freeze_v29),
            monitor_checkpoint=load_json(args.monitor_checkpoint),
            archive_manifest=load_json(args.archive_manifest),
            edge_gate=load_json(args.edge_gate),
            signer_records=[load_json(path) for path in args.signer_record],
            artifacts=_artifacts(args.artifact),
        )
        save_json(result, args.output, overwrite=args.overwrite)
        print(json.dumps({"saved": args.output, "public_evidence_bundle_gate_satisfied": result["manifest"]["public_evidence_bundle_gate_satisfied"], "manual_launch_decision_required": True, "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["public_evidence_bundle_gate_satisfied"] else 2

    if args.command == "public-evidence-v30-verify":
        print(json.dumps(verify_public_evidence_bundle(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "operator-checklist-v30-build":
        result = build_operator_checklist(
            signing_key_path=args.key,
            public_evidence_bundle=load_json(args.public_evidence_bundle),
            operator_id=args.operator_id,
            checks=_load_checks(args.input),
            notes=args.notes,
        )
        save_json(result, args.output, overwrite=args.overwrite)
        print(json.dumps({"saved": args.output, "operator_id": result["manifest"]["operator_id"], "operator_checklist_complete": result["manifest"]["operator_checklist_complete"], "automatic_launch": False, "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["operator_checklist_complete"] else 2

    print(json.dumps(verify_operator_checklist(load_json(args.record), expected_signer=args.expected_signer), indent=2))
    return 0


def main() -> int:
    commands = {
        "monitor-inventory-v30-build", "monitor-inventory-v30-verify",
        "monitor-sample-v30-probe", "monitor-sample-v30-verify",
        "monitor-checkpoint-v30-build", "monitor-checkpoint-v30-verify",
        "archive-v30-build", "archive-v30-verify",
        "edge-v30-probe", "edge-v30-verify", "edge-gate-v30-build", "edge-gate-v30-verify",
        "signer-v30-probe", "signer-v30-verify",
        "public-evidence-v30-build", "public-evidence-v30-verify",
        "operator-checklist-v30-build", "operator-checklist-v30-verify",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        try:
            return _run(sys.argv[1:])
        except Exception as exc:
            print(json.dumps({"error": str(exc), "production_mainnet_ready": False}), file=sys.stderr)
            return 2
    return cli_v29.main()


if __name__ == "__main__":
    raise SystemExit(main())
