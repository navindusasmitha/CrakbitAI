from __future__ import annotations

from .integrity import verify_ledger_integrity
from .secure_node_v08 import create_app as create_v08_app


def create_app():
    """Create the v0.9 operations/integrity API on top of the v0.8 node.

    Consensus behavior remains unchanged in this phase. v0.9 adds local integrity
    diagnostics intended for operator recovery/testing and does not claim to replace an
    external audit or a mature BFT implementation.
    """

    app = create_v08_app()
    app.title = "Crakbit Chain Devnet"
    app.version = "0.9.0a1"

    @app.get("/integrity/status")
    def integrity_status(full: bool = False) -> dict:
        node = app.state.node
        return verify_ledger_integrity(node.ledger, full=bool(full))

    @app.get("/operations/status")
    def operations_status() -> dict:
        node = app.state.node
        report = verify_ledger_integrity(node.ledger, full=False)
        with node.ledger.connect() as conn:
            base = conn.execute(
                "SELECT value FROM metadata WHERE key='snapshot_base_height'"
            ).fetchone()
        return {
            "chain_id": node.genesis.chain_id,
            "version": app.version,
            "height": node.ledger.height,
            "last_hash": node.ledger.last_hash,
            "snapshot_bootstrapped": base is not None,
            "peer_replay_store": node.peer_authenticator.replay_store_mode,
            "quick_integrity_ok": bool(report["ok"]),
            "quick_integrity_errors": report["errors"],
            "production_ready": False,
        }

    return app


app = create_app()
