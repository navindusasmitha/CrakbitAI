from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Crakbit testnet proof-of-work reward service")
    parser.add_argument("--genesis", required=True)
    parser.add_argument("--key", required=True, help="Dedicated non-validator reward wallet key")
    parser.add_argument("--gateway", default="http://127.0.0.1:9600")
    parser.add_argument("--state", default="runtime/mining-state.sqlite3")
    parser.add_argument("--rate-limit-db", default="", help="Durable request-rate database; defaults beside mining state")
    parser.add_argument("--reward", default="1", help="Test CRKBIT reward per valid solution")
    parser.add_argument("--difficulty-bits", type=int, default=18)
    parser.add_argument("--ttl", type=int, default=300)
    parser.add_argument("--cooldown", type=int, default=3600)
    parser.add_argument("--max-daily", type=int, default=24)
    parser.add_argument("--challenge-rpm", type=int, default=30)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9500)
    args = parser.parse_args()

    os.environ["CRAKBIT_MINING_ENABLED"] = "1"
    os.environ["CRAKBIT_MINING_GENESIS"] = args.genesis
    os.environ["CRAKBIT_MINING_REWARD_KEY"] = args.key
    os.environ["CRAKBIT_MINING_GATEWAY"] = args.gateway
    os.environ["CRAKBIT_MINING_STATE"] = args.state
    os.environ["CRAKBIT_MINING_REWARD"] = str(args.reward)
    os.environ["CRAKBIT_MINING_DIFFICULTY_BITS"] = str(args.difficulty_bits)
    os.environ["CRAKBIT_MINING_CHALLENGE_TTL"] = str(args.ttl)
    os.environ["CRAKBIT_MINING_ADDRESS_COOLDOWN"] = str(args.cooldown)
    os.environ["CRAKBIT_MINING_MAX_DAILY"] = str(args.max_daily)
    os.environ["CRAKBIT_MINING_CHALLENGE_RPM"] = str(args.challenge_rpm)
    os.environ["CRAKBIT_RATE_LIMIT_DB"] = args.rate_limit_db or str(
        Path(args.state).with_name("public-rate-limits.sqlite3")
    )

    from crakbit_chain.pow_mining_v16 import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
