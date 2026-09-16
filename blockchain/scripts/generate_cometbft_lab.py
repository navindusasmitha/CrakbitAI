from __future__ import annotations

import argparse
import json

from crakbit_chain.comet_lab import generate_lab


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a repeatable local Crakbit/CometBFT validator lab"
    )
    parser.add_argument("--output", default="runtime/cometbft-lab")
    parser.add_argument("--chain-id", default="crakbit-v16-local")
    parser.add_argument("--nodes", type=int, default=4)
    parser.add_argument("--cometbft", default="cometbft")
    parser.add_argument("--bridge", default="./cometbft-app/crakbit-cometbft-bridge")
    parser.add_argument("--execution-script", default="scripts/run_execution_service_v16.py")
    parser.add_argument("--application-genesis", default="runtime/genesis.json")
    parser.add_argument("--base-rpc-port", type=int, default=27657)
    parser.add_argument("--base-p2p-port", type=int, default=27656)
    parser.add_argument("--base-abci-port", type=int, default=27658)
    parser.add_argument("--base-execution-port", type=int, default=27659)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    manifest = generate_lab(
        output=args.output,
        chain_id=args.chain_id,
        nodes=args.nodes,
        cometbft_binary=args.cometbft,
        bridge_binary=args.bridge,
        execution_script=args.execution_script,
        application_genesis=args.application_genesis,
        base_rpc_port=args.base_rpc_port,
        base_p2p_port=args.base_p2p_port,
        base_abci_port=args.base_abci_port,
        base_execution_port=args.base_execution_port,
        force=bool(args.force),
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
