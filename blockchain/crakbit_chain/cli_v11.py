from __future__ import annotations

from . import cli as legacy_cli


def _cmd_node_v11(args):
    import os
    from pathlib import Path

    import uvicorn

    from .genesis import Genesis
    from .snapshots import import_snapshot_certificate
    from .storage import Ledger

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

    from .secure_node_v11 import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port, reload=False)
    return 0


def main() -> int:
    # Keep the stable command surface while activating the current node implementation.
    legacy_cli.cmd_node = _cmd_node_v11
    return int(legacy_cli.main())


if __name__ == "__main__":
    raise SystemExit(main())
