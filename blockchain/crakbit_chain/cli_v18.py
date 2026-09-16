from __future__ import annotations

import argparse
import json
import sys

from . import cli_v17
from .explorer_reconcile import reconcile_explorer_index
from .genesis import Genesis
from .review_freeze import (
    build_review_freeze,
    load_review_freeze,
    save_review_freeze,
    verify_review_freeze,
)


def _parse_artifact(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("artifact must use ROLE=PATH")
    role, path = value.split("=", 1)
    role = role.strip()
    path = path.strip()
    if not role or not path:
        raise argparse.ArgumentTypeError("artifact must use ROLE=PATH")
    return role, path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.18 review-candidate freeze and explorer reconciliation tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    reconcile = sub.add_parser("explorer-reconcile")
    reconcile.add_argument("--genesis", required=True)
    reconcile.add_argument("--source-data", required=True)
    reconcile.add_argument("--index", required=True)
    reconcile.add_argument("--rebuilt-output", default=None)
    reconcile.add_argument("--output", default=None)

    freeze = sub.add_parser("review-freeze-build")
    freeze.add_argument("--genesis", required=True)
    freeze.add_argument("--key", required=True)
    freeze.add_argument("--source-commit", required=True)
    freeze.add_argument("--package-version", default="0.18.0a1")
    freeze.add_argument("--cometbft-version", default="v0.40.0")
    freeze.add_argument("--artifact", action="append", type=_parse_artifact, default=[])
    freeze.add_argument("--output", required=True)
    freeze.add_argument("--overwrite", action="store_true")

    verify = sub.add_parser("review-freeze-verify")
    verify.add_argument("--genesis", required=True)
    verify.add_argument("--freeze", required=True)
    verify.add_argument("--artifact-dir", default=None)
    verify.add_argument("--expected-signer", default=None)
    verify.add_argument("--expected-source-commit", default=None)
    return parser


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)
    if args.command == "explorer-reconcile":
        genesis = Genesis.load(args.genesis)
        result = reconcile_explorer_index(
            genesis=genesis,
            source_data_dir=args.source_data,
            index_path=args.index,
            rebuilt_output=args.rebuilt_output,
        )
        if args.output:
            with open(args.output, "w", encoding="utf-8") as handle:
                json.dump(result, handle, indent=2)
                handle.write("\n")
        print(json.dumps(result, indent=2))
        return 0 if result["matches_clean_rebuild"] else 2

    if args.command == "review-freeze-build":
        envelope = build_review_freeze(
            genesis_path=args.genesis,
            signing_key_path=args.key,
            source_commit=args.source_commit,
            package_version=args.package_version,
            cometbft_version=args.cometbft_version,
            artifacts=args.artifact,
        )
        target = save_review_freeze(envelope, args.output, overwrite=bool(args.overwrite))
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

    result = verify_review_freeze(
        load_review_freeze(args.freeze),
        genesis_path=args.genesis,
        artifact_directory=args.artifact_dir,
        expected_signer=args.expected_signer,
        expected_source_commit=args.expected_source_commit,
    )
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {
        "explorer-reconcile",
        "review-freeze-build",
        "review-freeze-verify",
    }:
        return _run(sys.argv[1:])
    return int(cli_v17.main())


if __name__ == "__main__":
    raise SystemExit(main())
