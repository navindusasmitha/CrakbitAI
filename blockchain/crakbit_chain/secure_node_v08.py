from __future__ import annotations

from fastapi import HTTPException

from .secure_node_v07 import create_app as create_v07_app
from .snapshot_transfer import build_snapshot_bundle, chunk_response
from .snapshots import sign_snapshot, snapshot_import_journal_status
from .storage import LedgerError


def _metadata(node, key: str) -> str | None:
    with node.ledger.connect() as conn:
        row = conn.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        return str(row["value"]) if row is not None else None


def create_app():
    """Create the v0.8 recovery/transfer API on top of the v0.7 secure node.

    Consensus is intentionally unchanged in this phase. v0.8 focuses on bounded chunked
    snapshot transfer, resumable client downloads, crash-visible import journaling and
    explicit history semantics for nodes bootstrapped from a snapshot.
    """

    app = create_v07_app()
    app.title = "Crakbit Chain Devnet"
    app.version = "0.8.0a1"
    app.state.snapshot_bundle_cache = {}

    @app.get("/snapshot/bundle/manifest")
    def snapshot_bundle_manifest(chunk_size: int = 64 * 1024) -> dict:
        node = app.state.node
        try:
            envelope = sign_snapshot(node.ledger, node.key)
            manifest, chunks = build_snapshot_bundle(envelope, chunk_size=chunk_size)
        except LedgerError as exc:
            raise HTTPException(400, str(exc)) from exc

        artifact_hash = str(manifest["artifact_sha256"])
        cache: dict = app.state.snapshot_bundle_cache
        cache[artifact_hash] = (manifest, chunks)
        while len(cache) > 4:
            oldest = next(iter(cache))
            if oldest == artifact_hash and len(cache) == 1:
                break
            cache.pop(oldest, None)

        return {
            **manifest,
            "snapshot_height": int(envelope["snapshot"]["height"]),
            "snapshot_hash": str(envelope["snapshot_hash"]),
            "signer": str(envelope["signer"]),
        }

    @app.get("/snapshot/bundle/chunk/{artifact_sha256}/{index}")
    def snapshot_bundle_chunk(artifact_sha256: str, index: int) -> dict:
        cached = app.state.snapshot_bundle_cache.get(artifact_sha256)
        if cached is None:
            raise HTTPException(404, "snapshot bundle not cached or expired; request a fresh manifest")
        manifest, chunks = cached
        try:
            return chunk_response(manifest, chunks, index)
        except LedgerError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/history/status")
    def history_status() -> dict:
        node = app.state.node
        base_raw = _metadata(node, "snapshot_base_height")
        base_height = int(base_raw) if base_raw is not None else None
        return {
            "chain_id": node.genesis.chain_id,
            "current_height": node.ledger.height,
            "snapshot_bootstrapped": base_height is not None,
            "snapshot_base_height": base_height,
            "snapshot_base_hash": _metadata(node, "snapshot_base_hash"),
            "local_block_history_start": (base_height + 1) if base_height is not None else 1,
            "pre_snapshot_history_local": base_height is None,
        }

    @app.get("/history/block/{height}")
    def history_block(height: int) -> dict:
        if height < 1:
            raise HTTPException(400, "height must be at least 1")
        node = app.state.node
        result = node.ledger.get_block(height)
        if result is not None:
            return {"available": True, "block": result}
        base_raw = _metadata(node, "snapshot_base_height")
        if base_raw is not None and height <= int(base_raw):
            raise HTTPException(
                410,
                detail={
                    "reason": "history_not_local_after_snapshot_bootstrap",
                    "requested_height": height,
                    "snapshot_base_height": int(base_raw),
                    "snapshot_base_hash": _metadata(node, "snapshot_base_hash"),
                },
            )
        raise HTTPException(404, "block not found")

    @app.get("/recovery/import-journal")
    def recovery_import_journal() -> dict:
        node = app.state.node
        return snapshot_import_journal_status(node.ledger)

    return app


app = create_app()
