from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Iterable

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .crypto import KeyPair
from .pow_network_v32 import PowNetworkChain, PowNetworkV32Error, PowP2PNode
from .pow_v31 import PowChain, PowConfig, PowV31Error


class TemplateRequest(BaseModel):
    miner_address: str
    message: str = "Crakbit CPU miner"


class BlockRequest(BaseModel):
    block: dict[str, Any]


class TransactionRequest(BaseModel):
    transaction: dict[str, Any]


def create_app(
    db_path: str | Path | None = None,
    *,
    network_key_path: str | Path,
    p2p_host: str = "0.0.0.0",
    p2p_port: int = 28444,
    advertised_endpoint: str | None = None,
    peers: Iterable[str] = (),
    max_peers: int = 32,
) -> FastAPI:
    path = Path(db_path or os.environ.get("CRAKBIT_POW_DB", "runtime/pow-v32/chain.sqlite3"))
    if not path.exists():
        PowChain(path, PowConfig(), create=True).close()
    identity = KeyPair.load(network_key_path)
    network_chain = PowNetworkChain(path)
    p2p = PowP2PNode(
        network_chain,
        identity,
        listen_host=p2p_host,
        listen_port=p2p_port,
        advertised_endpoint=advertised_endpoint,
        seed_peers=peers,
        max_peers=max_peers,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await p2p.start()
        app.state.p2p = p2p
        try:
            yield
        finally:
            await p2p.stop()
            network_chain.close()

    app = FastAPI(title="Crakbit PoW P2P Node", version="0.32.0a1", lifespan=lifespan)

    def with_chain() -> PowNetworkChain:
        return PowNetworkChain(path)

    @app.get("/pow/v2/health")
    @app.get("/pow/v1/health")
    def health() -> dict[str, Any]:
        chain = with_chain()
        try:
            info = chain.info()
            return {
                "ok": True,
                "height": info["height"],
                "chain_id": info["chain_id"],
                "pow_algo": info["pow_algo"],
                "p2p_protocol": info["p2p_protocol"],
                "peer_count": len(p2p.sessions),
                "production_mainnet_ready": False,
            }
        finally:
            chain.close()

    @app.get("/pow/v2/info")
    @app.get("/pow/v1/info")
    def info() -> dict[str, Any]:
        chain = with_chain()
        try:
            return {**chain.info(), "peer_count": len(p2p.sessions), "p2p_listen_port": p2p.listen_port}
        finally:
            chain.close()

    @app.get("/pow/v2/peers")
    def peers_info() -> dict[str, Any]:
        return {
            "node_id": p2p.node_id,
            "peer_count": len(p2p.sessions),
            "peers": p2p.peer_snapshot(),
            "known_endpoints": sorted(p2p.known_endpoints),
            "production_mainnet_ready": False,
        }

    @app.get("/pow/v2/graph")
    def graph(limit: int = 200) -> dict[str, Any]:
        chain = with_chain()
        try:
            return {"blocks": chain.graph(limit=limit), "production_mainnet_ready": False}
        finally:
            chain.close()

    @app.get("/pow/v2/block/{height}")
    @app.get("/pow/v1/block/{height}")
    def block(height: int) -> dict[str, Any]:
        chain = with_chain()
        try:
            return chain.chain.get_block(height)
        except (PowV31Error, PowNetworkV32Error) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        finally:
            chain.close()

    @app.get("/pow/v2/blockhash/{block_hash_value}")
    def blockhash(block_hash_value: str) -> dict[str, Any]:
        chain = with_chain()
        try:
            return chain.get_block_by_hash(block_hash_value)
        except PowNetworkV32Error as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        finally:
            chain.close()

    @app.get("/pow/v2/balance/{address}")
    @app.get("/pow/v1/balance/{address}")
    def balance(address: str) -> dict[str, Any]:
        chain = with_chain()
        try:
            result = chain.chain.balance(address)
            return {"address": address, **result, "production_mainnet_ready": False}
        finally:
            chain.close()

    @app.get("/pow/v2/utxos/{address}")
    @app.get("/pow/v1/utxos/{address}")
    def utxos(address: str) -> dict[str, Any]:
        chain = with_chain()
        try:
            return {"address": address, "utxos": chain.chain.get_utxos(address), "production_mainnet_ready": False}
        finally:
            chain.close()

    @app.get("/pow/v2/mempool")
    @app.get("/pow/v1/mempool")
    def mempool() -> dict[str, Any]:
        chain = with_chain()
        try:
            rows = chain.db.execute("SELECT txid,fee,received_at_ms,tx_json FROM mempool ORDER BY fee DESC,received_at_ms ASC").fetchall()
            return {
                "transactions": [
                    {
                        "txid": str(row["txid"]),
                        "fee": int(row["fee"]),
                        "received_at_ms": int(row["received_at_ms"]),
                        "transaction": json.loads(row["tx_json"]),
                    }
                    for row in rows
                ],
                "production_mainnet_ready": False,
            }
        finally:
            chain.close()

    @app.post("/pow/v2/getblocktemplate")
    @app.post("/pow/v1/getblocktemplate")
    def getblocktemplate(request: TemplateRequest) -> dict[str, Any]:
        chain = with_chain()
        try:
            return chain.chain.get_block_template(request.miner_address, message=request.message)
        except (PowV31Error, PowNetworkV32Error) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            chain.close()

    @app.post("/pow/v2/submitblock")
    @app.post("/pow/v1/submitblock")
    async def submitblock(request: BlockRequest) -> dict[str, Any]:
        chain = with_chain()
        try:
            result = chain.accept_block(request.block, source="rpc")
        except (PowV31Error, PowNetworkV32Error) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            chain.close()
        if result.get("accepted") and not result.get("known"):
            await p2p.announce_block(str(result["block_hash"]))
        return result

    @app.post("/pow/v2/submittransaction")
    @app.post("/pow/v1/submittransaction")
    async def submittransaction(request: TransactionRequest) -> dict[str, Any]:
        chain = with_chain()
        try:
            result = chain.submit_transaction(request.transaction)
        except (PowV31Error, PowNetworkV32Error) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            chain.close()
        await p2p.announce_transaction(str(result["txid"]))
        return result

    return app
