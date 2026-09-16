from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import cli as legacy_cli
from .genesis import Genesis
from .history_archive import export_history_archive, import_history_archive, verify_history_archive
from .snapshots import import_snapshot_certificate
from .storage import Ledger


def _cmd_node_v12(args):
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

    from .secure_node_v12 import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port, reload=False)
    return 0


def _archive_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crakchain", description="Crakbit Chain v0.12 archive tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    export = sub.add_parser("archive-export", help="Export and fully verify genesis-anchored block history")
    export.add_argument("--genesis", required=True)
    export.add_argument("--data", required=True)
    export.add_argument("--output", required=True)
    export.add_argument("--end-height", type=int, default=None)
    export.add_argument("--overwrite", action="store_true")

    verify = sub.add_parser("archive-verify", help="Replay and cryptographically verify a history archive")
    verify.add_argument("--genesis", required=True)
    verify.add_argument("--archive", required=True)

    restore = sub.add_parser(
        "archive-import",
        help="Backfill verified pre-snapshot blocks into a snapshot-bootstrapped node without changing state",
    )
    restore.add_argument("--genesis", required=True)
    restore.add_argument("--data", required=True)
    restore.add_argument("--archive", required=True)
    return parser


def _run_archive(argv: list[str]) -> int:
    args = _archive_parser().parse_args(argv)
    genesis = Genesis.load(args.genesis)
    if args.command == "archive-export":
        ledger = Ledger(Path(args.data) / "chain.sqlite3", genesis)
        result = export_history_archive(
            ledger,
            args.output,
            end_height=args.end_height,
            overwrite=bool(args.overwrite),
        )
    elif args.command == "archive-verify":
        artifact = json.loads(Path(args.archive).read_text(encoding="utf-8"))
        result = verify_history_archive(artifact, genesis)
    else:
        ledger = Ledger(Path(args.data) / "chain.sqlite3", genesis)
        artifact = json.loads(Path(args.archive).read_text(encoding="utf-8"))
        result = import_history_archive(ledger, artifact)
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {"archive-export", "archive-verify", "archive-import"}:
        return _run_archive(sys.argv[1:])
    legacy_cli.cmd_node = _cmd_node_v12
    return int(legacy_cli.main())


if __name__ == "__main__":
    raise SystemExit(main())
