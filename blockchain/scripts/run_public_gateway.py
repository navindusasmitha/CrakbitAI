from __future__ import annotations

import argparse
import os

import uvicorn


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Crakbit public wallet/explorer gateway")
    parser.add_argument("--genesis", required=True)
    parser.add_argument("--mode", choices=["research", "cometbft"], default="research")
    parser.add_argument("--research-rpc", default="http://127.0.0.1:9101")
    parser.add_argument("--comet-rpc", default="http://127.0.0.1:26657")
    parser.add_argument("--execution-url", default="http://127.0.0.1:26659")
    parser.add_argument("--execution-token", default="")
    parser.add_argument("--faucet-url", default="")
    parser.add_argument("--mining-url", default="")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9600)
    args = parser.parse_args()

    os.environ["CRAKBIT_GATEWAY_GENESIS"] = args.genesis
    os.environ["CRAKBIT_GATEWAY_MODE"] = args.mode
    os.environ["CRAKBIT_GATEWAY_RESEARCH_RPC"] = args.research_rpc
    os.environ["CRAKBIT_GATEWAY_COMET_RPC"] = args.comet_rpc
    os.environ["CRAKBIT_GATEWAY_EXECUTION_URL"] = args.execution_url
    os.environ["CRAKBIT_GATEWAY_EXECUTION_TOKEN"] = args.execution_token
    os.environ["CRAKBIT_GATEWAY_FAUCET_URL"] = args.faucet_url
    os.environ["CRAKBIT_GATEWAY_MINING_URL"] = args.mining_url

    from crakbit_chain.public_gateway import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
