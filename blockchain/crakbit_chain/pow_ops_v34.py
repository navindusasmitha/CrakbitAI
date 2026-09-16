from __future__ import annotations

import ipaddress
import json
import math
import sqlite3
import statistics
import time
from pathlib import Path
from typing import Any

from .crypto import canonical_json, sha256_hex
from .pow_v31 import MAX_UINT256, parse_target, transaction_id


class PowOpsV34Error(ValueError):
    pass


def _connect(path: str | Path) -> sqlite3.Connection:
    db = sqlite3.connect(Path(path))
    db.row_factory = sqlite3.Row
    return db


def _peer_bucket(endpoint: str) -> str:
    text = str(endpoint).strip()
    if not text:
        raise PowOpsV34Error("empty peer endpoint")
    if text.startswith("["):
        end = text.find("]")
        if end < 0:
            raise PowOpsV34Error("invalid IPv6 endpoint")
        host = text[1:end]
    else:
        if ":" not in text:
            raise PowOpsV34Error("peer endpoint must contain a port")
        host = text.rsplit(":", 1)[0]
    try:
        ip = ipaddress.ip_address(host)
        if isinstance(ip, ipaddress.IPv4Address):
            net = ipaddress.ip_network(f"{ip}/16", strict=False)
            return f"ipv4:{net.network_address}/16"
        net = ipaddress.ip_network(f"{ip}/32", strict=False)
        return f"ipv6:{net.network_address}/32"
    except ValueError:
        labels = [v for v in host.lower().strip(".").split(".") if v]
        suffix = ".".join(labels[-2:]) if len(labels) >= 2 else host.lower()
        return f"dns:{suffix}"


