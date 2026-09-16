from __future__ import annotations

import argparse
import os

import uvicorn


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the Crakbit v0.17 external execution service with CometBFT ABCI state sync"
    )
    parser.add_argument("--genesis", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=26659)
    args = parser.parse_args()

    if len(args.token) < 24:
        raise SystemExit("--token must be at least 24 characters")

    os.environ["CRAKBIT_GENESIS"] = args.genesis
    os.environ["CRAKBIT_EXTERNAL_DATA_DIR"] = args.data
    os.environ["CRAKBIT_EXECUTION_SERVICE_TOKEN"] = args.token

    from crakbit_chain.execution_service_v17 import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
