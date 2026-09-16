from __future__ import annotations

import argparse
import os

import uvicorn


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the Crakbit v0.16 dedicated external-consensus explorer index service"
    )
    parser.add_argument("--genesis", required=True)
    parser.add_argument("--source-data", required=True)
    parser.add_argument("--index", default="runtime/explorer-index.sqlite3")
    parser.add_argument("--sync-seconds", type=float, default=2.0)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9700)
    args = parser.parse_args()

    os.environ["CRAKBIT_EXPLORER_GENESIS"] = args.genesis
    os.environ["CRAKBIT_EXPLORER_SOURCE_DATA"] = args.source_data
    os.environ["CRAKBIT_EXPLORER_INDEX"] = args.index
    os.environ["CRAKBIT_EXPLORER_SYNC_SECONDS"] = str(args.sync_seconds)

    from crakbit_chain.explorer_index_service import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
