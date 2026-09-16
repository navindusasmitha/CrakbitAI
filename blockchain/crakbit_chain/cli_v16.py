from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import cli as legacy_cli
from . import cli_v14
from . import cli_v15
from .explorer_index import ExternalExplorerIndex
from .external_commit_v16 import ExternalExecutionStoreV16
from .external_state_sync import (
    export_external_snapshot,
    import_external_snapshot,
    load_snapshot,
    save_snapshot,
    verify_external_snapshot,
)
from .genesis import Genesis
from .snapshots import import_snapshot_certificate
from .storage import Ledger


def _cmd_node_v16(args):
    import uvicorn

    os.environ["CRAKBIT_GENESIS"] = args.genesis
    os.environ["CRAKBIT_VALIDATOR_KEY"] = args.key
    os.environ["CRAKBIT_DATA_DIR"] = args.data
    if args.require_peer_tls:
        os.environ["CRAKBIT_REQUIRE_PEER_TLS"] = "1"

    if args.bootstrap_snapshot:
        genesis = Genesis.load(args.genesis)
        ledger = Ledger(Path(args.data) / "chain.sqlite3", genesis)
        certificate = legacy_cli._load_json(args.bootstrap_snapshot)
        import_snapshot_certificate(ledger, certificate)

    from .secure_node_v16 import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port, reload=False)
    return 0


def _snapshot_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.16 external application checkpoint tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    export = sub.add_parser("external-snapshot-export")
    export.add_argument("--genesis", required=True)
    export.add_argument("--data", required=True)
    export.add_argument("--output", required=True)
    export.add_argument("--overwrite", action="store_true")

    verify = sub.add_parser("external-snapshot-verify")
    verify.add_argument("--genesis", required=True)
    verify.add_argument("--snapshot", required=True)
    verify.add_argument("--expected-height", type=int, default=None)
    verify.add_argument("--expected-app-hash", default=None)

    restore = sub.add_parser("external-snapshot-import")
    restore.add_argument("--genesis", required=True)
    restore.add_argument("--snapshot", required=True)
    restore.add_argument("--data", required=True)
    restore.add_argument("--expected-height", type=int, default=None)
    restore.add_argument("--expected-app-hash", default=None)

    status = sub.add_parser("external-state-status")
    status.add_argument("--genesis", required=True)
    status.add_argument("--data", required=True)
    return parser


def _run_snapshot(argv: list[str]) -> int:
    args = _snapshot_parser().parse_args(argv)
    genesis = Genesis.load(args.genesis)
    if args.command == "external-snapshot-export":
        ledger = Ledger(Path(args.data) / "chain.sqlite3", genesis)
        envelope = export_external_snapshot(ledger)
        target = save_snapshot(envelope, args.output, overwrite=bool(args.overwrite))
        result = {
            "saved": str(target),
            "height": envelope["snapshot"]["height"],
            "application_hash": envelope["snapshot"]["application_hash"],
            "artifact_hash": envelope["artifact_hash"],
        }
    elif args.command == "external-snapshot-verify":
        result = verify_external_snapshot(
            load_snapshot(args.snapshot),
            genesis,
            expected_height=args.expected_height,
            expected_application_hash=args.expected_app_hash,
        )
    elif args.command == "external-snapshot-import":
        result = import_external_snapshot(
            envelope=load_snapshot(args.snapshot),
            genesis=genesis,
            data_dir=args.data,
            expected_height=args.expected_height,
            expected_application_hash=args.expected_app_hash,
        )
    else:
        ledger = Ledger(Path(args.data) / "chain.sqlite3", genesis)
        result = ExternalExecutionStoreV16(ledger).status()
    print(json.dumps(result, indent=2))
    return 0


def _index_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.16 dedicated external explorer index tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("explorer-index-sync")
    build.add_argument("--genesis", required=True)
    build.add_argument("--source-data", required=True)
    build.add_argument("--index", required=True)

    status = sub.add_parser("explorer-index-status")
    status.add_argument("--genesis", required=True)
    status.add_argument("--index", required=True)
    return parser


def _run_index(argv: list[str]) -> int:
    args = _index_parser().parse_args(argv)
    genesis = Genesis.load(args.genesis)
    index = ExternalExplorerIndex(args.index, genesis)
    if args.command == "explorer-index-sync":
        result = index.sync_from_source(args.source_data)
        result["summary"] = index.summary()
    else:
        result = index.summary()
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command in {
            "external-snapshot-export",
            "external-snapshot-verify",
            "external-snapshot-import",
            "external-state-status",
        }:
            return _run_snapshot(sys.argv[1:])
        if command in {"explorer-index-sync", "explorer-index-status"}:
            return _run_index(sys.argv[1:])

    # Reuse every earlier command while routing normal node startup through v0.16.
    cli_v15._cmd_node_v15 = _cmd_node_v16
    cli_v14._cmd_node_v14 = _cmd_node_v16
    return int(cli_v15.main())


if __name__ == "__main__":
    raise SystemExit(main())
