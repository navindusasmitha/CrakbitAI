from __future__ import annotations

import argparse
import threading

import uvicorn

import local_dashboard_v39 as base
import local_dashboard_v40 as ops
import local_dashboard_v41  # noqa: F401 - registers v0.41 wallet/explorer routes and UI


def collect_status() -> dict:
    status = ops.collect_status()
    status["format"] = "crakbit-local-dashboard-v41/1"
    status["source_commit"] = base.SOURCE_COMMIT
    return status


base.collect_status = collect_status
base.app.version = "0.41.1-local"


def main() -> None:
    parser = argparse.ArgumentParser(description="Crakbit local wallet/explorer dashboard v0.41.1")
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
