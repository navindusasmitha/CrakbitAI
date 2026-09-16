from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from crakbit_chain.operations_v30 import (
    build_monitor_checkpoint,
    load_json,
    probe_monitor_sample,
)


def _atomic_write_json(path: Path, body: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the read-only Crakbit v0.30 resumable cluster monitor")
    parser.add_argument("--inventory", required=True, help="Signed v0.30 monitor inventory")
    parser.add_argument("--key", required=True, help="Dedicated monitoring evidence signing key")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--interval-seconds", type=float, default=30.0)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--maximum-height-spread", type=int, default=2)
    parser.add_argument("--target-duration-seconds", type=int, default=604800)
    parser.add_argument("--minimum-success-ratio", type=float, default=0.99)
    parser.add_argument("--max-samples", type=int, default=0, help="0 means continue until checkpoint target completes")
    args = parser.parse_args()

    if args.interval_seconds < 5:
        raise SystemExit("interval-seconds must be at least 5")
    if args.max_samples < 0:
        raise SystemExit("max-samples may not be negative")

    inventory = load_json(args.inventory)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = Path(args.checkpoint) if args.checkpoint else output_dir / "checkpoint.json"
    previous = load_json(checkpoint_path) if checkpoint_path.is_file() else None
    sequence = int(previous["manifest"]["sample_count"]) if previous else 0
    collected = 0

    print(json.dumps({
        "session_id": args.session_id,
        "resume": previous is not None,
        "starting_sample_count": sequence,
        "target_duration_seconds": args.target_duration_seconds,
        "minimum_success_ratio": args.minimum_success_ratio,
        "read_only": True,
        "production_mainnet_ready": False,
    }, indent=2))

    while True:
        if previous and previous["manifest"].get("checkpoint_complete") is True:
            print(json.dumps({"checkpoint_complete": True, "sample_count": previous["manifest"]["sample_count"]}, indent=2))
            return 0
        if args.max_samples and collected >= args.max_samples:
            return 0

        sequence += 1
        try:
            sample = probe_monitor_sample(
                signing_key_path=args.key,
                inventory=inventory,
                timeout_seconds=args.timeout_seconds,
                maximum_height_spread=args.maximum_height_spread,
            )
        except Exception as exc:
            print(json.dumps({"sample": sequence, "probe_error": str(exc), "production_mainnet_ready": False}), flush=True)
            time.sleep(args.interval_seconds)
            continue

        sample_path = output_dir / f"sample-{sequence:08d}.json"
        _atomic_write_json(sample_path, sample)
        checkpoint = build_monitor_checkpoint(
            signing_key_path=args.key,
            session_id=args.session_id,
            samples=[sample],
            target_duration_seconds=args.target_duration_seconds,
            minimum_success_ratio=args.minimum_success_ratio,
            previous_checkpoint=previous,
        )
        _atomic_write_json(checkpoint_path, checkpoint)
        previous = checkpoint
        collected += 1

        print(json.dumps({
            "sample": sequence,
            "sample_gate_satisfied": sample["manifest"]["sample_gate_satisfied"],
            "height_spread": sample["manifest"]["height_spread"],
            "checkpoint_duration_seconds": checkpoint["manifest"]["duration_seconds"],
            "checkpoint_success_ratio": checkpoint["manifest"]["success_ratio"],
            "checkpoint_complete": checkpoint["manifest"]["checkpoint_complete"],
            "production_mainnet_ready": False,
        }), flush=True)

        if checkpoint["manifest"]["checkpoint_complete"] is True:
            return 0
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