class PeerBookV34:
    """Persistent, non-secret peer reputation/address book.

    This is a seed-selection aid, not a claim of Sybil resistance. Diversity is
    enforced with coarse endpoint buckets only; ASN/operator diversity remains an
    external/public-testnet gate.
    """

    def __init__(self, db_path: str | Path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = _connect(self.path)
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS peer_book_v34(
                endpoint TEXT PRIMARY KEY,
                node_id TEXT,
                source TEXT NOT NULL,
                bucket TEXT NOT NULL,
                score INTEGER NOT NULL,
                successes INTEGER NOT NULL,
                failures INTEGER NOT NULL,
                last_success_ms INTEGER,
                last_failure_ms INTEGER,
                last_seen_ms INTEGER NOT NULL,
                banned_until_ms INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS peer_book_v34_score_idx
              ON peer_book_v34(score DESC, last_success_ms DESC);
            """
        )
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def note(
        self,
        endpoint: str,
        *,
        node_id: str | None = None,
        source: str = "manual",
        success: bool | None = None,
        score_delta: int = 0,
    ) -> dict[str, Any]:
        endpoint = str(endpoint).strip()
        bucket = _peer_bucket(endpoint)
        now = int(time.time() * 1000)
        row = self.db.execute("SELECT * FROM peer_book_v34 WHERE endpoint=?", (endpoint,)).fetchone()
        score = int(row["score"]) if row else 0
        successes = int(row["successes"]) if row else 0
        failures = int(row["failures"]) if row else 0
        last_success = row["last_success_ms"] if row else None
        last_failure = row["last_failure_ms"] if row else None
        banned_until = int(row["banned_until_ms"]) if row else 0
        if success is True:
            successes += 1
            score += 5
            last_success = now
            if failures and successes % 3 == 0:
                failures = max(0, failures - 1)
        elif success is False:
            failures += 1
            score -= min(50, 5 + failures * 2)
            last_failure = now
            if failures >= 5:
                banned_until = max(banned_until, now + min(86_400_000, failures * 600_000))
        score += int(score_delta)
        score = max(-1000, min(1000, score))
        self.db.execute(
            """
            INSERT INTO peer_book_v34(endpoint,node_id,source,bucket,score,successes,failures,last_success_ms,last_failure_ms,last_seen_ms,banned_until_ms)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(endpoint) DO UPDATE SET
              node_id=COALESCE(excluded.node_id,peer_book_v34.node_id),
              source=excluded.source,
              bucket=excluded.bucket,
              score=excluded.score,
              successes=excluded.successes,
              failures=excluded.failures,
              last_success_ms=excluded.last_success_ms,
              last_failure_ms=excluded.last_failure_ms,
              last_seen_ms=excluded.last_seen_ms,
              banned_until_ms=excluded.banned_until_ms
            """,
            (endpoint, node_id, str(source), bucket, score, successes, failures, last_success, last_failure, now, banned_until),
        )
        self.db.commit()
        return self.get(endpoint)

    def get(self, endpoint: str) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM peer_book_v34 WHERE endpoint=?", (str(endpoint),)).fetchone()
        if row is None:
            raise PowOpsV34Error("peer not found")
        return dict(row)

    def list(self, *, limit: int = 500) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT * FROM peer_book_v34 ORDER BY score DESC, COALESCE(last_success_ms,0) DESC, endpoint LIMIT ?",
            (max(1, min(int(limit), 5000)),),
        ).fetchall()
        return [dict(row) for row in rows]

    def select(self, *, limit: int = 16, max_per_bucket: int = 2) -> list[str]:
        now = int(time.time() * 1000)
        rows = self.db.execute(
            "SELECT * FROM peer_book_v34 WHERE banned_until_ms<=? ORDER BY score DESC, COALESCE(last_success_ms,0) DESC, failures ASC, endpoint",
            (now,),
        ).fetchall()
        selected: list[str] = []
        buckets: dict[str, int] = {}
        for row in rows:
            bucket = str(row["bucket"])
            if buckets.get(bucket, 0) >= max(1, int(max_per_bucket)):
                continue
            selected.append(str(row["endpoint"]))
            buckets[bucket] = buckets.get(bucket, 0) + 1
            if len(selected) >= max(1, int(limit)):
                break
        return selected


class UndoJournalV34:
    """Backfillable canonical UTXO undo metadata for future efficient reorgs.

    v0.34 records/verifies the data required to disconnect a canonical block:
    outputs created by the block and pre-block UTXOs spent by it. The live v0.32
    reorg engine still uses replay/state replacement; this journal is deliberately
    introduced and tested before changing consensus-critical activation mechanics.
    """

    def __init__(self, chain_db: str | Path):
        self.path = Path(chain_db)
        self.db = _connect(self.path)
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS block_undo_v34(
                block_hash TEXT PRIMARY KEY,
                height INTEGER NOT NULL UNIQUE,
                undo_hash TEXT NOT NULL,
                undo_json TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL
            );
            """
        )
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def _creator(self, txid: str, vout: int) -> dict[str, Any]:
        row = self.db.execute(
            "SELECT block_height,tx_index,tx_json FROM transactions WHERE txid=?",
            (str(txid),),
        ).fetchone()
        if row is None:
            raise PowOpsV34Error(f"missing creator transaction for {txid}:{vout}")
        tx = json.loads(row["tx_json"])
        outputs = list(tx.get("outputs", []))
        if int(vout) < 0 or int(vout) >= len(outputs):
            raise PowOpsV34Error("prevout index exceeds creator outputs")
        output = outputs[int(vout)]
        return {
            "txid": str(txid),
            "vout": int(vout),
            "address": str(output["address"]),
            "amount": int(output["amount"]),
            "coinbase_height": int(row["block_height"]) if bool(tx.get("coinbase", False)) else None,
            "creator_height": int(row["block_height"]),
        }

    def build_for_height(self, height: int) -> dict[str, Any]:
        height = int(height)
        if height <= 0:
            raise PowOpsV34Error("genesis does not need UTXO undo data")
        block_row = self.db.execute(
            "SELECT block_hash,block_json FROM blocks WHERE height=?",
            (height,),
        ).fetchone()
        if block_row is None:
            raise PowOpsV34Error("canonical block not found")
        block_hash = str(block_row["block_hash"])
        block = json.loads(block_row["block_json"])
        txs = list(block.get("transactions", []))
        created: list[dict[str, Any]] = []
        spent_external: dict[tuple[str, int], dict[str, Any]] = {}

        txids_in_block = {transaction_id(tx): index for index, tx in enumerate(txs)}
        for tx in txs:
            txid = transaction_id(tx)
            for vout, _output in enumerate(tx.get("outputs", [])):
                created.append({"txid": txid, "vout": int(vout)})
        for tx in txs[1:]:
            for item in tx.get("inputs", []):
                key = (str(item["txid"]), int(item["vout"]))
                creator = self._creator(*key)
                if creator["creator_height"] < height:
                    spent_external[key] = creator
                elif creator["creator_height"] > height:
                    raise PowOpsV34Error("block spends an output from a future block")
                elif key[0] not in txids_in_block:
                    raise PowOpsV34Error("same-height input creator not present in block")

        manifest = {
            "format": "crakbit-utxo-undo-v34/1",
            "height": height,
            "block_hash": block_hash,
            "created_outpoints": sorted(created, key=lambda item: (item["txid"], item["vout"])),
            "restore_utxos": sorted(spent_external.values(), key=lambda item: (item["txid"], item["vout"])),
        }
        undo_hash = sha256_hex(canonical_json(manifest))
        self.db.execute(
            "INSERT OR REPLACE INTO block_undo_v34(block_hash,height,undo_hash,undo_json,created_at_ms) VALUES(?,?,?,?,?)",
            (block_hash, height, undo_hash, json.dumps(manifest, sort_keys=True), int(time.time() * 1000)),
        )
        self.db.commit()
        return {**manifest, "undo_hash": undo_hash, "production_mainnet_ready": False}

    def backfill(self, *, start_height: int = 1, end_height: int | None = None) -> dict[str, Any]:
        tip = self.db.execute("SELECT MAX(height) FROM blocks").fetchone()[0]
        if tip is None:
            raise PowOpsV34Error("chain contains no blocks")
        end = int(tip) if end_height is None else min(int(end_height), int(tip))
        start = max(1, int(start_height))
        records: list[dict[str, Any]] = []
        for height in range(start, end + 1):
            records.append(self.build_for_height(height))
        return {
            "format": "crakbit-utxo-undo-backfill-v34/1",
            "start_height": start,
            "end_height": end,
            "count": len(records),
            "undo_hashes": [record["undo_hash"] for record in records],
            "live_reorg_engine_uses_incremental_undo": False,
            "production_mainnet_ready": False,
        }

    def verify(self) -> dict[str, Any]:
        rows = self.db.execute("SELECT * FROM block_undo_v34 ORDER BY height").fetchall()
        failures: list[str] = []
        checked = 0
        for row in rows:
            manifest = json.loads(row["undo_json"])
            digest = sha256_hex(canonical_json(manifest))
            if digest != str(row["undo_hash"]):
                failures.append(f"height {row['height']}: undo hash mismatch")
                continue
            block = self.db.execute(
                "SELECT block_hash,block_json FROM blocks WHERE height=?",
                (int(row["height"]),),
            ).fetchone()
            if block is None or str(block["block_hash"]) != str(row["block_hash"]):
                failures.append(f"height {row['height']}: canonical block mismatch")
                continue
            rebuilt = self.build_for_height(int(row["height"]))
            if rebuilt["undo_hash"] != digest:
                failures.append(f"height {row['height']}: rebuilt undo differs")
                continue
            checked += 1
        return {
            "format": "crakbit-utxo-undo-verify-v34/1",
            "checked": checked,
            "failures": failures,
            "valid": not failures,
            "live_reorg_engine_uses_incremental_undo": False,
            "production_mainnet_ready": False,
        }


def chain_statistics(chain_db: str | Path, *, window: int = 120) -> dict[str, Any]:
    db = _connect(chain_db)
    try:
        window = max(2, min(int(window), 10_000))
        rows = db.execute(
            "SELECT height,block_hash,timestamp,target,chainwork,block_json FROM blocks ORDER BY height DESC LIMIT ?",
            (window,),
        ).fetchall()
        if not rows:
            raise PowOpsV34Error("chain has no blocks")
        ordered = list(reversed(rows))
        tip = ordered[-1]
        difficulties = [float(MAX_UINT256 / parse_target(row["target"])) for row in ordered if int(row["height"]) > 0]
        estimated_hashrate = None
        observed_seconds = None
        if len(ordered) >= 2:
            first, last = ordered[0], ordered[-1]
            observed_seconds = max(1, int(last["timestamp"]) - int(first["timestamp"]))
            work_delta = max(0, int(last["chainwork"]) - int(first["chainwork"]))
            estimated_hashrate = work_delta / observed_seconds

        miner_counts: dict[str, int] = {}
        coinbase_total = 0
        for row in ordered:
            if int(row["height"]) <= 0:
                continue
            block = json.loads(row["block_json"])
            txs = list(block.get("transactions", []))
            if not txs:
                continue
            coinbase = txs[0]
            for output in coinbase.get("outputs", []):
                address = str(output.get("address", ""))
                amount = int(output.get("amount", 0))
                if address:
                    miner_counts[address] = miner_counts.get(address, 0) + 1
                coinbase_total += amount
        miners = [
            {"address": address, "blocks": count}
            for address, count in sorted(miner_counts.items(), key=lambda item: (-item[1], item[0]))
        ]
        return {
            "format": "crakbit-pow-stats-v34/1",
            "height": int(tip["height"]),
            "best_block_hash": str(tip["block_hash"]),
            "difficulty": float(MAX_UINT256 / parse_target(tip["target"])),
            "median_difficulty_window": statistics.median(difficulties) if difficulties else 0.0,
            "window_blocks": len(ordered),
            "observed_seconds": observed_seconds,
            "estimated_network_hashrate_hps": estimated_hashrate,
            "coinbase_output_total_atomic": coinbase_total,
            "miner_block_counts": miners,
            "production_mainnet_ready": False,
        }
    finally:
        db.close()


def transaction_confirmations(chain_db: str | Path, txid: str) -> dict[str, Any]:
    db = _connect(chain_db)
    try:
        tip = int(db.execute("SELECT MAX(height) FROM blocks").fetchone()[0] or 0)
        row = db.execute("SELECT block_height,tx_index FROM transactions WHERE txid=?", (str(txid),)).fetchone()
        if row is not None:
            height = int(row["block_height"])
            return {
                "txid": str(txid),
                "state": "confirmed",
                "block_height": height,
                "confirmations": max(0, tip - height + 1),
                "tip_height": tip,
                "production_mainnet_ready": False,
            }
        mempool = db.execute("SELECT 1 FROM mempool WHERE txid=?", (str(txid),)).fetchone()
        return {
            "txid": str(txid),
            "state": "mempool" if mempool else "unknown",
            "block_height": None,
            "confirmations": 0,
            "tip_height": tip,
            "production_mainnet_ready": False,
        }
    finally:
        db.close()


def fee_estimate(chain_db: str | Path, *, fallback_atomic_per_byte: int = 1) -> dict[str, Any]:
    db = _connect(chain_db)
    try:
        rates: list[float] = []
        for row in db.execute("SELECT fee,tx_json FROM mempool"):
            size = max(1, len(str(row["tx_json"]).encode("utf-8")))
            rates.append(int(row["fee"]) / size)
        if rates:
            median = statistics.median(rates)
            p75 = sorted(rates)[min(len(rates) - 1, math.floor(len(rates) * 0.75))]
        else:
            median = float(max(1, int(fallback_atomic_per_byte)))
            p75 = median
        return {
            "format": "crakbit-fee-estimate-v34/1",
            "mempool_samples": len(rates),
            "median_atomic_per_byte": median,
            "priority_atomic_per_byte": p75,
            "policy_only": True,
            "production_mainnet_ready": False,
        }
    finally:
        db.close()


def build_watch_only(address: str, *, label: str = "") -> dict[str, Any]:
    address = str(address).strip()
    if not address.startswith("crk1") or len(address) < 12:
        raise PowOpsV34Error("invalid Crakbit address")
    return {
        "format": "crakbit-watch-only-v34/1",
        "address": address,
        "label": str(label)[:128],
        "contains_private_key": False,
        "production_mainnet_ready": False,
    }
