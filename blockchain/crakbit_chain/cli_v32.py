from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import cli_v31
from .crypto import KeyPair
from .pow_network_v32 import PowNetworkChain, PowNetworkV32Error
from .pow_v31 import COIN, PowConfig, parse_target, target_hex


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.32 native PoW P2P networking, fork tracking and highest-chainwork reorganization tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    key = sub.add_parser("pow-p2p-key-v32-new")
    key.add_argument("--output", required=True)
    key.add_argument("--overwrite", action="store_true")

    init = sub.add_parser("pow-network-v32-init")
    init.add_argument("--db", required=True)
    init.add_argument("--chain-id", default="crakbit-pow-devnet-v1")
    init.add_argument("--network", default="devnet")
    init.add_argument("--target-block-time", type=int, default=60)
    init.add_argument("--retarget-interval", type=int, default=20)
    init.add_argument("--initial-target", default=target_hex((1 << 248) - 1))
    init.add_argument("--initial-subsidy-crk", type=float, default=50.0)
    init.add_argument("--halving-interval", type=int, default=210000)
    init.add_argument("--coinbase-maturity", type=int, default=10)
    init.add_argument("--scrypt-n", type=int, default=1024)
    init.add_argument("--scrypt-r", type=int, default=8)
    init.add_argument("--scrypt-p", type=int, default=1)

    info = sub.add_parser("pow-network-v32-info")
    info.add_argument("--db", required=True)

    graph = sub.add_parser("pow-network-v32-graph")
    graph.add_argument("--db", required=True)
    graph.add_argument("--limit", type=int, default=200)

    locator = sub.add_parser("pow-network-v32-locator")
    locator.add_argument("--db", required=True)

    block_import = sub.add_parser("pow-network-v32-import-block")
    block_import.add_argument("--db", required=True)
    block_import.add_argument("--block", required=True)

    node = sub.add_parser("pow-node-v32-run")
    node.add_argument("--db", required=True)
    node.add_argument("--network-key", required=True, help="dedicated P2P identity key; do not reuse a wallet/mining key")
    node.add_argument("--rpc-host", default="127.0.0.1")
    node.add_argument("--rpc-port", type=int, default=28443)
    node.add_argument("--p2p-host", default="0.0.0.0")
    node.add_argument("--p2p-port", type=int, default=28444)
    node.add_argument("--advertise", default=None, help="public host:port announced to peers")
    node.add_argument("--peer", action="append", default=[], help="static seed peer host:port; repeatable")
    node.add_argument("--max-peers", type=int, default=32)

    return parser


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "pow-p2p-key-v32-new":
        path = Path(args.output)
        if path.exists() and not args.overwrite:
            raise PowNetworkV32Error("P2P identity file exists; pass --overwrite to replace")
        key = KeyPair.generate()
        key.save(path)
        print(json.dumps({
            "saved": str(path),
            "public_address_label": key.address,
            "warning": "dedicated P2P identity only; keep the private key secret and do not reuse wallet/pool keys",
            "production_mainnet_ready": False,
        }, indent=2))
        return 0

    if args.command == "pow-network-v32-init":
        path = Path(args.db)
        if path.exists():
            raise PowNetworkV32Error("database already exists")
        config = PowConfig(
            chain_id=args.chain_id,
            network=args.network,
            target_block_time_seconds=args.target_block_time,
            retarget_interval=args.retarget_interval,
            initial_target=parse_target(args.initial_target),
            initial_subsidy=int(round(float(args.initial_subsidy_crk) * COIN)),
            halving_interval=args.halving_interval,
            coinbase_maturity=args.coinbase_maturity,
            scrypt_n=args.scrypt_n,
            scrypt_r=args.scrypt_r,
            scrypt_p=args.scrypt_p,
        )
        chain = PowNetworkChain(path, config, create=True)
        try:
            print(json.dumps({
                "created": str(path),
                "config": config.to_dict(),
                "genesis_hash": chain.genesis_hash,
                "p2p_protocol": "crakbit-p2p/1",
                "fork_choice": "highest-cumulative-work",
                "production_mainnet_ready": False,
            }, indent=2))
        finally:
            chain.close()
        return 0

    if args.command == "pow-network-v32-info":
        chain = PowNetworkChain(args.db)
        try:
            print(json.dumps(chain.info(), indent=2))
        finally:
            chain.close()
        return 0

    if args.command == "pow-network-v32-graph":
        chain = PowNetworkChain(args.db)
        try:
            print(json.dumps({"blocks": chain.graph(limit=args.limit), "production_mainnet_ready": False}, indent=2))
        finally:
            chain.close()
        return 0

    if args.command == "pow-network-v32-locator":
        chain = PowNetworkChain(args.db)
        try:
            print(json.dumps({"locator": chain.block_locator(), "production_mainnet_ready": False}, indent=2))
        finally:
            chain.close()
        return 0

    if args.command == "pow-network-v32-import-block":
        block = json.loads(Path(args.block).read_text(encoding="utf-8"))
        if isinstance(block, dict) and isinstance(block.get("block"), dict):
            block = block["block"]
        if not isinstance(block, dict):
            raise PowNetworkV32Error("block file must contain a block object")
        chain = PowNetworkChain(args.db)
        try:
            print(json.dumps(chain.accept_block(block, source="file-import"), indent=2))
        finally:
            chain.close()
        return 0

    if args.command == "pow-node-v32-run":
        import uvicorn
        from .pow_node_v32 import create_app

        app = create_app(
            args.db,
            network_key_path=args.network_key,
            p2p_host=args.p2p_host,
            p2p_port=args.p2p_port,
            advertised_endpoint=args.advertise,
            peers=args.peer,
            max_peers=args.max_peers,
        )
        print(json.dumps({
            "rpc": f"http://{args.rpc_host}:{args.rpc_port}",
            "p2p_listen": f"{args.p2p_host}:{args.p2p_port}",
            "advertised_endpoint": args.advertise,
            "seed_peers": args.peer,
            "consensus": "native-proof-of-work",
            "fork_choice": "highest-cumulative-work",
            "production_mainnet_ready": False,
        }, indent=2))
        uvicorn.run(app, host=args.rpc_host, port=args.rpc_port, log_level="info")
        return 0

    raise PowNetworkV32Error("unknown v0.32 command")


def main() -> int:
    commands = {
        "pow-p2p-key-v32-new",
        "pow-network-v32-init",
        "pow-network-v32-info",
        "pow-network-v32-graph",
        "pow-network-v32-locator",
        "pow-network-v32-import-block",
        "pow-node-v32-run",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        try:
            return _run(sys.argv[1:])
        except Exception as exc:
            print(json.dumps({"error": str(exc), "production_mainnet_ready": False}), file=sys.stderr)
            return 2
    return cli_v31.main()


if __name__ == "__main__":
    raise SystemExit(main())
