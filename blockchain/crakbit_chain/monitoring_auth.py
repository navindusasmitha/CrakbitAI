from __future__ import annotations

import hmac
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class MonitoringAuthConfig:
    token: str | None = None

    @classmethod
    def from_env(cls) -> "MonitoringAuthConfig":
        value = os.environ.get("CRAKBIT_MONITORING_BEARER_TOKEN")
        token = value.strip() if value and value.strip() else None
        if token is not None and len(token) < 24:
            raise ValueError("CRAKBIT_MONITORING_BEARER_TOKEN must be at least 24 characters")
        return cls(token=token)

    @property
    def enabled(self) -> bool:
        return self.token is not None

    def accepts(self, authorization: str | None) -> bool:
        if not self.enabled:
            return True
        if not authorization or not authorization.startswith("Bearer "):
            return False
        supplied = authorization[7:]
        return hmac.compare_digest(supplied, self.token or "")

    def status(self) -> dict:
        return {
            "monitoring_auth_enabled": self.enabled,
            "scheme": "bearer" if self.enabled else "none",
        }
