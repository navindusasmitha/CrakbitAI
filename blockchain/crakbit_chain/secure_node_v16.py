from __future__ import annotations

from .secure_node_v15 import create_app as create_v15_app


def create_app():
    app = create_v15_app()
    app.title = "Crakbit Chain Public-Testnet Candidate Node"
    app.version = "0.16.0a1"

    @app.get("/v16/status")
    def v16_status() -> dict:
        return {
            "version": app.version,
            "public_testnet_candidate": True,
            "production_mainnet": False,
            "external_bft_path": "CometBFT v0.40.0 integration",
            "browser_wallet": True,
            "external_state_checkpoint_adapter": True,
            "dedicated_explorer_index": True,
            "durable_public_rate_limit_components": True,
            "independent_security_review_complete": False,
        }

    return app


app = create_app()
