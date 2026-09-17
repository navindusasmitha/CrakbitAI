from __future__ import annotations

import argparse
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

import uvicorn

import local_dashboard_v39 as base
import local_dashboard_v40 as ops
import local_dashboard_v41 as ui

POOL_DB = Path("/runtime/pool/pool.sqlite3")
_ORIGINAL_POOL_RPC = base._pool_rpc


def _read_pool_db() -> dict[str, Any]:
    if not POOL_DB.is_file():
        raise RuntimeError("pool database not found")

    uri = f"file:{POOL_DB.as_posix()}?mode=ro"
    last_error: Exception | None = None
    for attempt in range(3):
        db: sqlite3.Connection | None = None
        try:
            db = sqlite3.connect(uri, uri=True, timeout=1.5)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")

            share_count = int(db.execute("SELECT COUNT(*) FROM shares").fetchone()[0])
            rounds = int(db.execute("SELECT COUNT(*) FROM rounds").fetchone()[0])
            balances = {
                str(row["payout_address"]): int(row["pending_amount"])
                for row in db.execute("SELECT payout_address,pending_amount FROM balances ORDER BY payout_address")
            }

            try:
                unique_submissions = int(db.execute("SELECT COUNT(*) FROM share_submissions_v33").fetchone()[0])
            except sqlite3.Error:
                unique_submissions = share_count

            try:
                workers = int(db.execute("SELECT COUNT(*) FROM worker_vardiff_v33").fetchone()[0])
            except sqlite3.Error:
                workers = 0

            return {
                "share_count": share_count,
                "unique_submissions": unique_submissions,
                "workers": workers,
                "rounds": rounds,
                "balances": balances,
                "stats_source": "read-only-sqlite",
            }
        except sqlite3.Error as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.05 * (attempt + 1))
        finally:
            if db is not None:
                db.close()
    raise RuntimeError(str(last_error) if last_error is not None else "pool DB read failed")


def _local_pool_rpc(method: str, timeout: float = 2.0) -> dict[str, Any]:
    del timeout
    stats = _read_pool_db()
    if method == "pool.stats":
        return stats
    if method == "pool.balances":
        return dict(stats["balances"])
    return _ORIGINAL_POOL_RPC(method)


base._pool_rpc = _local_pool_rpc


def collect_status() -> dict[str, Any]:
    status = ops.collect_status()
    status["format"] = "crakbit-local-dashboard-v42/1"
    status["source_commit"] = os.environ.get("CRAKBIT_SOURCE_COMMIT", "unknown")
    status["monitoring"] = {
        "pool_stats_source": "read-only-sqlite",
        "pool_tcp_probe_required": False,
        "production_mainnet_ready": False,
    }
    return status


base.collect_status = collect_status
base.app.version = "0.42.0-local"
base.INDEX_HTML = base.INDEX_HTML.replace("v0.41", "v0.42")


@base.app.get("/api/v42/pool-local-stats")
def api_pool_local_stats() -> dict[str, Any]:
    return {
        **_read_pool_db(),
        "local_only": True,
        "production_mainnet_ready": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Crakbit local-only rehearsal dashboard v0.42")
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
