from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import cli_v20
from .external_commit_v21 import ExternalExecutionStoreV21
from .external_state_sync_v21 import (
    export_external_snapshot_v21,
    import_external_snapshot_v21,
    verify_external_snapshot_v21,
)
from .genesis import Genesis
from .schema_migrations_v21 import dry_run_v21_migration, migrate_to_v21_copy
from .storage import Ledger
from .validator_governance_v21 import (
    ValidatorGovernanceStore,
    build_governance_request,
    load_governance_request,
    save_governance_request,
    sign_governance_request,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.21 deterministic validator governance and upgrade activation tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    migrate_dry = sub.add_parser("migration-v21-dry-run")
    migrate_dry.add_argument("--genesis", required=True)
    migrate_dry.add_argument("--source", required=True)

    migrate = sub.add_parser("migration-v21-copy")
    migrate.add_argument("--genesis", required=True)
    migrate.add_argument("--source", required=True)
    migrate.add_argument("--output", required=True)
    migrate.add_argument("--overwrite", action="store_true")

    status = sub.add_parser("governance-status")
    status.add_argument("--genesis", required=True)
    status.add_argument("--data", required=True)

    build = sub.add_parser("validator-change-build")
    build.add_argument("--genesis", required=True)
    build.add_argument("--data", required=True)
    build.add_argument("--kind", required=True, choices=["join", "remove", "replace"])
    build.add_argument("--emit-height", required=True, type=int)
    build.add_argument("--existing-address", default=None)
    build.add_argument("--new-public-key", default=None)
    build.add_argument("--new-name", default="validator-new")
    build.add_argument("--new-power", type=int, default=1)
    build.add_argument("--output", required=True)
    build.add_argument("--overwrite", action="store_true")

    sign = sub.add_parser("validator-change-sign")
    sign.add_argument("--genesis", required=True)
    sign.add_argument("--data", required=True)
    sign.add_argument("--request", required=True)
    sign.add_argument("--key", required=True)
    sign.add_argument("--output", required=True)
    sign.add_argument("--overwrite", action="store_true")

    verify = sub.add_parser("validator-change-verify")
    verify.add_argument("--genesis", required=True)
    verify.add_argument("--data", required=True)
    verify.add_argument("--request", required=True)
    verify.add_argument("--allow-partial", action="store_true")

    snap_export = sub.add_parser("snapshot-v21-export")
    snap_export.add_argument("--genesis", required=True)
    snap_export.add_argument("--data", required=True)
    snap_export.add_argument("--output", required=True)
    snap_export.add_argument("--overwrite", action="store_true")

    snap_verify = sub.add_parser("snapshot-v21-verify")
    snap_verify.add_argument("--genesis", required=True)
    snap_verify.add_argument("--snapshot", required=True)
    snap_verify.add_argument("--expected-height", type=int, default=None)
    snap_verify.add_argument("--expected-app-hash", default=None)

    snap_import = sub.add_parser("snapshot-v21-import")
    snap_import.add_argument("--genesis", required=True)
    snap_import.add_argument("--snapshot", required=True)
    snap_import.add_argument("--data", required=True)
    snap_import.add_argument("--expected-height", type=int, default=None)
    snap_import.add_argument("--expected-app-hash", default=None)
    return parser


def _ledger(genesis_path: str, data: str) -> Ledger:
    genesis = Genesis.load(genesis_path)
    return Ledger(Path(data) / "chain.sqlite3", genesis)


def _save_json(payload: dict, path: str, *, overwrite: bool) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"output already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "migration-v21-dry-run":
        print(
            json.dumps(
                dry_run_v21_migration(genesis_path=args.genesis, source=args.source),
                indent=2,
            )
        )
        return 0

    if args.command == "migration-v21-copy":
        result = migrate_to_v21_copy(
            genesis_path=args.genesis,
            source=args.source,
            output=args.output,
            overwrite=bool(args.overwrite),
            verify_rollback=True,
        )
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "governance-status":
        ledger = _ledger(args.genesis, args.data)
        store = ExternalExecutionStoreV21(ledger)
        print(json.dumps({"execution": store.status(), "governance": store.governance.status()}, indent=2))
        return 0

    if args.command == "validator-change-build":
        envelope = build_governance_request(
            genesis_path=args.genesis,
            data_dir=args.data,
            kind=args.kind,
            emit_height=args.emit_height,
            existing_address=args.existing_address,
            new_public_key=args.new_public_key,
            new_name=args.new_name,
            new_power=args.new_power,
        )
        target = save_governance_request(envelope, args.output, overwrite=bool(args.overwrite))
        print(
            json.dumps(
                {
                    "saved": str(target),
                    "change_id": envelope["change_id"],
                    "emit_height": envelope["request"]["emit_height"],
                    "effective_height": envelope["request"]["effective_height"],
                    "approvals": 0,
                    "production_mainnet_ready": False,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "validator-change-sign":
        envelope = sign_governance_request(
            load_governance_request(args.request),
            genesis_path=args.genesis,
            data_dir=args.data,
            signing_key_path=args.key,
        )
        target = save_governance_request(envelope, args.output, overwrite=bool(args.overwrite))
        print(
            json.dumps(
                {
                    "saved": str(target),
                    "change_id": envelope["change_id"],
                    "approval_count": len(envelope.get("approvals", [])),
                },
                indent=2,
            )
        )
        return 0

    if args.command == "validator-change-verify":
        ledger = _ledger(args.genesis, args.data)
        governance = ValidatorGovernanceStore(ledger, allow_pristine_initialize=True)
        result = governance.verify_envelope(
            load_governance_request(args.request),
            active_validators=governance.active_validators(),
            require_quorum=not bool(args.allow_partial),
        )
        print(json.dumps(result, indent=2))
        return 0 if (result["quorum"] or args.allow_partial) else 2

    if args.command == "snapshot-v21-export":
        ledger = _ledger(args.genesis, args.data)
        envelope = export_external_snapshot_v21(ledger)
        target = _save_json(envelope, args.output, overwrite=bool(args.overwrite))
        print(
            json.dumps(
                {
                    "saved": str(target),
                    "height": envelope["snapshot"]["height"],
                    "application_hash": envelope["snapshot"]["application_hash"],
                    "governance_hash": envelope["snapshot"]["governance_hash"],
                },
                indent=2,
            )
        )
        return 0

    envelope = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    genesis = Genesis.load(args.genesis)
    if args.command == "snapshot-v21-verify":
        result = verify_external_snapshot_v21(
            envelope,
            genesis,
            expected_height=args.expected_height,
            expected_application_hash=args.expected_app_hash,
        )
        print(json.dumps(result, indent=2))
        return 0

    result = import_external_snapshot_v21(
        envelope=envelope,
        genesis=genesis,
        data_dir=args.data,
        expected_height=args.expected_height,
        expected_application_hash=args.expected_app_hash,
    )
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    commands = {
        "migration-v21-dry-run",
        "migration-v21-copy",
        "governance-status",
        "validator-change-build",
        "validator-change-sign",
        "validator-change-verify",
        "snapshot-v21-export",
        "snapshot-v21-verify",
        "snapshot-v21-import",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        return _run(sys.argv[1:])
    return int(cli_v20.main())


if __name__ == "__main__":
    raise SystemExit(main())
