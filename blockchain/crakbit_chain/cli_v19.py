from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import cli_v18
from .ops_drill_evidence import (
    build_drill_evidence,
    load_drill_evidence,
    save_drill_evidence,
    verify_drill_evidence,
)
from .release_provenance_v19 import (
    build_release_provenance,
    load_release_provenance,
    save_release_provenance,
    verify_release_provenance,
)
from .reproducible_build import compare_build_outputs, save_repro_report
from .review_findings import build_remediation_matrix, save_remediation_matrix, verify_remediation_matrix
from .sbom_v19 import build_sbom, save_sbom


def _role_path(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("value must use ROLE=PATH")
    role, path = value.split("=", 1)
    role = role.strip()
    path = path.strip()
    if not role or not path:
        raise argparse.ArgumentTypeError("value must use ROLE=PATH")
    return role, path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.19 review-remediation and reproducible release-engineering tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sbom = sub.add_parser("sbom-build")
    sbom.add_argument("--repo-root", default="..")
    sbom.add_argument("--output", required=True)
    sbom.add_argument("--overwrite", action="store_true")

    repro = sub.add_parser("repro-compare")
    repro.add_argument("--left", required=True)
    repro.add_argument("--right", required=True)
    repro.add_argument("--file", action="append", required=True)
    repro.add_argument("--output", default=None)
    repro.add_argument("--overwrite", action="store_true")

    matrix = sub.add_parser("review-findings-build")
    matrix.add_argument("--source-commit", required=True)
    matrix.add_argument("--finding", action="append", required=True)
    matrix.add_argument("--output", required=True)
    matrix.add_argument("--overwrite", action="store_true")

    matrix_check = sub.add_parser("review-findings-check")
    matrix_check.add_argument("--matrix", required=True)

    provenance = sub.add_parser("release-provenance-build")
    provenance.add_argument("--genesis", required=True)
    provenance.add_argument("--key", required=True)
    provenance.add_argument("--source-commit", required=True)
    provenance.add_argument("--package-version", default="0.19.0a1")
    provenance.add_argument("--cometbft-version", default="v0.40.0")
    provenance.add_argument("--artifact", action="append", type=_role_path, default=[])
    provenance.add_argument("--sbom", default=None)
    provenance.add_argument("--repro-report", default=None)
    provenance.add_argument("--output", required=True)
    provenance.add_argument("--overwrite", action="store_true")

    provenance_verify = sub.add_parser("release-provenance-verify")
    provenance_verify.add_argument("--genesis", required=True)
    provenance_verify.add_argument("--provenance", required=True)
    provenance_verify.add_argument("--artifact-dir", default=None)
    provenance_verify.add_argument("--expected-signer", default=None)
    provenance_verify.add_argument("--expected-source-commit", default=None)

    drill = sub.add_parser("ops-drill-build")
    drill.add_argument("--key", required=True)
    drill.add_argument("--source-commit", required=True)
    drill.add_argument(
        "--kind",
        required=True,
        choices=["upgrade", "rollback", "incident-response", "disaster-recovery", "validator-lifecycle"],
    )
    drill.add_argument("--started-at-ms", type=int, required=True)
    drill.add_argument("--completed-at-ms", type=int, required=True)
    drill.add_argument("--success", action="store_true")
    drill.add_argument("--summary", required=True)
    drill.add_argument("--evidence", action="append", default=[])
    drill.add_argument("--output", required=True)
    drill.add_argument("--overwrite", action="store_true")

    drill_verify = sub.add_parser("ops-drill-verify")
    drill_verify.add_argument("--drill", required=True)
    drill_verify.add_argument("--evidence-dir", default=None)
    drill_verify.add_argument("--expected-signer", default=None)
    return parser


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "sbom-build":
        sbom = build_sbom(args.repo_root)
        target = save_sbom(sbom, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": str(target), "components": len(sbom.get("components", []))}, indent=2))
        return 0

    if args.command == "repro-compare":
        report = compare_build_outputs(
            left_root=args.left,
            right_root=args.right,
            relative_files=args.file,
        )
        if args.output:
            save_repro_report(report, args.output, overwrite=bool(args.overwrite))
        print(json.dumps(report, indent=2))
        return 0 if report["reproducible"] else 2

    if args.command == "review-findings-build":
        matrix = build_remediation_matrix(
            source_commit=args.source_commit,
            finding_paths=args.finding,
        )
        target = save_remediation_matrix(matrix, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": str(target), **matrix["summary"]}, indent=2))
        return 0

    if args.command == "review-findings-check":
        matrix = json.loads(Path(args.matrix).read_text(encoding="utf-8"))
        result = verify_remediation_matrix(matrix)
        print(json.dumps(result, indent=2))
        return 0 if result["high_critical_release_gate_clear"] else 2

    if args.command == "release-provenance-build":
        envelope = build_release_provenance(
            genesis_path=args.genesis,
            signing_key_path=args.key,
            source_commit=args.source_commit,
            package_version=args.package_version,
            cometbft_version=args.cometbft_version,
            artifacts=args.artifact,
            sbom_path=args.sbom,
            reproducibility_report_path=args.repro_report,
        )
        target = save_release_provenance(envelope, args.output, overwrite=bool(args.overwrite))
        print(
            json.dumps(
                {
                    "saved": str(target),
                    "manifest_sha256": envelope["manifest_sha256"],
                    "signer": envelope["signer"],
                    "supplied_artifacts_reproducible": envelope["manifest"]["claims"]["supplied_artifacts_reproducible"],
                    "production_mainnet_ready": False,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "release-provenance-verify":
        result = verify_release_provenance(
            load_release_provenance(args.provenance),
            genesis_path=args.genesis,
            artifact_directory=args.artifact_dir,
            expected_signer=args.expected_signer,
            expected_source_commit=args.expected_source_commit,
        )
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "ops-drill-build":
        envelope = build_drill_evidence(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            kind=args.kind,
            started_at_ms=args.started_at_ms,
            completed_at_ms=args.completed_at_ms,
            success=bool(args.success),
            summary=args.summary,
            evidence_paths=args.evidence,
        )
        target = save_drill_evidence(envelope, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": str(target), "signer": envelope["signer"], "success": bool(args.success)}, indent=2))
        return 0

    result = verify_drill_evidence(
        load_drill_evidence(args.drill),
        evidence_directory=args.evidence_dir,
        expected_signer=args.expected_signer,
    )
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    commands = {
        "sbom-build",
        "repro-compare",
        "review-findings-build",
        "review-findings-check",
        "release-provenance-build",
        "release-provenance-verify",
        "ops-drill-build",
        "ops-drill-verify",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        return _run(sys.argv[1:])
    return int(cli_v18.main())


if __name__ == "__main__":
    raise SystemExit(main())
