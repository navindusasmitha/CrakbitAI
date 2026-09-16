from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from .crypto import KeyPair
from .genesis import Genesis
from .limits import FixedWindowLimiter
from .models import ATOMIC_UNITS, Transaction


class FaucetRequest(BaseModel):
    address: str


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def valid_crakbit_address(address: str) -> bool:
    value = str(address).strip().lower()
    if len(value) != 44 or not value.startswith("crk1"):
        return False
    return all(ch in "0123456789abcdef" for ch in value[4:])


@dataclass(frozen=True)
class FaucetConfig:
    enabled: bool = False
    genesis_path: str = "runtime/genesis.json"
    key_path: str = ""
    rpc_url: str = "http://127.0.0.1:9101"
    gateway_url: str = ""
    state_path: str = "runtime/faucet-state.sqlite3"
    amount_atomic: int = 10 * ATOMIC_UNITS
    address_cooldown_seconds: int = 3600
    global_requests_per_minute: int = 10

    @classmethod
    def from_env(cls) -> "FaucetConfig":
        raw_amount = os.environ.get("CRAKBIT_FAUCET_AMOUNT", "10")
        try:
            amount_atomic = int(Decimal(raw_amount) * ATOMIC_UNITS)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("CRAKBIT_FAUCET_AMOUNT must be a decimal number") from exc
        config = cls(
            enabled=_truthy(os.environ.get("CRAKBIT_FAUCET_ENABLED")),
            genesis_path=os.environ.get("CRAKBIT_FAUCET_GENESIS", "runtime/genesis.json"),
            key_path=os.environ.get("CRAKBIT_FAUCET_KEY", ""),
            rpc_url=os.environ.get("CRAKBIT_FAUCET_RPC", "http://127.0.0.1:9101").rstrip("/"),
            gateway_url=os.environ.get("CRAKBIT_FAUCET_GATEWAY", "").rstrip("/"),
            state_path=os.environ.get("CRAKBIT_FAUCET_STATE", "runtime/faucet-state.sqlite3"),
            amount_atomic=amount_atomic,
            address_cooldown_seconds=int(os.environ.get("CRAKBIT_FAUCET_ADDRESS_COOLDOWN", "3600")),
            global_requests_per_minute=int(os.environ.get("CRAKBIT_FAUCET_GLOBAL_RPM", "10")),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.amount_atomic <= 0 or self.amount_atomic > 100 * ATOMIC_UNITS:
            raise ValueError("test faucet amount must be greater than 0 and at most 100 CRKBIT")
        if self.address_cooldown_seconds < 60:
            raise ValueError("faucet address cooldown must be at least 60 seconds")
        if self.global_requests_per_minute <= 0 or self.global_requests_per_minute > 120:
            raise ValueError("faucet global RPM must be between 1 and 120")
        if self.gateway_url and not self.gateway_url.startswith(("http://", "https://")):
            raise ValueError("test faucet gateway must use http or https")
        if self.enabled:
            if not self.key_path or not Path(self.key_path).is_file():
                raise ValueError("test faucet is enabled but CRAKBIT_FAUCET_KEY is missing")
            if not Path(self.genesis_path).is_file():
                raise ValueError("test faucet genesis file was not found")
            if not self.gateway_url and not self.rpc_url.startswith(("http://", "https://")):
                raise ValueError("test faucet RPC must use http or https")


class FaucetState:
    def __init__(self, config: FaucetConfig):
        self.config = config
        self.global_limiter = FixedWindowLimiter(config.global_requests_per_minute, 60)
        self.state_path = Path(config.state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.state_path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS faucet_distributions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address TEXT NOT NULL,
                    amount_atomic INTEGER NOT NULL,
                    txid TEXT NOT NULL,
                    created_at_ms INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_faucet_address_time
                    ON faucet_distributions(address, created_at_ms);
                """
            )

    def cooldown_remaining(self, address: str, now: float | None = None) -> int:
        current = time.time() if now is None else float(now)
        with self.connect() as conn:
            row = conn.execute(
                "SELECT created_at_ms FROM faucet_distributions WHERE address=? "
                "ORDER BY created_at_ms DESC LIMIT 1",
                (address,),
            ).fetchone()
        if row is None:
            return 0
        previous = int(row["created_at_ms"]) / 1000
        remaining = self.config.address_cooldown_seconds - int(current - previous)
        return max(0, remaining)

    def mark_success(self, address: str, txid: str = "", now: float | None = None) -> None:
        created_at_ms = int((time.time() if now is None else float(now)) * 1000)
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO faucet_distributions(address,amount_atomic,txid,created_at_ms) VALUES(?,?,?,?)",
                (address, self.config.amount_atomic, txid, created_at_ms),
            )

    def distribution_count(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) AS n FROM faucet_distributions").fetchone()["n"])


async def _gateway_account(config: FaucetConfig, client: httpx.AsyncClient, address: str) -> dict:
    if config.gateway_url:
        response = await client.get(f"{config.gateway_url}/api/account/{address}")
        response.raise_for_status()
        body = response.json()
        return body.get("account", body)
    response = await client.get(f"{config.rpc_url}/balance/{address}")
    response.raise_for_status()
    return response.json()


async def _broadcast_transaction(config: FaucetConfig, client: httpx.AsyncClient, tx: Transaction) -> httpx.Response:
    if config.gateway_url:
        return await client.post(
            f"{config.gateway_url}/api/transactions",
            json={"transaction": tx.to_dict()},
        )
    return await client.post(
        f"{config.rpc_url}/transactions",
        json={"transaction": tx.to_dict()},
    )


def create_app(config: FaucetConfig | None = None) -> FastAPI:
    config = config or FaucetConfig.from_env()
    state = FaucetState(config)
    app = FastAPI(title="Crakbit Testnet Faucet", version="0.15.0a1")
    app.state.faucet = state

    @app.get("/health")
    def health() -> dict:
        return {
            "ok": True,
            "enabled": config.enabled,
            "test_only": True,
            "amount_atomic": config.amount_atomic,
            "address_cooldown_seconds": config.address_cooldown_seconds,
            "global_requests_per_minute": config.global_requests_per_minute,
            "persistent_address_cooldown": True,
            "distribution_count": state.distribution_count(),
            "broadcast_via_gateway": bool(config.gateway_url),
            "real_value_supported": False,
        }

    @app.post("/request")
    async def request_funds(payload: FaucetRequest, request: Request) -> dict:
        if not config.enabled:
            raise HTTPException(503, "test faucet is disabled")
        address = payload.address.strip().lower()
        if not valid_crakbit_address(address):
            raise HTTPException(400, "invalid Crakbit address")
        client_address = request.headers.get("X-Crakbit-Client-IP") or (
            request.client.host if request.client else "unknown"
        )
        allowed, _ = state.global_limiter.allow(client_address)
        if not allowed:
            raise HTTPException(429, "test faucet global rate limit exceeded")
        remaining = state.cooldown_remaining(address)
        if remaining:
            raise HTTPException(429, f"address faucet cooldown active for {remaining} more seconds")

        genesis = Genesis.load(config.genesis_path)
        key = KeyPair.load(config.key_path)
        if key.address in {validator.address for validator in genesis.validators}:
            raise HTTPException(500, "faucet key must not be a validator consensus key")
        if address == key.address:
            raise HTTPException(400, "faucet cannot send to itself")

        async with httpx.AsyncClient(timeout=10.0) as client_http:
            account = await _gateway_account(config, client_http, key.address)
            nonce = int(account.get("nonce", 0)) + 1
            if int(account.get("balance", 0)) < config.amount_atomic + genesis.min_fee:
                raise HTTPException(503, "test faucet balance is insufficient")

            tx = Transaction(
                chain_id=genesis.chain_id,
                sender=key.address,
                recipient=address,
                amount=config.amount_atomic,
                fee=genesis.min_fee,
                nonce=nonce,
                public_key=key.public_key_b64,
                memo="Crakbit public testnet faucet",
            )
            tx.signature = key.sign(tx.signing_bytes())
            response = await _broadcast_transaction(config, client_http, tx)
            if response.status_code >= 400:
                raise HTTPException(
                    503,
                    detail={
                        "reason": "faucet transaction submission failed",
                        "upstream_status": response.status_code,
                        "upstream_detail": response.text[:240],
                    },
                )
            result = response.json()
            txid = str(result.get("txid") or tx.txid)

        state.mark_success(address, txid)
        return {
            "accepted": True,
            "test_only": True,
            "txid": txid,
            "recipient": address,
            "amount_atomic": config.amount_atomic,
            "symbol": genesis.symbol,
            "persistent_cooldown": True,
            "message": "test units only; no production value is represented",
        }

    return app


app = create_app()
