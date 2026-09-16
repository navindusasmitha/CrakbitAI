from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .testnet_health import check_inventory


SOAK_FORMAT = "crakbit-testnet-soak-v1"


def summarize_soak(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if not samples:
        return {
            "format": SOAK_FORMAT,
            "sample_count": 0,
            "healthy_samples": 0,
            "unhealthy_samples": 0,
            "max_height_spread_observed": None,
            "all_samples_healthy": False,
        }
    spreads = [
        int(item["height_spread"])
        for item in samples
        if item.get("height_spread") is not None
    ]
    healthy = sum(1 for item in samples if item.get("healthy") is True)
    return {
        "format": SOAK_FORMAT,
        "sample_count": len(samples),
        "healthy_samples": healthy,
        "unhealthy_samples": len(samples) - healthy,
        "max_height_spread_observed": max(spreads) if spreads else None,
        "all_samples_healthy": healthy == len(samples),
    }


def collect_soak(
    inventory: dict[str, Any],
    *,
    duration_seconds: int,
    interval_seconds: int = 30,
    timeout_seconds: float = 5.0,
    max_height_spread: int = 2,
) -> dict[str, Any]:
    duration = int(duration_seconds)
    interval = int(interval_seconds)
    if duration <= 0:
        raise ValueError("duration_seconds must be positive")
    if interval <= 0:
        raise ValueError("interval_seconds must be positive")

    started_ms = int(time.time() * 1000)
    deadline = time.monotonic() + duration
    samples: list[dict[str, Any]] = []
    while True:
        sample = check_inventory(
            inventory,
            timeout_seconds=timeout_seconds,
            max_height_spread=max_height_spread,
        )
        samples.append(sample)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(interval, remaining))

    summary = summarize_soak(samples)
    return {
        "format": SOAK_FORMAT,
        "started_at_ms": started_ms,
        "finished_at_ms": int(time.time() * 1000),
        "requested_duration_seconds": duration,
        "interval_seconds": interval,
        "inventory_name": str(inventory.get("name", "Crakbit testnet")),
        "summary": summary,
        "samples": samples,
        "claims": {
            "independent_host_operation_verified": False,
            "production_mainnet_ready": False,
        },
        "note": (
            "This file records only the endpoints actually sampled by the operator. "
            "Independent-host operation is not inferred automatically from hostnames or URLs."
        ),
    }


def save_soak(result: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"soak evidence already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return target
