from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass
class Sample:
    timestamp: float
    nodes: list[dict]


def fetch_status(url: str, token: str | None, timeout: float) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    started = time.monotonic()
    try:
        response = httpx.get(f"{url.rstrip('/')}/status", timeout=timeout, headers=headers)
        response.raise_for_status()
        data = response.json()
        return {
            "url": url,
            "ok": True,
            "latency_ms": round((time.monotonic() - started) * 1000, 2),
            "height": int(data.get("height", 0)),
            "last_hash": str(data.get("last_hash", "")),
            "round": int(data.get("consensus_round", 0)),
            "healthy_validator_views": int(data.get("healthy_validator_views", 0)),
        }
    except Exception as exc:
        return {
            "url": url,
            "ok": False,
            "latency_ms": round((time.monotonic() - started) * 1000, 2),
            "error": f"{type(exc).__name__}: {str(exc)[:180]}",
        }


def analyze(nodes: list[dict]) -> dict:
    healthy = [node for node in nodes if node.get("ok")]
    by_height: dict[int, set[str]] = {}
    for node in healthy:
        by_height.setdefault(int(node["height"]), set()).add(str(node["last_hash"]))
    divergence = {
        height: sorted(hashes)
        for height, hashes in by_height.items()
        if len(hashes) > 1
    }
    heights = [int(node["height"]) for node in healthy]
    return {
        "healthy_nodes": len(healthy),
        "total_nodes": len(nodes),
        "height_min": min(heights) if heights else None,
        "height_max": max(heights) if heights else None,
        "height_spread": (max(heights) - min(heights)) if heights else None,
        "same_height_hash_divergence": divergence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Crakbit Chain multi-node soak monitor")
    parser.add_argument("--node", action="append", required=True, help="Validator/public RPC base URL; repeat for each node")
    parser.add_argument("--duration-seconds", type=int, default=3600)
    parser.add_argument("--interval-seconds", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--monitoring-token", default=None)
    parser.add_argument("--output", default="runtime/soak-results.jsonl")
    parser.add_argument("--fail-on-divergence", action="store_true")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + max(1, args.duration_seconds)
    divergence_seen = False
    samples = 0

    with output.open("a", encoding="utf-8") as handle:
        while time.monotonic() < deadline:
            nodes = [fetch_status(url, args.monitoring_token, args.timeout) for url in args.node]
            analysis = analyze(nodes)
            divergence_seen = divergence_seen or bool(analysis["same_height_hash_divergence"])
            record = {
                "timestamp_ms": int(time.time() * 1000),
                "nodes": nodes,
                "analysis": analysis,
            }
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")
            handle.flush()
            samples += 1
            print(json.dumps(record))
            time.sleep(max(0.1, args.interval_seconds))

    summary = {
        "samples": samples,
        "divergence_seen": divergence_seen,
        "output": str(output),
    }
    print(json.dumps(summary, indent=2))
    return 2 if args.fail_on_divergence and divergence_seen else 0


if __name__ == "__main__":
    raise SystemExit(main())
