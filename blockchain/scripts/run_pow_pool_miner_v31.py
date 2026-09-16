from __future__ import annotations

import argparse
import json
import socket
import time

from crakbit_chain.pow_v31 import PowConfig, parse_target, pow_hash


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Crakbit v0.31 native CPU pool miner")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3333)
    parser.add_argument("--address", required=True)
    parser.add_argument("--worker", default="cpu-01")
    parser.add_argument("--max-hashes-per-job", type=int, default=250000)
    parser.add_argument("--reconnect-seconds", type=float, default=2.0)
    args = parser.parse_args()

    request_id = 0
    total_hashes = 0
    started = time.perf_counter()
    while True:
        try:
            with socket.create_connection((args.host, args.port), timeout=10.0) as sock:
                file = sock.makefile("rwb")
                request_id += 1
                subscribed = send_request(file, request_id, "mining.subscribe", {})
                request_id += 1
                authorized = send_request(file, request_id, "mining.authorize", {"worker": args.worker, "address": args.address})
                job = authorized["job"]
                print(json.dumps({"connected": True, "protocol": subscribed["protocol"], "worker": args.worker, "height": job["height"], "job_id": job["job_id"]}))

                while True:
                    config = PowConfig(
                        scrypt_n=int(job["pow"]["scrypt_n"]),
                        scrypt_r=int(job["pow"]["scrypt_r"]),
                        scrypt_p=int(job["pow"]["scrypt_p"]),
                    )
                    block = job["block"]
                    block["header"]["extra_nonce"] = int(job["extra_nonce"])
                    share_target = parse_target(job["share_target"])
                    found_share = False
                    for nonce in range(args.max_hashes_per_job):
                        block["header"]["nonce"] = nonce
                        digest = pow_hash(block["header"], config)
                        total_hashes += 1
                        if int.from_bytes(digest, "big") <= share_target:
                            request_id += 1
                            result = send_request(
                                file,
                                request_id,
                                "mining.submit",
                                {"job_id": job["job_id"], "nonce": nonce},
                            )
                            elapsed = max(1e-9, time.perf_counter() - started)
                            print(json.dumps({"share": result, "hashrate_hps": total_hashes / elapsed}))
                            found_share = True
                            break
                    request_id += 1
                    job = send_request(file, request_id, "mining.get_job", {})
                    if not found_share:
                        elapsed = max(1e-9, time.perf_counter() - started)
                        print(json.dumps({"job_refresh": job["job_id"], "height": job["height"], "hashrate_hps": total_hashes / elapsed}))
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            print(json.dumps({"error": str(exc), "reconnecting_in_seconds": args.reconnect_seconds}))
            time.sleep(args.reconnect_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
