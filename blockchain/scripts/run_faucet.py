from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the strictly test-only Crakbit faucet service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9400)
    parser.add_argument("--genesis", required=True)
    parser.add_argument("--key", required=True, help="Dedicated funded faucet key; never use a validator key")
    parser.add_argument("--rpc", default="http://127.0.0.1:9101", help="Research-node RPC fallback")
    parser.add_argument("--gateway", default="", help="Optional public gateway; supports research or CometBFT mode")
    parser.add_argument("--state", default="runtime/faucet-state.sqlite3")
    parser.add_argument("--rate-limit-db", default="", help="Durable request-rate database; defaults beside faucet state")
    parser.add_argument("--amount", default="10", help="Test CRKBIT per successful request; max 100")
    parser.add_argument("--cooldown-seconds", type=int, default=3600)
    parser.add_argument("--global-rpm", type=int, default=10)
    args = parser.parse_args()

    os.environ["CRAKBIT_FAUCET_ENABLED"] = "1"
    os.environ["CRAKBIT_FAUCET_GENESIS"] = args.genesis
    os.environ["CRAKBIT_FAUCET_KEY"] = args.key
    os.environ["CRAKBIT_FAUCET_RPC"] = args.rpc
    os.environ["CRAKBIT_FAUCET_GATEWAY"] = args.gateway
    os.environ["CRAKBIT_FAUCET_STATE"] = args.state
    os.environ["CRAKBIT_FAUCET_AMOUNT"] = str(args.amount)
    os.environ["CRAKBIT_FAUCET_ADDRESS_COOLDOWN"] = str(args.cooldown_seconds)
    os.environ["CRAKBIT_FAUCET_GLOBAL_RPM"] = str(args.global_rpm)
    os.environ["CRAKBIT_RATE_LIMIT_DB"] = args.rate_limit_db or str(
        Path(args.state).with_name("public-rate-limits.sqlite3")
    )

    from crakbit_chain.faucet_service_v16 import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
