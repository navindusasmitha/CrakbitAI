from __future__ import annotations

import hashlib
import json
import os
import socket
import ssl
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import httpx


class TransportSecurityError(RuntimeError):
    pass


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def certificate_sha256_from_der(der_bytes: bytes) -> str:
    return hashlib.sha256(der_bytes).hexdigest()


def certificate_sha256_from_pem(path: str | Path) -> str:
    pem = Path(path).read_text(encoding="utf-8")
    der = ssl.PEM_cert_to_DER_cert(pem)
    return certificate_sha256_from_der(der)


def load_pin_map(path: str | Path | None) -> dict[str, str]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TransportSecurityError("peer certificate pin file must contain a JSON object")
    pins: dict[str, str] = {}
    for validator, fingerprint in data.items():
        value = str(fingerprint).lower().replace(":", "")
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise TransportSecurityError(f"invalid SHA-256 certificate pin for {validator}")
        pins[str(validator)] = value
    return pins


@dataclass
class TransportSecurityConfig:
    require_mtls: bool = False
    require_peer_pins: bool = False
    ca_file: str | None = None
    cert_file: str | None = None
    key_file: str | None = None
    pin_file: str | None = None
    pin_cache_seconds: int = 60
    _pins: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _pin_cache: dict[str, tuple[str, float]] = field(default_factory=dict, init=False, repr=False)

    @classmethod
    def from_env(cls) -> "TransportSecurityConfig":
        config = cls(
            require_mtls=_truthy(os.environ.get("CRAKBIT_REQUIRE_MTLS")),
            require_peer_pins=_truthy(os.environ.get("CRAKBIT_REQUIRE_PEER_PINS")),
            ca_file=os.environ.get("CRAKBIT_MTLS_CA") or None,
            cert_file=os.environ.get("CRAKBIT_MTLS_CERT") or None,
            key_file=os.environ.get("CRAKBIT_MTLS_KEY") or None,
            pin_file=os.environ.get("CRAKBIT_PEER_CERT_PINS") or None,
            pin_cache_seconds=max(0, int(os.environ.get("CRAKBIT_PEER_PIN_CACHE_SECONDS", "60"))),
        )
        config.validate()
        return config

    def validate(self) -> None:
        supplied = [self.ca_file, self.cert_file, self.key_file]
        if any(supplied) and not all(supplied):
            raise TransportSecurityError(
                "mTLS requires CRAKBIT_MTLS_CA, CRAKBIT_MTLS_CERT and CRAKBIT_MTLS_KEY together"
            )
        if self.require_mtls and not all(supplied):
            raise TransportSecurityError("CRAKBIT_REQUIRE_MTLS=1 but mTLS files are incomplete")
        for path in supplied:
            if path and not Path(path).is_file():
                raise TransportSecurityError(f"mTLS file not found: {path}")
        if self.pin_file and not Path(self.pin_file).is_file():
            raise TransportSecurityError(f"peer pin file not found: {self.pin_file}")
        self._pins = load_pin_map(self.pin_file)
        if self.require_peer_pins and not self._pins:
            raise TransportSecurityError("peer certificate pins are required but the pin map is empty")

    @property
    def mtls_configured(self) -> bool:
        return bool(self.ca_file and self.cert_file and self.key_file)

    def ssl_context(self) -> ssl.SSLContext | bool:
        if not self.mtls_configured:
            return True
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=self.ca_file)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(certfile=self.cert_file, keyfile=self.key_file)
        return context

    def async_client(self, *, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=timeout, verify=self.ssl_context())

    def validate_peer_url(self, peer_url: str) -> None:
        parsed = urlparse(peer_url)
        if self.require_mtls and parsed.scheme.lower() != "https":
            raise TransportSecurityError("mTLS mode requires HTTPS validator peer URLs")
        if parsed.scheme.lower() not in {"http", "https"}:
            raise TransportSecurityError("validator peer URL must use http or https")

    def _live_peer_fingerprint(self, peer_url: str, *, timeout: float = 3.0) -> str:
        parsed = urlparse(peer_url)
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            raise TransportSecurityError("certificate pinning requires an HTTPS peer URL")
        port = parsed.port or 443
        context = self.ssl_context()
        if context is True:
            context = ssl.create_default_context()
        assert isinstance(context, ssl.SSLContext)
        with socket.create_connection((parsed.hostname, port), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=parsed.hostname) as secured:
                certificate = secured.getpeercert(binary_form=True)
                if not certificate:
                    raise TransportSecurityError("peer did not present a TLS certificate")
                return certificate_sha256_from_der(certificate)

    def verify_peer_certificate(self, validator_address: str, peer_url: str) -> str | None:
        self.validate_peer_url(peer_url)
        expected = self._pins.get(validator_address)
        if expected is None:
            if self.require_peer_pins:
                raise TransportSecurityError(
                    f"missing TLS certificate pin for validator {validator_address}"
                )
            return None

        cached = self._pin_cache.get(validator_address)
        now = time.monotonic()
        if cached and now - cached[1] <= self.pin_cache_seconds:
            observed = cached[0]
        else:
            observed = self._live_peer_fingerprint(peer_url)
            self._pin_cache[validator_address] = (observed, now)
        if observed.lower() != expected.lower():
            raise TransportSecurityError(
                f"TLS certificate pin mismatch for validator {validator_address}"
            )
        return observed

    def status(self) -> dict:
        return {
            "require_mtls": self.require_mtls,
            "mtls_configured": self.mtls_configured,
            "require_peer_pins": self.require_peer_pins,
            "configured_peer_pins": len(self._pins),
            "pin_cache_seconds": self.pin_cache_seconds,
            "ca_configured": bool(self.ca_file),
            "client_certificate_configured": bool(self.cert_file),
        }
