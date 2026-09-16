from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any

from .crypto import KeyPair, address_from_public_key, canonical_json, sha256_hex, verify_signature
from .genesis import Genesis
from .storage import Ledger, LedgerError

GOVERNANCE_FORMAT = "crakbit-validator-governance-tx/1"
GOVERNANCE_STATE_FORMAT = "crakbit-validator-governance-state/1"
SCHEMA_VERSION_KEY = "application_schema_version"
SCHEMA_VERSION = 21
KINDS = {"join", "remove", "replace"}


class ValidatorGovernanceError(LedgerError):
    pass


def _validate_public_key(value: str) -> str:
    try:
        raw = base64.b64decode(str(value).encode("ascii"), validate=True)
    except Exception as exc:  # noqa: BLE001
        raise ValidatorGovernanceError("validator public key must be valid base64") from exc
    if len(raw) != 32:
        raise ValidatorGovernanceError("validator Ed25519 public key must be exactly 32 bytes")
    return str(value)


def _normalize_validator(item: dict[str, Any]) -> dict[str, Any]:
    public_key = _validate_public_key(str(item["public_key"]))
    address = str(item.get("address") or address_from_public_key(public_key)).lower()
    if address != address_from_public_key(public_key):
        raise ValidatorGovernanceError("validator address/public-key mismatch")
    power = int(item["power"])
    if power <= 0:
        raise ValidatorGovernanceError("active validator power must be positive")
    return {
        "address": address,
        "public_key": public_key,
        "name": str(item.get("name") or "validator"),
        "power": power,
    }


