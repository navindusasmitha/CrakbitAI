from __future__ import annotations

import asyncio
import hmac
import json
import ssl
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .pow_pool_v31 import CrakbitPool, PoolConfig, PoolLedger, PowPoolV31Error, pow_config_from_template
from .pow_v31 import MAX_UINT256, parse_target, pow_hash, target_hex

POOL_V33_PROTOCOL = "crakbit-pool/2"


class PowPoolV33Error(PowPoolV31Error):
    pass


@dataclass(frozen=True)
class VardiffPolicy:
    target_share_seconds: float = 15.0
    minimum_multiplier: int = 4
    maximum_multiplier: int = 1_048_576
    initial_multiplier: int = 256
    retarget_every_shares: int = 8

    def __post_init__(self) -> None:
        if self.target_share_seconds <= 0:
            raise PowPoolV33Error("target share seconds must be positive")
        if self.minimum_multiplier < 1 or self.maximum_multiplier < self.minimum_multiplier:
            raise PowPoolV33Error("invalid vardiff multiplier bounds")
        if not self.minimum_multiplier <= self.initial_multiplier <= self.maximum_multiplier:
            raise PowPoolV33Error("initial multiplier is outside vardiff bounds")
        if self.retarget_every_shares < 2:
            raise PowPoolV33Error("retarget_every_shares must be >= 2")


