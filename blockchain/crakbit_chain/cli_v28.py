from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import cli_v27_entry
from .launch_rehearsal_v28 import (
    build_cutover_rehearsal,
    build_edge_slo_evidence,
    build_launch_decision,
    build_launch_runbook,
    build_rehearsal_gate,
    build_release_freeze,
    build_repro_attestation,
    build_review_signoff,
    build_risk_register,
    build_signer_drill,
    build_upgrade_rehearsal,
    load_json,
    save_json,
    verify_cutover_rehearsal,
    verify_edge_slo_evidence,
    verify_launch_decision,
    verify_launch_runbook,
    verify_release_freeze,
    verify_repro_attestation,
    verify_review_signoff,
    verify_risk_register,
    verify_signer_drill,
    verify_upgrade_rehearsal,
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


def _load_risks(path: str) -> list[dict]:
    body = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(body, list):
        return body
    if isinstance(body, dict) and isinstance(body.get("risks"), list):
        return body["risks"]
    raise SystemExit("risk input must be a JSON array or an object with a risks array")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.28 launch rehearsal, independently corroborated evidence and manual release-freeze tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    runbook = sub.add_parser("launch-runbook-v28-build")
    runbook.add_argument("--key", required=True)
    runbook.add_argument("--source-commit", required=True)
    runbook.add_argument("--candidate-identity-sha256", required=True)
    runbook.add_argument("--validator-id", action="append", required=True)
    runbook.add_argument("--genesis-step", action="append", required=True)
    runbook.add_argument("--validator-start", action="append", required=True)
    runbook.add_argument("--rollback-step", action="append", required=True)
    runbook.add_argument("--cutover-window-minutes", type=int, default=60)
    runbook.add_argument("--output", required=True)
    runbook.add_argument("--overwrite", action="store_true")

    runbook_verify = sub.add_parser("launch-runbook-v28-verify")
    runbook_verify.add_argument("--runbook", required=True)
    runbook_verify.add_argument("--expected-signer", default=None)

    cutover = sub.add_parser("cutover-rehearsal-v28-build")
    cutover.add_argument("--key", required=True)
    cutover.add_argument("--source-commit", required=True)
    cutover.add_argument("--candidate-identity-sha256", required=True)
    cutover.add_argument("--dns-name", action="append", required=True)
    cutover.add_argument("--rpc-endpoint", action="append", required=True)
    cutover.add_argument("--explorer-endpoint", action="append", required=True)
    cutover.add_argument("--dns-ttl-seconds", type=int, default=300)
    cutover.add_argument("--rollback-verified", action="store_true")
    cutover.add_argument("--rpc-failover-verified", action="store_true")
    cutover.add_argument("--explorer-failover-verified", action="store_true")
    cutover.add_argument("--no-production-dns-changed", action="store_true")
    cutover.add_argument("--output", required=True)
    cutover.add_argument("--overwrite", action="store_true")

    cutover_verify = sub.add_parser("cutover-rehearsal-v28-verify")
    cutover_verify.add_argument("--record", required=True)
    cutover_verify.add_argument("--expected-signer", default=None)

    edge = sub.add_parser("edge-slo-v28-build")
    edge.add_argument("--key", required=True)
    edge.add_argument("--source-commit", required=True)
    edge.add_argument("--candidate-identity-sha256", required=True)
    edge.add_argument("--edge-id", required=True)
    edge.add_argument("--availability-percent", type=float, required=True)
    edge.add_argument("--p95-latency-ms", type=float, required=True)
    edge.add_argument("--error-rate-percent", type=float, required=True)
    edge.add_argument("--capacity-rps", type=int, required=True)
    edge.add_argument("--sustained-minutes", type=int, required=True)
    edge.add_argument("--failover-seconds", type=float, required=True)
    edge.add_argument("--min-availability-percent", type=float, required=True)
    edge.add_argument("--max-p95-latency-ms", type=float, required=True)
    edge.add_argument("--max-error-rate-percent", type=float, required=True)
    edge.add_argument("--min-capacity-rps", type=int, required=True)
    edge.add_argument("--max-failover-seconds", type=float, required=True)
    edge.add_argument("--output", required=True)
    edge.add_argument("--overwrite", action="store_true")

    edge_verify = sub.add_parser("edge-slo-v28-verify")
    edge_verify.add_argument("--record", required=True)
    edge_verify.add_argument("--expected-signer", default=None)

    signer = sub.add_parser("signer-drill-v28-build")
    signer.add_argument("--key", required=True)
    signer.add_argument("--source-commit", required=True)
    signer.add_argument("--candidate-identity-sha256", required=True)
    signer.add_argument("--signer-id", required=True)
    signer.add_argument("--custody-type", required=True, choices=["hsm", "remote-signer", "hardware-backed", "equivalent-protected"])
    signer.add_argument("--no-key-export", action="store_true")
    signer.add_argument("--rotation-successful", action="store_true")
    signer.add_argument("--old-key-revoked", action="store_true")
    signer.add_argument("--backup-recovery-successful", action="store_true")
    signer.add_argument("--catastrophic-recovery-drilled", action="store_true")
    signer.add_argument("--validator-quorum-preserved", action="store_true")
    signer.add_argument("--output", required=True)
    signer.add_argument("--overwrite", action="store_true")

    signer_verify = sub.add_parser("signer-drill-v28-verify")
    signer_verify.add_argument("--record", required=True)
    signer_verify.add_argument("--expected-signer", default=None)

    upgrade = sub.add_parser("upgrade-rehearsal-v28-build")
    upgrade.add_argument("--key", required=True)
    upgrade.add_argument("--source-commit", required=True)
    upgrade.add_argument("--candidate-identity-sha256", required=True)
    upgrade.add_argument("--upgrade-plan", required=True)
    upgrade.add_argument("--validator-count", type=int, required=True)
    upgrade.add_argument("--validators-successful", type=int, required=True)
    upgrade.add_argument("--upgrade-completed", action="store_true")
    upgrade.add_argument("--application-hash-converged", action="store_true")
    upgrade.add_argument("--rollback-exercised", action="store_true")
    upgrade.add_argument("--rollback-hash-converged", action="store_true")
    upgrade.add_argument("--no-data-loss", action="store_true")
    upgrade.add_argument("--output", required=True)
    upgrade.add_argument("--overwrite", action="store_true")

    upgrade_verify = sub.add_parser("upgrade-rehearsal-v28-verify")
    upgrade_verify.add_argument("--record", required=True)
    upgrade_verify.add_argument("--expected-signer", default=None)

    risks = sub.add_parser("risk-register-v28-build")
    risks.add_argument("--key", required=True)
    risks.add_argument("--source-commit", required=True)
    risks.add_argument("--candidate-identity-sha256", required=True)
    risks.add_argument("--input", required=True)
    risks.add_argument("--output", required=True)
    risks.add_argument("--overwrite", action="store_true")

    risks_verify = sub.add_parser("risk-register-v28-verify")
    risks_verify.add_argument("--register", required=True)
    risks_verify.add_argument("--expected-signer", default=None)

    review = sub.add_parser("review-signoff-v28-build")
    review.add_argument("--key", required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--scope", required=True)
    review.add_argument("--source-commit", required=True)
    review.add_argument("--candidate-identity-sha256", required=True)
    review.add_argument("--subject-sha256", required=True)
    review.add_argument("--decision", required=True, choices=["passed", "conditional", "failed"])
    review.add_argument("--independent-reviewer-asserted", action="store_true")
    review.add_argument("--condition", action="append", default=[])
    review.add_argument("--output", required=True)
    review.add_argument("--overwrite", action="store_true")

    review_verify = sub.add_parser("review-signoff-v28-verify")
    review_verify.add_argument("--record", required=True)
    review_verify.add_argument("--expected-signer", default=None)

    repro = sub.add_parser("repro-attestation-v28-build")
    repro.add_argument("--key", required=True)
    repro.add_argument("--attestor", required=True)
    repro.add_argument("--source-commit", required=True)
    repro.add_argument("--candidate-identity-sha256", required=True)
    repro.add_argument("--package-version", default="0.28.0a1")
    repro.add_argument("--dependency-lock-sha256", required=True)
    repro.add_argument("--sbom-sha256", required=True)
    repro.add_argument("--python-wheel-sha256", required=True)
    repro.add_argument("--go-binary-sha256", required=True)
    repro.add_argument("--python-reproducible", action="store_true")
    repro.add_argument("--go-reproducible", action="store_true")
    repro.add_argument("--transitive-dependencies-reviewed", action="store_true")
    repro.add_argument("--source-tag-verified", action="store_true")
    repro.add_argument("--output", required=True)
    repro.add_argument("--overwrite", action="store_true")

    repro_verify = sub.add_parser("repro-attestation-v28-verify")
    repro_verify.add_argument("--record", required=True)
    repro_verify.add_argument("--expected-signer", default=None)

    gate = sub.add_parser("rehearsal-gate-v28-build")
    gate.add_argument("--final-report-v27", required=True)
    gate.add_argument("--launch-runbook", required=True)
    gate.add_argument("--cutover-rehearsal", required=True)
    gate.add_argument("--edge-slo", action="append", required=True)
    gate.add_argument("--signer-drill", required=True)
    gate.add_argument("--upgrade-rehearsal", required=True)
    gate.add_argument("--risk-register", required=True)
    gate.add_argument("--review-signoff", action="append", required=True)
    gate.add_argument("--repro-attestation", required=True)
    gate.add_argument("--minimum-edge-slos", type=int, default=2)
    gate.add_argument("--minimum-unique-review-signers", type=int, default=3)
    gate.add_argument("--output", required=True)
    gate.add_argument("--overwrite", action="store_true")

    freeze = sub.add_parser("release-freeze-v28-build")
    freeze.add_argument("--key", required=True)
    freeze.add_argument("--rehearsal-gate", required=True)
    freeze.add_argument("--artifact", action="append", default=[], help="ROLE=PATH")
    freeze.add_argument("--output", required=True)
    freeze.add_argument("--overwrite", action="store_true")

    freeze_verify = sub.add_parser("release-freeze-v28-verify")
    freeze_verify.add_argument("--freeze", required=True)
    freeze_verify.add_argument("--expected-signer", default=None)

    decision = sub.add_parser("launch-decision-v28-record")
    decision.add_argument("--key", required=True)
    decision.add_argument("--release-freeze", required=True)
    decision.add_argument("--decision-maker", required=True)
    decision.add_argument("--decision", required=True, choices=["hold", "approve-launch-window"])
    decision.add_argument("--rationale", required=True)
    decision.add_argument("--output", required=True)
    decision.add_argument("--overwrite", action="store_true")

    decision_verify = sub.add_parser("launch-decision-v28-verify")
    decision_verify.add_argument("--record", required=True)
    decision_verify.add_argument("--expected-signer", default=None)
    return parser


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "launch-runbook-v28-build":
        result = build_launch_runbook(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            candidate_identity_sha256=args.candidate_identity_sha256,
            validator_ids=args.validator_id,
            genesis_ceremony_steps=args.genesis_step,
            validator_start_order=args.validator_start,
            rollback_steps=args.rollback_step,
            cutover_window_minutes=args.cutover_window_minutes,
        )
        save_json(result, args.output, overwrite=args.overwrite)
        print(json.dumps({"saved": args.output, "runbook_gate_satisfied": True, "automatic_launch": False, "production_mainnet_ready": False}, indent=2))
        return 0

    if args.command == "launch-runbook-v28-verify":
        print(json.dumps(verify_launch_runbook(load_json(args.runbook), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "cutover-rehearsal-v28-build":
        result = build_cutover_rehearsal(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            candidate_identity_sha256=args.candidate_identity_sha256,
            dns_names=args.dns_name,
            rpc_endpoints=args.rpc_endpoint,
            explorer_endpoints=args.explorer_endpoint,
            dns_ttl_seconds=args.dns_ttl_seconds,
            rollback_verified=args.rollback_verified,
            rpc_failover_verified=args.rpc_failover_verified,
            explorer_failover_verified=args.explorer_failover_verified,
            no_production_dns_changed=args.no_production_dns_changed,
        )
        save_json(result, args.output, overwrite=args.overwrite)
        gate = result["manifest"]["cutover_gate_satisfied"]
        print(json.dumps({"saved": args.output, "cutover_gate_satisfied": gate, "automatic_dns_change": False, "production_mainnet_ready": False}, indent=2))
        return 0 if gate else 2

    if args.command == "cutover-rehearsal-v28-verify":
        print(json.dumps(verify_cutover_rehearsal(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "edge-slo-v28-build":
        result = build_edge_slo_evidence(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            candidate_identity_sha256=args.candidate_identity_sha256,
            edge_id=args.edge_id,
            availability_percent=args.availability_percent,
            p95_latency_ms=args.p95_latency_ms,
            error_rate_percent=args.error_rate_percent,
            capacity_rps=args.capacity_rps,
            sustained_minutes=args.sustained_minutes,
            failover_seconds=args.failover_seconds,
            min_availability_percent=args.min_availability_percent,
            max_p95_latency_ms=args.max_p95_latency_ms,
            max_error_rate_percent=args.max_error_rate_percent,
            min_capacity_rps=args.min_capacity_rps,
            max_failover_seconds=args.max_failover_seconds,
        )
        save_json(result, args.output, overwrite=args.overwrite)
        gate = result["manifest"]["slo_gate_satisfied"]
        print(json.dumps({"saved": args.output, "edge_id": args.edge_id, "slo_gate_satisfied": gate, "production_mainnet_ready": False}, indent=2))
        return 0 if gate else 2

    if args.command == "edge-slo-v28-verify":
        print(json.dumps(verify_edge_slo_evidence(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "signer-drill-v28-build":
        result = build_signer_drill(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            candidate_identity_sha256=args.candidate_identity_sha256,
            signer_id=args.signer_id,
            custody_type=args.custody_type,
            no_key_export=args.no_key_export,
            rotation_successful=args.rotation_successful,
            old_key_revoked=args.old_key_revoked,
            backup_recovery_successful=args.backup_recovery_successful,
            catastrophic_recovery_drilled=args.catastrophic_recovery_drilled,
            validator_quorum_preserved=args.validator_quorum_preserved,
        )
        save_json(result, args.output, overwrite=args.overwrite)
        gate = result["manifest"]["signer_drill_gate_satisfied"]
        print(json.dumps({"saved": args.output, "signer_drill_gate_satisfied": gate, "contains_private_key": False, "production_mainnet_ready": False}, indent=2))
        return 0 if gate else 2

    if args.command == "signer-drill-v28-verify":
        print(json.dumps(verify_signer_drill(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "upgrade-rehearsal-v28-build":
        result = build_upgrade_rehearsal(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            candidate_identity_sha256=args.candidate_identity_sha256,
            upgrade_plan=load_json(args.upgrade_plan),
            validator_count=args.validator_count,
            validators_successful=args.validators_successful,
            upgrade_completed=args.upgrade_completed,
            application_hash_converged=args.application_hash_converged,
            rollback_exercised=args.rollback_exercised,
            rollback_hash_converged=args.rollback_hash_converged,
            no_data_loss=args.no_data_loss,
        )
        save_json(result, args.output, overwrite=args.overwrite)
        gate = result["manifest"]["upgrade_rehearsal_gate_satisfied"]
        print(json.dumps({"saved": args.output, "upgrade_rehearsal_gate_satisfied": gate, "automatic_upgrade": False, "production_mainnet_ready": False}, indent=2))
        return 0 if gate else 2

    if args.command == "upgrade-rehearsal-v28-verify":
        print(json.dumps(verify_upgrade_rehearsal(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "risk-register-v28-build":
        result = build_risk_register(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            candidate_identity_sha256=args.candidate_identity_sha256,
            risks=_load_risks(args.input),
        )
        save_json(result, args.output, overwrite=args.overwrite)
        gate = result["manifest"]["risk_gate_satisfied"]
        print(json.dumps({"saved": args.output, "risk_gate_satisfied": gate, "blocking_risk_ids": result["manifest"]["blocking_risk_ids"], "production_mainnet_ready": False}, indent=2))
        return 0 if gate else 2

    if args.command == "risk-register-v28-verify":
        print(json.dumps(verify_risk_register(load_json(args.register), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "review-signoff-v28-build":
        result = build_review_signoff(
            signing_key_path=args.key,
            reviewer=args.reviewer,
            scope=args.scope,
            source_commit=args.source_commit,
            candidate_identity_sha256=args.candidate_identity_sha256,
            subject_sha256=args.subject_sha256,
            decision=args.decision,
            independent_reviewer_asserted=args.independent_reviewer_asserted,
            conditions=args.condition,
        )
        save_json(result, args.output, overwrite=args.overwrite)
        gate = result["manifest"]["signoff_gate_satisfied"]
        print(json.dumps({"saved": args.output, "scope": args.scope, "decision": args.decision, "signoff_gate_satisfied": gate, "production_mainnet_ready": False}, indent=2))
        return 0 if gate else 2

    if args.command == "review-signoff-v28-verify":
        print(json.dumps(verify_review_signoff(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "repro-attestation-v28-build":
        result = build_repro_attestation(
            signing_key_path=args.key,
            attestor=args.attestor,
            source_commit=args.source_commit,
            candidate_identity_sha256=args.candidate_identity_sha256,
            package_version=args.package_version,
            dependency_lock_sha256=args.dependency_lock_sha256,
            sbom_sha256=args.sbom_sha256,
            python_wheel_sha256=args.python_wheel_sha256,
            go_binary_sha256=args.go_binary_sha256,
            python_reproducible=args.python_reproducible,
            go_reproducible=args.go_reproducible,
            transitive_dependencies_reviewed=args.transitive_dependencies_reviewed,
            source_tag_verified=args.source_tag_verified,
        )
        save_json(result, args.output, overwrite=args.overwrite)
        gate = result["manifest"]["repro_gate_satisfied"]
        print(json.dumps({"saved": args.output, "repro_gate_satisfied": gate, "production_mainnet_ready": False}, indent=2))
        return 0 if gate else 2

    if args.command == "repro-attestation-v28-verify":
        print(json.dumps(verify_repro_attestation(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "rehearsal-gate-v28-build":
        result = build_rehearsal_gate(
            final_report_v27=load_json(args.final_report_v27),
            launch_runbook=load_json(args.launch_runbook),
            cutover_rehearsal=load_json(args.cutover_rehearsal),
            edge_slo_evidence=[load_json(path) for path in args.edge_slo],
            signer_drill=load_json(args.signer_drill),
            upgrade_rehearsal=load_json(args.upgrade_rehearsal),
            risk_register=load_json(args.risk_register),
            reviewer_signoffs=[load_json(path) for path in args.review_signoff],
            repro_attestation=load_json(args.repro_attestation),
            minimum_edge_slos=args.minimum_edge_slos,
            minimum_unique_review_signers=args.minimum_unique_review_signers,
        )
        save_json(result, args.output, overwrite=args.overwrite)
        gate_ok = result["launch_rehearsal_gate_satisfied"]
        print(json.dumps({"saved": args.output, "launch_rehearsal_gate_satisfied": gate_ok, "manual_launch_decision_required": True, "automatic_launch": False, "production_mainnet_ready": False}, indent=2))
        return 0 if gate_ok else 2

    if args.command == "release-freeze-v28-build":
        result = build_release_freeze(
            signing_key_path=args.key,
            rehearsal_gate=load_json(args.rehearsal_gate),
            artifacts=_artifacts(args.artifact),
        )
        save_json(result, args.output, overwrite=args.overwrite)
        print(json.dumps({"saved": args.output, "signer": result["signer"], "frozen_for_manual_launch_review": True, "automatic_launch": False, "production_mainnet_ready": False}, indent=2))
        return 0

    if args.command == "release-freeze-v28-verify":
        print(json.dumps(verify_release_freeze(load_json(args.freeze), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "launch-decision-v28-record":
        result = build_launch_decision(
            signing_key_path=args.key,
            release_freeze=load_json(args.release_freeze),
            decision_maker=args.decision_maker,
            decision=args.decision,
            rationale=args.rationale,
        )
        save_json(result, args.output, overwrite=args.overwrite)
        print(json.dumps({"saved": args.output, "decision": args.decision, "automatic_execution": False, "production_mainnet_launched": False}, indent=2))
        return 0

    print(json.dumps(verify_launch_decision(load_json(args.record), expected_signer=args.expected_signer), indent=2))
    return 0


def main() -> int:
    commands = {
        "launch-runbook-v28-build", "launch-runbook-v28-verify",
        "cutover-rehearsal-v28-build", "cutover-rehearsal-v28-verify",
        "edge-slo-v28-build", "edge-slo-v28-verify",
        "signer-drill-v28-build", "signer-drill-v28-verify",
        "upgrade-rehearsal-v28-build", "upgrade-rehearsal-v28-verify",
        "risk-register-v28-build", "risk-register-v28-verify",
        "review-signoff-v28-build", "review-signoff-v28-verify",
        "repro-attestation-v28-build", "repro-attestation-v28-verify",
        "rehearsal-gate-v28-build",
        "release-freeze-v28-build", "release-freeze-v28-verify",
        "launch-decision-v28-record", "launch-decision-v28-verify",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        return _run(sys.argv[1:])
    return int(cli_v27_entry.main())


if __name__ == "__main__":
    raise SystemExit(main())
