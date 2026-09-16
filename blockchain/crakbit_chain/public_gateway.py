from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .crypto import canonical_json
from .genesis import Genesis
from .models import ATOMIC_UNITS, Transaction


GATEWAY_VERSION = "crakbit-public-gateway/0.15"


def _clean_url(value: str) -> str:
    return value.rstrip("/")


@dataclass(frozen=True)
class GatewayConfig:
    genesis_path: str = "runtime/genesis.json"
    mode: str = "research"
    research_rpc: str = "http://127.0.0.1:9101"
    comet_rpc: str = "http://127.0.0.1:26657"
    execution_url: str = "http://127.0.0.1:26659"
    execution_token: str = ""
    faucet_url: str = ""
    mining_url: str = ""
    request_timeout_seconds: float = 8.0

    @classmethod
    def from_env(cls) -> "GatewayConfig":
        config = cls(
            genesis_path=os.environ.get("CRAKBIT_GATEWAY_GENESIS", "runtime/genesis.json"),
            mode=os.environ.get("CRAKBIT_GATEWAY_MODE", "research").strip().lower(),
            research_rpc=_clean_url(os.environ.get("CRAKBIT_GATEWAY_RESEARCH_RPC", "http://127.0.0.1:9101")),
            comet_rpc=_clean_url(os.environ.get("CRAKBIT_GATEWAY_COMET_RPC", "http://127.0.0.1:26657")),
            execution_url=_clean_url(os.environ.get("CRAKBIT_GATEWAY_EXECUTION_URL", "http://127.0.0.1:26659")),
            execution_token=os.environ.get("CRAKBIT_GATEWAY_EXECUTION_TOKEN", ""),
            faucet_url=_clean_url(os.environ.get("CRAKBIT_GATEWAY_FAUCET_URL", "")),
            mining_url=_clean_url(os.environ.get("CRAKBIT_GATEWAY_MINING_URL", "")),
            request_timeout_seconds=float(os.environ.get("CRAKBIT_GATEWAY_TIMEOUT", "8")),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.mode not in {"research", "cometbft"}:
            raise ValueError("CRAKBIT_GATEWAY_MODE must be research or cometbft")
        if not Path(self.genesis_path).is_file():
            raise ValueError("gateway genesis file was not found")
        for name, value in (
            ("research RPC", self.research_rpc),
            ("CometBFT RPC", self.comet_rpc),
            ("execution service", self.execution_url),
        ):
            if not value.startswith(("http://", "https://")):
                raise ValueError(f"gateway {name} URL must use http or https")
        if self.mode == "cometbft" and len(self.execution_token) < 24:
            raise ValueError("CometBFT gateway mode requires CRAKBIT_GATEWAY_EXECUTION_TOKEN")
        if self.request_timeout_seconds <= 0 or self.request_timeout_seconds > 60:
            raise ValueError("gateway request timeout must be between 0 and 60 seconds")


class TransactionEnvelope(BaseModel):
    transaction: dict


class FaucetProxyRequest(BaseModel):
    address: str


class MiningSubmitProxyRequest(BaseModel):
    address: str
    challenge_id: str
    nonce: int


class GatewayBackend:
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.genesis = Genesis.load(config.genesis_path)

    @property
    def execution_headers(self) -> dict[str, str]:
        if not self.config.execution_token:
            return {}
        return {"Authorization": f"Bearer {self.config.execution_token}"}

    async def comet_rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": "crakbit-gateway",
            "method": method,
            "params": params or {},
        }
        async with httpx.AsyncClient(timeout=self.config.request_timeout_seconds) as client:
            response = await client.post(self.config.comet_rpc, json=payload)
            response.raise_for_status()
            body = response.json()
        if body.get("error"):
            raise HTTPException(502, detail={"upstream": "cometbft", "error": body["error"]})
        return body.get("result", {})

    async def execution_get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.config.request_timeout_seconds) as client:
            response = await client.get(
                f"{self.config.execution_url}{path}",
                params=params,
                headers=self.execution_headers,
            )
        if response.status_code >= 400:
            raise HTTPException(502, detail={"upstream": "execution", "status": response.status_code, "detail": response.text[:300]})
        return response.json()

    async def network(self) -> dict[str, Any]:
        if self.config.mode == "research":
            async with httpx.AsyncClient(timeout=self.config.request_timeout_seconds) as client:
                response = await client.get(f"{self.config.research_rpc}/status")
                response.raise_for_status()
                status = response.json()
                integration: dict[str, Any] = {}
                try:
                    extra = await client.get(f"{self.config.research_rpc}/consensus/integration-status")
                    if extra.status_code == 200:
                        integration = extra.json()
                except Exception:
                    integration = {}
            return {
                "gateway": GATEWAY_VERSION,
                "mode": "research",
                "chain_id": self.genesis.chain_id,
                "network": self.genesis.network_name,
                "symbol": self.genesis.symbol,
                "decimals": self.genesis.decimals,
                "min_fee_atomic": self.genesis.min_fee,
                "max_supply_atomic": self.genesis.max_supply,
                "height": int(status.get("height", 0)),
                "last_hash": str(status.get("last_hash", "")),
                "validator_count": len(self.genesis.validators),
                "quorum": self.genesis.quorum_size,
                "consensus": status.get("consensus"),
                "integration": integration,
                "production_ready": False,
            }

        comet = await self.comet_rpc("status")
        execution = await self.execution_get("/v2/info")
        sync = comet.get("sync_info", {}) if isinstance(comet, dict) else {}
        node_info = comet.get("node_info", {}) if isinstance(comet, dict) else {}
        return {
            "gateway": GATEWAY_VERSION,
            "mode": "cometbft",
            "chain_id": self.genesis.chain_id,
            "network": self.genesis.network_name,
            "symbol": self.genesis.symbol,
            "decimals": self.genesis.decimals,
            "min_fee_atomic": self.genesis.min_fee,
            "max_supply_atomic": self.genesis.max_supply,
            "height": int(execution.get("height", 0)),
            "last_hash": str(execution.get("last_consensus_block_hash", "")),
            "application_hash": execution.get("application_hash"),
            "validator_count": len(self.genesis.validators),
            "quorum": self.genesis.quorum_size,
            "cometbft_node_id": node_info.get("id"),
            "cometbft_latest_height": sync.get("latest_block_height"),
            "cometbft_catching_up": sync.get("catching_up"),
            "consensus": "CometBFT v0.40.0 integration PoC",
            "production_ready": False,
        }

    async def account(self, address: str, limit: int = 50) -> dict[str, Any]:
        if self.config.mode == "research":
            async with httpx.AsyncClient(timeout=self.config.request_timeout_seconds) as client:
                activity = await client.get(
                    f"{self.config.research_rpc}/explorer/address/{address}",
                    params={"limit": limit},
                )
                if activity.status_code == 200:
                    return activity.json()
                balance = await client.get(f"{self.config.research_rpc}/balance/{address}")
                balance.raise_for_status()
                return {"account": balance.json(), "activity": [], "fully_indexed_history": False}
        return await self.execution_get(f"/v2/account/{address}", params={"limit": limit})

    async def transaction(self, txid: str) -> dict[str, Any]:
        if self.config.mode == "research":
            async with httpx.AsyncClient(timeout=self.config.request_timeout_seconds) as client:
                response = await client.get(f"{self.config.research_rpc}/transactions/{txid}")
            if response.status_code == 404:
                raise HTTPException(404, "transaction not found")
            response.raise_for_status()
            return response.json()
        try:
            return await self.execution_get(f"/v2/transaction/{txid}")
        except HTTPException as exc:
            if isinstance(exc.detail, dict) and exc.detail.get("status") == 404:
                raise HTTPException(404, "transaction not found") from exc
            raise

    async def blocks(self, limit: int) -> dict[str, Any]:
        if self.config.mode == "research":
            async with httpx.AsyncClient(timeout=self.config.request_timeout_seconds) as client:
                response = await client.get(
                    f"{self.config.research_rpc}/explorer/blocks",
                    params={"limit": limit},
                )
                response.raise_for_status()
                return response.json()
        return await self.execution_get("/v2/commits", params={"limit": limit})

    async def validators(self) -> dict[str, Any]:
        if self.config.mode == "research":
            async with httpx.AsyncClient(timeout=self.config.request_timeout_seconds) as client:
                response = await client.get(f"{self.config.research_rpc}/validators")
                response.raise_for_status()
                return response.json()
        result = await self.comet_rpc("validators", {"page": "1", "per_page": "100"})
        return {
            "mode": "cometbft",
            "quorum": self.genesis.quorum_size,
            "configured_validators": [
                {"name": item.name, "address": item.address, "public_key": item.public_key}
                for item in self.genesis.validators
            ],
            "cometbft": result,
        }

    async def broadcast(self, raw: dict[str, Any]) -> dict[str, Any]:
        try:
            tx = Transaction.from_dict(raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(400, f"invalid transaction: {exc}") from exc
        if tx.chain_id != self.genesis.chain_id:
            raise HTTPException(400, "transaction chain_id does not match gateway genesis")
        if not tx.verify_signature():
            raise HTTPException(400, "transaction signature is invalid")
        encoded = canonical_json(tx.to_dict())
        if len(encoded) > 64 * 1024:
            raise HTTPException(413, "transaction exceeds gateway size limit")

        if self.config.mode == "research":
            async with httpx.AsyncClient(timeout=self.config.request_timeout_seconds) as client:
                response = await client.post(
                    f"{self.config.research_rpc}/transactions",
                    json={"transaction": tx.to_dict()},
                )
            if response.status_code >= 400:
                raise HTTPException(response.status_code, response.text[:300])
            result = response.json()
            result.setdefault("txid", tx.txid)
            result["broadcast_mode"] = "research-rpc"
            return result

        result = await self.comet_rpc(
            "broadcast_tx_sync",
            {"tx": base64.b64encode(encoded).decode("ascii")},
        )
        code = int(result.get("code", 0) or 0)
        if code != 0:
            raise HTTPException(
                400,
                detail={
                    "reason": "CometBFT CheckTx rejected transaction",
                    "code": code,
                    "log": result.get("log"),
                    "codespace": result.get("codespace"),
                },
            )
        return {
            "accepted": True,
            "txid": tx.txid,
            "broadcast_mode": "cometbft-broadcast-tx-sync",
            "cometbft_hash": result.get("hash"),
            "check_tx": result,
        }


def create_app(config: GatewayConfig | None = None) -> FastAPI:
    config = config or GatewayConfig.from_env()
    backend = GatewayBackend(config)
    app = FastAPI(title="Crakbit Public Wallet Gateway", version="0.15.0a1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.state.gateway_backend = backend

    @app.get("/api/health")
    async def health() -> dict:
        return {
            "ok": True,
            "gateway": GATEWAY_VERSION,
            "mode": config.mode,
            "wallet_key_custody": "client-side-only",
            "production_ready": False,
        }

    @app.get("/api/network")
    async def network() -> dict:
        try:
            return await backend.network()
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"network backend unavailable: {exc}") from exc

    @app.get("/api/services")
    def services() -> dict:
        return {
            "faucet": bool(config.faucet_url),
            "mining": bool(config.mining_url),
            "mining_is_consensus": False,
            "mining_label": "testnet proof-of-work reward lab",
        }

    @app.get("/api/account/{address}")
    async def account(address: str, limit: int = Query(default=50, ge=1, le=100)) -> dict:
        return await backend.account(address.strip().lower(), limit)

    @app.get("/api/transactions/{txid}")
    async def transaction(txid: str) -> dict:
        return await backend.transaction(txid.strip().lower())

    @app.post("/api/transactions")
    async def submit_transaction(payload: TransactionEnvelope) -> dict:
        return await backend.broadcast(payload.transaction)

    @app.get("/api/blocks")
    async def blocks(limit: int = Query(default=20, ge=1, le=100)) -> dict:
        return await backend.blocks(limit)

    @app.get("/api/validators")
    async def validators() -> dict:
        return await backend.validators()

    @app.post("/api/faucet/request")
    async def faucet_request(payload: FaucetProxyRequest, request: Request) -> dict:
        if not config.faucet_url:
            raise HTTPException(503, "testnet faucet is not configured")
        headers = {}
        if request.client:
            headers["X-Crakbit-Client-IP"] = request.client.host
        async with httpx.AsyncClient(timeout=config.request_timeout_seconds) as client:
            response = await client.post(
                f"{config.faucet_url}/request",
                json={"address": payload.address},
                headers=headers,
            )
        if response.status_code >= 400:
            raise HTTPException(response.status_code, response.text[:300])
        return response.json()

    @app.get("/api/mining/challenge")
    async def mining_challenge(
        request: Request,
        address: str = Query(..., min_length=44, max_length=44),
    ) -> dict:
        if not config.mining_url:
            raise HTTPException(503, "test mining service is not configured")
        headers = {}
        if request.client:
            headers["X-Crakbit-Client-IP"] = request.client.host
        async with httpx.AsyncClient(timeout=config.request_timeout_seconds) as client:
            response = await client.get(
                f"{config.mining_url}/challenge",
                params={"address": address},
                headers=headers,
            )
        if response.status_code >= 400:
            raise HTTPException(response.status_code, response.text[:300])
        return response.json()

    @app.post("/api/mining/submit")
    async def mining_submit(payload: MiningSubmitProxyRequest) -> dict:
        if not config.mining_url:
            raise HTTPException(503, "test mining service is not configured")
        async with httpx.AsyncClient(timeout=max(config.request_timeout_seconds, 15.0)) as client:
            response = await client.post(
                f"{config.mining_url}/submit",
                json=payload.model_dump(),
            )
        if response.status_code >= 400:
            raise HTTPException(response.status_code, response.text[:300])
        return response.json()

    @app.get("/")
    def root() -> RedirectResponse:
        return RedirectResponse(url="/ui/")

    webui = Path(__file__).resolve().parent / "webui"
    if webui.is_dir():
        app.mount("/ui", StaticFiles(directory=str(webui), html=True), name="webui")

    return app


app = create_app()
