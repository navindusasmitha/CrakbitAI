from __future__ import annotations

import argparse
import json
from pathlib import Path

from crakbit_chain.crash_matrix import run_crash_matrix
from crakbit_chain.crypto import KeyPair
from crakbit_chain.genesis import Genesis


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run isolated Crakbit v0.16 external FinalizeBlock/Commit crash-replay checks"
    )
    parser.add_argument("--genesis", required=True)
    parser.add_argument("--key", required=True, help="A wallet key funded by the supplied test genesis")
    parser.add_argument("--work-dir", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    result = run_crash_matrix(
        genesis=Genesis.load(args.genesis),
        funded_key=KeyPair.load(args.key),
        root=args.work_dir or None,
    )
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
