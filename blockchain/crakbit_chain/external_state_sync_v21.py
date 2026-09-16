from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .crypto import canonical_json, sha256_hex
from .external_commit_v16 import (
    SNAPSHOT_BASE_APP_HASH_KEY,
    SNAPSHOT_BASE_HEIGHT_KEY,
    SNAPSHOT_BASE_STATE_HASH_KEY,
)
from .external_commit_v21 import COMMIT_PROTOCOL_VERSION_V21, ExternalExecutionStoreV21
from .external_state_sync import _normalized_accounts, accounts_root
from .genesis import Genesis
from .storage import Ledger, LedgerError
from .validator_governance_v21 import (
    GOVERNANCE_STATE_FORMAT,
    SCHEMA_VERSION,
    SCHEMA_VERSION_KEY,
    normalize_validator_set,
    validator_set_hash,
)

EXTERNAL_SNAPSHOT_FORMAT_V21 = "crakbit-external-state-snapshot-v2"


def _is_hex64(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in value)


def _normalize_governance_state(state: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise LedgerError("v0.21 snapshot governance state must be an object")
    active = normalize_validator_set(list(state.get("active_validators") or []))
    pending = list(state.get("pending") or [])
    normalized_pending: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in pending:
        if not isinstance(raw, dict):
            raise LedgerError("v0.21 snapshot pending governance entry is invalid")
        change_id = str(raw.get("change_id", ""))
        if not _is_hex64(change_id) or change_id in seen:
            raise LedgerError("v0.21 snapshot pending governance change_id is invalid")
        seen.add(change_id)
        emit_height = int(raw.get("emit_height", -1))
        effective_height = int(raw.get("effective_height", -1))
        if emit_height < 1 or effective_height != emit_height + 2:
            raise LedgerError("v0.21 snapshot pending governance heights are invalid")
        target = normalize_validator_set(list(raw.get("target_validators") or []))
        target_hash = validator_set_hash(target)
        if str(raw.get("target_set_hash", "")) != target_hash:
            raise LedgerError("v0.21 snapshot pending target validator-set hash mismatch")
        normalized_pending.append(
            {
                "change_id": change_id,
                "emit_height": emit_height,
                "effective_height": effective_height,
                "source_set_hash": str(raw.get("source_set_hash", "")),
                "target_set_hash": target_hash,
                "envelope": raw.get("envelope"),
                "target_validators": target,
                "updates": list(raw.get("updates") or []),
            }
        )
    normalized_pending.sort(key=lambda item: (item["effective_height"], item["change_id"]))
    if len(normalized_pending) > 1:
        raise LedgerError("v0.21 snapshot contains overlapping pending validator changes")
    return {
        "format": GOVERNANCE_STATE_FORMAT,
        "active_validators": active,
        "active_validator_set_hash": validator_set_hash(active),
        "pending": normalized_pending,
    }


def governance_hash(state: dict[str, Any]) -> str:
    normalized = _normalize_governance_state(state)
    return sha256_hex(
        canonical_json(
            {
                "format": GOVERNANCE_STATE_FORMAT,
                "active_validators": normalized["active_validators"],
                "pending": normalized["pending"],
            }
        )
    )


def application_hash_v21(
    *,
    chain_id: str,
    height: int,
    consensus_block_hash: str,
    accounts: list[dict[str, Any]],
    governance_state: dict[str, Any],
) -> str:
    normalized_accounts = _normalized_accounts(accounts)
    governance = _normalize_governance_state(governance_state)
    payload = {
        "protocol": COMMIT_PROTOCOL_VERSION_V21,
        "chain_id": chain_id,
        "height": int(height),
        "consensus_block_hash": str(consensus_block_hash).lower(),
        "accounts": [
            (item["address"], int(item["balance"]), int(item["nonce"]))
            for item in normalized_accounts
        ],
        "validator_governance": {
            "active_validators": governance["active_validators"],
            "pending": governance["pending"],
        },
    }
    return sha256_hex(canonical_json(payload))


def export_external_snapshot_v21(ledger: Ledger) -> dict[str, Any]:
    store = ExternalExecutionStoreV21(ledger)
    status = store.status()
    if status.get("pending_finalize") is not None:
        raise LedgerError("refusing to snapshot while a v0.21 external finalize is pending")
    with ledger.connect() as conn:
        rows = conn.execute(
            "SELECT address,balance,nonce FROM accounts ORDER BY address ASC"
        ).fetchall()
        governance_state = store.governance.state_from_conn(conn)
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
        raise LedgerError("v0.21 state supply invariant failed before snapshot export")
    app_hash = application_hash_v21(
        chain_id=ledger.genesis.chain_id,
        height=ledger.height,
        consensus_block_hash=ledger.last_hash,
        accounts=accounts,
        governance_state=governance_state,
    )
    if app_hash != status["application_hash"]:
        raise LedgerError("v0.21 application hash changed during snapshot export")
    snapshot = {
        "format": EXTERNAL_SNAPSHOT_FORMAT_V21,
        "protocol": COMMIT_PROTOCOL_VERSION_V21,
        "schema_version": SCHEMA_VERSION,
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
        "governance_hash": governance_hash(governance_state),
        "governance_state": _normalize_governance_state(governance_state),
        "created_at_ms": int(time.time() * 1000),
        "source_snapshot_base": status.get("snapshot_base"),
    }
    artifact_hash = sha256_hex(canonical_json(snapshot))
    return {
        "snapshot": snapshot,
        "artifact_hash": artifact_hash,
        "trust_model": "CometBFT light-client-verified v0.21 application hash",
    }


def verify_external_snapshot_v21(
    envelope: dict[str, Any],
    genesis: Genesis,
    *,
    expected_height: int | None = None,
    expected_application_hash: str | None = None,
) -> dict[str, Any]:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("snapshot"), dict):
        raise LedgerError("invalid v0.21 external snapshot envelope")
    snapshot = dict(envelope["snapshot"])
    if snapshot.get("format") != EXTERNAL_SNAPSHOT_FORMAT_V21:
        raise LedgerError("unsupported v0.21 external snapshot format")
    if snapshot.get("protocol") != COMMIT_PROTOCOL_VERSION_V21:
        raise LedgerError("v0.21 external snapshot protocol mismatch")
    if int(snapshot.get("schema_version", -1)) != SCHEMA_VERSION:
        raise LedgerError("v0.21 external snapshot schema mismatch")
    if str(snapshot.get("chain_id")) != genesis.chain_id:
        raise LedgerError("v0.21 external snapshot chain_id mismatch")
    if str(snapshot.get("genesis_fingerprint")) != genesis.fingerprint():
        raise LedgerError("v0.21 external snapshot genesis fingerprint mismatch")
    artifact_hash = sha256_hex(canonical_json(snapshot))
    if artifact_hash != str(envelope.get("artifact_hash")):
        raise LedgerError("v0.21 external snapshot artifact hash mismatch")

    height = int(snapshot.get("height", -1))
    if height < 0:
        raise LedgerError("v0.21 external snapshot height is invalid")
    last_hash = str(snapshot.get("last_consensus_block_hash", ""))
    if not _is_hex64(last_hash):
        raise LedgerError("v0.21 external snapshot consensus block hash is invalid")
    accounts = _normalized_accounts(list(snapshot.get("accounts", [])))
    if int(snapshot.get("account_count", -1)) != len(accounts):
        raise LedgerError("v0.21 external snapshot account count mismatch")
    if accounts_root(accounts) != str(snapshot.get("accounts_root")):
        raise LedgerError("v0.21 external snapshot accounts root mismatch")
    issued = sum(int(item["balance"]) for item in accounts)
    expected_issued = sum(int(value) for value in genesis.allocations.values())
    if issued != int(snapshot.get("issued_atomic_units", -1)) or issued != expected_issued:
        raise LedgerError("v0.21 external snapshot issued supply mismatch")

    governance_state = _normalize_governance_state(dict(snapshot.get("governance_state") or {}))
    if governance_hash(governance_state) != str(snapshot.get("governance_hash")):
        raise LedgerError("v0.21 external snapshot governance hash mismatch")
    app_hash = application_hash_v21(
        chain_id=genesis.chain_id,
        height=height,
        consensus_block_hash=last_hash,
        accounts=accounts,
        governance_state=governance_state,
    )
    if app_hash != str(snapshot.get("application_hash")):
        raise LedgerError("v0.21 external snapshot application hash mismatch")
    if expected_height is not None and height != int(expected_height):
        raise LedgerError("v0.21 external snapshot does not match trusted expected height")
    if expected_application_hash is not None and app_hash.lower() != str(expected_application_hash).lower():
        raise LedgerError("v0.21 external snapshot does not match trusted application hash")
    return {
        "valid": True,
        "height": height,
        "application_hash": app_hash,
        "last_consensus_block_hash": last_hash,
        "artifact_hash": artifact_hash,
        "account_count": len(accounts),
        "issued_atomic_units": issued,
        "active_validator_count": len(governance_state["active_validators"]),
        "pending_validator_changes": len(governance_state["pending"]),
        "governance_hash": str(snapshot["governance_hash"]),
        "trusted_height_checked": expected_height is not None,
        "trusted_application_hash_checked": expected_application_hash is not None,
    }


