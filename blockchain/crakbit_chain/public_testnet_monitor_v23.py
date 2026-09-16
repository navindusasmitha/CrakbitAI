from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

from .public_testnet_v23 import load_inventory


OBSERVATION_FORMAT = "crakbit-public-testnet-observation/1"
SOAK_SUMMARY_FORMAT = "crakbit-public-testnet-soak-summary/1"


class PublicTestnetMonitorError(ValueError):
    pass


def _rpc_status(client: httpx.Client, url: str) -> dict[str, Any]:
    response = client.get(url.rstrip("/") + "/status")
    response.raise_for_status()
    body = response.json()
    result = body.get("result") or {}
    sync = result.get("sync_info") or {}
    node = result.get("node_info") or {}
    return {
        "network": str(node.get("network", "")),
        "latest_block_hash": str(sync.get("latest_block_hash", "")),
        "latest_app_hash": str(sync.get("latest_app_hash", "")),
        "latest_block_height": int(sync.get("latest_block_height", 0)),
        "catching_up": bool(sync.get("catching_up", False)),
    }


def _abci_info(client: httpx.Client, url: str) -> dict[str, Any]:
    response = client.get(url.rstrip("/") + "/abci_info")
    response.raise_for_status()
    body = response.json()
    response_body = ((body.get("result") or {}).get("response") or {})
    return {
        "data": str(response_body.get("data", "")),
        "version": str(response_body.get("version", "")),
        "app_version": int(response_body.get("app_version", 0) or 0),
        "last_block_height": int(response_body.get("last_block_height", 0) or 0),
        "last_block_app_hash": str(response_body.get("last_block_app_hash", "")),
    }


