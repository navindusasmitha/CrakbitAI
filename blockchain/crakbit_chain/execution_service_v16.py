from __future__ import annotations

from . import execution_service_v14 as legacy
from .external_commit_v16 import ExternalExecutionStoreV16
from .external_state_sync import export_external_snapshot


def create_app(config: legacy.ExecutionServiceV14Config | None = None):
    previous_store = legacy.ExternalExecutionStore
    legacy.ExternalExecutionStore = ExternalExecutionStoreV16
    try:
        app = legacy.create_app(config)
    finally:
        legacy.ExternalExecutionStore = previous_store

    app.title = "Crakbit External Consensus Execution Service"
    app.version = "0.16.0a1"
    store = app.state.external_execution

    @app.get("/v2/state-sync/status")
    def state_sync_status() -> dict:
        status = store.status()
        return {
            "version": app.version,
            "protocol": status["protocol"],
            "height": status["height"],
            "application_hash": status["application_hash"],
            "snapshot_base": status.get("snapshot_base"),
            "checkpoint_export_supported": True,
            "checkpoint_restore_supported": True,
            "cometbft_native_state_sync_wiring_complete": False,
            "trust_requirement": (
                "restore only after matching the checkpoint height/application hash "
                "to a separately trusted CometBFT consensus checkpoint"
            ),
            "production_ready": False,
        }

    @app.get("/v2/state-snapshot/latest")
    def latest_state_snapshot() -> dict:
        return export_external_snapshot(app.state.ledger)

    return app


app = create_app()
