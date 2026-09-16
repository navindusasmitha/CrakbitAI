from __future__ import annotations

from fastapi import Query

from .app_protocol import ExecutionProtocolAdapter
from .explorer_queries import account_activity, explorer_summary, recent_blocks
from .secure_node_v12 import create_app as create_v12_app


def create_app():
    """Create the v0.13 large-phase devnet application.

    v0.13 exposes a deterministic application-protocol status boundary and bounded,
    read-only explorer queries. It does not expose an alternate mutating consensus path.
    """

    app = create_v12_app()
    app.title = "Crakbit Chain Devnet"
    app.version = "0.13.0a1"
    node = app.state.node
    protocol = ExecutionProtocolAdapter(node.ledger)
    app.state.execution_protocol = protocol

    @app.get("/protocol/status")
    def protocol_status() -> dict:
        return {
            **protocol.info(),
            "external_consensus_poc": True,
            "reviewed_bft_core_integrated": False,
        }

    @app.get("/explorer/summary")
    def explorer_network_summary() -> dict:
        return {
            **explorer_summary(node.ledger),
            "version": app.version,
            "test_network": True,
            "production_ready": False,
        }

    @app.get("/explorer/blocks")
    def explorer_recent_blocks(limit: int = Query(default=20, ge=1, le=100)) -> dict:
        items = recent_blocks(node.ledger, limit)
        return {"count": len(items), "items": items}

    @app.get("/explorer/address/{address}")
    def explorer_address(address: str, limit: int = Query(default=50, ge=1, le=100)) -> dict:
        return account_activity(node.ledger, address, limit)

    return app


app = create_app()