def import_external_snapshot_v21(
    *,
    envelope: dict[str, Any],
    genesis: Genesis,
    data_dir: str | Path,
    expected_height: int | None = None,
    expected_application_hash: str | None = None,
) -> dict[str, Any]:
    verified = verify_external_snapshot_v21(
        envelope,
        genesis,
        expected_height=expected_height,
        expected_application_hash=expected_application_hash,
    )
    target = Path(data_dir)
    target.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(target / "chain.sqlite3", genesis)
    store = ExternalExecutionStoreV21(ledger)
    with ledger.connect() as conn:
        commits = int(conn.execute("SELECT COUNT(*) AS n FROM external_commits").fetchone()["n"])
        pending_finalize = int(
            conn.execute("SELECT COUNT(*) AS n FROM external_pending_finalizes").fetchone()["n"]
        )
        history = int(
            conn.execute("SELECT COUNT(*) AS n FROM validator_governance_history").fetchone()["n"]
        )
        emissions = int(
            conn.execute("SELECT COUNT(*) AS n FROM validator_governance_emissions").fetchone()["n"]
        )
        current_accounts = {
            str(row["address"]): (int(row["balance"]), int(row["nonce"]))
            for row in conn.execute("SELECT address,balance,nonce FROM accounts")
        }
    expected_accounts = {
        str(address): (int(amount), 0) for address, amount in genesis.allocations.items()
    }
    current_governance = store.governance.state()
    genesis_governance = normalize_validator_set(
        [
            {
                "address": item.address,
                "public_key": item.public_key,
                "name": item.name,
                "power": 1,
            }
            for item in genesis.validators
        ]
    )
    if (
        ledger.height != 0
        or commits
        or pending_finalize
        or history
        or emissions
        or current_accounts != expected_accounts
        or current_governance["active_validators"] != genesis_governance
        or current_governance["pending"]
    ):
        raise LedgerError("v0.21 snapshot import requires a pristine application database")

    snapshot = envelope["snapshot"]
    accounts = _normalized_accounts(list(snapshot["accounts"]))
    governance_state = _normalize_governance_state(dict(snapshot["governance_state"]))
    artifact_hash = str(envelope["artifact_hash"])
    with ledger.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute("DELETE FROM accounts")
            conn.execute("DELETE FROM transactions")
            conn.execute("DELETE FROM external_commits")
            conn.execute("DELETE FROM external_pending_finalizes")
            conn.execute("DELETE FROM validator_governance_validators")
            conn.execute("DELETE FROM validator_governance_pending")
            conn.execute("DELETE FROM validator_governance_history")
            conn.execute("DELETE FROM validator_governance_emissions")
            for item in accounts:
                conn.execute(
                    "INSERT INTO accounts(address,balance,nonce) VALUES(?,?,?)",
                    (item["address"], int(item["balance"]), int(item["nonce"])),
                )
            for validator in governance_state["active_validators"]:
                conn.execute(
                    "INSERT INTO validator_governance_validators(address,public_key,name,power,activated_height) "
                    "VALUES(?,?,?,?,?)",
                    (
                        validator["address"],
                        validator["public_key"],
                        validator["name"],
                        int(validator["power"]),
                        int(snapshot["height"]),
                    ),
                )
            for pending in governance_state["pending"]:
                conn.execute(
                    "INSERT INTO validator_governance_pending("
                    "change_id,emit_height,effective_height,source_set_hash,target_set_hash,envelope_json,"
                    "target_validators_json,updates_json,created_at_ms) VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        pending["change_id"],
                        int(pending["emit_height"]),
                        int(pending["effective_height"]),
                        pending["source_set_hash"],
                        pending["target_set_hash"],
                        json.dumps(pending["envelope"], separators=(",", ":"), sort_keys=True),
                        json.dumps(pending["target_validators"], separators=(",", ":"), sort_keys=True),
                        json.dumps(pending["updates"], separators=(",", ":"), sort_keys=True),
                        int(time.time() * 1000),
                    ),
                )
            conn.execute("UPDATE metadata SET value=? WHERE key='height'", (str(int(snapshot["height"])),))
            conn.execute(
                "UPDATE metadata SET value=? WHERE key='last_hash'",
                (str(snapshot["last_consensus_block_hash"]),),
            )
            for key, value in (
                (SCHEMA_VERSION_KEY, str(SCHEMA_VERSION)),
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

    reopened = ExternalExecutionStoreV21(Ledger(target / "chain.sqlite3", genesis))
    status = reopened.status()
    if status["application_hash"] != verified["application_hash"]:
        raise LedgerError("restored v0.21 application hash does not match snapshot")
    return {
        "imported": True,
        "data_dir": str(target),
        "height": status["height"],
        "application_hash": status["application_hash"],
        "snapshot_base": status["snapshot_base"],
        "active_validator_count": status["validator_governance"]["active_validator_count"],
        "pending_validator_changes": len(status["validator_governance"]["pending"]),
        "historical_commits_recreated": False,
        "governance_history_recreated": False,
    }
