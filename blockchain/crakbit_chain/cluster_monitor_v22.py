from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx


CLUSTER_EVIDENCE_FORMAT = "crakbit-governed-cluster-observation/1"


class ClusterMonitorError(ValueError):
    pass


def load_inventory(path: str | Path) -> dict[str, Any]:
    body = json.loads(Path(path).read_text(encoding="utf-8"))
    if body.get("format") != "crakbit-governed-cometbft-lab/1":
        raise ClusterMonitorError("unsupported governed-lab inventory format")
    nodes = list(body.get("nodes") or [])
    if len(nodes) < 4:
        raise ClusterMonitorError("governed cluster inventory must contain at least four nodes")
    return body


def _pending_ids(governance: dict[str, Any]) -> list[str]:
    pending = governance.get("pending")
    if pending is None:
        return []
    if isinstance(pending, dict):
        pending = [pending]
    if not isinstance(pending, list):
        return []
    values: list[str] = []
    for item in pending:
        if isinstance(item, dict) and item.get("change_id"):
            values.append(str(item["change_id"]))
    return sorted(values)


def _active_set_hash(governance: dict[str, Any]) -> str:
    return str(
        governance.get("active_validator_set_hash")
        or governance.get("validator_set_hash")
        or governance.get("active_set_hash")
        or ""
    )


def evaluate_observations(
    observations: list[dict[str, Any]], *, max_height_spread: int = 1
) -> dict[str, Any]:
    if max_height_spread < 0:
        raise ClusterMonitorError("max_height_spread must be non-negative")
    if not observations:
        raise ClusterMonitorError("at least one observation is required")

    reachable = [item for item in observations if bool(item.get("reachable"))]
    heights = [int(item["execution"]["height"]) for item in reachable if item.get("execution")]
    if not heights:
        height_min = height_max = height_spread = None
    else:
        height_min = min(heights)
        height_max = max(heights)
        height_spread = height_max - height_min

    same_height_app_hash_conflicts: list[dict[str, Any]] = []
    governance_conflicts: list[dict[str, Any]] = []
    grouped: dict[int, list[dict[str, Any]]] = {}
    for item in reachable:
        execution = item.get("execution") or {}
        if "height" not in execution:
            continue
        grouped.setdefault(int(execution["height"]), []).append(item)
    for height, items in sorted(grouped.items()):
        hashes = sorted({str((item.get("execution") or {}).get("application_hash", "")) for item in items})
        hashes = [value for value in hashes if value]
        if len(hashes) > 1:
            same_height_app_hash_conflicts.append({"height": height, "application_hashes": hashes})
        gov_states = {
            (
                _active_set_hash(item.get("governance") or {}),
                tuple(_pending_ids(item.get("governance") or {})),
            )
            for item in items
        }
        if len(gov_states) > 1:
            governance_conflicts.append(
                {
                    "height": height,
                    "states": [
                        {"active_validator_set_hash": state[0], "pending_change_ids": list(state[1])}
                        for state in sorted(gov_states)
                    ],
                }
            )

    catching_up = [
        str(item.get("name", "node"))
        for item in reachable
        if bool((item.get("cometbft") or {}).get("catching_up"))
    ]
    unreachable = [str(item.get("name", "node")) for item in observations if not item.get("reachable")]
    expected = len(observations)
    all_reachable = len(reachable) == expected
    spread_ok = height_spread is not None and height_spread <= max_height_spread
    divergence_free = (
        all_reachable
        and spread_ok
        and not same_height_app_hash_conflicts
        and not governance_conflicts
    )
    return {
        "format": CLUSTER_EVIDENCE_FORMAT,
        "observed_at_ms": int(time.time() * 1000),
        "node_count": expected,
        "reachable_count": len(reachable),
        "all_reachable": all_reachable,
        "unreachable_nodes": unreachable,
        "height_min": height_min,
        "height_max": height_max,
        "height_spread": height_spread,
        "max_allowed_height_spread": int(max_height_spread),
        "same_height_application_hash_conflicts": same_height_app_hash_conflicts,
        "governance_conflicts": governance_conflicts,
        "catching_up_nodes": catching_up,
        "divergence_free": divergence_free,
        "observations": observations,
        "production_mainnet_ready": False,
        "interpretation": "operational test evidence only; not a consensus-safety proof",
    }


def collect_cluster_observations(
    inventory: dict[str, Any], *, timeout_seconds: float = 3.0
) -> list[dict[str, Any]]:
    if timeout_seconds <= 0 or timeout_seconds > 60:
        raise ClusterMonitorError("timeout_seconds must be greater than 0 and at most 60")
    observations: list[dict[str, Any]] = []
    with httpx.Client(timeout=timeout_seconds) as client:
        for node in list(inventory.get("nodes") or []):
            name = str(node.get("name") or "node")
            execution_url = str(node.get("execution_url") or "").rstrip("/")
            rpc_url = str(node.get("rpc_url") or "").rstrip("/")
            record: dict[str, Any] = {
                "name": name,
                "execution_url": execution_url,
                "rpc_url": rpc_url,
                "reachable": False,
            }
            try:
                info_response = client.get(execution_url + "/v4/info")
                info_response.raise_for_status()
                governance_response = client.get(execution_url + "/v4/governance/status")
                governance_response.raise_for_status()
                rpc_response = client.get(rpc_url + "/status")
                rpc_response.raise_for_status()
                info = info_response.json()
                governance = governance_response.json()
                rpc = rpc_response.json()
                sync_info = ((rpc.get("result") or {}).get("sync_info") or {})
                record.update(
                    {
                        "reachable": True,
                        "execution": {
                            "protocol": str(info.get("protocol", "")),
                            "chain_id": str(info.get("chain_id", "")),
                            "height": int(info.get("height", 0)),
                            "application_hash": str(info.get("application_hash", "")),
                            "schema_version": int(info.get("schema_version", 0)),
                        },
                        "governance": governance,
                        "cometbft": {
                            "latest_block_height": int(sync_info.get("latest_block_height", 0)),
                            "latest_block_hash": str(sync_info.get("latest_block_hash", "")),
                            "catching_up": bool(sync_info.get("catching_up", False)),
                        },
                    }
                )
            except Exception as exc:  # noqa: BLE001
                record["error"] = f"{exc.__class__.__name__}: {exc}"
            observations.append(record)
    return observations


def collect_and_evaluate(
    inventory_path: str | Path,
    *,
    timeout_seconds: float = 3.0,
    max_height_spread: int = 1,
) -> dict[str, Any]:
    inventory = load_inventory(inventory_path)
    observations = collect_cluster_observations(inventory, timeout_seconds=timeout_seconds)
    result = evaluate_observations(observations, max_height_spread=max_height_spread)
    result["chain_id"] = str(inventory.get("chain_id", ""))
    result["inventory"] = str(inventory_path)
    return result
