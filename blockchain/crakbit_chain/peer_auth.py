from __future__ import annotations

import os
import secrets
import sqlite3
import time
from pathlib import Path
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


class ReplayNonceStore:
    """Small SQLite-backed replay cache for validator HTTP nonces.

    The cache is deliberately separate from chain state. It survives validator process
    restarts and expires entries after the bounded authentication window.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        with sqlite3.connect(self.path, timeout=30) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS peer_request_nonces (
                    replay_key TEXT PRIMARY KEY,
                    seen_at_ms INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    def check_and_record(self, replay_key: str, now_ms: int, retention_ms: int) -> None:
        cutoff = int(now_ms) - int(retention_ms)
        with self._lock, sqlite3.connect(self.path, timeout=30) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "DELETE FROM peer_request_nonces WHERE seen_at_ms < ?",
                    (cutoff,),
                )
                existing = conn.execute(
                    "SELECT 1 FROM peer_request_nonces WHERE replay_key=?",
                    (replay_key,),
                ).fetchone()
                if existing is not None:
                    conn.execute("ROLLBACK")
                    raise PeerAuthError("replayed peer request")
                conn.execute(
                    "INSERT INTO peer_request_nonces(replay_key,seen_at_ms) VALUES(?,?)",
                    (replay_key, int(now_ms)),
                )
                conn.execute("COMMIT")
            except PeerAuthError:
                raise
            except Exception:
                conn.execute("ROLLBACK")
                raise


class PeerAuthenticator:
    """Verify signed validator-to-validator HTTP requests and reject recent replays.

    v0.7 can persist replay nonces in SQLite. If ``replay_store_path`` is omitted and
    ``CRAKBIT_DATA_DIR`` is set, the replay cache is automatically stored at
    ``<CRAKBIT_DATA_DIR>/peer-replay.sqlite3``. Tests and standalone callers without a
    data directory retain an in-memory cache for backward compatibility.
    """

    def __init__(
        self,
        genesis: Genesis,
        max_skew_ms: int = DEFAULT_MAX_SKEW_MS,
        replay_store_path: str | Path | None = None,
    ):
        self.genesis = genesis
        self.max_skew_ms = int(max_skew_ms)
        if replay_store_path is None:
            data_dir = os.environ.get("CRAKBIT_DATA_DIR")
            if data_dir:
                replay_store_path = Path(data_dir) / "peer-replay.sqlite3"
        self._persistent_store = ReplayNonceStore(replay_store_path) if replay_store_path else None
        self._seen: dict[str, int] = {}
        self._lock = Lock()

    @property
    def replay_store_mode(self) -> str:
        return "sqlite" if self._persistent_store is not None else "memory"

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

    def _check_replay(self, replay_key: str, current: int) -> None:
        retention = self.max_skew_ms * 2
        if self._persistent_store is not None:
            self._persistent_store.check_and_record(replay_key, current, retention)
            return
        with self._lock:
            self._prune(current)
            if replay_key in self._seen:
                raise PeerAuthError("replayed peer request")
            self._seen[replay_key] = current

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

        self._check_replay(f"{address}:{nonce}", current)
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