class HardenedPoolLedger(PoolLedger):
    def __init__(self, db_path: str | Path):
        super().__init__(db_path)
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS share_submissions_v33(
                job_id TEXT NOT NULL,
                extra_nonce TEXT NOT NULL,
                nonce TEXT NOT NULL,
                hash_hex TEXT NOT NULL,
                accepted_at_ms INTEGER NOT NULL,
                PRIMARY KEY(job_id, extra_nonce, nonce)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS share_hash_unique_v33
              ON share_submissions_v33(job_id, hash_hex);
            CREATE TABLE IF NOT EXISTS worker_vardiff_v33(
                payout_address TEXT NOT NULL,
                worker TEXT NOT NULL,
                multiplier INTEGER NOT NULL,
                last_share_ms INTEGER,
                share_count INTEGER NOT NULL,
                ewma_interval_ms REAL,
                PRIMARY KEY(payout_address, worker)
            );
            """
        )
        self.db.commit()

    def reserve_share(self, *, job_id: str, extra_nonce: int, nonce: int, hash_hex: str) -> bool:
        try:
            self.db.execute(
                "INSERT INTO share_submissions_v33(job_id,extra_nonce,nonce,hash_hex,accepted_at_ms) VALUES(?,?,?,?,?)",
                (str(job_id), str(int(extra_nonce)), str(int(nonce)), str(hash_hex), int(time.time() * 1000)),
            )
            self.db.commit()
            return True
        except sqlite3.IntegrityError:
            self.db.rollback()
            return False

    def worker_multiplier(self, payout_address: str, worker: str, policy: VardiffPolicy) -> int:
        row = self.db.execute(
            "SELECT multiplier FROM worker_vardiff_v33 WHERE payout_address=? AND worker=?",
            (str(payout_address), str(worker)),
        ).fetchone()
        return policy.initial_multiplier if row is None else int(row[0])

    def record_worker_share(self, payout_address: str, worker: str, policy: VardiffPolicy) -> dict[str, Any]:
        now_ms = int(time.time() * 1000)
        row = self.db.execute(
            "SELECT multiplier,last_share_ms,share_count,ewma_interval_ms FROM worker_vardiff_v33 WHERE payout_address=? AND worker=?",
            (str(payout_address), str(worker)),
        ).fetchone()
        if row is None:
            multiplier = policy.initial_multiplier
            count = 1
            ewma = None
        else:
            multiplier = int(row["multiplier"])
            count = int(row["share_count"]) + 1
            last = row["last_share_ms"]
            prior = row["ewma_interval_ms"]
            interval = None if last is None else max(1, now_ms - int(last))
            if interval is None:
                ewma = None if prior is None else float(prior)
            elif prior is None:
                ewma = float(interval)
            else:
                ewma = 0.75 * float(prior) + 0.25 * float(interval)

            if ewma is not None and count % policy.retarget_every_shares == 0:
                target_ms = policy.target_share_seconds * 1000.0
                if ewma < target_ms * 0.70:
                    multiplier = max(policy.minimum_multiplier, max(1, multiplier // 2))
                elif ewma > target_ms * 1.50:
                    multiplier = min(policy.maximum_multiplier, multiplier * 2)

        self.db.execute(
            """
            INSERT INTO worker_vardiff_v33(payout_address,worker,multiplier,last_share_ms,share_count,ewma_interval_ms)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(payout_address,worker) DO UPDATE SET
              multiplier=excluded.multiplier,
              last_share_ms=excluded.last_share_ms,
              share_count=excluded.share_count,
              ewma_interval_ms=excluded.ewma_interval_ms
            """,
            (str(payout_address), str(worker), int(multiplier), now_ms, int(count), ewma),
        )
        self.db.commit()
        return {
            "multiplier": int(multiplier),
            "share_count": int(count),
            "ewma_interval_ms": ewma,
        }

    def stats(self) -> dict[str, Any]:
        share_count = int(self.db.execute("SELECT COUNT(*) FROM shares").fetchone()[0])
        unique_submissions = int(self.db.execute("SELECT COUNT(*) FROM share_submissions_v33").fetchone()[0])
        workers = int(self.db.execute("SELECT COUNT(*) FROM worker_vardiff_v33").fetchone()[0])
        rounds = int(self.db.execute("SELECT COUNT(*) FROM rounds").fetchone()[0])
        return {
            "share_count": share_count,
            "unique_submissions": unique_submissions,
            "workers": workers,
            "rounds": rounds,
            "balances": self.balances(),
        }


class HardenedCrakbitPool(CrakbitPool):
    def __init__(
        self,
        config: PoolConfig,
        ledger: HardenedPoolLedger,
        *,
        vardiff: VardiffPolicy | None = None,
        stale_job_seconds: int = 120,
    ):
        super().__init__(config, ledger)
        self.ledger: HardenedPoolLedger = ledger
        self.vardiff = vardiff or VardiffPolicy(initial_multiplier=config.share_target_multiplier)
        self.stale_job_seconds = max(15, int(stale_job_seconds))

    def _worker_share_target(self, active: dict[str, Any], payout_address: str, worker: str) -> tuple[int, int]:
        network_target = parse_target(active["network_target"])
        multiplier = self.ledger.worker_multiplier(payout_address, worker, self.vardiff)
        return min(MAX_UINT256, network_target * multiplier), multiplier

    def worker_job(self, *, worker: str, payout_address: str, extra_nonce: int) -> dict[str, Any]:
        if not worker.strip() or not payout_address.startswith("crk1"):
            raise PowPoolV33Error("worker and valid payout address are required")
        active = self.refresh_job()
        share_target, multiplier = self._worker_share_target(active, payout_address, worker)
        block = json.loads(json.dumps(active["template"]["block"]))
        block["header"]["extra_nonce"] = int(extra_nonce) & 0xFFFFFFFFFFFFFFFF
        block["header"]["nonce"] = 0
        return {
            "protocol": POOL_V33_PROTOCOL,
            "job_id": active["job_id"],
            "height": active["height"],
            "share_target": target_hex(share_target),
            "share_multiplier": multiplier,
            "network_target": active["network_target"],
            "extra_nonce": block["header"]["extra_nonce"],
            "block": block,
            "pow": dict(active["template"]["pow"]),
            "vardiff_target_share_seconds": self.vardiff.target_share_seconds,
            "production_mainnet_ready": False,
        }

    def submit_share(self, *, job_id: str, worker: str, payout_address: str, extra_nonce: int, nonce: int) -> dict[str, Any]:
        active = self.ledger.active_job()
        if active is None or str(active["job_id"]) != str(job_id):
            raise PowPoolV33Error("stale or unknown job")
        age_seconds = max(0.0, (time.time() * 1000 - int(active["created_at_ms"])) / 1000.0)
        if age_seconds > self.stale_job_seconds:
            raise PowPoolV33Error("job expired by v0.33 stale-work policy")

        block = json.loads(json.dumps(active["template"]["block"]))
        block["header"]["extra_nonce"] = int(extra_nonce) & 0xFFFFFFFFFFFFFFFF
        block["header"]["nonce"] = int(nonce)
        pow_config = pow_config_from_template(active["template"])
        digest = pow_hash(block["header"], pow_config)
        digest_int = int.from_bytes(digest, "big")
        share_target, old_multiplier = self._worker_share_target(active, payout_address, worker)
        network_target = parse_target(active["network_target"])
        if digest_int > share_target:
            raise PowPoolV33Error("low difficulty share")
        hash_hex = digest.hex()
        if not self.ledger.reserve_share(
            job_id=job_id,
            extra_nonce=extra_nonce,
            nonce=nonce,
            hash_hex=hash_hex,
        ):
            raise PowPoolV33Error("duplicate/replayed share")

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
        vardiff_state = self.ledger.record_worker_share(payout_address, worker, self.vardiff)

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
            "previous_share_multiplier": old_multiplier,
            "next_share_multiplier": vardiff_state["multiplier"],
            "worker_share_count": vardiff_state["share_count"],
            "production_mainnet_ready": False,
        }


class PoolSessionV33:
    def __init__(self, pool: HardenedCrakbitPool, *, auth_token: str | None = None):
        self.pool = pool
        self.auth_token = auth_token
        self.worker = ""
        self.payout_address = ""
        self.extra_nonce = uuid.uuid4().int & 0xFFFFFFFFFFFFFFFF

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        request_id = request.get("id")
        method = str(request.get("method", ""))
        params = request.get("params", {}) or {}
        try:
            if method == "mining.subscribe":
                result = {"protocol": POOL_V33_PROTOCOL, "extra_nonce": self.extra_nonce}
            elif method == "mining.authorize":
                if self.auth_token is not None:
                    supplied = str(params.get("token", ""))
                    if not hmac.compare_digest(supplied, self.auth_token):
                        raise PowPoolV33Error("pool authorization failed")
                self.worker = str(params.get("worker", "")).strip()
                self.payout_address = str(params.get("address", "")).strip()
                if not self.worker or not self.payout_address.startswith("crk1"):
                    raise PowPoolV33Error("invalid worker/address")
                result = {
                    "authorized": True,
                    "job": self.pool.worker_job(
                        worker=self.worker,
                        payout_address=self.payout_address,
                        extra_nonce=self.extra_nonce,
                    ),
                }
            elif method == "mining.get_job":
                if not self.worker:
                    raise PowPoolV33Error("authorize first")
                result = self.pool.worker_job(
                    worker=self.worker,
                    payout_address=self.payout_address,
                    extra_nonce=self.extra_nonce,
                )
            elif method == "mining.submit":
                if not self.worker:
                    raise PowPoolV33Error("authorize first")
                result = self.pool.submit_share(
                    job_id=str(params.get("job_id", "")),
                    worker=self.worker,
                    payout_address=self.payout_address,
                    extra_nonce=self.extra_nonce,
                    nonce=int(params.get("nonce", -1)),
                )
            elif method == "pool.balances":
                result = self.pool.ledger.balances()
            elif method == "pool.stats":
                result = self.pool.ledger.stats()
            else:
                raise PowPoolV33Error("unknown method")
            return {"id": request_id, "result": result, "error": None}
        except Exception as exc:
            return {"id": request_id, "result": None, "error": str(exc)}


async def run_pool_server_v33(
    pool: HardenedCrakbitPool,
    *,
    host: str = "127.0.0.1",
    port: int = 3333,
    tls_cert: str | None = None,
    tls_key: str | None = None,
    auth_token: str | None = None,
    max_messages_per_second: int = 25,
    max_line_bytes: int = 64 * 1024,
) -> None:
    if bool(tls_cert) != bool(tls_key):
        raise PowPoolV33Error("TLS certificate and key must be provided together")
    ssl_context: ssl.SSLContext | None = None
    if tls_cert and tls_key:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        ssl_context.load_cert_chain(tls_cert, tls_key)

    max_messages_per_second = max(1, min(int(max_messages_per_second), 1000))
    max_line_bytes = max(1024, min(int(max_line_bytes), 1_000_000))

    async def client_connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        session = PoolSessionV33(pool, auth_token=auth_token)
        window_second = int(time.time())
        count = 0
        try:
            while not reader.at_eof():
                raw = await reader.readline()
                if not raw:
                    break
                if len(raw) > max_line_bytes:
                    break
                current = int(time.time())
                if current != window_second:
                    window_second = current
                    count = 0
                count += 1
                if count > max_messages_per_second:
                    response = {"id": None, "result": None, "error": "pool connection rate limit exceeded"}
                    writer.write((json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8"))
                    await writer.drain()
                    break
                try:
                    request = json.loads(raw.decode("utf-8"))
                    if not isinstance(request, dict):
                        raise PowPoolV33Error("request must be a JSON object")
                    response = session.handle(request)
                except Exception as exc:
                    response = {"id": None, "result": None, "error": str(exc)}
                writer.write((json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8"))
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(client_connected, host=host, port=int(port), ssl=ssl_context)
    async with server:
        await server.serve_forever()
