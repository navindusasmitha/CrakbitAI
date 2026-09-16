from __future__ import annotations

from pathlib import Path

from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .models import ATOMIC_UNITS
from .secure_node_v14 import create_app as create_v14_app


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

    @app.get("/web")
    def web_redirect() -> RedirectResponse:
        return RedirectResponse(url="/ui/")

    webui = Path(__file__).resolve().parent / "webui"
    if webui.is_dir():
        app.mount("/ui", StaticFiles(directory=str(webui), html=True), name="wallet-ui")

    return app


app = create_app()
