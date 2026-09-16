from __future__ import annotations

import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .crypto import KeyPair, sha256_hex
from .genesis import Genesis
from .limits import FixedWindowLimiter
from .models import ATOMIC_UNITS, Transaction


MINING_PROTOCOL = "crakbit-work-reward/1"


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def valid_crakbit_address(address: str) -> bool:
    value = str(address).strip().lower()
    return (
        len(value) == 44
        and value.startswith("crk1")
        and all(ch in "0123456789abcdef" for ch in value[4:])
    )


def work_digest(challenge_id: str, address: str, seed: str, nonce: int) -> str:
    payload = f"{challenge_id}:{address.lower()}:{seed}:{int(nonce)}".encode("utf-8")
    return sha256_hex(payload)


def meets_difficulty(digest_hex: str, difficulty_bits: int) -> bool:
    if len(digest_hex) != 64:
        return False
    value = int(digest_hex, 16)
    target = 1 << (256 - int(difficulty_bits))
    return value < target


@dataclass(frozen=True)
class MiningConfig:
    enabled: bool = False
    genesis_path: str = "runtime/genesis.json"
    reward_key_path: str = ""
    gateway_url: str = "http://127.0.0.1:9600"
    state_path: str = "runtime/mining-state.sqlite3"
    reward_atomic: int = 1 * ATOMIC_UNITS
    difficulty_bits: int = 18
    challenge_ttl_seconds: int = 300
    address_cooldown_seconds: int = 3600
    max_rewards_per_address_per_day: int = 24
    challenge_requests_per_minute: int = 30

    @classmethod
    def from_env(cls) -> "MiningConfig":
        raw_reward = os.environ.get("CRAKBIT_MINING_REWARD", "1")
        try:
            reward_atomic = int(Decimal(raw_reward) * ATOMIC_UNITS)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("CRAKBIT_MINING_REWARD must be a decimal number") from exc
        config = cls(
            enabled=_truthy(os.environ.get("CRAKBIT_MINING_ENABLED")),
            genesis_path=os.environ.get("CRAKBIT_MINING_GENESIS", "runtime/genesis.json"),
            reward_key_path=os.environ.get("CRAKBIT_MINING_REWARD_KEY", ""),
            gateway_url=os.environ.get("CRAKBIT_MINING_GATEWAY", "http://127.0.0.1:9600"),
            state_path=os.environ.get("CRAKBIT_MINING_STATE", "runtime/mining-state.sqlite3"),
            reward_atomic=reward_atomic,
            difficulty_bits=int(os.environ.get("CRAKBIT_MINING_DIFFICULTY_BITS", "18")),
            challenge_ttl_seconds=int(os.environ.get("CRAKBIT_MINING_CHALLENGE_TTL", "300")),
            address_cooldown_seconds=int(os.environ.get("CRAKBIT_MINING_ADDRESS_COOLDOWN", "3600")),
            max_rewards_per_address_per_day=int(os.environ.get("CRAKBIT_MINING_MAX_DAILY", "24")),
            challenge_requests_per_minute=int(os.environ.get("CRAKBIT_MINING_CHALLENGE_RPM", "30")),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if not (8 <= self.difficulty_bits <= 30):
            raise ValueError("mining difficulty must be between 8 and 30 bits")
        if self.reward_atomic <= 0 or self.reward_atomic > 100 * ATOMIC_UNITS:
            raise ValueError("test mining reward must be greater than 0 and at most 100 CRKBIT")
        if self.challenge_ttl_seconds < 30 or self.challenge_ttl_seconds > 3600:
            raise ValueError("challenge TTL must be between 30 and 3600 seconds")
        if self.address_cooldown_seconds < 60:
            raise ValueError("mining address cooldown must be at least 60 seconds")
        if self.max_rewards_per_address_per_day < 1 or self.max_rewards_per_address_per_day > 1000:
            raise ValueError("daily mining reward limit must be between 1 and 1000")
        if self.challenge_requests_per_minute < 1 or self.challenge_requests_per_minute > 600:
            raise ValueError("challenge request RPM must be between 1 and 600")
        if not self.gateway_url.startswith(("http://", "https://")):
            raise ValueError("mining gateway URL must use http or https")
        if self.enabled:
            if not Path(self.genesis_path).is_file():
                raise ValueError("mining genesis file was not found")
            if not self.reward_key_path or not Path(self.reward_key_path).is_file():
                raise ValueError("mining reward key is required when mining service is enabled")


class MiningStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS mining_challenges (
                    challenge_id TEXT PRIMARY KEY,
                    address TEXT NOT NULL,
                    seed TEXT NOT NULL,
                    difficulty_bits INTEGER NOT NULL,
                    reward_atomic INTEGER NOT NULL,
                    created_at_ms INTEGER NOT NULL,
                    expires_at_ms INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    nonce INTEGER,
                    digest TEXT,
                    claimed_at_ms INTEGER,
                    txid TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_mining_address_time
                    ON mining_challenges(address, claimed_at_ms);
                CREATE INDEX IF NOT EXISTS idx_mining_status_expiry
                    ON mining_challenges(status, expires_at_ms);
                """
            )

    def issue_challenge(
        self,
        address: str,
        *,
        difficulty_bits: int,
        reward_atomic: int,
        ttl_seconds: int,
        cooldown_seconds: int,
        daily_limit: int,
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        address = address.strip().lower()
        if not valid_crakbit_address(address):
            raise ValueError("invalid Crakbit address")
        now = int(time.time() * 1000) if now_ms is None else int(now_ms)
        cutoff = now - 86_400_000
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                last = conn.execute(
                    "SELECT claimed_at_ms FROM mining_challenges "
                    "WHERE address=? AND status='submitted' AND claimed_at_ms IS NOT NULL "
                    "ORDER BY claimed_at_ms DESC LIMIT 1",
                    (address,),
                ).fetchone()
                if last is not None:
                    remaining_ms = cooldown_seconds * 1000 - (now - int(last["claimed_at_ms"]))
                    if remaining_ms > 0:
                        raise ValueError(
                            f"address mining cooldown active for {(remaining_ms + 999) // 1000} more seconds"
                        )
                daily_count = int(
                    conn.execute(
                        "SELECT COUNT(*) AS n FROM mining_challenges "
                        "WHERE address=? AND status='submitted' AND claimed_at_ms>=?",
                        (address, cutoff),
                    ).fetchone()["n"]
                )
                if daily_count >= daily_limit:
                    raise ValueError("address reached the daily test mining reward limit")
                existing = conn.execute(
                    "SELECT * FROM mining_challenges WHERE address=? AND status='open' "
                    "AND expires_at_ms>? ORDER BY created_at_ms DESC LIMIT 1",
                    (address, now),
                ).fetchone()
                if existing is not None:
                    conn.execute("COMMIT")
                    return self._public_challenge(existing)
                challenge_id = secrets.token_hex(16)
                seed = secrets.token_hex(32)
                expires_at_ms = now + ttl_seconds * 1000
                conn.execute(
                    "INSERT INTO mining_challenges(" 
                    "challenge_id,address,seed,difficulty_bits,reward_atomic,created_at_ms,expires_at_ms" 
                    ") VALUES(?,?,?,?,?,?,?)",
                    (
                        challenge_id,
                        address,
                        seed,
                        int(difficulty_bits),
                        int(reward_atomic),
                        now,
                        expires_at_ms,
                    ),
                )
                row = conn.execute(
                    "SELECT * FROM mining_challenges WHERE challenge_id=?", (challenge_id,)
                ).fetchone()
                conn.execute("COMMIT")
                return self._public_challenge(row)
            except Exception:
                conn.execute("ROLLBACK")
                raise

    @staticmethod
    def _public_challenge(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "protocol": MINING_PROTOCOL,
            "challenge_id": str(row["challenge_id"]),
            "address": str(row["address"]),
            "seed": str(row["seed"]),
            "difficulty_bits": int(row["difficulty_bits"]),
            "reward_atomic": int(row["reward_atomic"]),
            "created_at_ms": int(row["created_at_ms"]),
            "expires_at_ms": int(row["expires_at_ms"]),
            "status": str(row["status"]),
        }

    def reserve_solution(
        self,
        challenge_id: str,
        address: str,
        nonce: int,
        *,
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        address = address.strip().lower()
        now = int(time.time() * 1000) if now_ms is None else int(now_ms)
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT * FROM mining_challenges WHERE challenge_id=?",
                    (challenge_id,),
                ).fetchone()
                if row is None:
                    raise ValueError("mining challenge not found")
                if str(row["address"]) != address:
                    raise ValueError("mining challenge belongs to a different address")
                if str(row["status"]) != "open":
                    raise ValueError("mining challenge was already claimed or is being submitted")
                if int(row["expires_at_ms"]) < now:
                    conn.execute(
                        "UPDATE mining_challenges SET status='expired' WHERE challenge_id=?",
                        (challenge_id,),
                    )
                    raise ValueError("mining challenge expired")
                digest = work_digest(
                    challenge_id,
                    address,
                    str(row["seed"]),
                    int(nonce),
                )
                if not meets_difficulty(digest, int(row["difficulty_bits"])):
                    raise ValueError("submitted nonce does not satisfy the proof-of-work target")
                conn.execute(
                    "UPDATE mining_challenges SET status='submitting',nonce=?,digest=?,claimed_at_ms=? "
                    "WHERE challenge_id=? AND status='open'",
                    (int(nonce), digest, now, challenge_id),
                )
                if conn.total_changes < 1:
                    raise ValueError("mining challenge could not be reserved")
                conn.execute("COMMIT")
                return {
                    **self._public_challenge(row),
                    "status": "submitting",
                    "nonce": int(nonce),
                    "digest": digest,
                }
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def mark_submitted(self, challenge_id: str, txid: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE mining_challenges SET status='submitted',txid=? "
                "WHERE challenge_id=? AND status='submitting'",
                (txid, challenge_id),
            )

    def release_solution(self, challenge_id: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE mining_challenges SET status='open',nonce=NULL,digest=NULL,claimed_at_ms=NULL "
                "WHERE challenge_id=? AND status='submitting'",
                (challenge_id,),
            )

    def stats(self) -> dict[str, int]:
        with self.connect() as conn:
            total = int(conn.execute("SELECT COUNT(*) AS n FROM mining_challenges").fetchone()["n"])
            submitted = int(
                conn.execute(
                    "SELECT COUNT(*) AS n FROM mining_challenges WHERE status='submitted'"
                ).fetchone()["n"]
            )
            open_count = int(
                conn.execute(
                    "SELECT COUNT(*) AS n FROM mining_challenges WHERE status='open'"
                ).fetchone()["n"]
            )
        return {"challenges": total, "submitted_rewards": submitted, "open_challenges": open_count}


class MiningSubmitRequest(BaseModel):
    address: str
    challenge_id: str
    nonce: int


def create_app(config: MiningConfig | None = None) -> FastAPI:
    config = config or MiningConfig.from_env()
    store = MiningStore(config.state_path)
    limiter = FixedWindowLimiter(config.challenge_requests_per_minute, 60)
    app = FastAPI(title="Crakbit Testnet Work Reward", version="0.15.0a1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.state.mining_store = store

    genesis: Genesis | None = None
    reward_key: KeyPair | None = None
    if config.enabled:
        genesis = Genesis.load(config.genesis_path)
        reward_key = KeyPair.load(config.reward_key_path)
        if reward_key.address in {validator.address for validator in genesis.validators}:
            raise ValueError("mining reward key must not be a validator consensus key")

    @app.get("/health")
    def health() -> dict:
        return {
            "ok": True,
            "enabled": config.enabled,
            "protocol": MINING_PROTOCOL,
            "test_only": True,
            "consensus_mining": False,
            "reward_model": "hashcash-style-work-reward",
            "difficulty_bits": config.difficulty_bits,
            "reward_atomic": config.reward_atomic,
            "challenge_ttl_seconds": config.challenge_ttl_seconds,
            "address_cooldown_seconds": config.address_cooldown_seconds,
            "max_rewards_per_address_per_day": config.max_rewards_per_address_per_day,
            **store.stats(),
        }

    @app.get("/challenge")
    def challenge(
        request: Request,
        address: str = Query(..., min_length=44, max_length=44),
    ) -> dict:
        if not config.enabled:
            raise HTTPException(503, "test mining service is disabled")
        client = request.client.host if request.client else "unknown"
        allowed, _ = limiter.allow(client)
        if not allowed:
            raise HTTPException(429, "mining challenge rate limit exceeded")
        try:
            return store.issue_challenge(
                address,
                difficulty_bits=config.difficulty_bits,
                reward_atomic=config.reward_atomic,
                ttl_seconds=config.challenge_ttl_seconds,
                cooldown_seconds=config.address_cooldown_seconds,
                daily_limit=config.max_rewards_per_address_per_day,
            )
        except ValueError as exc:
            raise HTTPException(429 if "cooldown" in str(exc) or "daily" in str(exc) else 400, str(exc)) from exc

    @app.post("/submit")
    async def submit(payload: MiningSubmitRequest) -> dict:
        if not config.enabled or genesis is None or reward_key is None:
            raise HTTPException(503, "test mining service is disabled")
        address = payload.address.strip().lower()
        try:
            reserved = store.reserve_solution(
                payload.challenge_id,
                address,
                int(payload.nonce),
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                account_response = await client.get(
                    f"{config.gateway_url.rstrip('/')}/api/account/{reward_key.address}"
                )
                account_response.raise_for_status()
                account_payload = account_response.json()
                account = account_payload.get("account", account_payload)
                nonce = int(account.get("nonce", 0)) + 1
                required = int(reserved["reward_atomic"]) + genesis.min_fee
                if int(account.get("balance", 0)) < required:
                    raise RuntimeError("mining reward wallet balance is insufficient")
                tx = Transaction(
                    chain_id=genesis.chain_id,
                    sender=reward_key.address,
                    recipient=address,
                    amount=int(reserved["reward_atomic"]),
                    fee=genesis.min_fee,
                    nonce=nonce,
                    public_key=reward_key.public_key_b64,
                    memo="Crakbit testnet proof-of-work reward",
                )
                tx.signature = reward_key.sign(tx.signing_bytes())
                submit_response = await client.post(
                    f"{config.gateway_url.rstrip('/')}/api/transactions",
                    json={"transaction": tx.to_dict()},
                )
                if submit_response.status_code >= 400:
                    raise RuntimeError(
                        f"gateway rejected mining reward transaction: {submit_response.text[:240]}"
                    )
                result = submit_response.json()
                txid = str(result.get("txid") or tx.txid)
            store.mark_submitted(payload.challenge_id, txid)
            return {
                "accepted": True,
                "protocol": MINING_PROTOCOL,
                "test_only": True,
                "consensus_mining": False,
                "address": address,
                "challenge_id": payload.challenge_id,
                "nonce": int(payload.nonce),
                "digest": reserved["digest"],
                "reward_atomic": int(reserved["reward_atomic"]),
                "txid": txid,
                "message": "work reward submitted as an ordinary testnet transaction",
            }
        except Exception as exc:
            store.release_solution(payload.challenge_id)
            raise HTTPException(503, str(exc)) from exc

    return app


app = create_app()
