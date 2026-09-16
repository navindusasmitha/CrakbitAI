from __future__ import annotations

import os
from pathlib import Path

import httpx
from fastapi import HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .durable_limits import DurableFixedWindowLimiter
from .public_gateway import GatewayConfig, create_app as create_v15_app


SECURITY_PROFILE = "crakbit-web-security/1"
DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'none'; "
    "frame-ancestors 'none'; "
    "form-action 'self'"
)


def _origins() -> list[str]:
    raw = os.environ.get("CRAKBIT_GATEWAY_ALLOWED_ORIGINS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def create_app(config: GatewayConfig | None = None):
    config = config or GatewayConfig.from_env()
    app = create_v15_app(config)
    app.title = "Crakbit Public Wallet Gateway"
    app.version = "0.16.0a1"

    # v0.15 was convenient for local development and allowed CORS from any origin.
    # v0.16 defaults to same-origin only; explicit origins must be configured.
    app.user_middleware = [
        middleware
        for middleware in app.user_middleware
        if middleware.cls is not CORSMiddleware
    ]
    app.middleware_stack = None
    allowed_origins = _origins()
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
            max_age=600,
        )

    rate_db = os.environ.get(
        "CRAKBIT_GATEWAY_RATE_LIMIT_DB",
        "runtime/gateway-rate-limits.sqlite3",
    )
    write_rpm = int(os.environ.get("CRAKBIT_GATEWAY_WRITE_RPM", "60"))
    limiter = DurableFixedWindowLimiter(
        write_rpm,
        60,
        path=Path(rate_db),
        namespace="gateway-write",
    )
    app.state.durable_write_limiter = limiter
    app.state.explorer_index_url = os.environ.get(
        "CRAKBIT_GATEWAY_EXPLORER_URL", ""
    ).rstrip("/")

    protected_writes = {
        "/api/transactions",
        "/api/faucet/request",
        "/api/mining/submit",
    }

    @app.middleware("http")
    async def v16_security(request: Request, call_next):
        if request.method == "POST" and request.url.path in protected_writes:
            client = request.client.host if request.client else "unknown"
            allowed, remaining = limiter.allow(
                f"{request.url.path}:{client}"
            )
            if not allowed:
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=429,
                    content={"detail": "gateway durable write rate limit exceeded"},
                    headers={"Retry-After": "60", "X-RateLimit-Remaining": str(remaining)},
                )
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = DEFAULT_CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
        return response

    @app.get("/api/security/status")
    def security_status() -> dict:
        return {
            "version": app.version,
            "profile": SECURITY_PROFILE,
            "csp": DEFAULT_CSP,
            "cors": {
                "default_same_origin_only": True,
                "explicit_allowed_origins": allowed_origins,
            },
            "durable_write_rate_limit": limiter.status(),
            "trust_forwarded_client_ip": False,
            "upstream_shared_rate_limit_still_required_for_horizontal_scale": True,
            "production_ready": False,
        }

    @app.get("/api/index/health")
    async def index_health() -> dict:
        url = app.state.explorer_index_url
        if not url:
            raise HTTPException(503, "external explorer index service is not configured")
        async with httpx.AsyncClient(timeout=config.request_timeout_seconds) as client:
            response = await client.get(f"{url}/health")
        if response.status_code >= 400:
            raise HTTPException(502, response.text[:300])
        return response.json()

    @app.get("/api/index/summary")
    async def index_summary() -> dict:
        url = app.state.explorer_index_url
        if not url:
            raise HTTPException(503, "external explorer index service is not configured")
        async with httpx.AsyncClient(timeout=config.request_timeout_seconds) as client:
            response = await client.get(f"{url}/summary")
        if response.status_code >= 400:
            raise HTTPException(502, response.text[:300])
        return response.json()

    return app


app = create_app()
