from __future__ import annotations

import os
from pathlib import Path

from . import pow_mining as legacy
from .durable_limits import DurableFixedWindowLimiter


def create_app(config: legacy.MiningConfig | None = None):
    config = config or legacy.MiningConfig.from_env()
    os.environ.setdefault(
        "CRAKBIT_RATE_LIMIT_DB",
        str(Path(config.state_path).with_name("public-rate-limits.sqlite3")),
    )
    previous_namespace = os.environ.get("CRAKBIT_RATE_LIMIT_NAMESPACE")
    os.environ["CRAKBIT_RATE_LIMIT_NAMESPACE"] = "mining-challenge"
    previous_limiter = legacy.FixedWindowLimiter
    legacy.FixedWindowLimiter = DurableFixedWindowLimiter
    try:
        app = legacy.create_app(config)
    finally:
        legacy.FixedWindowLimiter = previous_limiter
        if previous_namespace is None:
            os.environ.pop("CRAKBIT_RATE_LIMIT_NAMESPACE", None)
        else:
            os.environ["CRAKBIT_RATE_LIMIT_NAMESPACE"] = previous_namespace

    app.title = "Crakbit Testnet Work Reward"
    app.version = "0.16.0a1"

    @app.get("/security/status")
    def security_status() -> dict:
        return {
            "version": app.version,
            "persistent_challenge_and_reward_state": True,
            "persistent_challenge_request_limit": True,
            "rate_limit_backend": "sqlite",
            "horizontal_shared_upstream_limit_required": True,
            "consensus_mining": False,
            "test_only": True,
        }

    return app


app = create_app()
