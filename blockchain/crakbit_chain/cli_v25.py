from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, cli_v24
from .review_candidate_v25 import (
    build_host_attestation,
    build_incident_record,
    build_review_freeze,
    build_review_gate,
    load_json,
    save_json,
    verify_host_attestation,
    verify_review_freeze,
)


def _artifacts(values: list[str]) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for value in values:
        if "=" not in value:
            raise SystemExit("artifact must use ROLE=PATH")
        role, path = value.split("=", 1)
        if not role.strip() or not path.strip():
            raise SystemExit("artifact must use non-empty ROLE=PATH")
        parsed.append((role.strip(), path.strip()))
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.25 independent-host evidence, incident-response and review-freeze tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    incident = sub.add_parser("incident-v25-record")
    incident.add_argument("--incident-id", required=True)
    incident.add_argument("--severity", required=True, choices=["low", "medium", "high", "critical"])
    incident.add_argument("--started-at-ms", required=True, type=int)
    incident.add_argument("--acknowledged-at-ms", required=True, type=int)
    incident.add_argument("--resolved-at-ms", required=True, type=int)
    incident.add_argument("--alert-source", required=True)
    incident.add_argument("--component", action="append", required=True)
    incident.add_argument("--escalation-target", default="")
    incident.add_argument("--summary", default="")
    incident.add_argument("--recovery-verified", action="store_true")
    incident.add_argument("--evidence", action="append", default=[], help="ROLE=PATH")
    incident.add_argument("--output", required=True)
    incident.add_argument("--overwrite", action="store_true")

    host = sub.add_parser("host-attestation-v25-build")
    host.add_argument("--key", required=True, help="dedicated operator evidence-signing key; do not use a validator private key")
    host.add_argument("--operator-id", required=True)
    host.add_argument("--validator-id", required=True)
    host.add_argument("--provider", required=True)
    host.add_argument("--region", required=True)
    host.add_argument("--node-id", required=True)
    host.add_argument("--source-commit", required=True)
    host.add_argument("--package-version", default="0.25.0a1")
    host.add_argument("--cometbft-version", default="v0.40.0")
    host.add_argument("--application-genesis-sha256", required=True)
    host.add_argument("--consensus-genesis-sha256", required=True)
    host.add_argument("--independent-management-asserted", action="store_true")
    host.add_argument("--protected-signer-drilled", action="store_true")
    host.add_argument("--soak-7d-completed", action="store_true")
    host.add_argument("--backup-restore-drilled", action="store_true")
    host.add_argument("--clean-host-state-sync-drilled", action="store_true")
    host.add_argument("--governance-campaign-completed", action="store_true")
    host.add_argument("--fault-kind", action="append", default=[])
    host.add_argument("--evidence", action="append", default=[], help="ROLE=PATH")
    host.add_argument("--output", required=True)
    host.add_argument("--overwrite", action="store_true")

    host_verify = sub.add_parser("host-attestation-v25-verify")
    host_verify.add_argument("--attestation", required=True)
    host_verify.add_argument("--artifact-dir", default=None)
    host_verify.add_argument("--expected-signer", default=None)

    gate = sub.add_parser("review-gate-v25-build")
    gate.add_argument("--operational-readiness", required=True)
    gate.add_argument("--host-attestation", action="append", required=True)
    gate.add_argument("--incident", action="append", required=True)
    gate.add_argument("--minimum-hosts", type=int, default=4)
    gate.add_argument("--output", required=True)
    gate.add_argument("--overwrite", action="store_true")

    freeze = sub.add_parser("review-freeze-v25-build")
    freeze.add_argument("--key", required=True, help="dedicated release/review evidence key")
    freeze.add_argument("--source-commit", required=True)
    freeze.add_argument("--package-version", default="0.25.0a1")
    freeze.add_argument("--cometbft-version", default="v0.40.0")
    freeze.add_argument("--application-genesis", required=True)
    freeze.add_argument("--consensus-genesis", required=True)
    freeze.add_argument("--review-gate", required=True)
    freeze.add_argument("--artifact", action="append", required=True, help="ROLE=PATH")
    freeze.add_argument("--review-scope", action="append", required=True)
    freeze.add_argument("--output", required=True)
    freeze.add_argument("--overwrite", action="store_true")

    freeze_verify = sub.add_parser("review-freeze-v25-verify")
    freeze_verify.add_argument("--freeze", required=True)
    freeze_verify.add_argument("--review-gate", required=True)
    freeze_verify.add_argument("--application-genesis", required=True)
    freeze_verify.add_argument("--consensus-genesis", required=True)
    freeze_verify.add_argument("--artifact-dir", default=None)
    freeze_verify.add_argument("--expected-signer", default=None)
    freeze_verify.add_argument("--expected-source-commit", default=None)
    return parser


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "incident-v25-record":
        result = build_incident_record(
            incident_id=args.incident_id,
            severity=args.severity,
            started_at_ms=args.started_at_ms,
            acknowledged_at_ms=args.acknowledged_at_ms,
            resolved_at_ms=args.resolved_at_ms,
            alert_source=args.alert_source,
            affected_components=list(args.component),
            escalation_target=args.escalation_target,
            summary=args.summary,
            recovery_verified=bool(args.recovery_verified),
            evidence=_artifacts(list(args.evidence)),
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, **result}, indent=2))
        return 0 if result["closed"] else 2

    if args.command == "host-attestation-v25-build":
        result = build_host_attestation(
            signing_key_path=args.key,
            operator_id=args.operator_id,
            validator_id=args.validator_id,
            provider=args.provider,
            region=args.region,
            node_id=args.node_id,
            source_commit=args.source_commit,
            package_version=args.package_version,
            cometbft_version=args.cometbft_version,
            application_genesis_sha256=args.application_genesis_sha256,
            consensus_genesis_sha256=args.consensus_genesis_sha256,
            independent_management_asserted=bool(args.independent_management_asserted),
            protected_signer_drilled=bool(args.protected_signer_drilled),
            soak_7d_completed=bool(args.soak_7d_completed),
            backup_restore_drilled=bool(args.backup_restore_drilled),
            clean_host_state_sync_drilled=bool(args.clean_host_state_sync_drilled),
            governance_campaign_completed=bool(args.governance_campaign_completed),
            fault_kinds=list(args.fault_kind),
            evidence=_artifacts(list(args.evidence)),
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        manifest = result["manifest"]
        print(json.dumps({
            "saved": args.output,
            "signer": result["signer"],
            "manifest_sha256": result["manifest_sha256"],
            "host_gate_satisfied": manifest["host_gate_satisfied"],
            "operator_self_attested": True,
            "production_mainnet_ready": False,
        }, indent=2))
        return 0 if manifest["host_gate_satisfied"] else 2

    if args.command == "host-attestation-v25-verify":
        result = verify_host_attestation(
            load_json(args.attestation),
            artifact_directory=args.artifact_dir,
            expected_signer=args.expected_signer,
        )
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "review-gate-v25-build":
        result = build_review_gate(
            operational_readiness=load_json(args.operational_readiness),
            host_attestations=[load_json(path) for path in args.host_attestation],
            incident_records=[load_json(path) for path in args.incident],
            minimum_hosts=args.minimum_hosts,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, **result}, indent=2))
        return 0 if result["candidate_freeze_allowed"] else 2

    if args.command == "review-freeze-v25-build":
        result = build_review_freeze(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            package_version=args.package_version,
            cometbft_version=args.cometbft_version,
            application_genesis_path=args.application_genesis,
            consensus_genesis_path=args.consensus_genesis,
            review_gate=load_json(args.review_gate),
            artifacts=_artifacts(list(args.artifact)),
            reviewer_scope=list(args.review_scope),
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({
            "saved": args.output,
            "signer": result["signer"],
            "manifest_sha256": result["manifest_sha256"],
            "candidate_frozen_for_independent_review": True,
            "independent_security_review_completed": False,
            "production_mainnet_ready": False,
        }, indent=2))
        return 0

    result = verify_review_freeze(
        load_json(args.freeze),
        review_gate=load_json(args.review_gate),
        application_genesis_path=args.application_genesis,
        consensus_genesis_path=args.consensus_genesis,
        artifact_directory=args.artifact_dir,
        expected_signer=args.expected_signer,
        expected_source_commit=args.expected_source_commit,
    )
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    commands = {
        "incident-v25-record",
        "host-attestation-v25-build",
        "host-attestation-v25-verify",
        "review-gate-v25-build",
        "review-freeze-v25-build",
        "review-freeze-v25-verify",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        return _run(sys.argv[1:])
    return int(cli_v24.main())


if __name__ == "__main__":
    raise SystemExit(main())