def observe_public_testnet(
    inventory_path: str | Path,
    *,
    timeout_seconds: float = 4.0,
    max_height_spread: int = 2,
) -> dict[str, Any]:
    if timeout_seconds <= 0 or timeout_seconds > 60:
        raise PublicTestnetMonitorError("timeout_seconds must be >0 and <=60")
    if max_height_spread < 0:
        raise PublicTestnetMonitorError("max_height_spread must be non-negative")
    inventory = load_inventory(inventory_path)
    observations: list[dict[str, Any]] = []
    with httpx.Client(timeout=timeout_seconds) as client:
        for validator in inventory["validators"]:
            record: dict[str, Any] = {
                "name": validator["name"],
                "operator_id": validator["operator_id"],
                "provider": validator["provider"],
                "region": validator["region"],
                "rpc_url": validator.get("monitor_rpc_url", ""),
                "reachable": False,
            }
            rpc_url = str(validator.get("monitor_rpc_url", "")).strip()
            if not rpc_url:
                record["error"] = "monitor_rpc_url is not configured"
                observations.append(record)
                continue
            try:
                started = time.perf_counter()
                status = _rpc_status(client, rpc_url)
                abci = _abci_info(client, rpc_url)
                latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
                record.update(
                    {
                        "reachable": True,
                        "latency_ms": latency_ms,
                        "status": status,
                        "abci": abci,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                record["error"] = f"{exc.__class__.__name__}: {exc}"
            observations.append(record)

    reachable = [item for item in observations if item["reachable"]]
    heights = [int(item["status"]["latest_block_height"]) for item in reachable]
    height_min = min(heights) if heights else None
    height_max = max(heights) if heights else None
    height_spread = (height_max - height_min) if heights else None

    same_height_conflicts: list[dict[str, Any]] = []
    grouped: dict[int, list[dict[str, Any]]] = {}
    for item in reachable:
        grouped.setdefault(int(item["status"]["latest_block_height"]), []).append(item)
    for height, items in sorted(grouped.items()):
        app_hashes = sorted(
            {
                str(item["abci"].get("last_block_app_hash", ""))
                for item in items
                if item["abci"].get("last_block_app_hash")
            }
        )
        if len(app_hashes) > 1:
            same_height_conflicts.append(
                {"height": height, "application_hashes": app_hashes}
            )

    networks = sorted(
        {str(item["status"].get("network", "")) for item in reachable if item["status"].get("network")}
    )
    catching_up = [item["name"] for item in reachable if item["status"]["catching_up"]]
    all_reachable = len(reachable) == len(observations)
    network_consistent = len(networks) <= 1 and (not networks or networks[0] == inventory["chain_id"])
    spread_ok = height_spread is not None and height_spread <= max_height_spread
    healthy = all_reachable and network_consistent and spread_ok and not same_height_conflicts
    return {
        "format": OBSERVATION_FORMAT,
        "observed_at_ms": int(time.time() * 1000),
        "chain_id": inventory["chain_id"],
        "validator_count": inventory["validator_count"],
        "reachable_count": len(reachable),
        "all_reachable": all_reachable,
        "network_values": networks,
        "network_consistent": network_consistent,
        "height_min": height_min,
        "height_max": height_max,
        "height_spread": height_spread,
        "max_allowed_height_spread": int(max_height_spread),
        "same_height_application_hash_conflicts": same_height_conflicts,
        "catching_up_nodes": catching_up,
        "healthy": healthy,
        "observations": observations,
        "production_mainnet_ready": False,
        "interpretation": "public-testnet operational observation only; not an independent consensus audit",
    }


def append_observation_jsonl(path: str | Path, observation: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(observation, sort_keys=True, separators=(",", ":")) + "\n")


def run_soak_collection(
    inventory_path: str | Path,
    *,
    output_jsonl: str | Path,
    duration_seconds: int,
    interval_seconds: int = 30,
    timeout_seconds: float = 4.0,
    max_height_spread: int = 2,
) -> dict[str, Any]:
    duration = int(duration_seconds)
    interval = int(interval_seconds)
    if duration < 1:
        raise PublicTestnetMonitorError("duration_seconds must be positive")
    if interval < 5:
        raise PublicTestnetMonitorError("interval_seconds must be at least 5")
    started = time.monotonic()
    samples = 0
    healthy_samples = 0
    while True:
        observation = observe_public_testnet(
            inventory_path,
            timeout_seconds=timeout_seconds,
            max_height_spread=max_height_spread,
        )
        append_observation_jsonl(output_jsonl, observation)
        samples += 1
        if observation["healthy"]:
            healthy_samples += 1
        elapsed = time.monotonic() - started
        if elapsed >= duration:
            break
        time.sleep(min(interval, max(0.0, duration - elapsed)))
    return {
        "output": str(output_jsonl),
        "samples": samples,
        "healthy_samples": healthy_samples,
        "requested_duration_seconds": duration,
        "interval_seconds": interval,
        "production_mainnet_ready": False,
    }


def summarize_soak(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        raise PublicTestnetMonitorError(f"soak JSONL not found: {source}")
    samples: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                item = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise PublicTestnetMonitorError(f"invalid JSONL at line {number}") from exc
            if item.get("format") != OBSERVATION_FORMAT:
                raise PublicTestnetMonitorError(f"unexpected observation format at line {number}")
            samples.append(item)
    if not samples:
        raise PublicTestnetMonitorError("soak JSONL contains no observations")

    first_ms = int(samples[0]["observed_at_ms"])
    last_ms = int(samples[-1]["observed_at_ms"])
    healthy = sum(1 for item in samples if bool(item.get("healthy")))
    all_reachable = sum(1 for item in samples if bool(item.get("all_reachable")))
    divergence_samples = sum(
        1 for item in samples if list(item.get("same_height_application_hash_conflicts") or [])
    )
    max_spread = max(
        (int(item["height_spread"]) for item in samples if item.get("height_spread") is not None),
        default=None,
    )
    catching_up_samples = sum(1 for item in samples if list(item.get("catching_up_nodes") or []))
    latency_values = [
        float(node["latency_ms"])
        for item in samples
        for node in list(item.get("observations") or [])
        if node.get("reachable") and node.get("latency_ms") is not None
    ]
    return {
        "format": SOAK_SUMMARY_FORMAT,
        "source": str(source),
        "chain_id": str(samples[0].get("chain_id", "")),
        "samples": len(samples),
        "first_observed_at_ms": first_ms,
        "last_observed_at_ms": last_ms,
        "observed_duration_seconds": max(0.0, (last_ms - first_ms) / 1000.0),
        "healthy_samples": healthy,
        "healthy_ratio": healthy / len(samples),
        "all_reachable_samples": all_reachable,
        "all_reachable_ratio": all_reachable / len(samples),
        "divergence_samples": divergence_samples,
        "divergence_free": divergence_samples == 0,
        "catching_up_samples": catching_up_samples,
        "max_height_spread": max_spread,
        "latency_observations": len(latency_values),
        "latency_average_ms": (sum(latency_values) / len(latency_values)) if latency_values else None,
        "latency_max_ms": max(latency_values) if latency_values else None,
        "production_mainnet_ready": False,
        "interpretation": "operator-generated public-testnet evidence; not an independent security review",
    }
