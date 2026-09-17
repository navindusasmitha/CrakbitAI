from __future__ import annotations

import argparse
import json
import os
import socket
import ssl
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from crakbit_chain.pow_v31 import PowConfig, parse_target, pow_hash

MAX_NONCE = 0xFFFFFFFFFFFFFFFF


def send_request(file, request_id: int, method: str, params: dict) -> dict:
    file.write((json.dumps({"id": request_id, "method": method, "params": params}, separators=(",", ":")) + "\n").encode())
    file.flush()
    line = file.readline()
    if not line:
        raise RuntimeError("pool disconnected")
    response = json.loads(line.decode())
    if response.get("error"):
        raise RuntimeError(str(response["error"]))
    return response["result"]


def mine_share(
    job: dict,
    threads: int,
    max_hashes_per_thread: int,
    start_nonce: int = 0,
) -> tuple[int | None, int, float, int]:
    config = PowConfig(
        pow_algo=str(job["pow"]["algo"]),
        scrypt_n=int(job["pow"]["scrypt_n"]),
        scrypt_r=int(job["pow"]["scrypt_r"]),
        scrypt_p=int(job["pow"]["scrypt_p"]),
    )
    if config.pow_algo != "crakpow-scrypt-v1":
        raise RuntimeError("v0.33 native pool miner currently supports the active scrypt consensus path")
    if start_nonce < 0 or start_nonce > MAX_NONCE:
        raise RuntimeError("nonce cursor is outside uint64 range")

    share_target = parse_target(job["share_target"])
    stop = threading.Event()
    winner_lock = threading.Lock()
    winner: int | None = None
    started = time.perf_counter()

    def worker(worker_id: int) -> tuple[int | None, int, int]:
        nonlocal winner
        block = json.loads(json.dumps(job["block"]))
        block["header"]["extra_nonce"] = int(job["extra_nonce"])
        nonce = start_nonce + worker_id
        hashes = 0
        last_nonce = start_nonce - 1

        while not stop.is_set() and nonce <= MAX_NONCE:
            last_nonce = nonce
            block["header"]["nonce"] = nonce
            digest = pow_hash(block["header"], config)
            hashes += 1
            if int.from_bytes(digest, "big") <= share_target:
                with winner_lock:
                    if winner is None:
                        winner = nonce
                        stop.set()
                return winner, hashes, last_nonce
            if max_hashes_per_thread and hashes >= max_hashes_per_thread:
                break
            nonce += threads
        return None, hashes, last_nonce

    total_hashes = 0
    highest_nonce = start_nonce - 1
    with ThreadPoolExecutor(max_workers=threads, thread_name_prefix="crakbit-pool-miner") as executor:
        futures = [executor.submit(worker, worker_id) for worker_id in range(threads)]
        for future in as_completed(futures):
            _, hashes, last_nonce = future.result()
            total_hashes += hashes
            highest_nonce = max(highest_nonce, last_nonce)

    elapsed = max(1e-9, time.perf_counter() - started)
    next_nonce = highest_nonce + 1
    return winner, total_hashes, elapsed, next_nonce


def main() -> int:
    parser = argparse.ArgumentParser(description="Crakbit v0.33 multi-thread native CPU pool miner")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3333)
    parser.add_argument("--address", required=True)
    parser.add_argument("--worker", default="cpu-01")
    parser.add_argument("--threads", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--max-hashes-per-thread", type=int, default=250000)
    parser.add_argument("--reconnect-seconds", type=float, default=2.0)
    parser.add_argument("--token", default=None)
    parser.add_argument("--tls", action="store_true")
    parser.add_argument("--ca-file", default=None)
    parser.add_argument("--insecure-skip-verify", action="store_true")
    args = parser.parse_args()

    if args.threads < 1 or args.threads > 256:
        raise SystemExit("--threads must be 1..256")
    if args.insecure_skip_verify and not args.tls:
        raise SystemExit("--insecure-skip-verify requires --tls")

    request_id = 0
    total_hashes = 0
    total_elapsed = 0.0
    while True:
        try:
            raw = socket.create_connection((args.host, args.port), timeout=10.0)
            if args.tls:
                context = ssl.create_default_context(cafile=args.ca_file)
                if args.insecure_skip_verify:
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                sock = context.wrap_socket(raw, server_hostname=None if args.insecure_skip_verify else args.host)
            else:
                sock = raw
            with sock:
                file = sock.makefile("rwb")
                request_id += 1
                subscribed = send_request(file, request_id, "mining.subscribe", {})
                request_id += 1
                authorize_params = {"worker": args.worker, "address": args.address}
                if args.token is not None:
                    authorize_params["token"] = args.token
                authorized = send_request(file, request_id, "mining.authorize", authorize_params)
                job = authorized["job"]
                active_job_id = str(job["job_id"])
                nonce_cursor = 0
                print(json.dumps({
                    "connected": True,
                    "protocol": subscribed["protocol"],
                    "worker": args.worker,
                    "threads": args.threads,
                    "height": job["height"],
                    "job_id": job["job_id"],
                    "share_multiplier": job.get("share_multiplier"),
                    "tls": bool(args.tls),
                }))

                while True:
                    nonce, hashes, elapsed, next_nonce = mine_share(
                        job,
                        args.threads,
                        args.max_hashes_per_thread,
                        nonce_cursor,
                    )
                    total_hashes += hashes
                    total_elapsed += elapsed
                    if nonce is not None:
                        request_id += 1
                        result = send_request(
                            file,
                            request_id,
                            "mining.submit",
                            {"job_id": job["job_id"], "nonce": nonce},
                        )
                        print(json.dumps({
                            "share": result,
                            "job_hashes": hashes,
                            "job_hashrate_hps": hashes / elapsed,
                            "total_hashrate_hps": total_hashes / max(1e-9, total_elapsed),
                        }))

                    request_id += 1
                    next_job = send_request(file, request_id, "mining.get_job", {})
                    next_job_id = str(next_job["job_id"])
                    if next_job_id == active_job_id:
                        if next_nonce > MAX_NONCE:
                            raise RuntimeError("nonce space exhausted; reconnecting for a fresh extra_nonce")
                        nonce_cursor = next_nonce
                    else:
                        active_job_id = next_job_id
                        nonce_cursor = 0
                    job = next_job

                    if nonce is None:
                        print(json.dumps({
                            "job_refresh": job["job_id"],
                            "height": job["height"],
                            "share_multiplier": job.get("share_multiplier"),
                            "nonce_cursor": nonce_cursor,
                            "total_hashrate_hps": total_hashes / max(1e-9, total_elapsed),
                        }))
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            print(json.dumps({"error": str(exc), "reconnecting_in_seconds": args.reconnect_seconds}))
            time.sleep(args.reconnect_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
