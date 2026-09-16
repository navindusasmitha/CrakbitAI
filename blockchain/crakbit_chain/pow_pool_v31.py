from __future__ import annotations

import asyncio
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .crypto import canonical_json, sha256_hex
from .pow_v31 import MAX_UINT256, PowConfig, parse_target, pow_hash, target_hex

POOL_PROTOCOL = "crakbit-pool/1"


class PowPoolV31Error(ValueError):
    pass


@dataclass(frozen=True)
class PoolConfig:
    node_url: str
    pool_address: str
    share_target_multiplier: int = 256
    pplns_window_shares: int = 1000
    refresh_seconds: int = 15

    def __post_init__(self) -> None:
        if not self.node_url.startswith(("http://", "https://")):
            raise PowPoolV31Error("node_url must be http(s)")
        if not self.pool_address.startswith("crk1"):
            raise PowPoolV31Error("invalid pool payout address")
        if self.share_target_multiplier < 1:
            raise PowPoolV31Error("share_target_multiplier must be >= 1")
        if self.pplns_window_shares < 1:
            raise PowPoolV31Error("pplns_window_shares must be >= 1")


class PoolLedger:
    def __init__(self, db_path: str | Path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS jobs(
                job_id TEXT PRIMARY KEY,
                height INTEGER NOT NULL,
                network_target TEXT NOT NULL,
                share_target TEXT NOT NULL,
                template_json TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL,
                active INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS shares(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                worker TEXT NOT NULL,
                payout_address TEXT NOT NULL,
                hash_hex TEXT NOT NULL,
                accepted_at_ms INTEGER NOT NULL,
                is_block INTEGER NOT NULL,
                block_hash TEXT
            );
            CREATE INDEX IF NOT EXISTS shares_job_idx ON shares(job_id);
            CREATE INDEX IF NOT EXISTS shares_address_idx ON shares(payout_address);
            CREATE TABLE IF NOT EXISTS balances(
                payout_address TEXT PRIMARY KEY,
                pending_amount INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rounds(
                block_hash TEXT PRIMARY KEY,
                height INTEGER NOT NULL,
                reward INTEGER NOT NULL,
                share_count INTEGER NOT NULL,
                created_at_ms INTEGER NOT NULL
            );
            """
        )
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def put_job(self, job: dict[str, Any]) -> None:
        self.db.execute("UPDATE jobs SET active=0")
        self.db.execute(
            "INSERT OR REPLACE INTO jobs(job_id,height,network_target,share_target,template_json,created_at_ms,active) VALUES(?,?,?,?,?,?,1)",
            (
                job["job_id"], int(job["height"]), job["network_target"], job["share_target"],
                json.dumps(job["template"], sort_keys=True), int(time.time() * 1000),
            ),
        )
        self.db.commit()

    def active_job(self) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM jobs WHERE active=1 ORDER BY created_at_ms DESC LIMIT 1").fetchone()
        if row is None:
            return None
        return {
            "job_id": str(row["job_id"]),
            "height": int(row["height"]),
            "network_target": str(row["network_target"]),
            "share_target": str(row["share_target"]),
            "template": json.loads(row["template_json"]),
            "created_at_ms": int(row["created_at_ms"]),
        }

    def add_share(self, *, job_id: str, worker: str, payout_address: str, hash_hex: str, is_block: bool, block_hash_value: str | None) -> int:
        cur = self.db.execute(
            "INSERT INTO shares(job_id,worker,payout_address,hash_hex,accepted_at_ms,is_block,block_hash) VALUES(?,?,?,?,?,?,?)",
            (job_id, worker, payout_address, hash_hex, int(time.time() * 1000), 1 if is_block else 0, block_hash_value),
        )
        self.db.commit()
        return int(cur.lastrowid)

    def recent_shares(self, limit: int) -> list[sqlite3.Row]:
        return self.db.execute("SELECT * FROM shares ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()

    def credit_pplns(self, *, block_hash_value: str, height: int, reward: int, window: int) -> dict[str, int]:
        if self.db.execute("SELECT 1 FROM rounds WHERE block_hash=?", (block_hash_value,)).fetchone():
            return {}
        shares = self.recent_shares(window)
        if not shares:
            return {}
        counts: dict[str, int] = {}
        for row in shares:
            address = str(row["payout_address"])
            counts[address] = counts.get(address, 0) + 1
        total = sum(counts.values())
        credits: dict[str, int] = {}
        allocated = 0
        ordered = sorted(counts.items())
        for index, (address, count) in enumerate(ordered):
            if index == len(ordered) - 1:
                amount = int(reward) - allocated
            else:
                amount = (int(reward) * count) // total
                allocated += amount
            credits[address] = amount
            self.db.execute(
                "INSERT INTO balances(payout_address,pending_amount) VALUES(?,?) ON CONFLICT(payout_address) DO UPDATE SET pending_amount=pending_amount+excluded.pending_amount",
                (address, amount),
            )
        self.db.execute(
            "INSERT INTO rounds(block_hash,height,reward,share_count,created_at_ms) VALUES(?,?,?,?,?)",
            (block_hash_value, int(height), int(reward), total, int(time.time() * 1000)),
        )
        self.db.commit()
        return credits

    def balances(self) -> dict[str, int]:
        return {str(row["payout_address"]): int(row["pending_amount"]) for row in self.db.execute("SELECT * FROM balances ORDER BY payout_address")}


def pow_config_from_template(template: dict[str, Any]) -> PowConfig:
    params = template.get("pow", {}) or {}
    try:
        return PowConfig(
            pow_algo=str(params["algo"]),
            scrypt_n=int(params["scrypt_n"]),
            scrypt_r=int(params["scrypt_r"]),
            scrypt_p=int(params["scrypt_p"]),
        )
    except Exception as exc:
        raise PowPoolV31Error("node template is missing/invalid PoW parameters") from exc


class CrakbitPool:
    def __init__(self, config: PoolConfig, ledger: PoolLedger):
        self.config = config
        self.ledger = ledger
        self._last_refresh = 0.0

    def _node_post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(self.config.node_url.rstrip("/") + path, json=payload)
            response.raise_for_status()
            return response.json()

    def refresh_job(self, *, force: bool = False) -> dict[str, Any]:
        current = self.ledger.active_job()
        if current and not force and time.time() - self._last_refresh < self.config.refresh_seconds:
            return current
        template = self._node_post(
            "/pow/v1/getblocktemplate",
            {"miner_address": self.config.pool_address, "message": "Crakbit Pool v0.31"},
        )
        pow_config_from_template(template)
        network_target = parse_target(template["target"])
        share_target = min(MAX_UINT256, network_target * self.config.share_target_multiplier)
        stable = {
            "height": int(template["height"]),
            "previous_hash": template["block"]["header"]["previous_hash"],
            "merkle_root": template["block"]["header"]["merkle_root"],
            "network_target": target_hex(network_target),
            "share_target": target_hex(share_target),
            "pow": template["pow"],
        }
        job_id = sha256_hex(canonical_json(stable))[:24]
        job = {
            "protocol": POOL_PROTOCOL,
            "job_id": job_id,
            "height": int(template["height"]),
            "network_target": target_hex(network_target),
            "share_target": target_hex(share_target),
            "template": template,
        }
        self.ledger.put_job(job)
        self._last_refresh = time.time()
        return self.ledger.active_job() or job

    def worker_job(self, *, worker: str, payout_address: str, extra_nonce: int) -> dict[str, Any]:
        if not worker.strip() or not payout_address.startswith("crk1"):
            raise PowPoolV31Error("worker and valid payout address are required")
        job = self.refresh_job()
        block = json.loads(json.dumps(job["template"]["block"]))
        block["header"]["extra_nonce"] = int(extra_nonce) & 0xFFFFFFFFFFFFFFFF
        block["header"]["nonce"] = 0
        return {
            "protocol": POOL_PROTOCOL,
            "job_id": job["job_id"],
            "height": job["height"],
            "share_target": job["share_target"],
            "network_target": job["network_target"],
            "extra_nonce": block["header"]["extra_nonce"],
            "block": block,
            "pow": dict(job["template"]["pow"]),
            "production_mainnet_ready": False,
        }

    def submit_share(self, *, job_id: str, worker: str, payout_address: str, extra_nonce: int, nonce: int) -> dict[str, Any]:
        active = self.ledger.active_job()
        if active is None or str(active["job_id"]) != str(job_id):
            raise PowPoolV31Error("stale or unknown job")
        block = json.loads(json.dumps(active["template"]["block"]))
        block["header"]["extra_nonce"] = int(extra_nonce) & 0xFFFFFFFFFFFFFFFF
        block["header"]["nonce"] = int(nonce)
        pow_config = pow_config_from_template(active["template"])
        digest = pow_hash(block["header"], pow_config)
        digest_int = int.from_bytes(digest, "big")
        share_target = parse_target(active["share_target"])
        network_target = parse_target(active["network_target"])
        if digest_int > share_target:
            raise PowPoolV31Error("low difficulty share")
        hash_hex = digest.hex()
        is_block = digest_int <= network_target
        block_result: dict[str, Any] | None = None
        if is_block:
            block_result = self._node_post("/pow/v1/submitblock", {"block": block})
        self.ledger.add_share(
            job_id=job_id,
            worker=worker,
            payout_address=payout_address,
            hash_hex=hash_hex,
            is_block=is_block,
            block_hash_value=hash_hex if is_block else None,
        )
        credits: dict[str, int] = {}
        if is_block and block_result and block_result.get("accepted"):
            reward = int(active["template"].get("coinbase_value", 0))
            credits = self.ledger.credit_pplns(
                block_hash_value=hash_hex,
                height=int(active["height"]),
                reward=reward,
                window=self.config.pplns_window_shares,
            )
            self.refresh_job(force=True)
        return {
            "accepted": True,
            "share_hash": hash_hex,
            "is_block": bool(is_block),
            "block_result": block_result,
            "pplns_credits": credits,
            "production_mainnet_ready": False,
        }


class PoolSession:
    def __init__(self, pool: CrakbitPool):
        self.pool = pool
        self.worker = ""
        self.payout_address = ""
        self.extra_nonce = uuid.uuid4().int & 0xFFFFFFFFFFFFFFFF

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        request_id = request.get("id")
        method = str(request.get("method", ""))
        params = request.get("params", {}) or {}
        try:
            if method == "mining.subscribe":
                result = {"protocol": POOL_PROTOCOL, "extra_nonce": self.extra_nonce}
            elif method == "mining.authorize":
                self.worker = str(params.get("worker", "")).strip()
                self.payout_address = str(params.get("address", "")).strip()
                if not self.worker or not self.payout_address.startswith("crk1"):
                    raise PowPoolV31Error("invalid worker/address")
                result = {"authorized": True, "job": self.pool.worker_job(worker=self.worker, payout_address=self.payout_address, extra_nonce=self.extra_nonce)}
            elif method == "mining.get_job":
                if not self.worker:
                    raise PowPoolV31Error("authorize first")
                result = self.pool.worker_job(worker=self.worker, payout_address=self.payout_address, extra_nonce=self.extra_nonce)
            elif method == "mining.submit":
                if not self.worker:
                    raise PowPoolV31Error("authorize first")
                result = self.pool.submit_share(
                    job_id=str(params.get("job_id", "")),
                    worker=self.worker,
                    payout_address=self.payout_address,
                    extra_nonce=self.extra_nonce,
                    nonce=int(params.get("nonce", -1)),
                )
            elif method == "pool.balances":
                result = self.pool.ledger.balances()
            else:
                raise PowPoolV31Error("unknown method")
            return {"id": request_id, "result": result, "error": None}
        except Exception as exc:
            return {"id": request_id, "result": None, "error": str(exc)}


async def run_pool_server(pool: CrakbitPool, host: str = "127.0.0.1", port: int = 3333) -> None:
    async def client_connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        session = PoolSession(pool)
        try:
            while not reader.at_eof():
                raw = await reader.readline()
                if not raw:
                    break
                if len(raw) > 1_000_000:
                    break
                try:
                    request = json.loads(raw.decode("utf-8"))
                    response = session.handle(request)
                except Exception as exc:
                    response = {"id": None, "result": None, "error": str(exc)}
                writer.write((json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8"))
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(client_connected, host=host, port=int(port))
    async with server:
        await server.serve_forever()
