from __future__ import annotations

import time

from fastapi import Request
from fastapi.responses import JSONResponse

from .integrity import verify_ledger_integrity
from .limits import FixedWindowLimiter, LimitConfig, install_node_limits
from .secure_node_v08 import create_app as create_v08_app


def create_app():
    """Create the v0.10 hardened development RPC.

    v0.10 does not alter consensus semantics. It adds bounded request/mempool behavior,
    public transaction rate limiting and retains the v0.9 integrity/operator endpoints.
    These controls are defense-in-depth for a test network, not a substitute for a
    production reverse proxy, DDoS service, reviewed BFT core or mTLS transport.
    """

    app = create_v08_app()
    app.title = "Crakbit Chain Devnet"
    app.version = "0.10.0a1"

    node = app.state.node
    limits = LimitConfig.from_env()
    install_node_limits(node, limits)
    public_tx_limiter = FixedWindowLimiter(limits.public_tx_requests_per_minute, 60)
    app.state.limit_config = limits
    app.state.public_tx_limiter = public_tx_limiter

    @app.middleware("http")
    async def bounded_rpc(request: Request, call_next):
        path = request.url.path
        internal = path.startswith("/internal/")
        max_body = limits.max_internal_body_bytes if internal else limits.max_public_body_bytes

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                announced = int(content_length)
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "invalid Content-Length"})
            if announced < 0 or announced > max_body:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": "request body too large",
                        "maximum_bytes": max_body,
                    },
                )

        if request.method == "POST" and path == "/transactions":
            client_host = request.client.host if request.client else "unknown"
            allowed, remaining = public_tx_limiter.allow(client_host)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": "60"},
                    content={
                        "detail": "public transaction submission rate limit exceeded",
                        "limit_per_minute": limits.public_tx_requests_per_minute,
                    },
                )
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limits.public_tx_requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response

        return await call_next(request)

    @app.get("/integrity/status")
    def integrity_status(full: bool = False) -> dict:
        return verify_ledger_integrity(node.ledger, full=bool(full))

    @app.get("/operations/status")
    def operations_status() -> dict:
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
            "mempool_transactions": len(node.mempool),
            "mempool_capacity": limits.max_mempool_transactions,
            "production_ready": False,
        }

    @app.get("/limits/status")
    def limits_status() -> dict:
        return {
            "max_public_body_bytes": limits.max_public_body_bytes,
            "max_internal_body_bytes": limits.max_internal_body_bytes,
            "public_tx_requests_per_minute": limits.public_tx_requests_per_minute,
            "max_mempool_transactions": limits.max_mempool_transactions,
            "max_block_transactions": limits.max_block_transactions,
            "max_transaction_bytes": limits.max_transaction_bytes,
            "rate_limit_scope": "per-process direct client IP",
            "reverse_proxy_limits_still_required": True,
            "reported_at_ms": int(time.time() * 1000),
        }

    return app


app = create_app()
