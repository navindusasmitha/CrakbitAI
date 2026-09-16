from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Crakbit soak-test JSONL evidence")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    path = Path(args.input)
    samples = 0
    divergence_samples = 0
    unhealthy_samples = 0
    max_height_spread = 0
    latency_values: list[float] = []
    node_failures: dict[str, int] = defaultdict(int)
    first_timestamp = None
    last_timestamp = None

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid JSON at line {line_number}: {exc}") from exc
            samples += 1
            timestamp = int(record.get("timestamp_ms", 0))
            first_timestamp = timestamp if first_timestamp is None else min(first_timestamp, timestamp)
            last_timestamp = timestamp if last_timestamp is None else max(last_timestamp, timestamp)
            analysis = record.get("analysis", {})
            if analysis.get("same_height_hash_divergence"):
                divergence_samples += 1
            healthy = int(analysis.get("healthy_nodes", 0))
            total = int(analysis.get("total_nodes", 0))
            if healthy < total:
                unhealthy_samples += 1
            spread = analysis.get("height_spread")
            if spread is not None:
                max_height_spread = max(max_height_spread, int(spread))
            for node in record.get("nodes", []):
                url = str(node.get("url", "unknown"))
                if node.get("ok"):
                    latency_values.append(float(node.get("latency_ms", 0.0)))
                else:
                    node_failures[url] += 1

    if samples == 0:
        raise SystemExit("no soak samples found")
    latency_values.sort()
    p95 = latency_values[min(len(latency_values) - 1, int(len(latency_values) * 0.95))] if latency_values else None
    summary = {
        "format": "crakbit-soak-summary/1",
        "input": str(path),
        "samples": samples,
        "first_timestamp_ms": first_timestamp,
        "last_timestamp_ms": last_timestamp,
        "duration_ms": (last_timestamp - first_timestamp) if first_timestamp is not None and last_timestamp is not None else 0,
        "divergence_samples": divergence_samples,
        "divergence_free": divergence_samples == 0,
        "samples_with_unreachable_nodes": unhealthy_samples,
        "max_height_spread": max_height_spread,
        "latency_ms": {
            "observations": len(latency_values),
            "max": max(latency_values) if latency_values else None,
            "average": round(sum(latency_values) / len(latency_values), 2) if latency_values else None,
            "p95_approx": p95,
        },
        "node_failure_counts": dict(sorted(node_failures.items())),
        "interpretation": "operational evidence only; not a formal consensus-safety proof",
    }
    encoded = json.dumps(summary, indent=2) + "\n"
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
