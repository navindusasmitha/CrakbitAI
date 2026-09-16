from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from . import cli_v32
from .mining_v33 import MiningV33Error, mine_via_rpc
from .pow_pool_v31 import PoolConfig
from .pow_pool_v33 import HardenedCrakbitPool, HardenedPoolLedger, PowPoolV33Error, VardiffPolicy, run_pool_server_v33
from .randomx_v33 import (
    RandomXV33Error,
    benchmark_randomx,
    candidate_vectors,
    randomx_key_height,
    randomx_runtime_info,
    randomx_selftest,
)
from .xmrig_v33 import build_xmrig_candidate_job, load_json, verify_xmrig_candidate_submit


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.33 CPU mining hardening, native RandomX candidate and pool vardiff/TLS tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    rx_info = sub.add_parser("pow-randomx-v33-info")
    rx_info.add_argument("--library", default=None)

    rx_self = sub.add_parser("pow-randomx-v33-selftest")
    rx_self.add_argument("--library", default=None)
    rx_self.add_argument("--mode", choices=["light", "fast"], default="light")

    rx_bench = sub.add_parser("pow-randomx-v33-benchmark")
    rx_bench.add_argument("--library", default=None)
    rx_bench.add_argument("--mode", choices=["light", "fast"], default="light")
    rx_bench.add_argument("--seconds", type=float, default=3.0)

    rx_key = sub.add_parser("pow-randomx-v33-key-height")
    rx_key.add_argument("--height", type=int, required=True)

    vectors = sub.add_parser("pow-randomx-v33-vectors")
    vectors.add_argument("--output", required=True)
    vectors.add_argument("--overwrite", action="store_true")

    mine = sub.add_parser("pow-mine-v33-rpc")
    mine.add_argument("--node-url", default="http://127.0.0.1:28443")
    mine.add_argument("--miner-address", required=True)
    mine.add_argument("--blocks", type=int, default=1)
    mine.add_argument("--threads", type=int, default=max(1, os.cpu_count() or 1))
    mine.add_argument("--max-hashes-per-thread", type=int, default=0)
    mine.add_argument("--timeout-seconds", type=float, default=20.0)

    pool = sub.add_parser("pow-pool-v33-run")
    pool.add_argument("--db", required=True)
    pool.add_argument("--node-url", default="http://127.0.0.1:28443")
    pool.add_argument("--pool-address", required=True)
    pool.add_argument("--host", default="127.0.0.1")
    pool.add_argument("--port", type=int, default=3333)
    pool.add_argument("--pplns-window-shares", type=int, default=1000)
    pool.add_argument("--initial-share-multiplier", type=int, default=256)
    pool.add_argument("--minimum-share-multiplier", type=int, default=4)
    pool.add_argument("--maximum-share-multiplier", type=int, default=1048576)
    pool.add_argument("--vardiff-target-seconds", type=float, default=15.0)
    pool.add_argument("--vardiff-retarget-shares", type=int, default=8)
    pool.add_argument("--stale-job-seconds", type=int, default=120)
    pool.add_argument("--tls-cert", default=None)
    pool.add_argument("--tls-key", default=None)
    pool.add_argument("--auth-token", default=None)
    pool.add_argument("--max-messages-per-second", type=int, default=25)

    stats = sub.add_parser("pow-pool-v33-stats")
    stats.add_argument("--db", required=True)

    xmrig_job = sub.add_parser("pow-xmrig-v33-job")
    xmrig_job.add_argument("--header", required=True, help="JSON file containing a header object")
    xmrig_job.add_argument("--job-id", required=True)
    xmrig_job.add_argument("--seed-hash", required=True)
    xmrig_job.add_argument("--full-target", required=True, help="256-bit target as hex")
    xmrig_job.add_argument("--output", required=True)
    xmrig_job.add_argument("--overwrite", action="store_true")

    xmrig_verify = sub.add_parser("pow-xmrig-v33-verify-submit")
    xmrig_verify.add_argument("--job", required=True)
    xmrig_verify.add_argument("--submit", required=True)
    xmrig_verify.add_argument("--library", default=None)
    xmrig_verify.add_argument("--mode", choices=["light", "fast"], default="light")

    return parser


