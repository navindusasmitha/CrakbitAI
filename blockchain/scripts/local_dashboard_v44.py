from __future__ import annotations

import argparse
import json
import os
import socket
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

import uvicorn

import local_dashboard_v39 as base
import local_dashboard_v42 as v42
import local_dashboard_v43 as v43
from crakbit_chain.pow_v31 import MAX_UINT256, parse_target

NODE_DBS = {name: Path(f"/runtime/{name}/chain.sqlite3") for name in ("node1", "node2", "node3", "node4")}
NODE_RPC_PORT = 28443
NODE_P2P_PORT = 28444


def _tcp(host: str, port: int, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _read_node_db(name: str) -> dict[str, Any]:
    path = NODE_DBS[name]
    if not path.is_file():
        raise RuntimeError("node chain database not found")
    uri = f"file:{path.as_posix()}?mode=ro"
    last_error: Exception | None = None
    for attempt in range(3):
        db: sqlite3.Connection | None = None
        try:
            db = sqlite3.connect(uri, uri=True, timeout=1.5)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            meta = {str(r["key"]): str(r["value"]) for r in db.execute("SELECT key,value FROM meta")}
            config = json.loads(meta.get("config", "{}"))
            tip = db.execute("SELECT height,block_hash,target,chainwork FROM blocks ORDER BY height DESC LIMIT 1").fetchone()
            if tip is None:
                raise RuntimeError("chain has no blocks")
            graph_count = int(db.execute("SELECT COUNT(*) FROM block_graph").fetchone()[0])
            side_count = int(db.execute("SELECT COUNT(*) FROM block_graph WHERE status='side'").fetchone()[0])
            orphan_count = int(db.execute("SELECT COUNT(*) FROM orphan_blocks").fetchone()[0])
            mempool_size = int(db.execute("SELECT COUNT(*) FROM mempool").fetchone()[0])
            target = str(tip["target"])
            return {
                "protocol": "crakbit-pow/1",
                "chain_id": str(config.get("chain_id", "unknown")),
                "network": str(config.get("network", "unknown")),
                "pow_algo": str(config.get("pow_algo", "unknown")),
                "height": int(tip["height"]),
                "best_block_hash": str(tip["block_hash"]),
                "target": target,
                "difficulty": float(MAX_UINT256 / parse_target(target)),
                "chainwork": str(tip["chainwork"]),
                "mempool_size": mempool_size,
                "p2p_protocol": "crakbit-p2p/1",
                "fork_choice": "highest-cumulative-work",
                "block_graph_count": graph_count,
                "side_chain_blocks": side_count,
                "orphan_blocks": orphan_count,
                "mtp_window": 11,
                "peer_count": None,
                "peer_count_source": "not-polled-by-local-monitor",
                "state_source": "read-only-sqlite",
                "production_mainnet_ready": False,
                "production_crkbit_launched": False,
            }
        except (sqlite3.Error, ValueError, RuntimeError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.05 * (attempt + 1))
        finally:
            if db is not None:
                db.close()
    raise RuntimeError(str(last_error) if last_error is not None else "node DB read failed")


def _node_snapshot(name: str) -> dict[str, Any]:
    rpc_reachable = _tcp(name, NODE_RPC_PORT)
    p2p_reachable = _tcp(name, NODE_P2P_PORT)
    try:
        state = _read_node_db(name)
        return {
            "online": bool(rpc_reachable and p2p_reachable),
            "rpc_service_reachable": rpc_reachable,
            "p2p_service_reachable": p2p_reachable,
            **state,
        }
    except Exception as exc:
        return {
            "online": False,
            "rpc_service_reachable": rpc_reachable,
            "p2p_service_reachable": p2p_reachable,
            "error": str(exc),
        }


def collect_status() -> dict[str, Any]:
    nodes = {name: _node_snapshot(name) for name in NODE_DBS}
    online = [value for value in nodes.values() if value.get("online")]
    heights = [int(value["height"]) for value in online if "height" in value]
    tips = {str(value.get("best_block_hash")) for value in online if value.get("best_block_hash")}
    works = {str(value.get("chainwork")) for value in online if value.get("chainwork")}
    chain_ids = {str(value.get("chain_id")) for value in online if value.get("chain_id")}
    height_spread = (max(heights) - min(heights)) if heights else None
    strict_convergence = len(online) == 4 and len(heights) == 4 and len(set(heights)) == 1 and len(tips) == 1 and len(works) == 1
    same_height_tip_disagreement = bool(len(online) == 4 and height_spread == 0 and len(tips) > 1)
    degraded = len(online) < 4 or (height_spread is not None and height_spread > 2) or len(chain_ids) > 1 or same_height_tip_disagreement

    try:
        pool = {"online": True, **v42._read_pool_db()}
    except Exception as exc:
        pool = {"online": False, "error": str(exc)}
    pool_reachable = v42._pool_service_reachable()
    pool["stats_available"] = "error" not in pool
    pool["service_reachable"] = pool_reachable
    pool["online"] = bool(pool.get("stats_available") and pool_reachable)

    workers = base._worker_activity()
    return {
        "format": "crakbit-local-dashboard-v44/1",
        "timestamp": base._now_iso(),
        "banner": base.BANNER,
        "source_commit": os.environ.get("CRAKBIT_SOURCE_COMMIT", "unknown"),
        "source_commit_source": "environment",
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
        "pool": pool,
        "workers": workers,
        "active_workers": sum(1 for item in workers if item.get("active")),
        "phase3": base._phase3_summary(),
        "monitoring": {
            "node_state_source": "per-node-read-only-sqlite",
            "node_liveness_probe": "rpc-and-p2p-tcp-connect",
            "pool_stats_source": "read-only-sqlite",
            "pool_service_probe": "tcp-connect-only",
            "explorer_read_source": "node1-read-only-sqlite",
            "explorer_writes_via_rpc": True,
            "production_mainnet_ready": False,
        },
    }


base.collect_status = collect_status
base.app.version = "0.44.0-local"
base.INDEX_HTML = base.INDEX_HTML.replace("v0.43", "v0.44")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crakbit local-only rehearsal dashboard v0.44")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=38080)
    parser.add_argument("--auto-evidence-seconds", type=int, default=300)
    args = parser.parse_args()
    if args.auto_evidence_seconds > 0:
        threading.Thread(target=base._auto_snapshot_loop, args=(args.auto_evidence_seconds,), daemon=True).start()
    uvicorn.run(base.app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
