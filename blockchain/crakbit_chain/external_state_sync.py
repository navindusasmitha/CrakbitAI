from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .crypto import canonical_json, sha256_hex
from .external_commit import COMMIT_PROTOCOL_VERSION
from .external_commit_v16 import (
    SNAPSHOT_BASE_APP_HASH_KEY,
    SNAPSHOT_BASE_HEIGHT_KEY,
    SNAPSHOT_BASE_STATE_HASH_KEY,
    ExternalExecutionStoreV16,
)
from .genesis import Genesis
from .storage import Ledger, LedgerError


EXTERNAL_SNAPSHOT_FORMAT = "crakbit-external-state-snapshot-v1"


def _is_hex64(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in value)


def _normalized_accounts(accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in accounts:
        address = str(item["address"])
        balance = int(item["balance"])
        nonce = int(item["nonce"])
        if not address.startswith("crk1") or len(address) != 44:
            raise LedgerError("external snapshot contains invalid account address")
        if address in seen:
            raise LedgerError("external snapshot contains duplicate account address")
        if balance < 0 or nonce < 0:
            raise LedgerError("external snapshot contains negative account state")
        seen.add(address)
        normalized.append({"address": address, "balance": balance, "nonce": nonce})
    normalized.sort(key=lambda item: item["address"])
    return normalized


def accounts_root(accounts: list[dict[str, Any]]) -> str:
    normalized = _normalized_accounts(accounts)
    payload = [
        (item["address"], int(item["balance"]), int(item["nonce"]))
        for item in normalized
    ]
    return sha256_hex(canonical_json(payload))


def application_hash(
    *,
    chain_id: str,
    height: int,
    consensus_block_hash: str,
    accounts: list[dict[str, Any]],
) -> str:
    normalized = _normalized_accounts(accounts)
    payload = {
        "protocol": COMMIT_PROTOCOL_VERSION,
        "chain_id": chain_id,
        "height": int(height),
        "consensus_block_hash": str(consensus_block_hash),
        "accounts": [
            (item["address"], int(item["balance"]), int(item["nonce"]))
            for item in normalized
        ],
    }
    return sha256_hex(canonical_json(payload))


def export_external_snapshot(ledger: Ledger) -> dict[str, Any]:
    store = ExternalExecutionStoreV16(ledger)
    status = store.status()
    if status.get("pending_finalize") is not None:
        raise LedgerError("refusing to snapshot while an external finalize is pending")

    with ledger.connect() as conn:
        rows = conn.execute(
            "SELECT address,balance,nonce FROM accounts ORDER BY address ASC"
        ).fetchall()
    accounts = [
        {
            "address": str(row["address"]),
            "balance": int(row["balance"]),
            "nonce": int(row["nonce"]),
        }
        for row in rows
    ]
    issued = sum(item["balance"] for item in accounts)
    expected_issued = sum(int(value) for value in ledger.genesis.allocations.values())
    if issued != expected_issued:
        raise LedgerError("external state supply invariant failed before snapshot export")

    app_hash = application_hash(
        chain_id=ledger.genesis.chain_id,
        height=ledger.height,
        consensus_block_hash=ledger.last_hash,
        accounts=accounts,
    )
    if app_hash != status["application_hash"]:
        raise LedgerError("external state application hash changed during snapshot export")

    snapshot = {
        "format": EXTERNAL_SNAPSHOT_FORMAT,
        "protocol": COMMIT_PROTOCOL_VERSION,
        "chain_id": ledger.genesis.chain_id,
        "network": ledger.genesis.network_name,
        "genesis_fingerprint": ledger.genesis.fingerprint(),
        "height": ledger.height,
        "last_consensus_block_hash": ledger.last_hash,
        "application_hash": app_hash,
        "accounts_root": accounts_root(accounts),
        "issued_atomic_units": issued,
        "account_count": len(accounts),
        "accounts": accounts,
        "created_at_ms": int(time.time() * 1000),
        "source_snapshot_base": status.get("snapshot_base"),
    }
    artifact_hash = sha256_hex(canonical_json(snapshot))
    return {
        "snapshot": snapshot,
        "artifact_hash": artifact_hash,
        "trust_model": (
            "verify artifact and application hash against a trusted CometBFT height/app-hash "
            "checkpoint before restore"
        ),
    }


def verify_external_snapshot(
    envelope: dict[str, Any],
    genesis: Genesis,
    *,
    expected_height: int | None = None,
    expected_application_hash: str | None = None,
) -> dict[str, Any]:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("snapshot"), dict):
        raise LedgerError("invalid external snapshot envelope")
    snapshot = dict(envelope["snapshot"])
    if snapshot.get("format") != EXTERNAL_SNAPSHOT_FORMAT:
        raise LedgerError("unsupported external snapshot format")
    if snapshot.get("protocol") != COMMIT_PROTOCOL_VERSION:
        raise LedgerError("external snapshot protocol mismatch")
    if str(snapshot.get("chain_id")) != genesis.chain_id:
        raise LedgerError("external snapshot chain_id mismatch")
    if str(snapshot.get("genesis_fingerprint")) != genesis.fingerprint():
        raise LedgerError("external snapshot genesis fingerprint mismatch")

    artifact_hash = sha256_hex(canonical_json(snapshot))
    if artifact_hash != str(envelope.get("artifact_hash")):
        raise LedgerError("external snapshot artifact hash mismatch")

    height = int(snapshot.get("height", -1))
    if height < 0:
        raise LedgerError("external snapshot height is invalid")
    last_hash = str(snapshot.get("last_consensus_block_hash", ""))
    if not _is_hex64(last_hash):
        raise LedgerError("external snapshot consensus block hash is invalid")

    accounts = _normalized_accounts(list(snapshot.get("accounts", [])))
    if int(snapshot.get("account_count", -1)) != len(accounts):
        raise LedgerError("external snapshot account count mismatch")
    root = accounts_root(accounts)
    if root != str(snapshot.get("accounts_root")):
        raise LedgerError("external snapshot accounts root mismatch")

    issued = sum(int(item["balance"]) for item in accounts)
    expected_issued = sum(int(value) for value in genesis.allocations.values())
    if issued != int(snapshot.get("issued_atomic_units", -1)):
        raise LedgerError("external snapshot issued supply field mismatch")
    if issued != expected_issued:
        raise LedgerError("external snapshot violates fixed issued-supply invariant")

    app_hash = application_hash(
        chain_id=genesis.chain_id,
        height=height,
        consensus_block_hash=last_hash,
        accounts=accounts,
    )
    if app_hash != str(snapshot.get("application_hash")):
        raise LedgerError("external snapshot application hash mismatch")
    if expected_height is not None and height != int(expected_height):
        raise LedgerError("external snapshot does not match trusted expected height")
    if expected_application_hash is not None and app_hash.lower() != str(
        expected_application_hash
    ).lower():
        raise LedgerError("external snapshot does not match trusted expected application hash")

    return {
        "valid": True,
        "height": height,
        "application_hash": app_hash,
        "last_consensus_block_hash": last_hash,
        "artifact_hash": artifact_hash,
        "account_count": len(accounts),
        "issued_atomic_units": issued,
        "trusted_height_checked": expected_height is not None,
        "trusted_application_hash_checked": expected_application_hash is not None,
    }


