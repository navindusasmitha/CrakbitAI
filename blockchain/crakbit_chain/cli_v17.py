from __future__ import annotations

import argparse
import json
import sys

from . import cli_v16
from .comet_state_sync import CometStateSyncManager
from .genesis import Genesis


def _parser() -> argparse.ArgumentParser:
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


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)
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


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {
        "comet-snapshot-materialize",
        "comet-snapshot-status",
    }:
        return _run(sys.argv[1:])
    return int(cli_v16.main())


if __name__ == "__main__":
    raise SystemExit(main())
