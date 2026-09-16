from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from . import cli_v30
from .crypto import KeyPair
from .pow_pool_v31 import CrakbitPool, PoolConfig, PoolLedger, run_pool_server
from .pow_v31 import COIN, PowChain, PowConfig, PowV31Error, mine_block, parse_target, target_hex


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.31 native Proof-of-Work UTXO devnet, CPU miner and mining-pool tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    wallet = sub.add_parser("pow-wallet-v31-new")
    wallet.add_argument("--output", required=True)
    wallet.add_argument("--overwrite", action="store_true")

    init = sub.add_parser("pow-chain-v31-init")
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

    info = sub.add_parser("pow-chain-v31-info")
    info.add_argument("--db", required=True)

    balance = sub.add_parser("pow-balance-v31")
    balance.add_argument("--db", required=True)
    balance.add_argument("--address", required=True)

    template = sub.add_parser("pow-template-v31")
    template.add_argument("--db", required=True)
    template.add_argument("--miner-address", required=True)

    mine = sub.add_parser("pow-mine-v31")
    mine.add_argument("--db", required=True)
    mine.add_argument("--miner-address", required=True)
    mine.add_argument("--blocks", type=int, default=1)
    mine.add_argument("--start-nonce", type=int, default=0)
    mine.add_argument("--max-hashes", type=int, default=0, help="0 means unlimited per block")
    mine.add_argument("--extra-nonce", type=int, default=0)

    send = sub.add_parser("pow-send-v31")
    send.add_argument("--db", required=True)
    send.add_argument("--wallet", required=True)
    send.add_argument("--to", required=True)
    send.add_argument("--amount-crk", type=float, required=True)
    send.add_argument("--fee-crk", type=float, default=0.0001)

    submit_tx = sub.add_parser("pow-submit-tx-v31")
    submit_tx.add_argument("--db", required=True)
    submit_tx.add_argument("--transaction", required=True)

    node = sub.add_parser("pow-node-v31-run")
    node.add_argument("--db", required=True)
    node.add_argument("--host", default="127.0.0.1")
    node.add_argument("--port", type=int, default=28443)

    pool = sub.add_parser("pow-pool-v31-run")
    pool.add_argument("--db", required=True, help="pool accounting SQLite database")
    pool.add_argument("--node-url", default="http://127.0.0.1:28443")
    pool.add_argument("--pool-address", required=True)
    pool.add_argument("--host", default="127.0.0.1")
    pool.add_argument("--port", type=int, default=3333)
    pool.add_argument("--share-target-multiplier", type=int, default=256)
    pool.add_argument("--pplns-window-shares", type=int, default=1000)

    pool_balances = sub.add_parser("pow-pool-v31-balances")
    pool_balances.add_argument("--db", required=True)

    return parser


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "pow-wallet-v31-new":
        path = Path(args.output)
        if path.exists() and not args.overwrite:
            raise PowV31Error("wallet file exists; pass --overwrite to replace")
        key = KeyPair.generate()
        key.save(path)
        print(json.dumps({"saved": str(path), "address": key.address, "warning": "keep this private key file secret; never commit it", "production_mainnet_ready": False}, indent=2))
        return 0

    if args.command == "pow-chain-v31-init":
        path = Path(args.db)
        if path.exists():
            raise PowV31Error("database already exists")
        subsidy = int(round(float(args.initial_subsidy_crk) * COIN))
        config = PowConfig(
            chain_id=args.chain_id,
            network=args.network,
            target_block_time_seconds=args.target_block_time,
            retarget_interval=args.retarget_interval,
            initial_target=parse_target(args.initial_target),
            initial_subsidy=subsidy,
            halving_interval=args.halving_interval,
            coinbase_maturity=args.coinbase_maturity,
            scrypt_n=args.scrypt_n,
            scrypt_r=args.scrypt_r,
            scrypt_p=args.scrypt_p,
        )
        chain = PowChain(path, config, create=True)
        try:
            print(json.dumps({"created": str(path), "config": config.to_dict(), "genesis_hash": chain.tip()["block_hash"], "production_mainnet_ready": False}, indent=2))
        finally:
            chain.close()
        return 0

    if args.command == "pow-chain-v31-info":
        chain = PowChain(args.db)
        try:
            print(json.dumps(chain.info(), indent=2))
        finally:
            chain.close()
        return 0

    if args.command == "pow-balance-v31":
        chain = PowChain(args.db)
        try:
            result = chain.balance(args.address)
            print(json.dumps({"address": args.address, **result, "confirmed_crk": result["confirmed"] / COIN, "immature_crk": result["immature"] / COIN, "production_mainnet_ready": False}, indent=2))
        finally:
            chain.close()
        return 0

    if args.command == "pow-template-v31":
        chain = PowChain(args.db)
        try:
            print(json.dumps(chain.get_block_template(args.miner_address), indent=2))
        finally:
            chain.close()
        return 0

    if args.command == "pow-mine-v31":
        if args.blocks <= 0:
            raise PowV31Error("--blocks must be positive")
        chain = PowChain(args.db)
        try:
            total_hashes = 0
            started = time.perf_counter()
            results = []
            for index in range(args.blocks):
                template = chain.get_block_template(args.miner_address)
                block = template["block"]
                block["header"]["extra_nonce"] = (int(args.extra_nonce) + index) & 0xFFFFFFFFFFFFFFFF
                found, hashes = mine_block(
                    block,
                    chain.config,
                    start_nonce=args.start_nonce,
                    max_hashes=None if args.max_hashes == 0 else args.max_hashes,
                )
                total_hashes += hashes
                if found is None:
                    results.append({"height": template["height"], "found": False, "hashes": hashes})
                    break
                accepted = chain.submit_block(found)
                results.append({"height": accepted["height"], "found": True, "hashes": hashes, "block_hash": accepted["block_hash"]})
            elapsed = max(1e-9, time.perf_counter() - started)
            print(json.dumps({"results": results, "total_hashes": total_hashes, "elapsed_seconds": elapsed, "hashrate_hps": total_hashes / elapsed, "pow_algo": chain.config.pow_algo, "production_mainnet_ready": False}, indent=2))
        finally:
            chain.close()
        return 0

    if args.command == "pow-send-v31":
        key = KeyPair.load(args.wallet)
        chain = PowChain(args.db)
        try:
            tx = chain.create_payment(
                key,
                args.to,
                int(round(args.amount_crk * COIN)),
                int(round(args.fee_crk * COIN)),
            )
            result = chain.submit_transaction(tx)
            print(json.dumps({"transaction": tx, **result, "production_mainnet_ready": False}, indent=2))
        finally:
            chain.close()
        return 0

    if args.command == "pow-submit-tx-v31":
        tx = json.loads(Path(args.transaction).read_text(encoding="utf-8"))
        chain = PowChain(args.db)
        try:
            print(json.dumps(chain.submit_transaction(tx), indent=2))
        finally:
            chain.close()
        return 0

    if args.command == "pow-node-v31-run":
        import uvicorn
        from .pow_node_v31 import create_app
        uvicorn.run(create_app(args.db), host=args.host, port=args.port, log_level="info")
        return 0

    if args.command == "pow-pool-v31-run":
        ledger = PoolLedger(args.db)
        pool = CrakbitPool(
            PoolConfig(
                node_url=args.node_url,
                pool_address=args.pool_address,
                share_target_multiplier=args.share_target_multiplier,
                pplns_window_shares=args.pplns_window_shares,
            ),
            ledger,
        )
        print(json.dumps({"pool_protocol": "crakbit-pool/1", "listen": f"{args.host}:{args.port}", "node_url": args.node_url, "pool_address": args.pool_address, "note": "native Crakbit JSON-line pool protocol; not yet XMRig/RandomX compatible", "production_mainnet_ready": False}, indent=2))
        try:
            asyncio.run(run_pool_server(pool, host=args.host, port=args.port))
        finally:
            ledger.close()
        return 0

    if args.command == "pow-pool-v31-balances":
        ledger = PoolLedger(args.db)
        try:
            balances = ledger.balances()
            print(json.dumps({"balances": balances, "balances_crk": {k: v / COIN for k, v in balances.items()}, "auto_payout_enabled": False, "production_mainnet_ready": False}, indent=2))
        finally:
            ledger.close()
        return 0

    raise PowV31Error("unknown command")


def main() -> int:
    commands = {
        "pow-wallet-v31-new", "pow-chain-v31-init", "pow-chain-v31-info", "pow-balance-v31",
        "pow-template-v31", "pow-mine-v31", "pow-send-v31", "pow-submit-tx-v31",
        "pow-node-v31-run", "pow-pool-v31-run", "pow-pool-v31-balances",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        try:
            return _run(sys.argv[1:])
        except Exception as exc:
            print(json.dumps({"error": str(exc), "production_mainnet_ready": False}), file=sys.stderr)
            return 2
    return cli_v30.main()


if __name__ == "__main__":
    raise SystemExit(main())
