from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx


def _clean(value: str) -> str:
    return str(value or "").rstrip("/")


def evaluate_health(records: list[dict[str, Any]], *, max_height_spread: int = 2) -> dict[str, Any]:
    heights = [int(item["height"]) for item in records if item.get("reachable") and item.get("height") is not None]
    spread = max(heights) - min(heights) if heights else None
    unhealthy = [
        item["name"]
        for item in records
        if not item.get("reachable") or item.get("catching_up") is True
    ]
    if spread is not None and spread > int(max_height_spread):
        unhealthy.extend(
            item["name"] for item in records if item.get("reachable") and item["name"] not in unhealthy
        )
    return {
        "healthy": bool(records) and not unhealthy,
        "validator_count": len(records),
        "reachable": sum(1 for item in records if item.get("reachable")),
        "height_min": min(heights) if heights else None,
        "height_max": max(heights) if heights else None,
        "height_spread": spread,
        "max_height_spread": int(max_height_spread),
        "unhealthy": sorted(set(unhealthy)),
        "validators": records,
    }


def check_inventory(
    inventory: dict[str, Any],
    *,
    timeout_seconds: float = 5.0,
    max_height_spread: int = 2,
) -> dict[str, Any]:
    validators = inventory.get("validators")
    if not isinstance(validators, list) or not validators:
        raise ValueError("inventory must contain a non-empty validators list")

    records: list[dict[str, Any]] = []
    with httpx.Client(timeout=timeout_seconds) as client:
        for index, item in enumerate(validators):
            name = str(item.get("name") or f"validator-{index + 1}")
            rpc = _clean(str(item.get("comet_rpc", "")))
            if not rpc.startswith(("http://", "https://")):
                records.append(
                    {
                        "name": name,
                        "reachable": False,
                        "error": "missing or invalid comet_rpc",
                    }
                )
                continue
            try:
                response = client.get(f"{rpc}/status")
                response.raise_for_status()
                body = response.json()
                result = body.get("result", body)
                sync = result.get("sync_info", {}) if isinstance(result, dict) else {}
                node = result.get("node_info", {}) if isinstance(result, dict) else {}
                record: dict[str, Any] = {
                    "name": name,
                    "reachable": True,
                    "comet_rpc": rpc,
                    "node_id": node.get("id"),
                    "network": node.get("network"),
                    "height": int(sync.get("latest_block_height", 0) or 0),
                    "catching_up": bool(sync.get("catching_up", False)),
                    "latest_block_hash": sync.get("latest_block_hash"),
                }
                gateway = _clean(str(item.get("gateway", "")))
                if gateway:
                    try:
                        gateway_response = client.get(f"{gateway}/api/network")
                        gateway_response.raise_for_status()
                        network = gateway_response.json()
                        record["gateway_ok"] = True
                        record["application_height"] = int(network.get("height", 0) or 0)
                        record["application_hash"] = network.get("application_hash")
                    except Exception as exc:
                        record["gateway_ok"] = False
                        record["gateway_error"] = f"{type(exc).__name__}: {exc}"
                records.append(record)
            except Exception as exc:
                records.append(
                    {
                        "name": name,
                        "reachable": False,
                        "comet_rpc": rpc,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

    result = evaluate_health(records, max_height_spread=max_height_spread)
    result.update(
        {
            "format": "crakbit-testnet-health-v1",
            "checked_at_ms": int(time.time() * 1000),
            "inventory_name": str(inventory.get("name", "Crakbit testnet")),
        }
    )
    return result


def load_inventory(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
