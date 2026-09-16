from __future__ import annotations

import hmac
import os
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from .app_protocol import ExecutionProtocolAdapter, PROTOCOL_VERSION
from .genesis import Genesis
from .storage import Ledger, LedgerError


class CheckTxRequest(BaseModel):
    transaction: dict


class PreviewBatchRequest(BaseModel):
    transactions: list[dict]
    fee_recipient: str


@dataclass(frozen=True)
class ExecutionServiceConfig:
    genesis_path: str
    data_dir: str
    bearer_token: str

    @classmethod
    def from_env(cls) -> "ExecutionServiceConfig":
        token = os.environ.get("CRAKBIT_EXECUTION_SERVICE_TOKEN", "")
        config = cls(
            genesis_path=os.environ.get("CRAKBIT_GENESIS", "runtime/genesis.json"),
            data_dir=os.environ.get("CRAKBIT_DATA_DIR", "runtime/data"),
            bearer_token=token,
        )
        config.validate()
        return config

    def validate(self) -> None:
        if not Path(self.genesis_path).is_file():
            raise ValueError("execution service genesis file was not found")
        if len(self.bearer_token) < 24:
            raise ValueError("CRAKBIT_EXECUTION_SERVICE_TOKEN must be at least 24 characters")

    def accepts(self, authorization: str | None) -> bool:
        if not authorization or not authorization.startswith("Bearer "):
            return False
        supplied = authorization[7:]
        return hmac.compare_digest(supplied, self.bearer_token)


def create_app(config: ExecutionServiceConfig | None = None) -> FastAPI:
    config = config or ExecutionServiceConfig.from_env()
    genesis = Genesis.load(config.genesis_path)
    ledger = Ledger(Path(config.data_dir) / "chain.sqlite3", genesis)
    protocol = ExecutionProtocolAdapter(ledger)
    app = FastAPI(title="Crakbit Execution Protocol PoC", version="0.13.0a1")

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        if request.url.path != "/health" and not config.accepts(request.headers.get("authorization")):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
                content={"detail": "execution-service authentication required"},
            )
        return await call_next(request)

    @app.get("/health")
    def health() -> dict:
        return {
            "ok": True,
            "protocol": PROTOCOL_VERSION,
            "mutating_external_consensus_enabled": False,
            "production_ready": False,
        }

    @app.get("/v1/info")
    def info() -> dict:
        return protocol.info()

    @app.post("/v1/check-tx")
    def check_tx(payload: CheckTxRequest) -> dict:
        return protocol.check_transaction(payload.transaction)

    @app.post("/v1/preview-batch")
    def preview_batch(payload: PreviewBatchRequest) -> dict:
        if len(payload.transactions) > 1000:
            raise HTTPException(413, "execution preview is limited to 1000 transactions")
        try:
            return protocol.preview_batch(
                payload.transactions,
                fee_recipient=payload.fee_recipient,
            )
        except (KeyError, TypeError, ValueError, LedgerError) as exc:
            raise HTTPException(400, str(exc)) from exc

    return app