def import_external_snapshot(
    *,
    envelope: dict[str, Any],
    genesis: Genesis,
    data_dir: str | Path,
    expected_height: int | None = None,
    expected_application_hash: str | None = None,
) -> dict[str, Any]:
    verified = verify_external_snapshot(
        envelope,
        genesis,
        expected_height=expected_height,
        expected_application_hash=expected_application_hash,
    )
    target = Path(data_dir)
    target.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(target / "chain.sqlite3", genesis)
    store = ExternalExecutionStoreV16(ledger)

    if ledger.height != 0:
        raise LedgerError("external snapshot import requires a fresh application database")
    with ledger.connect() as conn:
        commits = int(conn.execute("SELECT COUNT(*) AS n FROM external_commits").fetchone()["n"])
        pending = int(
            conn.execute("SELECT COUNT(*) AS n FROM external_pending_finalizes").fetchone()["n"]
        )
        current_accounts = {
            str(row["address"]): (int(row["balance"]), int(row["nonce"]))
            for row in conn.execute("SELECT address,balance,nonce FROM accounts").fetchall()
        }
    expected_accounts = {
        str(address): (int(amount), 0) for address, amount in genesis.allocations.items()
    }
    if commits or pending or current_accounts != expected_accounts:
        raise LedgerError("external snapshot import target is not a pristine genesis database")

    snapshot = envelope["snapshot"]
    accounts = _normalized_accounts(list(snapshot["accounts"]))
    artifact_hash = str(envelope["artifact_hash"])
    with ledger.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute("DELETE FROM accounts")
            conn.execute("DELETE FROM transactions")
            conn.execute("DELETE FROM external_commits")
            conn.execute("DELETE FROM external_pending_finalizes")
            for item in accounts:
                conn.execute(
                    "INSERT INTO accounts(address,balance,nonce) VALUES(?,?,?)",
                    (item["address"], int(item["balance"]), int(item["nonce"])),
                )
            conn.execute(
                "UPDATE metadata SET value=? WHERE key='height'",
                (str(int(snapshot["height"])),),
            )
            conn.execute(
                "UPDATE metadata SET value=? WHERE key='last_hash'",
                (str(snapshot["last_consensus_block_hash"]),),
            )
            for key, value in (
                (SNAPSHOT_BASE_HEIGHT_KEY, str(int(snapshot["height"]))),
                (SNAPSHOT_BASE_APP_HASH_KEY, str(snapshot["application_hash"])),
                (SNAPSHOT_BASE_STATE_HASH_KEY, artifact_hash),
            ):
                conn.execute(
                    "INSERT INTO metadata(key,value) VALUES(?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    reopened = ExternalExecutionStoreV16(Ledger(target / "chain.sqlite3", genesis))
    status = reopened.status()
    if status["application_hash"] != verified["application_hash"]:
        raise LedgerError("restored external application hash does not match snapshot")
    return {
        "imported": True,
        "data_dir": str(target),
        "height": status["height"],
        "application_hash": status["application_hash"],
        "snapshot_base": status["snapshot_base"],
        "historical_commits_recreated": False,
    }


def load_snapshot(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_snapshot(envelope: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"snapshot already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    return target
