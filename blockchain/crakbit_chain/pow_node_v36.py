from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from fastapi import FastAPI

from .pow_node_v32 import create_app
from .pow_ops_v34 import PeerBookV34
from .pow_network_v32 import parse_peer_endpoint


class PowNodeV36Error(ValueError):
    pass


def select_seed_peers_v36(
    *,
    peer_db: str | Path | None,
    explicit_peers: Iterable[str] = (),
    limit: int = 16,
    max_per_bucket: int = 2,
) -> dict[str, Any]:
    limit = max(1, min(int(limit), 128))
    max_per_bucket = max(1, min(int(max_per_bucket), 16))
    explicit: list[str] = []
    for peer in explicit_peers:
        endpoint = str(peer).strip()
        if not endpoint:
            continue
        parse_peer_endpoint(endpoint)
        if endpoint not in explicit:
            explicit.append(endpoint)

    persisted: list[str] = []
    if peer_db is not None and Path(peer_db).exists():
        book = PeerBookV34(peer_db)
        try:
            persisted = book.select(limit=limit, max_per_bucket=max_per_bucket)
        finally:
            book.close()

    selected: list[str] = []
    for endpoint in explicit + persisted:
        if endpoint not in selected:
            selected.append(endpoint)
        if len(selected) >= limit:
            break
    return {
        "format": "crakbit-peer-seed-selection-v36/1",
        "selected_peers": selected,
        "explicit_peer_count": len(explicit),
        "persisted_candidate_count": len(persisted),
        "limit": limit,
        "max_per_bucket": max_per_bucket,
        "peer_db_used": None if peer_db is None else str(peer_db),
        "coarse_diversity_only": True,
        "asn_operator_diversity_not_proven": True,
        "production_mainnet_ready": False,
    }


def create_app_v36(
    db_path: str | Path,
    *,
    network_key_path: str | Path,
    peer_db: str | Path | None = None,
    explicit_peers: Iterable[str] = (),
    p2p_host: str = "0.0.0.0",
    p2p_port: int = 28444,
    advertised_endpoint: str | None = None,
    max_peers: int = 32,
    seed_limit: int = 16,
    max_per_bucket: int = 2,
) -> FastAPI:
    selection = select_seed_peers_v36(
        peer_db=peer_db,
        explicit_peers=explicit_peers,
        limit=seed_limit,
        max_per_bucket=max_per_bucket,
    )
    app = create_app(
        db_path,
        network_key_path=network_key_path,
        p2p_host=p2p_host,
        p2p_port=p2p_port,
        advertised_endpoint=advertised_endpoint,
        peers=selection["selected_peers"],
        max_peers=max_peers,
    )
    app.title = "Crakbit PoW P2P Node v0.36"
    app.version = "0.36.0a1"

    @app.get("/pow/v36/seed-policy")
    def seed_policy() -> dict[str, Any]:
        return selection

    return app


def run_node_v36(
    *,
    db_path: str | Path,
    network_key_path: str | Path,
    peer_db: str | Path | None = None,
    explicit_peers: Iterable[str] = (),
    rpc_host: str = "127.0.0.1",
    rpc_port: int = 28443,
    p2p_host: str = "0.0.0.0",
    p2p_port: int = 28444,
    advertised_endpoint: str | None = None,
    max_peers: int = 32,
    seed_limit: int = 16,
    max_per_bucket: int = 2,
) -> None:
    import uvicorn

    app = create_app_v36(
        db_path,
        network_key_path=network_key_path,
        peer_db=peer_db,
        explicit_peers=explicit_peers,
        p2p_host=p2p_host,
        p2p_port=p2p_port,
        advertised_endpoint=advertised_endpoint,
        max_peers=max_peers,
        seed_limit=seed_limit,
        max_per_bucket=max_per_bucket,
    )
    uvicorn.run(app, host=str(rpc_host), port=int(rpc_port), log_level="info")
