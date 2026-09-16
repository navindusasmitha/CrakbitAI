from __future__ import annotations

import secrets
import time
from threading import Lock
from typing import Mapping

from .crypto import KeyPair, canonical_json, sha256_hex, verify_signature
from .genesis import Genesis, Validator

HEADER_VALIDATOR = "x-crakbit-validator"
HEADER_TIMESTAMP = "x-crakbit-timestamp"
HEADER_NONCE = "x-crakbit-nonce"
HEADER_SIGNATURE = "x-crakbit-signature"
DEFAULT_MAX_SKEW_MS = 30_000


class PeerAuthError(ValueError):
    pass


def peer_request_payload(
    *,
    method: str,
    path: str,
    body: bytes,
    validator: str,
    timestamp_ms: int,
    nonce: str,
) -> bytes:
    return canonical_json(
        {
            "method": method.upper(),
            "path": path,
            "body_sha256": sha256_hex(body),
            "validator": validator,
            "timestamp_ms": int(timestamp_ms),
            "nonce": nonce,
        }
    )


def sign_peer_request(
    key: KeyPair,
    *,
    method: str,
    path: str,
    body: bytes,
    timestamp_ms: int | None = None,
    nonce: str | None = None,
) -> dict[str, str]:
    timestamp_ms = int(time.time() * 1000) if timestamp_ms is None else int(timestamp_ms)
    nonce = nonce or secrets.token_hex(16)
    payload = peer_request_payload(
        method=method,
        path=path,
        body=body,
        validator=key.address,
        timestamp_ms=timestamp_ms,
        nonce=nonce,
    )
    return {
        "X-Crakbit-Validator": key.address,
        "X-Crakbit-Timestamp": str(timestamp_ms),
        "X-Crakbit-Nonce": nonce,
        "X-Crakbit-Signature": key.sign(payload),
    }


class PeerAuthenticator:
    """Verify signed validator-to-validator HTTP requests and reject recent replays.

    Replay tracking is intentionally process-local in v0.6. Timestamp validation bounds the
    replay window after a restart; a production network should persist or otherwise harden
    replay state at the transport/session layer.
    """

    def __init__(self, genesis: Genesis, max_skew_ms: int = DEFAULT_MAX_SKEW_MS):
        self.genesis = genesis
        self.max_skew_ms = int(max_skew_ms)
        self._seen: dict[str, int] = {}
        self._lock = Lock()

    @staticmethod
    def _get(headers: Mapping[str, str], name: str) -> str:
        value = headers.get(name) or headers.get(name.lower()) or headers.get(name.title())
        if not value:
            raise PeerAuthError(f"missing peer authentication header: {name}")
        return str(value)

    def _prune(self, now_ms: int) -> None:
        cutoff = now_ms - (self.max_skew_ms * 2)
        stale = [key for key, seen_at in self._seen.items() if seen_at < cutoff]
        for key in stale:
            self._seen.pop(key, None)

    def verify(
        self,
        headers: Mapping[str, str],
        *,
        method: str,
        path: str,
        body: bytes,
        now_ms: int | None = None,
    ) -> Validator:
        address = self._get(headers, HEADER_VALIDATOR)
        timestamp_raw = self._get(headers, HEADER_TIMESTAMP)
        nonce = self._get(headers, HEADER_NONCE)
        signature = self._get(headers, HEADER_SIGNATURE)

        try:
            timestamp_ms = int(timestamp_raw)
        except ValueError as exc:
            raise PeerAuthError("invalid peer authentication timestamp") from exc

        current = int(time.time() * 1000) if now_ms is None else int(now_ms)
        if abs(current - timestamp_ms) > self.max_skew_ms:
            raise PeerAuthError("peer authentication timestamp outside accepted window")
        if len(nonce) < 16 or len(nonce) > 128:
            raise PeerAuthError("invalid peer authentication nonce")

        validator = self.genesis.validator_by_address(address)
        if validator is None:
            raise PeerAuthError("peer is not a configured validator")

        payload = peer_request_payload(
            method=method,
            path=path,
            body=body,
            validator=address,
            timestamp_ms=timestamp_ms,
            nonce=nonce,
        )
        if not verify_signature(validator.public_key, payload, signature):
            raise PeerAuthError("invalid peer request signature")

        replay_key = f"{address}:{nonce}"
        with self._lock:
            self._prune(current)
            if replay_key in self._seen:
                raise PeerAuthError("replayed peer request")
            self._seen[replay_key] = current
        return validator


def build_hello_payload(
    key: KeyPair,
    *,
    chain_id: str,
    challenge: str,
    timestamp_ms: int | None = None,
) -> dict:
    timestamp_ms = int(time.time() * 1000) if timestamp_ms is None else int(timestamp_ms)
    hello = {
        "chain_id": chain_id,
        "address": key.address,
        "public_key": key.public_key_b64,
        "challenge": challenge,
        "timestamp_ms": timestamp_ms,
    }
    return {"hello": hello, "signature": key.sign(canonical_json(hello))}


def verify_hello_response(
    peer: Validator,
    response: dict,
    *,
    chain_id: str,
    challenge: str,
    now_ms: int | None = None,
    max_skew_ms: int = DEFAULT_MAX_SKEW_MS,
) -> dict:
    hello = dict(response.get("hello") or {})
    signature = str(response.get("signature") or "")
    if hello.get("chain_id") != chain_id:
        raise PeerAuthError("peer hello chain_id mismatch")
    if hello.get("address") != peer.address or hello.get("public_key") != peer.public_key:
        raise PeerAuthError("peer hello identity mismatch")
    if hello.get("challenge") != challenge:
        raise PeerAuthError("peer hello challenge mismatch")
    try:
        timestamp_ms = int(hello["timestamp_ms"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PeerAuthError("peer hello timestamp invalid") from exc
    current = int(time.time() * 1000) if now_ms is None else int(now_ms)
    if abs(current - timestamp_ms) > int(max_skew_ms):
        raise PeerAuthError("peer hello timestamp outside accepted window")
    if not verify_signature(peer.public_key, canonical_json(hello), signature):
        raise PeerAuthError("invalid peer hello signature")
    return hello
