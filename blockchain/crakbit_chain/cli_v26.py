from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import cli_v25
from .review_remediation_v26 import (
    build_edge_attestation,
    build_findings_register,
    build_refreeze,
    build_remediation_gate,
    build_retest_record,
    build_supply_chain_attestation,
    load_json,
    save_json,
    verify_edge_attestation,
    verify_findings_register,
    verify_refreeze,
    verify_retest_record,
    verify_supply_chain_attestation,
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


def _load_findings(path: str) -> list[dict]:
    body = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(body, list):
        return body
    if isinstance(body, dict) and isinstance(body.get("findings"), list):
        return body["findings"]
    raise SystemExit("findings input must be a JSON array or an object with a findings array")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.26 independent-review findings, remediation, retest, supply-chain and re-freeze tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    findings = sub.add_parser("review-findings-v26-build")
    findings.add_argument("--key", required=True)
    findings.add_argument("--review-id", required=True)
    findings.add_argument("--reviewer", required=True)
    findings.add_argument("--source-commit", required=True)
    findings.add_argument("--input", required=True)
    findings.add_argument("--output", required=True)
    findings.add_argument("--overwrite", action="store_true")

    findings_verify = sub.add_parser("review-findings-v26-verify")
    findings_verify.add_argument("--register", required=True)
    findings_verify.add_argument("--expected-signer", default=None)

    retest = sub.add_parser("review-retest-v26-build")
    retest.add_argument("--key", required=True)
    retest.add_argument("--reviewer", required=True)
    retest.add_argument("--finding-id", required=True)
    retest.add_argument("--tested-commit", required=True)
    retest.add_argument("--result", required=True, choices=["passed", "failed"])
    retest.add_argument("--notes", default="")
    retest.add_argument("--evidence", action="append", default=[], help="ROLE=PATH")
    retest.add_argument("--output", required=True)
    retest.add_argument("--overwrite", action="store_true")

    retest_verify = sub.add_parser("review-retest-v26-verify")
    retest_verify.add_argument("--record", required=True)
    retest_verify.add_argument("--expected-signer", default=None)

    supply = sub.add_parser("supply-attestation-v26-build")
    supply.add_argument("--key", required=True)
    supply.add_argument("--attestor", required=True)
    supply.add_argument("--source-commit", required=True)
    supply.add_argument("--package-version", default="0.26.0a1")
    supply.add_argument("--dependency-lock-sha256", required=True)
    supply.add_argument("--sbom-sha256", required=True)
    supply.add_argument("--python-reproducible", action="store_true")
    supply.add_argument("--go-reproducible", action="store_true")
    supply.add_argument("--dependency-review-complete", action="store_true")
    supply.add_argument("--transitive-sbom-complete", action="store_true")
    supply.add_argument("--evidence", action="append", default=[], help="ROLE=PATH")
    supply.add_argument("--output", required=True)
    supply.add_argument("--overwrite", action="store_true")

    supply_verify = sub.add_parser("supply-attestation-v26-verify")
    supply_verify.add_argument("--attestation", required=True)
    supply_verify.add_argument("--expected-signer", default=None)

    edge = sub.add_parser("edge-attestation-v26-build")
    edge.add_argument("--key", required=True)
    edge.add_argument("--operator", required=True)
    edge.add_argument("--edge-id", required=True)
    edge.add_argument("--source-commit", required=True)
    edge.add_argument("--tls-min-version", required=True)
    edge.add_argument("--tls-automation", action="store_true")
    edge.add_argument("--waf-enabled", action="store_true")
    edge.add_argument("--ddos-protection-enabled", action="store_true")
    edge.add_argument("--load-test-passed", action="store_true")
    edge.add_argument("--failover-drilled", action="store_true")
    edge.add_argument("--capacity-rps", required=True, type=int)
    edge.add_argument("--sustained-minutes", required=True, type=int)
    edge.add_argument("--evidence", action="append", default=[], help="ROLE=PATH")
    edge.add_argument("--output", required=True)
    edge.add_argument("--overwrite", action="store_true")

    edge_verify = sub.add_parser("edge-attestation-v26-verify")
    edge_verify.add_argument("--attestation", required=True)
    edge_verify.add_argument("--expected-signer", default=None)

    gate = sub.add_parser("remediation-gate-v26-build")
    gate.add_argument("--findings", required=True)
    gate.add_argument("--retest", action="append", default=[])
    gate.add_argument("--supply-attestation", required=True)
    gate.add_argument("--edge-attestation", action="append", required=True)
    gate.add_argument("--candidate-source-commit", required=True)
    gate.add_argument("--package-version", default="0.26.0a1")
    gate.add_argument("--cometbft-version", default="v0.40.0")
    gate.add_argument("--application-genesis-sha256", required=True)
    gate.add_argument("--consensus-genesis-sha256", required=True)
    gate.add_argument("--previous-freeze", default=None)
    gate.add_argument("--output", required=True)
    gate.add_argument("--overwrite", action="store_true")

    freeze = sub.add_parser("review-refreeze-v26-build")
    freeze.add_argument("--key", required=True)
    freeze.add_argument("--remediation-gate", required=True)
    freeze.add_argument("--artifact", action="append", required=True, help="ROLE=PATH")
    freeze.add_argument("--review-scope", action="append", required=True)
    freeze.add_argument("--output", required=True)
    freeze.add_argument("--overwrite", action="store_true")

    freeze_verify = sub.add_parser("review-refreeze-v26-verify")
    freeze_verify.add_argument("--freeze", required=True)
    freeze_verify.add_argument("--remediation-gate", required=True)
    freeze_verify.add_argument("--artifact-dir", default=None)
    freeze_verify.add_argument("--expected-signer", default=None)
    return parser


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "review-findings-v26-build":
        result = build_findings_register(
            signing_key_path=args.key,
            review_id=args.review_id,
            reviewer=args.reviewer,
            source_commit=args.source_commit,
            findings=_load_findings(args.input),
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "signer": result["signer"], **result["manifest"]["summary"], "release_blocked": result["manifest"]["release_blocked"], "production_mainnet_ready": False}, indent=2))
        return 2 if result["manifest"]["release_blocked"] else 0

    if args.command == "review-findings-v26-verify":
        print(json.dumps(verify_findings_register(load_json(args.register), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "review-retest-v26-build":
        result = build_retest_record(
            signing_key_path=args.key,
            reviewer=args.reviewer,
            finding_id=args.finding_id,
            tested_commit=args.tested_commit,
            result=args.result,
            notes=args.notes,
            evidence=_artifacts(list(args.evidence)),
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "signer": result["signer"], "finding_id": result["manifest"]["finding_id"], "result": result["manifest"]["result"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["result"] == "passed" else 2

    if args.command == "review-retest-v26-verify":
        print(json.dumps(verify_retest_record(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "supply-attestation-v26-build":
        result = build_supply_chain_attestation(
            signing_key_path=args.key,
            attestor=args.attestor,
            source_commit=args.source_commit,
            package_version=args.package_version,
            dependency_lock_sha256=args.dependency_lock_sha256,
            sbom_sha256=args.sbom_sha256,
            python_reproducible=bool(args.python_reproducible),
            go_reproducible=bool(args.go_reproducible),
            dependency_review_complete=bool(args.dependency_review_complete),
            transitive_sbom_complete=bool(args.transitive_sbom_complete),
            evidence=_artifacts(list(args.evidence)),
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "signer": result["signer"], "supply_chain_gate_satisfied": result["manifest"]["supply_chain_gate_satisfied"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["supply_chain_gate_satisfied"] else 2

    if args.command == "supply-attestation-v26-verify":
        print(json.dumps(verify_supply_chain_attestation(load_json(args.attestation), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "edge-attestation-v26-build":
        result = build_edge_attestation(
            signing_key_path=args.key,
            operator=args.operator,
            edge_id=args.edge_id,
            source_commit=args.source_commit,
            tls_min_version=args.tls_min_version,
            tls_automation=bool(args.tls_automation),
            waf_enabled=bool(args.waf_enabled),
            ddos_protection_enabled=bool(args.ddos_protection_enabled),
            load_test_passed=bool(args.load_test_passed),
            failover_drilled=bool(args.failover_drilled),
            capacity_rps=args.capacity_rps,
            sustained_minutes=args.sustained_minutes,
            evidence=_artifacts(list(args.evidence)),
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "signer": result["signer"], "edge_gate_satisfied": result["manifest"]["edge_gate_satisfied"], "contains_provider_secrets": False, "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["edge_gate_satisfied"] else 2

    if args.command == "edge-attestation-v26-verify":
        print(json.dumps(verify_edge_attestation(load_json(args.attestation), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "remediation-gate-v26-build":
        result = build_remediation_gate(
            findings_register=load_json(args.findings),
            retest_records=[load_json(path) for path in args.retest],
            supply_chain_attestation=load_json(args.supply_attestation),
            edge_attestations=[load_json(path) for path in args.edge_attestation],
            candidate_source_commit=args.candidate_source_commit,
            package_version=args.package_version,
            cometbft_version=args.cometbft_version,
            application_genesis_sha256=args.application_genesis_sha256,
            consensus_genesis_sha256=args.consensus_genesis_sha256,
            previous_freeze=load_json(args.previous_freeze) if args.previous_freeze else None,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "refreeze_allowed": result["refreeze_allowed"], "unresolved_high_critical_ids": result["unresolved_high_critical_ids"], "previous_candidate_superseded": result["previous_candidate_superseded"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["refreeze_allowed"] else 2

    if args.command == "review-refreeze-v26-build":
        result = build_refreeze(
            signing_key_path=args.key,
            remediation_gate=load_json(args.remediation_gate),
            artifacts=_artifacts(list(args.artifact)),
            reviewer_scope=list(args.review_scope),
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "signer": result["signer"], "manifest_sha256": result["manifest_sha256"], "independent_security_review_completed": False, "production_mainnet_ready": False}, indent=2))
        return 0

    result = verify_refreeze(
        load_json(args.freeze),
        remediation_gate=load_json(args.remediation_gate),
        artifact_directory=args.artifact_dir,
        expected_signer=args.expected_signer,
    )
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    commands = {
        "review-findings-v26-build",
        "review-findings-v26-verify",
        "review-retest-v26-build",
        "review-retest-v26-verify",
        "supply-attestation-v26-build",
        "supply-attestation-v26-verify",
        "edge-attestation-v26-build",
        "edge-attestation-v26-verify",
        "remediation-gate-v26-build",
        "review-refreeze-v26-build",
        "review-refreeze-v26-verify",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        return _run(sys.argv[1:])
    return int(cli_v25.main())


if __name__ == "__main__":
    raise SystemExit(main())
