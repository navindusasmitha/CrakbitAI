from __future__ import annotations

import argparse
import json

from crakbit_chain.fault_campaign import load_json, run_campaign, save_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Plan or explicitly execute a controlled Crakbit public-testnet fault campaign"
    )
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--execute", action="store_true", help="Actually run operator-supplied commands; default is dry-run")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--health-timeout", type=float, default=5.0)
    parser.add_argument("--max-height-spread", type=int, default=2)
    parser.add_argument("--command-timeout", type=float, default=120.0)
    args = parser.parse_args()

    result = run_campaign(
        inventory=load_json(args.inventory),
        spec=load_json(args.campaign),
        execute=args.execute,
        health_timeout_seconds=args.health_timeout,
        max_height_spread=args.max_height_spread,
        command_timeout_seconds=args.command_timeout,
    )
    target = save_json(result, args.output, overwrite=args.overwrite)
    print(json.dumps({"saved": str(target), "execute": args.execute, "steps": len(result.get("steps", []))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
