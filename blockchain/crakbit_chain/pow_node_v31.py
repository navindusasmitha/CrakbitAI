from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .pow_v31 import PowChain, PowConfig, PowV31Error


class TemplateRequest(BaseModel):
    miner_address: str
    message: str = "Crakbit CPU miner"


class BlockRequest(BaseModel):
    block: dict[str, Any]


class TransactionRequest(BaseModel):
    transaction: dict[str, Any]


class PaymentRequest(BaseModel):
    wallet_path: str
    to_address: str
    amount: int = Field(gt=0)
    fee: int = Field(ge=0)


def create_app(db_path: str | Path | None = None) -> FastAPI:
    path = Path(db_path or os.environ.get("CRAKBIT_POW_DB", "runtime/pow-v31/chain.sqlite3"))
    if not path.exists():
        PowChain(path, PowConfig(), create=True).close()

    app = FastAPI(title="Crakbit PoW Node", version="0.31.0a1")

    def with_chain():
        return PowChain(path)

    @app.get("/pow/v1/health")
    def health() -> dict[str, Any]:
        chain = with_chain()
        try:
            info = chain.info()
            return {"ok": True, "height": info["height"], "chain_id": info["chain_id"], "pow_algo": info["pow_algo"], "production_mainnet_ready": False}
        finally:
            chain.close()

    @app.get("/pow/v1/info")
    def info() -> dict[str, Any]:
        chain = with_chain()
        try:
            return chain.info()
        finally:
            chain.close()

    @app.get("/pow/v1/block/{height}")
    def block(height: int) -> dict[str, Any]:
        chain = with_chain()
        try:
            return chain.get_block(height)
        except PowV31Error as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        finally:
            chain.close()

    @app.get("/pow/v1/balance/{address}")
    def balance(address: str) -> dict[str, Any]:
        chain = with_chain()
        try:
            result = chain.balance(address)
            return {"address": address, **result, "production_mainnet_ready": False}
        finally:
            chain.close()

    @app.get("/pow/v1/utxos/{address}")
    def utxos(address: str) -> dict[str, Any]:
        chain = with_chain()
        try:
            return {"address": address, "utxos": chain.get_utxos(address), "production_mainnet_ready": False}
        finally:
            chain.close()

    @app.get("/pow/v1/mempool")
    def mempool() -> dict[str, Any]:
        chain = with_chain()
        try:
            rows = chain.db.execute("SELECT txid,fee,received_at_ms,tx_json FROM mempool ORDER BY fee DESC,received_at_ms ASC").fetchall()
            return {
                "transactions": [
                    {"txid": str(row["txid"]), "fee": int(row["fee"]), "received_at_ms": int(row["received_at_ms"]), "transaction": __import__("json").loads(row["tx_json"])}
                    for row in rows
                ],
                "production_mainnet_ready": False,
            }
        finally:
            chain.close()

    @app.post("/pow/v1/getblocktemplate")
    def getblocktemplate(request: TemplateRequest) -> dict[str, Any]:
        chain = with_chain()
        try:
            return chain.get_block_template(request.miner_address, message=request.message)
        except PowV31Error as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            chain.close()

    @app.post("/pow/v1/submitblock")
    def submitblock(request: BlockRequest) -> dict[str, Any]:
        chain = with_chain()
        try:
            return chain.submit_block(request.block)
        except PowV31Error as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            chain.close()

    @app.post("/pow/v1/submittransaction")
    def submittransaction(request: TransactionRequest) -> dict[str, Any]:
        chain = with_chain()
        try:
            return chain.submit_transaction(request.transaction)
        except PowV31Error as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            chain.close()

    return app


app = create_app()
