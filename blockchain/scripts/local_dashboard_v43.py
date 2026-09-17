from __future__ import annotations

import argparse
import json
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
import local_dashboard_v42 as v42


NODE1_DB = Path("/runtime/node1/chain.sqlite3")
NODE1_URL = base.NODE_URLS["node1"].rstrip("/")
_ORIGINAL_HTTP_JSON = base._http_json


def _with_node_db(callback):
    if not NODE1_DB.is_file():
        raise RuntimeError("node1 chain database not found")
    uri = f"file:{NODE1_DB.as_posix()}?mode=ro"
    last_error: Exception | None = None
    for attempt in range(3):
        db: sqlite3.Connection | None = None
        try:
            db = sqlite3.connect(uri, uri=True, timeout=1.5)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            return callback(db)
        except sqlite3.Error as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.05 * (attempt + 1))
        finally:
            if db is not None:
                db.close()
    raise RuntimeError(str(last_error) if last_error is not None else "node1 DB read failed")


def _row_to_block(row: sqlite3.Row) -> dict[str, Any]:
    block = json.loads(str(row["block_json"]))
    block["block_hash"] = str(row["block_hash"])
    block["chainwork"] = str(row["chainwork"])
    return block


def _local_block_by_height(height: int) -> dict[str, Any]:
    def read(db: sqlite3.Connection) -> dict[str, Any]:
        row = db.execute(
            "SELECT height,block_hash,previous_hash,timestamp,target,chainwork,block_json FROM blocks WHERE height=?",
            (int(height),),
        ).fetchone()
        if row is None:
            raise RuntimeError("block not found")
        return _row_to_block(row)

    return _with_node_db(read)


def _local_block_by_hash(block_hash: str) -> dict[str, Any]:
    def read(db: sqlite3.Connection) -> dict[str, Any]:
        row = db.execute(
            "SELECT height,block_hash,previous_hash,timestamp,target,chainwork,block_json FROM blocks WHERE block_hash=?",
            (str(block_hash).lower(),),
        ).fetchone()
        if row is None:
            raise RuntimeError("block not found")
        return _row_to_block(row)

    return _with_node_db(read)


def _local_mempool() -> dict[str, Any]:
    def read(db: sqlite3.Connection) -> dict[str, Any]:
        rows = db.execute(
            "SELECT txid,fee,received_at_ms,tx_json FROM mempool ORDER BY fee DESC, received_at_ms ASC"
        ).fetchall()
        return {
            "transactions": [
                {
                    "txid": str(row["txid"]),
                    "fee": int(row["fee"]),
                    "received_at_ms": int(row["received_at_ms"]),
                    "transaction": json.loads(str(row["tx_json"])),
                }
                for row in rows
            ],
            "explorer_source": "read-only-sqlite",
            "production_mainnet_ready": False,
        }

    return _with_node_db(read)


def _local_latest_blocks(limit: int) -> dict[str, Any]:
    limit = max(1, min(int(limit), 20))

    def read(db: sqlite3.Connection) -> dict[str, Any]:
        rows = db.execute(
            "SELECT height,block_hash,previous_hash,timestamp,target,chainwork,block_json "
            "FROM blocks ORDER BY height DESC LIMIT ?",
            (limit,),
        ).fetchall()
        if not rows:
            raise RuntimeError("chain has no blocks")
        blocks: list[dict[str, Any]] = []
        for row in rows:
            block = json.loads(str(row["block_json"]))
            header = dict(block.get("header") or {})
            blocks.append(
                {
                    "height": int(row["height"]),
                    "block_hash": str(row["block_hash"]),
                    "previous_hash": str(row["previous_hash"]),
                    "timestamp": int(row["timestamp"]),
                    "target": str(row["target"]),
                    "chainwork": str(row["chainwork"]),
                    "transaction_count": len(block.get("transactions") or []),
                    "nonce": header.get("nonce"),
                    "extra_nonce": header.get("extra_nonce"),
                }
            )
        return {
            "tip_height": int(rows[0]["height"]),
            "blocks": blocks,
            "explorer_source": "read-only-sqlite",
            "production_mainnet_ready": False,
        }

    return _with_node_db(read)


def _http_json_local_explorer(url: str, timeout: float = 3.0) -> dict[str, Any]:
    normalized = str(url).rstrip("/")
    prefix = f"{NODE1_URL}/pow/v2"
    if normalized == f"{prefix}/mempool":
        return _local_mempool()
    if normalized.startswith(f"{prefix}/block/"):
        return _local_block_by_height(int(normalized.rsplit("/", 1)[1]))
    if normalized.startswith(f"{prefix}/blockhash/"):
        return _local_block_by_hash(normalized.rsplit("/", 1)[1])
    return _ORIGINAL_HTTP_JSON(url, timeout=timeout)


# Keep writes/balance/UTXO/status RPCs on the node, but satisfy explorer reads locally.
base._http_json = _http_json_local_explorer
ui._latest_blocks = _local_latest_blocks


def collect_status() -> dict[str, Any]:
    status = v42.collect_status()
    status["format"] = "crakbit-local-dashboard-v43/1"
    status["source_commit"] = os.environ.get("CRAKBIT_SOURCE_COMMIT", "unknown")
    monitoring = dict(status.get("monitoring") or {})
    monitoring["explorer_read_source"] = "node1-read-only-sqlite"
    monitoring["explorer_writes_via_rpc"] = True
    monitoring["production_mainnet_ready"] = False
    status["monitoring"] = monitoring
    return status


base.collect_status = collect_status
base.app.version = "0.43.0-local"
base.INDEX_HTML = base.INDEX_HTML.replace("v0.42", "v0.43")


@base.app.get("/api/v43/explorer/latest")
def api_v43_latest(limit: int = 10) -> dict[str, Any]:
    return _local_latest_blocks(limit)


@base.app.get("/api/v43/explorer/mempool")
def api_v43_mempool() -> dict[str, Any]:
    return _local_mempool()


@base.app.get("/api/v43/explorer/block/{height}")
def api_v43_block(height: int) -> dict[str, Any]:
    return _local_block_by_height(height)


@base.app.get("/api/v43/explorer/hash/{block_hash}")
def api_v43_hash(block_hash: str) -> dict[str, Any]:
    if len(block_hash) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in block_hash):
        raise RuntimeError("invalid block hash")
    return _local_block_by_hash(block_hash)


def main() -> None:
    parser = argparse.ArgumentParser(description="Crakbit local-only rehearsal dashboard v0.43")
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
