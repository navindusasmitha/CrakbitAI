from __future__ import annotations

from .secure_node import create_app as create_v06_app


def create_app():
    """Create the v0.7 alpha node API on top of the v0.6 secure transport layer.

    v0.7 keeps the consensus engine unchanged while adding durable replay protection and
    quorum-certified snapshot recovery tooling. The recovery endpoint exposes only local
    operational metadata; it does not claim that a snapshot replaces historical blocks.
    """

    app = create_v06_app()
    app.title = "Crakbit Chain Devnet"
    app.version = "0.7.0a1"

    @app.get("/recovery/status")
    def recovery_status() -> dict:
        node = app.state.node
        keys = (
            "snapshot_base_height",
            "snapshot_base_hash",
            "snapshot_accounts_root",
            "snapshot_certificate_hash",
        )
        metadata: dict[str, str | None] = {}
        with node.ledger.connect() as conn:
            for key in keys:
                row = conn.execute(
                    "SELECT value FROM metadata WHERE key=?",
                    (key,),
                ).fetchone()
                metadata[key] = str(row["value"]) if row is not None else None
        return {
            "chain_id": node.genesis.chain_id,
            "height": node.ledger.height,
            "last_hash": node.ledger.last_hash,
            "peer_replay_store": node.peer_authenticator.replay_store_mode,
            "snapshot_bootstrapped": metadata["snapshot_base_height"] is not None,
            **metadata,
        }

    return app


app = create_app()
