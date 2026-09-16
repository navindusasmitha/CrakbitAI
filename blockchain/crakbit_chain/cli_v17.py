from __future__ import annotations

import argparse
import json
import sys

from . import cli_v16
from .comet_state_sync import CometStateSyncManager
from .evidence_bundle import (
    build_evidence_bundle,
    load_evidence_bundle,
    save_evidence_bundle,
    verify_evidence_bundle,
)
from .genesis import Genesis


def _state_sync_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.17 CometBFT native state-sync tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    materialize = sub.add_parser("comet-snapshot-materialize")
    materialize.add_argument("--genesis", required=True)
    materialize.add_argument("--data", required=True)
    materialize.add_argument("--chunk-bytes", type=int, default=1024 * 1024)

    status = sub.add_parser("comet-snapshot-status")
    status.add_argument("--genesis", required=True)
    status.add_argument("--data", required=True)
    status.add_argument("--chunk-bytes", type=int, default=1024 * 1024)
    return parser


def _run_state_sync(argv: list[str]) -> int:
    args = _state_sync_parser().parse_args(argv)
    genesis = Genesis.load(args.genesis)
    manager = CometStateSyncManager(
        genesis=genesis,
        data_dir=args.data,
        chunk_bytes=args.chunk_bytes,
    )
    if args.command == "comet-snapshot-materialize":
        result = manager.materialize_latest()
    else:
        result = manager.status()
    print(json.dumps(result, indent=2))
    return 0


def _evidence_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.17 signed public-testnet evidence bundle tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("evidence-build")
    build.add_argument("--genesis", required=True)
    build.add_argument("--key", required=True, help="Dedicated release/evidence signing key")
    build.add_argument("--source-commit", required=True)
    build.add_argument("--cometbft-version", required=True)
    build.add_argument("--evidence", action="append", default=[])
    build.add_argument("--release-manifest", default=None)
    build.add_argument("--output", required=True)
    build.add_argument("--overwrite", action="store_true")

    verify = sub.add_parser("evidence-verify")
    verify.add_argument("--genesis", required=True)
    verify.add_argument("--bundle", required=True)
    verify.add_argument("--evidence-dir", default=None)
    verify.add_argument("--expected-signer", default=None)
    return parser


def _run_evidence(argv: list[str]) -> int:
    args = _evidence_parser().parse_args(argv)
    if args.command == "evidence-build":
        envelope = build_evidence_bundle(
            genesis_path=args.genesis,
            signing_key_path=args.key,
            source_commit=args.source_commit,
            cometbft_version=args.cometbft_version,
            evidence_paths=args.evidence,
            release_manifest_path=args.release_manifest,
        )
        target = save_evidence_bundle(envelope, args.output, overwrite=args.overwrite)
        result = {
            "saved": str(target),
            "manifest_sha256": envelope["manifest_sha256"],
            "signer": envelope["signer"],
            "evidence_files": len(envelope["manifest"]["evidence"]),
        }
    else:
        result = verify_evidence_bundle(
            load_evidence_bundle(args.bundle),
            genesis_path=args.genesis,
            evidence_directory=args.evidence_dir,
            expected_signer=args.expected_signer,
        )
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command in {"comet-snapshot-materialize", "comet-snapshot-status"}:
            return _run_state_sync(sys.argv[1:])
        if command in {"evidence-build", "evidence-verify"}:
            return _run_evidence(sys.argv[1:])
    return int(cli_v16.main())


if __name__ == "__main__":
    raise SystemExit(main())
