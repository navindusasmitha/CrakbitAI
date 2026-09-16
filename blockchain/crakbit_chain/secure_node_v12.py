from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from .execution_adapter import LedgerExecutionAdapter
from .monitoring_auth import MonitoringAuthConfig
from .secure_node_v11 import create_app as create_v11_app


PROTECTED_MONITORING_PATHS = {
    "/metrics",
    "/metrics/prometheus",
    "/operations/status",
    "/integrity/status",
    "/transport/status",
    "/archive/status",
    "/execution/status",
    "/consensus/events",
    "/evidence",
}


def create_app():
    """Create the v0.12 large devnet-hardening application.

    Consensus remains research-only. v0.12 adds an explicit execution boundary,
    archive/history visibility and optional authentication for operator endpoints.
    """

    app = create_v11_app()
    app.title = "Crakbit Chain Devnet"
    app.version = "0.12.0a1"
    node = app.state.node
    execution = LedgerExecutionAdapter(node.ledger)
    monitoring_auth = MonitoringAuthConfig.from_env()
    app.state.execution_adapter = execution
    app.state.monitoring_auth = monitoring_auth

    @app.middleware("http")
    async def protect_monitoring(request: Request, call_next):
        if monitoring_auth.enabled and request.url.path in PROTECTED_MONITORING_PATHS:
            if not monitoring_auth.accepts(request.headers.get("authorization")):
                return JSONResponse(
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                    content={"detail": "operator monitoring authentication required"},
                )
        return await call_next(request)

    @app.get("/execution/status")
    def execution_status() -> dict:
        return {
            "chain_id": node.genesis.chain_id,
            **execution.status(),
            "consensus_direction": "external-reviewed-bft-migration-gate",
            "production_ready": False,
        }

    @app.get("/archive/status")
    def archive_status() -> dict:
        with node.ledger.connect() as conn:
            base = conn.execute(
                "SELECT value FROM metadata WHERE key='snapshot_base_height'"
            ).fetchone()
            imported = conn.execute(
                "SELECT value FROM metadata WHERE key='archive_history_imported_to'"
            ).fetchone()
            archive_hash = conn.execute(
                "SELECT value FROM metadata WHERE key='archive_history_hash'"
            ).fetchone()
            bounds = conn.execute(
                "SELECT MIN(height) AS first_height, MAX(height) AS last_height, COUNT(*) AS n FROM blocks"
            ).fetchone()
        first = int(bounds["first_height"]) if bounds and bounds["first_height"] is not None else None
        last = int(bounds["last_height"]) if bounds and bounds["last_height"] is not None else None
        return {
            "chain_id": node.genesis.chain_id,
            "current_height": node.ledger.height,
            "snapshot_base_height": int(base["value"]) if base is not None else None,
            "archive_history_imported_to": int(imported["value"]) if imported is not None else None,
            "archive_history_hash": str(archive_hash["value"]) if archive_hash is not None else None,
            "stored_block_count": int(bounds["n"]) if bounds else 0,
            "stored_history_first": first,
            "stored_history_last": last,
            "genesis_anchored_history_local": first == 1 if first is not None else node.ledger.height == 0,
        }

    @app.get("/operator/security-status")
    def operator_security_status() -> dict:
        return {
            "chain_id": node.genesis.chain_id,
            "version": app.version,
            **monitoring_auth.status(),
            "transport": node.transport_security.status(),
            "execution_boundary": execution.status(),
            "production_ready": False,
        }

    return app


app = create_app()