def _save_json(path: str | Path, value: dict, *, overwrite: bool = False) -> None:
    target = Path(path)
    if target.exists() and not overwrite:
        raise ValueError(f"file exists: {target}; pass --overwrite to replace")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "pow-randomx-v33-info":
        print(json.dumps(randomx_runtime_info(args.library).to_dict(), indent=2))
        return 0

    if args.command == "pow-randomx-v33-selftest":
        result = randomx_selftest(library_path=args.library, mode=args.mode)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 2

    if args.command == "pow-randomx-v33-benchmark":
        print(json.dumps(benchmark_randomx(library_path=args.library, mode=args.mode, seconds=args.seconds), indent=2))
        return 0

    if args.command == "pow-randomx-v33-key-height":
        print(json.dumps({
            "height": args.height,
            "key_block_height": randomx_key_height(args.height),
            "consensus_enabled": False,
            "production_mainnet_ready": False,
        }, indent=2))
        return 0

    if args.command == "pow-randomx-v33-vectors":
        value = candidate_vectors()
        _save_json(args.output, value, overwrite=args.overwrite)
        print(json.dumps({"saved": args.output, "format": value["format"], "consensus_enabled": False}, indent=2))
        return 0

    if args.command == "pow-mine-v33-rpc":
        result = mine_via_rpc(
            node_url=args.node_url,
            miner_address=args.miner_address,
            blocks=args.blocks,
            threads=args.threads,
            max_hashes_per_thread=args.max_hashes_per_thread,
            timeout_seconds=args.timeout_seconds,
        )
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "pow-pool-v33-run":
        ledger = HardenedPoolLedger(args.db)
        vardiff = VardiffPolicy(
            target_share_seconds=args.vardiff_target_seconds,
            minimum_multiplier=args.minimum_share_multiplier,
            maximum_multiplier=args.maximum_share_multiplier,
            initial_multiplier=args.initial_share_multiplier,
            retarget_every_shares=args.vardiff_retarget_shares,
        )
        pool = HardenedCrakbitPool(
            PoolConfig(
                node_url=args.node_url,
                pool_address=args.pool_address,
                share_target_multiplier=args.initial_share_multiplier,
                pplns_window_shares=args.pplns_window_shares,
            ),
            ledger,
            vardiff=vardiff,
            stale_job_seconds=args.stale_job_seconds,
        )
        print(json.dumps({
            "pool_protocol": "crakbit-pool/2",
            "listen": f"{args.host}:{args.port}",
            "node_url": args.node_url,
            "pool_address": args.pool_address,
            "vardiff": {
                "target_share_seconds": vardiff.target_share_seconds,
                "initial_multiplier": vardiff.initial_multiplier,
                "minimum_multiplier": vardiff.minimum_multiplier,
                "maximum_multiplier": vardiff.maximum_multiplier,
                "retarget_every_shares": vardiff.retarget_every_shares,
            },
            "tls_enabled": bool(args.tls_cert and args.tls_key),
            "token_auth_enabled": args.auth_token is not None,
            "duplicate_share_protection": True,
            "stale_job_seconds": args.stale_job_seconds,
            "production_mainnet_ready": False,
        }, indent=2))
        try:
            asyncio.run(run_pool_server_v33(
                pool,
                host=args.host,
                port=args.port,
                tls_cert=args.tls_cert,
                tls_key=args.tls_key,
                auth_token=args.auth_token,
                max_messages_per_second=args.max_messages_per_second,
            ))
        finally:
            ledger.close()
        return 0

    if args.command == "pow-pool-v33-stats":
        ledger = HardenedPoolLedger(args.db)
        try:
            print(json.dumps({**ledger.stats(), "production_mainnet_ready": False}, indent=2))
        finally:
            ledger.close()
        return 0

    if args.command == "pow-xmrig-v33-job":
        header_data = load_json(args.header)
        header = header_data.get("header", header_data)
        if not isinstance(header, dict):
            raise ValueError("header JSON must contain an object")
        full_target_text = str(args.full_target).lower().removeprefix("0x")
        full_target = int(full_target_text, 16)
        record = build_xmrig_candidate_job(
            job_id=args.job_id,
            header=header,
            seed_hash=args.seed_hash,
            full_target=full_target,
        )
        _save_json(args.output, record, overwrite=args.overwrite)
        print(json.dumps({
            "saved": args.output,
            "algo": record["job"]["algo"],
            "consensus_enabled": False,
            "production_mainnet_ready": False,
        }, indent=2))
        return 0

    if args.command == "pow-xmrig-v33-verify-submit":
        result = verify_xmrig_candidate_submit(
            job_record=load_json(args.job),
            submit_payload=load_json(args.submit),
            library_path=args.library,
            mode=args.mode,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["accepted_candidate_share"] else 2

    raise ValueError("unknown v0.33 command")


def main() -> int:
    commands = {
        "pow-randomx-v33-info",
        "pow-randomx-v33-selftest",
        "pow-randomx-v33-benchmark",
        "pow-randomx-v33-key-height",
        "pow-randomx-v33-vectors",
        "pow-mine-v33-rpc",
        "pow-pool-v33-run",
        "pow-pool-v33-stats",
        "pow-xmrig-v33-job",
        "pow-xmrig-v33-verify-submit",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        try:
            return _run(sys.argv[1:])
        except (RandomXV33Error, MiningV33Error, PowPoolV33Error, ValueError, OSError) as exc:
            print(json.dumps({"error": str(exc), "production_mainnet_ready": False}), file=sys.stderr)
            return 2
    return cli_v32.main()


if __name__ == "__main__":
    raise SystemExit(main())