def normalize_validator_set(validators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = [_normalize_validator(item) for item in validators]
    normalized.sort(key=lambda item: item["address"])
    addresses = [item["address"] for item in normalized]
    public_keys = [item["public_key"] for item in normalized]
    if len(set(addresses)) != len(addresses):
        raise ValidatorGovernanceError("validator set contains duplicate addresses")
    if len(set(public_keys)) != len(public_keys):
        raise ValidatorGovernanceError("validator set contains duplicate public keys")
    if not normalized:
        raise ValidatorGovernanceError("validator set may not be empty")
    return normalized


def validator_set_hash(validators: list[dict[str, Any]]) -> str:
    normalized = normalize_validator_set(validators)
    return sha256_hex(
        canonical_json(
            [
                (item["address"], item["public_key"], item["name"], int(item["power"]))
                for item in normalized
            ]
        )
    )


def genesis_validator_set(genesis: Genesis) -> list[dict[str, Any]]:
    return normalize_validator_set(
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


def governance_signing_payload(envelope: dict[str, Any]) -> bytes:
    request = envelope.get("request")
    if not isinstance(request, dict):
        raise ValidatorGovernanceError("governance envelope is missing request")
    change_id = str(envelope.get("change_id", ""))
    expected = sha256_hex(canonical_json(request))
    if change_id != expected:
        raise ValidatorGovernanceError("governance change_id mismatch")
    return canonical_json(
        {
            "format": GOVERNANCE_FORMAT,
            "change_id": change_id,
            "request": request,
        }
    )


def governance_txid(envelope: dict[str, Any]) -> str:
    return sha256_hex(canonical_json(envelope))


def _apply_updates(
    validators: list[dict[str, Any]], updates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    current = {item["address"]: dict(item) for item in normalize_validator_set(validators)}
    for raw in updates:
        public_key = _validate_public_key(str(raw["public_key"]))
        address = str(raw.get("address") or address_from_public_key(public_key)).lower()
        if address != address_from_public_key(public_key):
            raise ValidatorGovernanceError("validator update address/public-key mismatch")
        power = int(raw["power"])
        operation = str(raw.get("operation") or ("remove" if power == 0 else "add"))
        if power == 0:
            existing = current.get(address)
            if existing is None or existing["public_key"] != public_key:
                raise ValidatorGovernanceError("validator removal does not match active validator")
            current.pop(address)
        else:
            if power < 1:
                raise ValidatorGovernanceError("validator power must be positive")
            if address in current:
                raise ValidatorGovernanceError("validator addition already exists")
            if any(item["public_key"] == public_key for item in current.values()):
                raise ValidatorGovernanceError("validator public key already exists")
            current[address] = {
                "address": address,
                "public_key": public_key,
                "name": str(raw.get("name") or "validator-new"),
                "power": power,
            }
        if operation not in {"add", "remove"}:
            raise ValidatorGovernanceError("unsupported validator update operation")
    if not current:
        raise ValidatorGovernanceError("validator change may not remove the final validator")
    return normalize_validator_set(list(current.values()))


def _build_updates(
    *,
    validators: list[dict[str, Any]],
    kind: str,
    existing_address: str | None,
    new_public_key: str | None,
    new_name: str,
    new_power: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if kind not in KINDS:
        raise ValidatorGovernanceError(f"kind must be one of: {', '.join(sorted(KINDS))}")
    active = normalize_validator_set(validators)
    by_address = {item["address"]: item for item in active}
    updates: list[dict[str, Any]] = []

    if kind in {"remove", "replace"}:
        address = str(existing_address or "").lower().strip()
        existing = by_address.get(address)
        if existing is None:
            raise ValidatorGovernanceError("existing validator address is not active")
        updates.append(
            {
                "operation": "remove",
                "address": existing["address"],
                "public_key": existing["public_key"],
                "power": 0,
                "name": existing["name"],
            }
        )

    if kind in {"join", "replace"}:
        if not new_public_key:
            raise ValidatorGovernanceError("new_public_key is required for join/replace")
        if int(new_power) <= 0:
            raise ValidatorGovernanceError("new validator power must be positive")
        public_key = _validate_public_key(new_public_key)
        address = address_from_public_key(public_key)
        updates.append(
            {
                "operation": "add",
                "address": address,
                "public_key": public_key,
                "power": int(new_power),
                "name": str(new_name).strip() or "validator-new",
            }
        )

    target = _apply_updates(active, updates)
    return updates, target


class ValidatorGovernanceStore:
    def __init__(self, ledger: Ledger, *, allow_pristine_initialize: bool = True):
        self.ledger = ledger
        self.genesis = ledger.genesis
        self._init_schema(allow_pristine_initialize=allow_pristine_initialize)

    def _init_schema(self, *, allow_pristine_initialize: bool) -> None:
        with self.ledger.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS validator_governance_validators (
                    address TEXT PRIMARY KEY,
                    public_key TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    power INTEGER NOT NULL,
                    activated_height INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS validator_governance_pending (
                    change_id TEXT PRIMARY KEY,
                    emit_height INTEGER UNIQUE NOT NULL,
                    effective_height INTEGER UNIQUE NOT NULL,
                    source_set_hash TEXT NOT NULL,
                    target_set_hash TEXT NOT NULL,
                    envelope_json TEXT NOT NULL,
                    target_validators_json TEXT NOT NULL,
                    updates_json TEXT NOT NULL,
                    created_at_ms INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS validator_governance_history (
                    change_id TEXT PRIMARY KEY,
                    emit_height INTEGER NOT NULL,
                    effective_height INTEGER NOT NULL,
                    source_set_hash TEXT NOT NULL,
                    target_set_hash TEXT NOT NULL,
                    envelope_json TEXT NOT NULL,
                    target_validators_json TEXT NOT NULL,
                    updates_json TEXT NOT NULL,
                    applied_height INTEGER NOT NULL,
                    applied_at_ms INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS validator_governance_emissions (
                    height INTEGER PRIMARY KEY,
                    change_id TEXT UNIQUE NOT NULL,
                    updates_json TEXT NOT NULL
                );
                """
            )
            row = conn.execute(
                "SELECT value FROM metadata WHERE key=?", (SCHEMA_VERSION_KEY,)
            ).fetchone()
            schema_version = int(row["value"]) if row is not None else 19
            active_count = int(
                conn.execute("SELECT COUNT(*) AS n FROM validator_governance_validators").fetchone()["n"]
            )
            external_count = int(
                conn.execute("SELECT COUNT(*) AS n FROM external_commits").fetchone()["n"]
            )
            pending_finalize_count = int(
                conn.execute("SELECT COUNT(*) AS n FROM external_pending_finalizes").fetchone()["n"]
            )
            pristine = self.ledger.height == 0 and external_count == 0 and pending_finalize_count == 0

            if schema_version < SCHEMA_VERSION:
                if not allow_pristine_initialize or not pristine:
                    raise ValidatorGovernanceError(
                        "existing application database requires the v0.21 offline schema migration before governance is enabled"
                    )
                conn.execute(
                    "INSERT INTO metadata(key,value) VALUES(?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (SCHEMA_VERSION_KEY, str(SCHEMA_VERSION)),
                )
            elif schema_version > SCHEMA_VERSION:
                raise ValidatorGovernanceError("application schema is newer than this v0.21 implementation")

            if active_count == 0:
                if not pristine:
                    raise ValidatorGovernanceError(
                        "validator governance active set is missing from a non-pristine database"
                    )
                for item in genesis_validator_set(self.genesis):
                    conn.execute(
                        "INSERT INTO validator_governance_validators(address,public_key,name,power,activated_height) "
                        "VALUES(?,?,?,?,0)",
                        (item["address"], item["public_key"], item["name"], int(item["power"])),
                    )

    def active_validators_from_conn(self, conn) -> list[dict[str, Any]]:
        rows = conn.execute(
            "SELECT address,public_key,name,power FROM validator_governance_validators ORDER BY address"
        ).fetchall()
        return normalize_validator_set(
            [
                {
                    "address": str(row["address"]),
                    "public_key": str(row["public_key"]),
                    "name": str(row["name"]),
                    "power": int(row["power"]),
                }
                for row in rows
            ]
        )

    def active_validators(self) -> list[dict[str, Any]]:
        with self.ledger.connect() as conn:
            return self.active_validators_from_conn(conn)

    def pending_from_conn(self, conn) -> list[dict[str, Any]]:
        rows = conn.execute(
            "SELECT change_id,emit_height,effective_height,source_set_hash,target_set_hash,"
            "envelope_json,target_validators_json,updates_json FROM validator_governance_pending "
            "ORDER BY effective_height,change_id"
        ).fetchall()
        return [
            {
                "change_id": str(row["change_id"]),
                "emit_height": int(row["emit_height"]),
                "effective_height": int(row["effective_height"]),
                "source_set_hash": str(row["source_set_hash"]),
                "target_set_hash": str(row["target_set_hash"]),
                "envelope": json.loads(str(row["envelope_json"])),
                "target_validators": json.loads(str(row["target_validators_json"])),
                "updates": json.loads(str(row["updates_json"])),
            }
            for row in rows
        ]

    def state_from_conn(self, conn) -> dict[str, Any]:
        active = self.active_validators_from_conn(conn)
        pending = self.pending_from_conn(conn)
        return {
            "format": GOVERNANCE_STATE_FORMAT,
            "active_validators": active,
            "active_validator_set_hash": validator_set_hash(active),
            "pending": pending,
        }

    def state(self) -> dict[str, Any]:
        with self.ledger.connect() as conn:
            return self.state_from_conn(conn)

    def governance_hash_from_state(self, state: dict[str, Any]) -> str:
        payload = {
            "format": GOVERNANCE_STATE_FORMAT,
            "active_validators": normalize_validator_set(list(state["active_validators"])),
            "pending": list(state.get("pending") or []),
        }
        return sha256_hex(canonical_json(payload))

    def governance_hash(self) -> str:
        return self.governance_hash_from_state(self.state())

    def verify_envelope(
        self,
        envelope: dict[str, Any],
        *,
        active_validators: list[dict[str, Any]] | None = None,
        expected_emit_height: int | None = None,
        require_quorum: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(envelope, dict) or envelope.get("type") != "validator_governance":
            raise ValidatorGovernanceError("not a validator-governance transaction")
        if envelope.get("format") != GOVERNANCE_FORMAT:
            raise ValidatorGovernanceError("unsupported validator-governance transaction format")
        request = envelope.get("request")
        if not isinstance(request, dict):
            raise ValidatorGovernanceError("governance request is missing")
        governance_signing_payload(envelope)
        if str(request.get("chain_id")) != self.genesis.chain_id:
            raise ValidatorGovernanceError("governance chain_id mismatch")
        if str(request.get("genesis_fingerprint")) != self.genesis.fingerprint():
            raise ValidatorGovernanceError("governance genesis fingerprint mismatch")
        kind = str(request.get("kind"))
        if kind not in KINDS:
            raise ValidatorGovernanceError("invalid governance change kind")
        emit_height = int(request.get("emit_height", -1))
        effective_height = int(request.get("effective_height", -1))
        if emit_height < 1 or effective_height != emit_height + 2:
            raise ValidatorGovernanceError("invalid governance activation-height relationship")
        if expected_emit_height is not None and emit_height != int(expected_emit_height):
            raise ValidatorGovernanceError("governance request is not scheduled for this FinalizeBlock height")

        active = normalize_validator_set(active_validators or self.active_validators())
        source_hash = validator_set_hash(active)
        if str(request.get("source_validator_set_hash")) != source_hash:
            raise ValidatorGovernanceError("governance source validator-set hash does not match committed state")
        updates = list(request.get("updates") or [])
        if not updates:
            raise ValidatorGovernanceError("governance request contains no validator updates")
        target = _apply_updates(active, updates)
        target_hash = validator_set_hash(target)
        if str(request.get("target_validator_set_hash")) != target_hash:
            raise ValidatorGovernanceError("governance target validator-set hash mismatch")

        by_address = {item["address"]: item for item in active}
        approvals = list(envelope.get("approvals") or [])
        seen: set[str] = set()
        approved_power = 0
        payload = governance_signing_payload(envelope)
        for approval in approvals:
            address = str(approval.get("validator", "")).lower()
            if address in seen:
                raise ValidatorGovernanceError("duplicate validator approval")
            validator = by_address.get(address)
            if validator is None:
                raise ValidatorGovernanceError("approval signer is not in the source validator set")
            public_key = str(approval.get("public_key", ""))
            if public_key != validator["public_key"]:
                raise ValidatorGovernanceError("approval public key does not match source validator")
            if not verify_signature(public_key, payload, str(approval.get("signature", ""))):
                raise ValidatorGovernanceError("invalid validator governance approval signature")
            seen.add(address)
            approved_power += int(validator["power"])

        total_power = sum(int(item["power"]) for item in active)
        quorum = approved_power * 3 > total_power * 2
        if require_quorum and not quorum:
            raise ValidatorGovernanceError("validator governance request does not have >2/3 approval power")
        return {
            "valid": True,
            "change_id": str(envelope["change_id"]),
            "kind": kind,
            "emit_height": emit_height,
            "effective_height": effective_height,
            "source_validator_set_hash": source_hash,
            "target_validator_set_hash": target_hash,
            "target_validators": target,
            "updates": updates,
            "approval_count": len(seen),
            "approved_power": approved_power,
            "total_power": total_power,
            "quorum": quorum,
            "txid": governance_txid(envelope),
        }

    def _activate_due_on_state(
        self,
        *,
        active: list[dict[str, Any]],
        pending: list[dict[str, Any]],
        height: int,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        current = normalize_validator_set(active)
        remaining: list[dict[str, Any]] = []
        activated: list[dict[str, Any]] = []
        for item in pending:
            effective = int(item["effective_height"])
            if effective < int(height):
                raise ValidatorGovernanceError("stale unapplied validator governance change detected")
            if effective == int(height):
                current = normalize_validator_set(list(item["target_validators"]))
                activated.append(item)
            else:
                remaining.append(item)
        return current, remaining, activated

    def simulate_height(
        self,
        conn,
        *,
        height: int,
        envelope: dict[str, Any] | None,
    ) -> dict[str, Any]:
        state = self.state_from_conn(conn)
        active, remaining, activated = self._activate_due_on_state(
            active=list(state["active_validators"]),
            pending=list(state["pending"]),
            height=height,
        )
        updates: list[dict[str, Any]] = []
        verified = None
        if envelope is not None:
            if remaining:
                raise ValidatorGovernanceError(
                    "overlapping validator governance changes are disabled until the pending change activates"
                )
            verified = self.verify_envelope(
                envelope,
                active_validators=active,
                expected_emit_height=height,
                require_quorum=True,
            )
            pending_item = {
                "change_id": verified["change_id"],
                "emit_height": verified["emit_height"],
                "effective_height": verified["effective_height"],
                "source_set_hash": verified["source_validator_set_hash"],
                "target_set_hash": verified["target_validator_set_hash"],
                "envelope": envelope,
                "target_validators": verified["target_validators"],
                "updates": verified["updates"],
            }
            remaining.append(pending_item)
            updates = list(verified["updates"])
        next_state = {
            "format": GOVERNANCE_STATE_FORMAT,
            "active_validators": active,
            "active_validator_set_hash": validator_set_hash(active),
            "pending": remaining,
        }
        return {
            "state": next_state,
            "governance_hash": self.governance_hash_from_state(next_state),
            "activated": activated,
            "new_change": verified,
            "validator_updates": updates,
        }

    def commit_height(
        self,
        conn,
        *,
        height: int,
        envelope: dict[str, Any] | None,
    ) -> dict[str, Any]:
        simulated = self.simulate_height(conn, height=height, envelope=envelope)
        for item in simulated["activated"]:
            target = normalize_validator_set(list(item["target_validators"]))
            conn.execute("DELETE FROM validator_governance_validators")
            for validator in target:
                conn.execute(
                    "INSERT INTO validator_governance_validators(address,public_key,name,power,activated_height) "
                    "VALUES(?,?,?,?,?)",
                    (
                        validator["address"],
                        validator["public_key"],
                        validator["name"],
                        int(validator["power"]),
                        int(height),
                    ),
                )
            conn.execute("DELETE FROM validator_governance_pending WHERE change_id=?", (item["change_id"],))
            conn.execute(
                "INSERT OR REPLACE INTO validator_governance_history("
                "change_id,emit_height,effective_height,source_set_hash,target_set_hash,envelope_json,"
                "target_validators_json,updates_json,applied_height,applied_at_ms) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    item["change_id"],
                    int(item["emit_height"]),
                    int(item["effective_height"]),
                    item["source_set_hash"],
                    item["target_set_hash"],
                    json.dumps(item["envelope"], separators=(",", ":"), sort_keys=True),
                    json.dumps(item["target_validators"], separators=(",", ":"), sort_keys=True),
                    json.dumps(item["updates"], separators=(",", ":"), sort_keys=True),
                    int(height),
                    int(time.time() * 1000),
                ),
            )

        verified = simulated["new_change"]
        if verified is not None:
            if conn.execute("SELECT 1 FROM validator_governance_pending LIMIT 1").fetchone() is not None:
                raise ValidatorGovernanceError("a validator governance change is already pending")
            conn.execute(
                "INSERT INTO validator_governance_pending("
                "change_id,emit_height,effective_height,source_set_hash,target_set_hash,envelope_json,"
                "target_validators_json,updates_json,created_at_ms) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    verified["change_id"],
                    int(verified["emit_height"]),
                    int(verified["effective_height"]),
                    verified["source_validator_set_hash"],
                    verified["target_validator_set_hash"],
                    json.dumps(envelope, separators=(",", ":"), sort_keys=True),
                    json.dumps(verified["target_validators"], separators=(",", ":"), sort_keys=True),
                    json.dumps(verified["updates"], separators=(",", ":"), sort_keys=True),
                    int(time.time() * 1000),
                ),
            )
            conn.execute(
                "INSERT OR REPLACE INTO validator_governance_emissions(height,change_id,updates_json) VALUES(?,?,?)",
                (
                    int(height),
                    verified["change_id"],
                    json.dumps(verified["updates"], separators=(",", ":"), sort_keys=True),
                ),
            )
        return simulated

    def emission_for_height(self, conn, height: int) -> list[dict[str, Any]]:
        row = conn.execute(
            "SELECT updates_json FROM validator_governance_emissions WHERE height=?", (int(height),)
        ).fetchone()
        return json.loads(str(row["updates_json"])) if row is not None else []

    def status(self) -> dict[str, Any]:
        with self.ledger.connect() as conn:
            state = self.state_from_conn(conn)
            history_count = int(
                conn.execute("SELECT COUNT(*) AS n FROM validator_governance_history").fetchone()["n"]
            )
            emission_count = int(
                conn.execute("SELECT COUNT(*) AS n FROM validator_governance_emissions").fetchone()["n"]
            )
        return {
            "schema_version": SCHEMA_VERSION,
            "active_validator_count": len(state["active_validators"]),
            "active_validator_set_hash": state["active_validator_set_hash"],
            "active_validators": state["active_validators"],
            "pending": state["pending"],
            "governance_hash": self.governance_hash_from_state(state),
            "history_count": history_count,
            "emission_count": emission_count,
            "quorum_rule": "strictly greater than two-thirds of current voting power",
            "production_mainnet_ready": False,
        }


def build_governance_request(
    *,
    genesis_path: str | Path,
    data_dir: str | Path,
    kind: str,
    emit_height: int,
    existing_address: str | None = None,
    new_public_key: str | None = None,
    new_name: str = "validator-new",
    new_power: int = 1,
) -> dict[str, Any]:
    genesis = Genesis.load(genesis_path)
    ledger = Ledger(Path(data_dir) / "chain.sqlite3", genesis)
    store = ValidatorGovernanceStore(ledger, allow_pristine_initialize=True)
    state = store.state()
    if state["pending"]:
        raise ValidatorGovernanceError("cannot build a new governance request while a change is pending")
    if int(emit_height) <= ledger.height:
        raise ValidatorGovernanceError("emit_height must be greater than the committed application height")
    updates, target = _build_updates(
        validators=list(state["active_validators"]),
        kind=kind,
        existing_address=existing_address,
        new_public_key=new_public_key,
        new_name=new_name,
        new_power=new_power,
    )
    request = {
        "chain_id": genesis.chain_id,
        "genesis_fingerprint": genesis.fingerprint(),
        "kind": kind,
        "emit_height": int(emit_height),
        "effective_height": int(emit_height) + 2,
        "source_validator_set_hash": state["active_validator_set_hash"],
        "target_validator_set_hash": validator_set_hash(target),
        "updates": updates,
    }
    return {
        "type": "validator_governance",
        "format": GOVERNANCE_FORMAT,
        "change_id": sha256_hex(canonical_json(request)),
        "request": request,
        "approvals": [],
    }


def sign_governance_request(
    envelope: dict[str, Any],
    *,
    genesis_path: str | Path,
    data_dir: str | Path,
    signing_key_path: str | Path,
) -> dict[str, Any]:
    genesis = Genesis.load(genesis_path)
    ledger = Ledger(Path(data_dir) / "chain.sqlite3", genesis)
    store = ValidatorGovernanceStore(ledger, allow_pristine_initialize=True)
    store.verify_envelope(envelope, active_validators=store.active_validators(), require_quorum=False)
    key = KeyPair.load(signing_key_path)
    active = {item["address"]: item for item in store.active_validators()}
    validator = active.get(key.address)
    if validator is None or validator["public_key"] != key.public_key_b64:
        raise ValidatorGovernanceError("signing key is not an active validator governance key")
    payload = governance_signing_payload(envelope)
    result = json.loads(json.dumps(envelope))
    approvals = [item for item in list(result.get("approvals") or []) if item.get("validator") != key.address]
    approvals.append(
        {
            "validator": key.address,
            "public_key": key.public_key_b64,
            "signature": key.sign(payload),
        }
    )
    approvals.sort(key=lambda item: str(item["validator"]))
    result["approvals"] = approvals
    return result


def load_governance_request(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_governance_request(
    envelope: dict[str, Any], path: str | Path, *, overwrite: bool = False
) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise ValidatorGovernanceError(f"governance request already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target
