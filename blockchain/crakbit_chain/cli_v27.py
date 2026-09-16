from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import cli_v26_entry
from .mainnet_candidate_v27 import (
    build_candidate_identity,
    build_economics_freeze,
    build_external_review,
    build_final_candidate_gate,
    build_final_report,
    build_governance_policy,
    build_release_approval,
    build_upgrade_plan,
    load_json,
    save_json,
    verify_economics_freeze,
    verify_external_review,
    verify_final_report,
    verify_governance_policy,
    verify_release_approval,
    verify_upgrade_plan,
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
        description="Crakbit v0.27 final mainnet-candidate policy, upgrade, economics and multi-party release evidence tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    upgrade = sub.add_parser("upgrade-plan-v27-build")
    upgrade.add_argument("--key", required=True)
    upgrade.add_argument("--source-commit", required=True)
    upgrade.add_argument("--from-package", required=True)
    upgrade.add_argument("--to-package", required=True)
    upgrade.add_argument("--from-schema", type=int, required=True)
    upgrade.add_argument("--to-schema", type=int, required=True)
    upgrade.add_argument("--activation-height", type=int, required=True)
    upgrade.add_argument("--rollback-deadline-height", type=int, required=True)
    upgrade.add_argument("--migration-artifact-sha256", required=True)
    upgrade.add_argument("--rollback-artifact-sha256", required=True)
    upgrade.add_argument("--minimum-ready-validators", type=int, required=True)
    upgrade.add_argument("--total-validators", type=int, required=True)
    upgrade.add_argument("--output", required=True)
    upgrade.add_argument("--overwrite", action="store_true")

    upgrade_verify = sub.add_parser("upgrade-plan-v27-verify")
    upgrade_verify.add_argument("--plan", required=True)
    upgrade_verify.add_argument("--expected-signer", default=None)

    gov = sub.add_parser("governance-policy-v27-build")
    gov.add_argument("--key", required=True)
    gov.add_argument("--source-commit", required=True)
    gov.add_argument("--normal-timelock-blocks", type=int, required=True)
    gov.add_argument("--emergency-timelock-blocks", type=int, required=True)
    gov.add_argument("--cancel-until-blocks-before-activation", type=int, required=True)
    gov.add_argument("--emergency-approval-numerator", type=int, required=True)
    gov.add_argument("--emergency-approval-denominator", type=int, required=True)
    gov.add_argument("--output", required=True)
    gov.add_argument("--overwrite", action="store_true")

    gov_verify = sub.add_parser("governance-policy-v27-verify")
    gov_verify.add_argument("--policy", required=True)
    gov_verify.add_argument("--expected-signer", default=None)

    economics = sub.add_parser("economics-freeze-v27-build")
    economics.add_argument("--key", required=True)
    economics.add_argument("--source-commit", required=True)
    economics.add_argument("--application-genesis-sha256", required=True)
    economics.add_argument("--consensus-genesis-sha256", required=True)
    economics.add_argument("--parameters", required=True, help="JSON object containing final candidate economics parameters")
    economics.add_argument("--output", required=True)
    economics.add_argument("--overwrite", action="store_true")

    economics_verify = sub.add_parser("economics-freeze-v27-verify")
    economics_verify.add_argument("--freeze", required=True)
    economics_verify.add_argument("--expected-signer", default=None)

    review = sub.add_parser("external-review-v27-build")
    review.add_argument("--key", required=True)
    review.add_argument("--kind", required=True, choices=["economic-security", "legal-regulatory"])
    review.add_argument("--reviewer", required=True)
    review.add_argument("--source-commit", required=True)
    review.add_argument("--subject-sha256", required=True)
    review.add_argument("--decision", required=True, choices=["passed", "failed"])
    review.add_argument("--scope", action="append", required=True)
    review.add_argument("--condition", action="append", default=[])
    review.add_argument("--output", required=True)
    review.add_argument("--overwrite", action="store_true")

    review_verify = sub.add_parser("external-review-v27-verify")
    review_verify.add_argument("--review", required=True)
    review_verify.add_argument("--expected-signer", default=None)

    identity = sub.add_parser("candidate-identity-v27-build")
    identity.add_argument("--operational-readiness", required=True)
    identity.add_argument("--remediation-gate", required=True)
    identity.add_argument("--governance-policy", required=True)
    identity.add_argument("--economics-freeze", required=True)
    identity.add_argument("--upgrade-plan", required=True)
    identity.add_argument("--economic-review", required=True)
    identity.add_argument("--legal-review", required=True)
    identity.add_argument("--output", required=True)
    identity.add_argument("--overwrite", action="store_true")

    approval = sub.add_parser("release-approval-v27-build")
    approval.add_argument("--key", required=True)
    approval.add_argument("--approver-id", required=True)
    approval.add_argument("--role", required=True)
    approval.add_argument("--source-commit", required=True)
    approval.add_argument("--candidate-identity-sha256", required=True)
    approval.add_argument("--decision", required=True, choices=["approve", "reject"])
    approval.add_argument("--note", default="")
    approval.add_argument("--output", required=True)
    approval.add_argument("--overwrite", action="store_true")

    approval_verify = sub.add_parser("release-approval-v27-verify")
    approval_verify.add_argument("--approval", required=True)
    approval_verify.add_argument("--expected-signer", default=None)

    gate = sub.add_parser("final-gate-v27-build")
    gate.add_argument("--identity", required=True)
    gate.add_argument("--operational-readiness", required=True)
    gate.add_argument("--remediation-gate", required=True)
    gate.add_argument("--governance-policy", required=True)
    gate.add_argument("--economics-freeze", required=True)
    gate.add_argument("--upgrade-plan", required=True)
    gate.add_argument("--economic-review", required=True)
    gate.add_argument("--legal-review", required=True)
    gate.add_argument("--release-approval", action="append", required=True)
    gate.add_argument("--minimum-approvals", type=int, default=3)
    gate.add_argument("--output", required=True)
    gate.add_argument("--overwrite", action="store_true")

    report = sub.add_parser("final-report-v27-build")
    report.add_argument("--key", required=True)
    report.add_argument("--final-gate", required=True)
    report.add_argument("--artifact", action="append", default=[], help="ROLE=PATH")
    report.add_argument("--output", required=True)
    report.add_argument("--overwrite", action="store_true")

    report_verify = sub.add_parser("final-report-v27-verify")
    report_verify.add_argument("--report", required=True)
    report_verify.add_argument("--expected-signer", default=None)
    return parser


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "upgrade-plan-v27-build":
        result = build_upgrade_plan(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            from_package=args.from_package,
            to_package=args.to_package,
            from_schema=args.from_schema,
            to_schema=args.to_schema,
            activation_height=args.activation_height,
            rollback_deadline_height=args.rollback_deadline_height,
            migration_artifact_sha256=args.migration_artifact_sha256,
            rollback_artifact_sha256=args.rollback_artifact_sha256,
            minimum_ready_validators=args.minimum_ready_validators,
            total_validators=args.total_validators,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "signer": result["signer"], "manifest_sha256": result["manifest_sha256"], "plan_only": True, "production_mainnet_ready": False}, indent=2))
        return 0

    if args.command == "upgrade-plan-v27-verify":
        print(json.dumps(verify_upgrade_plan(load_json(args.plan), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "governance-policy-v27-build":
        result = build_governance_policy(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            normal_timelock_blocks=args.normal_timelock_blocks,
            emergency_timelock_blocks=args.emergency_timelock_blocks,
            cancel_until_blocks_before_activation=args.cancel_until_blocks_before_activation,
            emergency_approval_numerator=args.emergency_approval_numerator,
            emergency_approval_denominator=args.emergency_approval_denominator,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "signer": result["signer"], "policy_gate_satisfied": result["manifest"]["policy_gate_satisfied"], "production_mainnet_ready": False}, indent=2))
        return 0

    if args.command == "governance-policy-v27-verify":
        print(json.dumps(verify_governance_policy(load_json(args.policy), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "economics-freeze-v27-build":
        parameters = load_json(args.parameters)
        result = build_economics_freeze(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            application_genesis_sha256=args.application_genesis_sha256,
            consensus_genesis_sha256=args.consensus_genesis_sha256,
            parameters=parameters,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "signer": result["signer"], "parameters_sha256": result["manifest"]["parameters_sha256"], "token_sale_authorized": False, "production_mainnet_ready": False}, indent=2))
        return 0

    if args.command == "economics-freeze-v27-verify":
        print(json.dumps(verify_economics_freeze(load_json(args.freeze), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "external-review-v27-build":
        result = build_external_review(
            signing_key_path=args.key,
            review_kind=args.kind,
            reviewer=args.reviewer,
            source_commit=args.source_commit,
            subject_sha256=args.subject_sha256,
            decision=args.decision,
            scope=list(args.scope),
            conditions=list(args.condition),
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "signer": result["signer"], "review_kind": result["manifest"]["review_kind"], "decision": result["manifest"]["decision"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["decision"] == "passed" else 2

    if args.command == "external-review-v27-verify":
        print(json.dumps(verify_external_review(load_json(args.review), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "candidate-identity-v27-build":
        result = build_candidate_identity(
            operational_readiness=load_json(args.operational_readiness),
            remediation_gate=load_json(args.remediation_gate),
            governance_policy=load_json(args.governance_policy),
            economics_freeze=load_json(args.economics_freeze),
            upgrade_plan=load_json(args.upgrade_plan),
            economic_review=load_json(args.economic_review),
            legal_review=load_json(args.legal_review),
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "candidate_identity_sha256": result["candidate_identity_sha256"], "production_mainnet_ready": False}, indent=2))
        return 0

    if args.command == "release-approval-v27-build":
        result = build_release_approval(
            signing_key_path=args.key,
            approver_id=args.approver_id,
            role=args.role,
            source_commit=args.source_commit,
            candidate_identity_sha256=args.candidate_identity_sha256,
            decision=args.decision,
            note=args.note,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "signer": result["signer"], "approver_id": result["manifest"]["approver_id"], "decision": result["manifest"]["decision"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["decision"] == "approve" else 2

    if args.command == "release-approval-v27-verify":
        print(json.dumps(verify_release_approval(load_json(args.approval), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "final-gate-v27-build":
        result = build_final_candidate_gate(
            identity=load_json(args.identity),
            operational_readiness=load_json(args.operational_readiness),
            remediation_gate=load_json(args.remediation_gate),
            governance_policy=load_json(args.governance_policy),
            economics_freeze=load_json(args.economics_freeze),
            upgrade_plan=load_json(args.upgrade_plan),
            economic_review=load_json(args.economic_review),
            legal_review=load_json(args.legal_review),
            release_approvals=[load_json(path) for path in args.release_approval],
            minimum_approvals=args.minimum_approvals,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "candidate_identity_sha256": result["candidate_identity_sha256"], "mainnet_candidate_gate_satisfied": result["mainnet_candidate_gate_satisfied"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["mainnet_candidate_gate_satisfied"] else 2

    if args.command == "final-report-v27-build":
        result = build_final_report(
            signing_key_path=args.key,
            final_gate=load_json(args.final_gate),
            artifacts=_artifacts(list(args.artifact)),
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "signer": result["signer"], "candidate_identity_sha256": result["manifest"]["candidate_identity_sha256"], "mainnet_candidate_gate_satisfied": True, "production_mainnet_ready": False}, indent=2))
        return 0

    result = verify_final_report(load_json(args.report), expected_signer=args.expected_signer)
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    commands = {
        "upgrade-plan-v27-build", "upgrade-plan-v27-verify",
        "governance-policy-v27-build", "governance-policy-v27-verify",
        "economics-freeze-v27-build", "economics-freeze-v27-verify",
        "external-review-v27-build", "external-review-v27-verify",
        "candidate-identity-v27-build",
        "release-approval-v27-build", "release-approval-v27-verify",
        "final-gate-v27-build", "final-report-v27-build", "final-report-v27-verify",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        return _run(sys.argv[1:])
    return int(cli_v26_entry.main())


if __name__ == "__main__":
    raise SystemExit(main())
