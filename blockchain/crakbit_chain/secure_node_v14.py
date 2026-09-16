from __future__ import annotations

from .secure_node_v13 import create_app as create_v13_app


COMETBFT_PIN = "v0.40.0"
EXTERNAL_EXECUTION_PROTOCOL = "crakbit-execution/2"


def create_app():
    app = create_v13_app()
    app.title = "Crakbit Chain Devnet"
    app.version = "0.14.0a1"

    @app.get("/consensus/integration-status")
    def consensus_integration_status() -> dict:
        return {
            "version": app.version,
            "research_python_consensus_active": True,
            "external_bft_bridge_available": True,
            "external_bft_candidate": "CometBFT",
            "external_bft_version_pin": COMETBFT_PIN,
            "external_execution_protocol": EXTERNAL_EXECUTION_PROTOCOL,
            "abci_bridge": "blockchain/cometbft-app",
            "external_commit_service": "execution_service_v14",
            "external_bft_active_in_this_node": False,
            "production_ready": False,
        }

    return app


app = create_app()
