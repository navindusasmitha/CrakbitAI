from __future__ import annotations

import argparse
import json
import time

from crakbit_chain.pow_campaign_v36 import CampaignLogV36


def main() -> int:
    parser = argparse.ArgumentParser(description="Crakbit v0.36 real-time public PoW campaign collector")
    parser.add_argument("--key", required=True, help="dedicated evidence-signing key")
    parser.add_argument("--log", required=True, help="append-only JSONL output")
    parser.add_argument("--rpc-url", action="append", required=True)
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--duration-seconds", type=int, default=24 * 3600)
    parser.add_argument("--timeout-seconds", type=float, default=8.0)
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    interval = max(10, int(args.interval_seconds))
    duration = max(0, int(args.duration_seconds))
    if duration == 0:
        raise SystemExit("--duration-seconds must be positive")

    log = CampaignLogV36(args.log, args.key)
    started = time.time()
    sequence = 0
    try:
        while True:
            sequence += 1
            result = log.probe_and_append(
                args.rpc_url,
                timeout_seconds=args.timeout_seconds,
                label=args.label or f"sample-{sequence}",
            )
            print(json.dumps({
                "sequence": sequence,
                "elapsed_seconds": int(time.time() - started),
                **result,
            }))
            if time.time() - started >= duration:
                return 0
            sleep_for = min(interval, max(0.0, duration - (time.time() - started)))
            time.sleep(sleep_for)
    except KeyboardInterrupt:
        print(json.dumps({"stopped": True, "sequence": sequence, "log": args.log}))
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
