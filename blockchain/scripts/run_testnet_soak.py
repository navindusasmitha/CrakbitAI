from __future__ import annotations

import argparse
import json

from crakbit_chain.soak_evidence import collect_soak, save_soak
from crakbit_chain.testnet_health import load_inventory


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect repeatable Crakbit public-testnet health/soak evidence")
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--duration-seconds", type=int, default=300)
    parser.add_argument("--interval-seconds", type=int, default=30)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--max-height-spread", type=int, default=2)
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    result = collect_soak(
        load_inventory(args.inventory),
        duration_seconds=args.duration_seconds,
        interval_seconds=args.interval_seconds,
        timeout_seconds=args.timeout_seconds,
        max_height_spread=args.max_height_spread,
    )
    target = save_soak(result, args.output, overwrite=bool(args.overwrite))
    print(json.dumps({"saved": str(target), "summary": result["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
