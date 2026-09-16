from __future__ import annotations

from pathlib import Path

import httpx
from fastapi import HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .explorer_queries import account_activity, recent_blocks
from .models import ATOMIC_UNITS, Transaction
from .secure_node_v14 import create_app as create_v14_app
from .storage import LedgerError


class WalletTransactionEnvelope(BaseModel):
    transaction: dict


def create_app():
    app = create_v14_app()
    app.title = "Crakbit Chain Testnet Node"
    app.version = "0.15.0a1"
    node = app.state.node

    @app.get("/wallet/config")
    def wallet_config() -> dict:
        return {
            "chain_id": node.genesis.chain_id,
            "network": node.genesis.network_name,
            "symbol": node.genesis.symbol,
            "decimals": node.genesis.decimals,
            "atomic_units": ATOMIC_UNITS,
            "min_fee_atomic": node.genesis.min_fee,
            "max_supply_atomic": node.genesis.max_supply,
            "address_prefix": "crk1",
            "signature_scheme": "Ed25519",
            "wallet_key_custody": "client-side-recommended",
            "production_ready": False,
        }

    # Same-origin public API used by the bundled browser wallet when the UI is served
    # directly from a research node. The standalone public gateway exposes the same
    # shape and can switch to the CometBFT path.
    @app.get("/api/network")
    def api_network() -> dict:
        node._sync_round_height()
        return {
            "gateway": "embedded-research-node/0.15",
            "mode": "research",
            "chain_id": node.genesis.chain_id,
            "network": node.genesis.network_name,
            "symbol": node.genesis.symbol,
            "decimals": node.genesis.decimals,
            "min_fee_atomic": node.genesis.min_fee,
            "max_supply_atomic": node.genesis.max_supply,
            "height": node.ledger.height,
            "last_hash": node.ledger.last_hash,
            "validator_count": len(node.genesis.validators),
            "quorum": node.genesis.quorum_size,
            "consensus": "research prevote/precommit path",
            "production_ready": False,
        }

    @app.get("/api/services")
    def api_services() -> dict:
        return {
            "faucet": False,
            "mining": False,
            "mining_is_consensus": False,
            "mining_label": "standalone testnet work-reward service not attached",
        }

    @app.get("/api/account/{address}")
    def api_account(address: str, limit: int = Query(default=50, ge=1, le=100)) -> dict:
        return account_activity(node.ledger, address.strip().lower(), limit)

    @app.get("/api/transactions/{txid}")
    def api_transaction(txid: str) -> dict:
        result = node.ledger.get_transaction(txid.strip().lower())
        if result is None:
            raise HTTPException(404, "transaction not found")
        return result

    @app.post("/api/transactions")
    async def api_submit(payload: WalletTransactionEnvelope) -> dict:
        try:
            tx = Transaction.from_dict(payload.transaction)
            txid = node.submit_transaction(tx)
        except (KeyError, TypeError, ValueError, LedgerError) as exc:
            raise HTTPException(400, str(exc)) from exc
        async with httpx.AsyncClient(timeout=2.0) as client:
            for peer in node.genesis.validators:
                if peer.address == node.key.address:
                    continue
                try:
                    await client.post(
                        f"{peer.peer_url.rstrip('/')}/internal/transaction",
                        json={"transaction": tx.to_dict()},
                    )
                except Exception:
                    pass
        return {"accepted": True, "txid": txid, "broadcast_mode": "embedded-research-rpc"}

    @app.get("/api/blocks")
    def api_blocks(limit: int = Query(default=20, ge=1, le=100)) -> dict:
        items = recent_blocks(node.ledger, limit)
        return {"count": len(items), "items": items}

    @app.get("/api/validators")
    def api_validators() -> dict:
        return {
            "mode": "research",
            "quorum": node.genesis.quorum_size,
            "validators": [
                {"name": item.name, "address": item.address, "peer_url": item.peer_url}
                for item in node.genesis.validators
            ],
        }

    @app.get("/web")
    def web_redirect() -> RedirectResponse:
        return RedirectResponse(url="/ui/")

    webui = Path(__file__).resolve().parent / "webui"
    if webui.is_dir():
        app.mount("/ui", StaticFiles(directory=str(webui), html=True), name="wallet-ui")

    return app


app = create_app()
