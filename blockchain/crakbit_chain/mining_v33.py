from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import httpx

from .pow_v31 import PowConfig, PowV31Error, parse_target, pow_hash


class MiningV33Error(RuntimeError):
    pass


@dataclass(frozen=True)
class MiningResult:
    block: dict[str, Any] | None
    hashes: int
    elapsed_seconds: float
    threads: int

    @property
    def hashrate_hps(self) -> float:
        return self.hashes / max(1e-9, self.elapsed_seconds)


def _config_from_template(template: dict[str, Any]) -> PowConfig:
    params = template.get("pow", {}) or {}
    try:
        return PowConfig(
            pow_algo=str(params["algo"]),
            scrypt_n=int(params["scrypt_n"]),
            scrypt_r=int(params["scrypt_r"]),
            scrypt_p=int(params["scrypt_p"]),
        )
    except Exception as exc:
        raise MiningV33Error("node template is missing valid v0.31/v0.32 scrypt parameters") from exc


def mine_block_multithread(
    block: dict[str, Any],
    config: PowConfig,
    *,
    threads: int | None = None,
    start_nonce: int = 0,
    max_hashes_per_thread: int = 0,
) -> MiningResult:
    """Mine a current Crakbit scrypt block template across CPU worker threads.

    hashlib.scrypt executes in native code, so the alpha can use multiple Python
    worker threads without serializing the expensive hash itself. Each worker scans
    a disjoint nonce sequence: start+worker, start+worker+threads, ...
    """

    threads = int(threads or max(1, os.cpu_count() or 1))
    if threads < 1 or threads > 256:
        raise MiningV33Error("threads must be between 1 and 256")
    start_nonce = int(start_nonce)
    if start_nonce < 0 or start_nonce > 0xFFFFFFFFFFFFFFFF:
        raise MiningV33Error("start nonce out of range")
    limit = int(max_hashes_per_thread)
    if limit < 0:
        raise MiningV33Error("max hashes per thread may not be negative")

    target = parse_target(block["header"]["target"])
    stop = threading.Event()
    lock = threading.Lock()
    winner: dict[str, Any] | None = None
    total_hashes = 0
    started = time.perf_counter()

    def worker(worker_id: int) -> tuple[dict[str, Any] | None, int]:
        nonlocal winner
        candidate = json.loads(json.dumps(block))
        nonce = start_nonce + worker_id
        hashes = 0
        while nonce <= 0xFFFFFFFFFFFFFFFF and not stop.is_set():
            candidate["header"]["nonce"] = nonce
            digest = pow_hash(candidate["header"], config)
            hashes += 1
            if int.from_bytes(digest, "big") <= target:
                with lock:
                    if winner is None:
                        winner = json.loads(json.dumps(candidate))
                        stop.set()
                return winner, hashes
            if limit and hashes >= limit:
                break
            nonce += threads
        return None, hashes

    with ThreadPoolExecutor(max_workers=threads, thread_name_prefix="crakbit-miner") as executor:
        futures = [executor.submit(worker, worker_id) for worker_id in range(threads)]
        for future in as_completed(futures):
            _, hashes = future.result()
            total_hashes += hashes
        # every future completes after stop is set or its local limit is reached

    elapsed = max(1e-9, time.perf_counter() - started)
    return MiningResult(block=winner, hashes=total_hashes, elapsed_seconds=elapsed, threads=threads)


def mine_via_rpc(
    *,
    node_url: str,
    miner_address: str,
    blocks: int = 1,
    threads: int | None = None,
    max_hashes_per_thread: int = 0,
    timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    if not node_url.startswith(("http://", "https://")):
        raise MiningV33Error("node URL must use http(s)")
    if not miner_address.startswith("crk1"):
        raise MiningV33Error("invalid miner payout address")
    blocks = int(blocks)
    if blocks < 1 or blocks > 10_000:
        raise MiningV33Error("blocks must be between 1 and 10000")

    accepted: list[dict[str, Any]] = []
    total_hashes = 0
    total_elapsed = 0.0
    with httpx.Client(timeout=float(timeout_seconds)) as client:
        for _ in range(blocks):
            response = client.post(
                node_url.rstrip("/") + "/pow/v1/getblocktemplate",
                json={"miner_address": miner_address, "message": "Crakbit multi-thread CPU miner v0.33"},
            )
            response.raise_for_status()
            template = response.json()
            config = _config_from_template(template)
            if config.pow_algo != "crakpow-scrypt-v1":
                raise MiningV33Error(
                    "v0.33 RPC multi-thread miner currently targets the active scrypt consensus path; "
                    "RandomX is integrated as an optional candidate benchmark, not active consensus"
                )
            result = mine_block_multithread(
                template["block"],
                config,
                threads=threads,
                max_hashes_per_thread=max_hashes_per_thread,
            )
            total_hashes += result.hashes
            total_elapsed += result.elapsed_seconds
            if result.block is None:
                accepted.append({
                    "height": int(template["height"]),
                    "found": False,
                    "hashes": result.hashes,
                    "elapsed_seconds": result.elapsed_seconds,
                })
                break
            submit = client.post(
                node_url.rstrip("/") + "/pow/v1/submitblock",
                json={"block": result.block},
            )
            submit.raise_for_status()
            payload = submit.json()
            accepted.append({
                "height": int(template["height"]),
                "found": True,
                "hashes": result.hashes,
                "elapsed_seconds": result.elapsed_seconds,
                "submit": payload,
            })

    return {
        "algorithm": "crakpow-scrypt-v1",
        "threads": int(threads or max(1, os.cpu_count() or 1)),
        "requested_blocks": blocks,
        "results": accepted,
        "total_hashes": total_hashes,
        "elapsed_seconds": total_elapsed,
        "hashrate_hps": total_hashes / max(1e-9, total_elapsed),
        "randomx_candidate_consensus_enabled": False,
        "production_mainnet_ready": False,
    }
