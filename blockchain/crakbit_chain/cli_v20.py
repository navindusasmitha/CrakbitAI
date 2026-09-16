from __future__ import annotations

import argparse
import json
import sys

from . import cli_v19
from .compatibility_v20 import check_compatibility, compatibility_matrix, save_matrix
from .genesis import Genesis
from .migration_evidence_v20 import (
    build_migration_evidence,
    load_migration_evidence,
    save_migration_evidence,
    verify_migration_evidence,
)
from .schema_migrations_v20 import (
    CURRENT_SCHEMA_VERSION,
    dry_run_migration,
    inspect_schema,
    migrate_database_copy,
)
from .upgrade_rehearsal_v20 import rehearse_upgrade, save_upgrade_rehearsal
from .validator_lifecycle_v20 import (
    build_validator_lifecycle_plan,
    load_validator_lifecycle_plan,
    save_validator_lifecycle_plan,
    verify_validator_lifecycle_plan,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.20 upgrade compatibility and validator-lifecycle rehearsal tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    schema = sub.add_parser("schema-status")
    schema.add_argument("--data", required=True)

    dry = sub.add_parser("migration-dry-run")
    dry.add_argument("--source", required=True)
    dry.add_argument("--target-version", type=int, default=CURRENT_SCHEMA_VERSION)

    copy = sub.add_parser("migration-copy")
    copy.add_argument("--source", required=True)
    copy.add_argument("--output", required=True)
    copy.add_argument("--target-version", type=int, default=CURRENT_SCHEMA_VERSION)
    copy.add_argument("--overwrite", action="store_true")

    matrix = sub.add_parser("compatibility-matrix")
    matrix.add_argument("--output", default=None)
    matrix.add_argument("--overwrite", action="store_true")

    compat = sub.add_parser("compatibility-check")
    compat.add_argument("--data", required=True)
    compat.add_argument("--cometbft-version", default="v0.40.0")
    compat.add_argument("--genesis", default=None)

    rehearse = sub.add_parser("upgrade-rehearse")
    rehearse.add_argument("--genesis", required=True)
    rehearse.add_argument("--source-data", required=True)
    rehearse.add_argument("--output-data", required=True)
    rehearse.add_argument("--cometbft-version", default="v0.40.0")
    rehearse.add_argument("--report", required=True)
    rehearse.add_argument("--overwrite", action="store_true")

    evidence = sub.add_parser("migration-evidence-build")
    evidence.add_argument("--key", required=True)
    evidence.add_argument("--source-commit", required=True)
    evidence.add_argument("--report", required=True)
    evidence.add_argument("--output", required=True)
    evidence.add_argument("--overwrite", action="store_true")

    evidence_verify = sub.add_parser("migration-evidence-verify")
    evidence_verify.add_argument("--evidence", required=True)
    evidence_verify.add_argument("--report-dir", default=None)
    evidence_verify.add_argument("--expected-signer", default=None)

    plan = sub.add_parser("validator-plan-build")
    plan.add_argument("--genesis", required=True)
    plan.add_argument("--key", required=True)
    plan.add_argument("--source-commit", required=True)
    plan.add_argument("--kind", required=True, choices=["join", "remove", "replace"])
    plan.add_argument("--effective-height", type=int, required=True)
    plan.add_argument("--existing-address", default=None)
    plan.add_argument("--new-public-key", default=None)
    plan.add_argument("--new-name", default="validator-new")
    plan.add_argument("--new-power", type=int, default=1)
    plan.add_argument("--output", required=True)
    plan.add_argument("--overwrite", action="store_true")

    plan_verify = sub.add_parser("validator-plan-verify")
    plan_verify.add_argument("--genesis", required=True)
    plan_verify.add_argument("--plan", required=True)
    plan_verify.add_argument("--expected-signer", default=None)
    plan_verify.add_argument("--expected-source-commit", default=None)
    return parser


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "schema-status":
        print(json.dumps(inspect_schema(args.data), indent=2))
        return 0

    if args.command == "migration-dry-run":
        report = dry_run_migration(source=args.source, target_version=args.target_version)
        print(json.dumps(report, indent=2))
        return 0

    if args.command == "migration-copy":
        report = migrate_database_copy(
            source=args.source,
            output=args.output,
            target_version=args.target_version,
            overwrite=bool(args.overwrite),
            verify_rollback=True,
        )
        print(json.dumps(report, indent=2))
        return 0

    if args.command == "compatibility-matrix":
        matrix = compatibility_matrix()
        if args.output:
            save_matrix(args.output, overwrite=bool(args.overwrite))
        print(json.dumps(matrix, indent=2))
        return 0

    if args.command == "compatibility-check":
        expected = None
        if args.genesis:
            expected = Genesis.load(args.genesis).fingerprint()
        result = check_compatibility(
            data=args.data,
            cometbft_version=args.cometbft_version,
            expected_genesis_fingerprint=expected,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["compatible_for_v020_testnet_rehearsal"] else 2

    if args.command == "upgrade-rehearse":
        report = rehearse_upgrade(
            genesis_path=args.genesis,
            source_data=args.source_data,
            output_data=args.output_data,
            cometbft_version=args.cometbft_version,
            overwrite=bool(args.overwrite),
        )
        target = save_upgrade_rehearsal(report, args.report, overwrite=bool(args.overwrite))
        print(
            json.dumps(
                {
                    "saved": str(target),
                    "testnet_rehearsal_passed": report["testnet_rehearsal_passed"],
                    "rollback_verified": report["rollback_verified"],
                    "source_modified": False,
                    "production_mainnet_ready": False,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "migration-evidence-build":
        envelope = build_migration_evidence(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            report_path=args.report,
        )
        target = save_migration_evidence(envelope, args.output, overwrite=bool(args.overwrite))
        print(
            json.dumps(
                {
                    "saved": str(target),
                    "manifest_sha256": envelope["manifest_sha256"],
                    "signer": envelope["signer"],
                    "production_mainnet_ready": False,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "migration-evidence-verify":
        result = verify_migration_evidence(
            load_migration_evidence(args.evidence),
            report_directory=args.report_dir,
            expected_signer=args.expected_signer,
        )
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "validator-plan-build":
        envelope = build_validator_lifecycle_plan(
            genesis_path=args.genesis,
            signing_key_path=args.key,
            source_commit=args.source_commit,
            kind=args.kind,
            effective_height=args.effective_height,
            existing_address=args.existing_address,
            new_public_key=args.new_public_key,
            new_name=args.new_name,
            new_power=args.new_power,
        )
        target = save_validator_lifecycle_plan(
            envelope, args.output, overwrite=bool(args.overwrite)
        )
        manifest = envelope["manifest"]
        print(
            json.dumps(
                {
                    "saved": str(target),
                    "manifest_sha256": envelope["manifest_sha256"],
                    "signer": envelope["signer"],
                    "kind": manifest["kind"],
                    "emit_height": manifest["emit_height"],
                    "effective_height": manifest["effective_height"],
                    "consensus_change_applied": False,
                    "production_mainnet_ready": False,
                },
                indent=2,
            )
        )
        return 0

    result = verify_validator_lifecycle_plan(
        load_validator_lifecycle_plan(args.plan),
        genesis_path=args.genesis,
        expected_signer=args.expected_signer,
        expected_source_commit=args.expected_source_commit,
    )
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    commands = {
        "schema-status",
        "migration-dry-run",
        "migration-copy",
        "compatibility-matrix",
        "compatibility-check",
        "upgrade-rehearse",
        "migration-evidence-build",
        "migration-evidence-verify",
        "validator-plan-build",
        "validator-plan-verify",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        return _run(sys.argv[1:])
    return int(cli_v19.main())


if __name__ == "__main__":
    raise SystemExit(main())
