from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import cli as legacy_cli
from . import cli_v12
from .app_protocol import ExecutionProtocolAdapter
from .genesis import Genesis
from .release_artifacts import (
    build_release_envelope,
    save_release_envelope,
    verify_release_envelope,
)
from .snapshots import import_snapshot_certificate
from .storage import Ledger


def _cmd_node_v13(args):
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

    from .secure_node_v13 import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port, reload=False)
    return 0


def _release_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crakchain", description="Crakbit v0.13 signed release tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("release-build", help="Build an Ed25519-signed genesis/release manifest")
    build.add_argument("--genesis", required=True)
    build.add_argument("--key", required=True, help="Dedicated release-signing key; do not use a validator key")
    build.add_argument("--version", required=True)
    build.add_argument("--output", required=True)
    build.add_argument("--artifact", action="append", default=[])
    build.add_argument("--overwrite", action="store_true")

    verify = sub.add_parser("release-verify", help="Verify a signed release manifest")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--genesis", default=None)
    verify.add_argument("--expected-signer", default=None)
    verify.add_argument("--artifact-dir", default=None)
    return parser


def _run_release(argv: list[str]) -> int:
    args = _release_parser().parse_args(argv)
    if args.command == "release-build":
        envelope = build_release_envelope(
            genesis_path=args.genesis,
            signing_key_path=args.key,
            version=args.version,
            artifact_paths=args.artifact,
        )
        target = save_release_envelope(envelope, args.output, overwrite=bool(args.overwrite))
        result = {
            "saved": str(target),
            "version": envelope["manifest"]["version"],
            "chain_id": envelope["manifest"]["chain_id"],
            "signer": envelope["signer"],
            "manifest_sha256": envelope["manifest_sha256"],
            "artifact_count": len(envelope["manifest"]["artifacts"]),
        }
    else:
        envelope = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        result = verify_release_envelope(
            envelope,
            genesis_path=args.genesis,
            expected_signer=args.expected_signer,
            artifact_directory=args.artifact_dir,
        )
    print(json.dumps(result, indent=2))
    return 0


def _protocol_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crakchain", description="Crakbit v0.13 execution protocol PoC")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("protocol-status", help="Print deterministic application protocol state")
    status.add_argument("--genesis", required=True)
    status.add_argument("--data", required=True)

    preview = sub.add_parser("protocol-preview", help="Preview an ordered transaction batch without mutating state")
    preview.add_argument("--genesis", required=True)
    preview.add_argument("--data", required=True)
    preview.add_argument("--transactions", required=True, help="JSON file containing a list of transaction objects")
    preview.add_argument("--fee-recipient", required=True)
    return parser


def _run_protocol(argv: list[str]) -> int:
    args = _protocol_parser().parse_args(argv)
    genesis = Genesis.load(args.genesis)
    ledger = Ledger(Path(args.data) / "chain.sqlite3", genesis)
    adapter = ExecutionProtocolAdapter(ledger)
    if args.command == "protocol-status":
        result = adapter.info()
    else:
        transactions = json.loads(Path(args.transactions).read_text(encoding="utf-8"))
        if not isinstance(transactions, list):
            raise ValueError("transactions file must contain a JSON list")
        result = adapter.preview_batch(transactions, fee_recipient=args.fee_recipient)
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command in {"archive-export", "archive-verify", "archive-import"}:
            return cli_v12._run_archive(sys.argv[1:])
        if command in {"release-build", "release-verify"}:
            return _run_release(sys.argv[1:])
        if command in {"protocol-status", "protocol-preview"}:
            return _run_protocol(sys.argv[1:])

    legacy_cli.cmd_node = _cmd_node_v13
    return int(legacy_cli.main())


if __name__ == "__main__":
    raise SystemExit(main())
