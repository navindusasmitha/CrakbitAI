from __future__ import annotations

import os

from . import cli as legacy_cli
from . import cli_v14
from .genesis import Genesis
from .snapshots import import_snapshot_certificate
from .storage import Ledger


def _cmd_node_v15(args):
    import uvicorn

    os.environ["CRAKBIT_GENESIS"] = args.genesis
    os.environ["CRAKBIT_VALIDATOR_KEY"] = args.key
    os.environ["CRAKBIT_DATA_DIR"] = args.data
    if args.require_peer_tls:
        os.environ["CRAKBIT_REQUIRE_PEER_TLS"] = "1"

    if args.bootstrap_snapshot:
        from pathlib import Path

        genesis = Genesis.load(args.genesis)
        ledger = Ledger(Path(args.data) / "chain.sqlite3", genesis)
        certificate = legacy_cli._load_json(args.bootstrap_snapshot)
        import_snapshot_certificate(ledger, certificate)

    from .secure_node_v15 import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port, reload=False)
    return 0


def main() -> int:
    # Reuse all v0.14 execution/genesis-ceremony commands while routing normal
    # `crakchain node` startup through the v0.15 web-wallet wrapper.
    cli_v14._cmd_node_v14 = _cmd_node_v15
    return int(cli_v14.main())


if __name__ == "__main__":
    raise SystemExit(main())
