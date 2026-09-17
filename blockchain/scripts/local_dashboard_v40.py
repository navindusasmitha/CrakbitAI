from __future__ import annotations

import argparse
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import uvicorn

import local_dashboard_v39 as base


def _fetch_node(name: str, url: str) -> tuple[str, dict[str, Any]]:
    last_error: Exception | None = None
    started = time.perf_counter()
    for attempt in range(2):
        try:
            info = base._http_json(url.rstrip("/") + "/pow/v2/info", timeout=6.0)
            latency_ms = round((time.perf_counter() - started) * 1000.0, 1)
            return name, {"online": True, "rpc_latency_ms": latency_ms, **info}
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(0.15)
    latency_ms = round((time.perf_counter() - started) * 1000.0, 1)
    return name, {
        "online": False,
        "rpc_latency_ms": latency_ms,
        "error": str(last_error) if last_error is not None else "unknown node RPC error",
    }


def collect_status() -> dict[str, Any]:
    nodes: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="crakbit-node-check") as executor:
        futures = [executor.submit(_fetch_node, name, url) for name, url in base.NODE_URLS.items()]
        for future in as_completed(futures):
            name, result = future.result()
            nodes[name] = result
    nodes = {name: nodes[name] for name in base.NODE_URLS}

    online = [value for value in nodes.values() if value.get("online")]
    heights = [int(value["height"]) for value in online if "height" in value]
    tips = {str(value.get("best_block_hash")) for value in online if value.get("best_block_hash")}
    works = {str(value.get("chainwork")) for value in online if value.get("chainwork")}
    chain_ids = {str(value.get("chain_id")) for value in online if value.get("chain_id")}
    height_spread = (max(heights) - min(heights)) if heights else None
    strict_convergence = (
        len(online) == 4
        and len(heights) == 4
        and len(set(heights)) == 1
        and len(tips) == 1
        and len(works) == 1
    )
    same_height_tip_disagreement = bool(
        len(online) == 4
        and height_spread == 0
        and len(tips) > 1
    )
    degraded = (
        len(online) < 4
        or (height_spread is not None and height_spread > 2)
        or len(chain_ids) > 1
        or same_height_tip_disagreement
    )

    try:
        pool_stats = {"online": True, **base._pool_rpc("pool.stats", timeout=5.0)}
    except Exception as exc:
        pool_stats = {"online": False, "error": str(exc)}

    workers = base._worker_activity()
    active_workers = sum(1 for item in workers if item.get("active"))

    return {
        "format": "crakbit-local-dashboard-v40/1",
        "timestamp": base._now_iso(),
        "banner": base.BANNER,
        "source_commit": base.SOURCE_COMMIT,
        "network_scope": "single-host Docker local rehearsal",
        "claims": {
            "production_mainnet_ready": False,
            "production_crkbit_launched": False,
            "independent_operator_diversity_verified": False,
            "independent_provider_diversity_verified": False,
            "independent_region_diversity_verified": False,
        },
        "nodes": nodes,
        "consensus": {
            "online_nodes": len(online),
            "height_spread": height_spread,
            "strict_convergence": strict_convergence,
            "same_height_tip_disagreement": same_height_tip_disagreement,
            "degraded_or_diverged": degraded,
        },
        "pool": pool_stats,
        "workers": workers,
        "active_workers": active_workers,
        "phase3": base._phase3_summary(),
    }


base.collect_status = collect_status
base.app.title = "Crakbit Local Rehearsal Dashboard"
base.app.version = "0.40.0-local"


def main() -> None:
    parser = argparse.ArgumentParser(description="Crakbit local-only rehearsal dashboard v0.40")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=38080)
    parser.add_argument("--auto-evidence-seconds", type=int, default=300)
    args = parser.parse_args()
    if args.auto_evidence_seconds > 0:
        thread = threading.Thread(
            target=base._auto_snapshot_loop,
            args=(args.auto_evidence_seconds,),
            daemon=True,
        )
        thread.start()
    uvicorn.run(base.app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
