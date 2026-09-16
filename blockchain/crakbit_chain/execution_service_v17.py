from __future__ import annotations

from fastapi import HTTPException, Query
from pydantic import BaseModel

from . import execution_service_v16 as legacy
from .comet_state_sync import CometStateSyncManager
from .storage import LedgerError


class SnapshotOfferRequest(BaseModel):
    height: int
    format: int
    chunks: int
    hash_hex: str
    metadata_base64: str
    app_hash_hex: str


class SnapshotApplyRequest(BaseModel):
    index: int
    chunk_base64: str
    sender: str = ""


def create_app(
    config: legacy.legacy.ExecutionServiceV14Config | None = None,
    *,
    state_sync_manager_cls=CometStateSyncManager,
):
    app = legacy.create_app(config)
    resolved = config or legacy.legacy.ExecutionServiceV14Config.from_env()
    manager = state_sync_manager_cls(genesis=app.state.ledger.genesis, data_dir=resolved.data_dir)
    app.title = "Crakbit External Consensus Execution Service"
    app.version = "0.17.0a1"
    app.state.comet_state_sync = manager

    @app.get("/v3/state-sync/status")
    def state_sync_status() -> dict:
        return manager.status()

    @app.post("/v3/state-sync/materialize")
    def materialize_state_sync_snapshot() -> dict:
        try:
            return manager.materialize_latest()
        except (LedgerError, ValueError) as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/v3/state-sync/snapshots")
    def list_state_sync_snapshots(limit: int = Query(default=2, ge=1, le=10)) -> dict:
        return {"snapshots": manager.list_snapshots(limit=limit)}

    @app.get("/v3/state-sync/chunk")
    def load_state_sync_chunk(
        height: int = Query(..., ge=1),
        format: int = Query(..., ge=1),  # noqa: A002
        chunk: int = Query(..., ge=0),
    ) -> dict:
        import base64

        try:
            raw = manager.load_chunk(height=height, format_id=format, chunk=chunk)
        except LedgerError as exc:
            raise HTTPException(404, str(exc)) from exc
        return {"chunk_base64": base64.b64encode(raw).decode("ascii")}

    @app.post("/v3/state-sync/offer")
    def offer_state_sync_snapshot(payload: SnapshotOfferRequest) -> dict:
        return manager.offer_snapshot(
            {
                "height": payload.height,
                "format": payload.format,
                "chunks": payload.chunks,
                "hash_hex": payload.hash_hex,
                "metadata_base64": payload.metadata_base64,
            },
            trusted_app_hash_hex=payload.app_hash_hex,
        )

    @app.post("/v3/state-sync/apply")
    def apply_state_sync_chunk(payload: SnapshotApplyRequest) -> dict:
        import base64

        try:
            chunk = base64.b64decode(payload.chunk_base64.encode("ascii"), validate=True)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, "invalid chunk_base64") from exc
        return manager.apply_chunk(index=payload.index, chunk=chunk, sender=payload.sender)

    return app


app = create_app()
