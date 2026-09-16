from __future__ import annotations

import hmac
import os
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel

from .app_protocol import ExecutionProtocolAdapter, PROTOCOL_VERSION
from .external_commit import COMMIT_PROTOCOL_VERSION, ExternalExecutionStore
from .external_replay import replay_safe_stage_finalize
from .explorer_queries import account_activity
from .genesis import Genesis
from .storage import Ledger, LedgerError


class CheckTxRequest(BaseModel):
    transaction: dict


class PreviewBatchRequest(BaseModel):
    transactions: list[dict]
    fee_recipient: str


class ExternalPreviewRequest(BaseModel):
    height: int
    consensus_block_hash: str
    transactions: list[dict]


class ExternalFinalizeRequest(BaseModel):
    height: int
    consensus_block_hash: str
    transactions: list[dict]


@dataclass(frozen=True)
class ExecutionServiceV14Config:
    genesis_path: str
    data_dir: str
    bearer_token: str

    @classmethod
    def from_env(cls) -> "ExecutionServiceV14Config":
        config = cls(
            genesis_path=os.environ.get("CRAKBIT_GENESIS", "runtime/genesis.json"),
            data_dir=os.environ.get("CRAKBIT_EXTERNAL_DATA_DIR", "runtime/external-app"),
            bearer_token=os.environ.get("CRAKBIT_EXECUTION_SERVICE_TOKEN", ""),
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
        return hmac.compare_digest(authorization[7:], self.bearer_token)


def create_app(config: ExecutionServiceV14Config | None = None) -> FastAPI:
    config = config or ExecutionServiceV14Config.from_env()
    genesis = Genesis.load(config.genesis_path)
    ledger = Ledger(Path(config.data_dir) / "chain.sqlite3", genesis)
    legacy_protocol = ExecutionProtocolAdapter(ledger)
    external = ExternalExecutionStore(ledger)

    app = FastAPI(
        title="Crakbit External Consensus Execution Service",
        version="0.15.0a1",
    )
    app.state.ledger = ledger
    app.state.external_execution = external

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        if request.url.path != "/health" and not config.accepts(
            request.headers.get("authorization")
        ):
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
            "preview_protocol": PROTOCOL_VERSION,
            "commit_protocol": COMMIT_PROTOCOL_VERSION,
            "external_consensus_commit_enabled": True,
            "app_ahead_finalize_replay": True,
            "read_api_enabled": True,
            "reviewed_bft_core_integrated": False,
            "production_ready": False,
        }

    # v0.13 compatibility endpoints remain read/preview only.
    @app.get("/v1/info")
    def v1_info() -> dict:
        return legacy_protocol.info()

    @app.post("/v1/check-tx")
    def v1_check_tx(payload: CheckTxRequest) -> dict:
        return legacy_protocol.check_transaction(payload.transaction)

    @app.post("/v1/preview-batch")
    def v1_preview_batch(payload: PreviewBatchRequest) -> dict:
        if len(payload.transactions) > 1000:
            raise HTTPException(413, "execution preview is limited to 1000 transactions")
        try:
            return legacy_protocol.preview_batch(
                payload.transactions,
                fee_recipient=payload.fee_recipient,
            )
        except (KeyError, TypeError, ValueError, LedgerError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/v2/info")
    def v2_info() -> dict:
        return {
            **external.status(),
            "network": genesis.network_name,
            "symbol": genesis.symbol,
            "decimals": genesis.decimals,
            "min_fee_atomic": genesis.min_fee,
            "max_supply_atomic": genesis.max_supply,
        }

    @app.get("/v2/pending")
    def v2_pending() -> dict:
        status = external.status()
        return {
            "protocol": COMMIT_PROTOCOL_VERSION,
            "height": status["height"],
            "pending_finalize": status["pending_finalize"],
        }

    @app.get("/v2/account/{address}")
    def v2_account(address: str, limit: int = Query(default=50, ge=1, le=100)) -> dict:
        return account_activity(ledger, address.strip().lower(), limit)

    @app.get("/v2/transaction/{txid}")
    def v2_transaction(txid: str) -> dict:
        result = ledger.get_transaction(txid.strip().lower())
        if result is None:
            raise HTTPException(404, "transaction not found")
        return result

    @app.get("/v2/commits")
    def v2_commits(limit: int = Query(default=20, ge=1, le=100)) -> dict:
        with ledger.connect() as conn:
            rows = conn.execute(
                "SELECT height,request_hash,application_hash,consensus_block_hash," 
                "transaction_root,transaction_count,fee_recipient,committed_at_ms " 
                "FROM external_commits ORDER BY height DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        items = [
            {
                "height": int(row["height"]),
                "request_hash": str(row["request_hash"]),
                "application_hash": str(row["application_hash"]),
                "hash": str(row["consensus_block_hash"]),
                "consensus_block_hash": str(row["consensus_block_hash"]),
                "transaction_root": str(row["transaction_root"]),
                "transaction_count": int(row["transaction_count"]),
                "fee_recipient": str(row["fee_recipient"]),
                "committed_at_ms": int(row["committed_at_ms"]),
            }
            for row in rows
        ]
        return {"count": len(items), "items": items, "mode": "external-consensus"}

    @app.post("/v2/check-tx")
    def v2_check_tx(payload: CheckTxRequest) -> dict:
        return legacy_protocol.check_transaction(payload.transaction)

    @app.post("/v2/preview-finalize")
    def v2_preview_finalize(payload: ExternalPreviewRequest) -> dict:
        if len(payload.transactions) > 1000:
            raise HTTPException(413, "external finalize preview is limited to 1000 transactions")
        try:
            return external.preview_finalize(
                height=payload.height,
                consensus_block_hash=payload.consensus_block_hash,
                transactions=payload.transactions,
            )
        except (KeyError, TypeError, ValueError, LedgerError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/v2/finalize")
    def v2_finalize(payload: ExternalFinalizeRequest) -> dict:
        if len(payload.transactions) > 1000:
            raise HTTPException(413, "external finalize is limited to 1000 transactions")
        try:
            return replay_safe_stage_finalize(
                external,
                height=payload.height,
                consensus_block_hash=payload.consensus_block_hash,
                transactions=payload.transactions,
            )
        except (KeyError, TypeError, ValueError, LedgerError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/v2/commit")
    def v2_commit() -> dict:
        try:
            return external.commit_pending()
        except LedgerError as exc:
            raise HTTPException(409, str(exc)) from exc

    return app
