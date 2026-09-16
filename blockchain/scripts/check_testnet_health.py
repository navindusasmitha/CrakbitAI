from __future__ import annotations

import argparse
import json
from pathlib import Path

from crakbit_chain.testnet_health import check_inventory, load_inventory


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check a Crakbit multi-host CometBFT public-testnet inventory"
    )
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--max-height-spread", type=int, default=2)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    result = check_inventory(
        load_inventory(args.inventory),
        timeout_seconds=args.timeout,
        max_height_spread=args.max_height_spread,
    )
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["healthy"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
