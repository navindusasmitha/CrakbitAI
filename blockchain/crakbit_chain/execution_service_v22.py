from __future__ import annotations

from fastapi import Query

from . import execution_service_v21 as legacy
from .governance_history_v22 import governance_history


def create_app(config=None):
    app = legacy.create_app(config)
    app.title = "Crakbit Governed External Execution Service"
    app.version = "0.22.0a1"

    @app.get("/v4/governance/history")
    def v4_governance_history(limit: int = Query(default=100, ge=1, le=1000)) -> dict:
        return governance_history(app.state.ledger, limit=limit)

    @app.get("/v4/governance/emissions")
    def v4_governance_emissions(limit: int = Query(default=100, ge=1, le=1000)) -> dict:
        history = governance_history(app.state.ledger, limit=limit)
        return {
            "chain_id": history["chain_id"],
            "height": history["height"],
            "active_validator_set_hash": history["active_validator_set_hash"],
            "emissions": history["emissions"],
            "production_mainnet_ready": False,
        }

    @app.get("/v4/campaign/readiness")
    def v4_campaign_readiness() -> dict:
        return {
            "package_version": "0.22.0a1",
            "execution_protocol": "crakbit-execution/3",
            "governed_finalize_commit": True,
            "validator_history_read_api": True,
            "cluster_monitor_supported": True,
            "signed_campaign_evidence_supported": True,
            "local_governed_lab_supported": True,
            "campaign_execution_proven": False,
            "independent_review_completed": False,
            "production_mainnet_ready": False,
        }

    return app


app = create_app()
