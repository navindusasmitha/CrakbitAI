from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel

from . import execution_service_v17 as legacy
from .comet_state_sync_v21 import CometStateSyncManagerV21
from .external_commit_v21 import COMMIT_PROTOCOL_VERSION_V21, ExternalExecutionStoreV21
from .storage import LedgerError
from .validator_governance_v21 import ValidatorGovernanceError


class CheckTxRequestV21(BaseModel):
    transaction: dict[str, Any]


class FinalizeRequestV21(BaseModel):
    height: int
    consensus_block_hash: str
    transactions: list[dict[str, Any]]


def create_app(config=None):
    app = legacy.create_app(config, state_sync_manager_cls=CometStateSyncManagerV21)
    store = ExternalExecutionStoreV21(app.state.ledger)
    app.state.external_execution_v21 = store
    app.title = "Crakbit External Consensus Execution Service"
    app.version = "0.21.0a1"

    @app.get("/v4/health")
    def v4_health() -> dict:
        return {
            "ok": True,
            "protocol": COMMIT_PROTOCOL_VERSION_V21,
            "validator_governance": True,
            "governance_in_application_hash": True,
            "live_abci_validator_updates": True,
            "governance_aware_state_sync": True,
            "production_mainnet_ready": False,
        }

    @app.get("/v4/info")
    def v4_info() -> dict:
        return {
            **store.status(),
            "network": store.ledger.genesis.network_name,
            "symbol": store.ledger.genesis.symbol,
            "decimals": store.ledger.genesis.decimals,
            "min_fee_atomic": store.ledger.genesis.min_fee,
            "max_supply_atomic": store.ledger.genesis.max_supply,
            "schema_version": 21,
        }

    @app.get("/v4/governance/status")
    def v4_governance_status() -> dict:
        return store.governance.status()

    @app.post("/v4/check-tx")
    def v4_check_tx(payload: CheckTxRequestV21) -> dict:
        try:
            return store.check_transaction(payload.transaction)
        except (KeyError, TypeError, ValueError, LedgerError, ValidatorGovernanceError) as exc:
            return {
                "accepted": False,
                "txid": "",
                "error": exc.__class__.__name__,
                "detail": str(exc),
            }

    @app.post("/v4/preview-finalize")
    def v4_preview_finalize(payload: FinalizeRequestV21) -> dict:
        if len(payload.transactions) > 1000:
            raise HTTPException(413, "v0.21 finalize preview is limited to 1000 transactions")
        try:
            return store.preview_finalize(
                height=payload.height,
                consensus_block_hash=payload.consensus_block_hash,
                transactions=payload.transactions,
            )
        except (KeyError, TypeError, ValueError, LedgerError, ValidatorGovernanceError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/v4/finalize")
    def v4_finalize(payload: FinalizeRequestV21) -> dict:
        if len(payload.transactions) > 1000:
            raise HTTPException(413, "v0.21 finalize is limited to 1000 transactions")
        try:
            return store.stage_finalize(
                height=payload.height,
                consensus_block_hash=payload.consensus_block_hash,
                transactions=payload.transactions,
            )
        except (KeyError, TypeError, ValueError, LedgerError, ValidatorGovernanceError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/v4/commit")
    def v4_commit() -> dict:
        try:
            return store.commit_pending()
        except (LedgerError, ValidatorGovernanceError) as exc:
            raise HTTPException(409, str(exc)) from exc

    return app


app = create_app()
