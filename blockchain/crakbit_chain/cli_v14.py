from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import cli as legacy_cli
from . import cli_v13
from .external_commit import ExternalExecutionStore
from .genesis import Genesis
from .genesis_ceremony import (
    add_attestation,
    build_ceremony,
    save_ceremony,
    verify_ceremony,
)
from .snapshots import import_snapshot_certificate
from .storage import Ledger


def _cmd_node_v14(args):
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

    from .secure_node_v14 import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port, reload=False)
    return 0


def _external_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.14 crash-safe external-consensus execution tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("external-status", "Show external-consensus committed/pending application state"),
        ("external-preview", "Preview a deterministic external-consensus finalize"),
        ("external-finalize", "Persist a non-mutating external-consensus finalize stage"),
        ("external-commit", "Atomically commit the currently staged external finalize"),
    ):
        item = sub.add_parser(name, help=help_text)
        item.add_argument("--genesis", required=True)
        item.add_argument("--data", required=True)
        if name in {"external-preview", "external-finalize"}:
            item.add_argument("--height", type=int, required=True)
            item.add_argument("--block-hash", required=True)
            item.add_argument(
                "--transactions",
                required=True,
                help="JSON file containing a list of signed transaction objects",
            )
    return parser


def _run_external(argv: list[str]) -> int:
    args = _external_parser().parse_args(argv)
    genesis = Genesis.load(args.genesis)
    ledger = Ledger(Path(args.data) / "chain.sqlite3", genesis)
    store = ExternalExecutionStore(ledger)
    if args.command == "external-status":
        result = store.status()
    elif args.command == "external-commit":
        result = store.commit_pending()
    else:
        transactions = json.loads(Path(args.transactions).read_text(encoding="utf-8"))
        if not isinstance(transactions, list):
            raise ValueError("transactions file must contain a JSON list")
        if args.command == "external-preview":
            result = store.preview_finalize(
                height=args.height,
                consensus_block_hash=args.block_hash,
                transactions=transactions,
            )
        else:
            result = store.stage_finalize(
                height=args.height,
                consensus_block_hash=args.block_hash,
                transactions=transactions,
            )
    print(json.dumps(result, indent=2))
    return 0


def _ceremony_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.14 signed testnet genesis ceremony tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("ceremony-create", help="Create a deterministic genesis ceremony statement")
    create.add_argument("--genesis", required=True)
    create.add_argument("--output", required=True)
    create.add_argument("--overwrite", action="store_true")

    sign = sub.add_parser("ceremony-sign", help="Add one configured validator attestation")
    sign.add_argument("--ceremony", required=True)
    sign.add_argument("--key", required=True)
    sign.add_argument("--output", default=None)
    sign.add_argument("--overwrite", action="store_true")

    verify = sub.add_parser("ceremony-verify", help="Verify ceremony signatures and >2/3 quorum")
    verify.add_argument("--ceremony", required=True)
    verify.add_argument("--genesis", required=True)
    return parser


def _run_ceremony(argv: list[str]) -> int:
    args = _ceremony_parser().parse_args(argv)
    if args.command == "ceremony-create":
        ceremony = build_ceremony(args.genesis)
        target = save_ceremony(ceremony, args.output, overwrite=bool(args.overwrite))
        result = {
            "saved": str(target),
            "statement_sha256": ceremony["statement_sha256"],
            "required_quorum": ceremony["statement"]["quorum_size"],
            "attestations": 0,
        }
    elif args.command == "ceremony-sign":
        source = Path(args.ceremony)
        ceremony = json.loads(source.read_text(encoding="utf-8"))
        ceremony = add_attestation(ceremony, args.key)
        target = Path(args.output) if args.output else source
        target.parent.mkdir(parents=True, exist_ok=True)
        if target != source and target.exists() and not args.overwrite:
            raise FileExistsError(f"ceremony file already exists: {target}")
        target.write_text(json.dumps(ceremony, indent=2) + "\n", encoding="utf-8")
        result = {
            "saved": str(target),
            "statement_sha256": ceremony["statement_sha256"],
            "attestations": len(ceremony.get("attestations", [])),
        }
    else:
        ceremony = json.loads(Path(args.ceremony).read_text(encoding="utf-8"))
        result = verify_ceremony(ceremony, genesis_path=args.genesis)
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command in {
            "external-status",
            "external-preview",
            "external-finalize",
            "external-commit",
        }:
            return _run_external(sys.argv[1:])
        if command in {"ceremony-create", "ceremony-sign", "ceremony-verify"}:
            return _run_ceremony(sys.argv[1:])

    # Reuse all v0.13 archive/release/protocol commands while routing `node` to v0.14.
    cli_v13._cmd_node_v13 = _cmd_node_v14
    return int(cli_v13.main())


if __name__ == "__main__":
    raise SystemExit(main())
