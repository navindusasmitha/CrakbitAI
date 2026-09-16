from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from .crypto import KeyPair, canonical_json, sha256_hex, verify_signature
from .genesis import Genesis
from .storage import Ledger, LedgerError

SNAPSHOT_FORMAT = "crakbit-state-snapshot-v1"
CERTIFICATE_FORMAT = "crakbit-snapshot-certificate-v1"
IMPORT_JOURNAL_FORMAT = "crakbit-snapshot-import-journal-v1"


def snapshot_state(ledger: Ledger) -> dict[str, Any]:
    with ledger.connect() as conn:
        accounts = [
            {
                "address": str(row["address"]),
                "balance": int(row["balance"]),
                "nonce": int(row["nonce"]),
            }
            for row in conn.execute(
                "SELECT address,balance,nonce FROM accounts ORDER BY address ASC"
            ).fetchall()
        ]
    accounts_root = sha256_hex(canonical_json(accounts))
    return {
        "format": SNAPSHOT_FORMAT,
        "chain_id": ledger.genesis.chain_id,
        "genesis_fingerprint": ledger.genesis.fingerprint(),
        "height": ledger.height,
        "last_hash": ledger.last_hash,
        "accounts_root": accounts_root,
        "accounts": accounts,
    }


def sign_snapshot(ledger: Ledger, key: KeyPair) -> dict[str, Any]:
    validator = ledger.genesis.validator_by_address(key.address)
    if validator is None or validator.public_key != key.public_key_b64:
        raise LedgerError("snapshot signer is not a configured validator")
    snapshot = snapshot_state(ledger)
    snapshot_hash = sha256_hex(canonical_json(snapshot))
    envelope = {
        "snapshot": snapshot,
        "snapshot_hash": snapshot_hash,
        "signer": key.address,
        "public_key": key.public_key_b64,
    }
    envelope["signature"] = key.sign(canonical_json(envelope))
    return envelope


def _validate_snapshot_body(snapshot: dict[str, Any], genesis: Genesis) -> list[dict[str, Any]]:
    if snapshot.get("format") != SNAPSHOT_FORMAT:
        raise LedgerError("unsupported snapshot format")
    if snapshot.get("chain_id") != genesis.chain_id:
        raise LedgerError("snapshot chain_id mismatch")
    if snapshot.get("genesis_fingerprint") != genesis.fingerprint():
        raise LedgerError("snapshot genesis fingerprint mismatch")
    if int(snapshot.get("height", -1)) < 0:
        raise LedgerError("invalid snapshot height")
    if len(str(snapshot.get("last_hash") or "")) != 64:
        raise LedgerError("invalid snapshot last_hash")

    accounts = list(snapshot.get("accounts") or [])
    normalized_accounts: list[dict[str, Any]] = []
    previous = ""
    total_supply = 0
    for item in accounts:
        address = str(item["address"])
        balance = int(item["balance"])
        nonce = int(item["nonce"])
        if not address.startswith("crk1") or balance < 0 or nonce < 0:
            raise LedgerError("invalid account entry in snapshot")
        if previous and address <= previous:
            raise LedgerError("snapshot accounts are not strictly sorted")
        previous = address
        total_supply += balance
        normalized_accounts.append({"address": address, "balance": balance, "nonce": nonce})

    expected_accounts_root = sha256_hex(canonical_json(normalized_accounts))
    if snapshot.get("accounts_root") != expected_accounts_root:
        raise LedgerError("snapshot accounts root mismatch")
    if total_supply != sum(genesis.allocations.values()):
        raise LedgerError("snapshot total supply does not match genesis issued supply")
    return normalized_accounts


def verify_snapshot(envelope: dict[str, Any], genesis: Genesis) -> dict[str, Any]:
    snapshot = dict(envelope.get("snapshot") or {})
    snapshot_hash = str(envelope.get("snapshot_hash") or "")
    signer = str(envelope.get("signer") or "")
    public_key = str(envelope.get("public_key") or "")
    signature = str(envelope.get("signature") or "")

    _validate_snapshot_body(snapshot, genesis)
    if sha256_hex(canonical_json(snapshot)) != snapshot_hash:
        raise LedgerError("snapshot hash mismatch")

    validator = genesis.validator_by_address(signer)
    if validator is None:
        raise LedgerError("snapshot signer is not a configured validator")
    if validator.public_key != public_key:
        raise LedgerError("snapshot signer public key mismatch")

    signed = {
        "snapshot": snapshot,
        "snapshot_hash": snapshot_hash,
        "signer": signer,
        "public_key": public_key,
    }
    if not verify_signature(public_key, canonical_json(signed), signature):
        raise LedgerError("invalid snapshot signature")
    return snapshot


def build_snapshot_certificate(
    envelopes: list[dict[str, Any]],
    genesis: Genesis,
) -> dict[str, Any]:
    """Build a >2/3 certificate from validator signatures over identical state."""

    groups: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    snapshots: dict[str, dict[str, Any]] = {}
    for envelope in envelopes:
        snapshot = verify_snapshot(envelope, genesis)
        snapshot_hash = str(envelope["snapshot_hash"])
        signer = str(envelope["signer"])
        snapshots[snapshot_hash] = snapshot
        groups[snapshot_hash][signer] = {
            "signer": signer,
            "public_key": str(envelope["public_key"]),
            "signature": str(envelope["signature"]),
        }

    candidates = [
        (snapshot_hash, signatures)
        for snapshot_hash, signatures in groups.items()
        if len(signatures) >= genesis.quorum_size
    ]
    if not candidates:
        raise LedgerError("no snapshot hash has validator quorum")

    snapshot_hash, signatures = max(
        candidates,
        key=lambda item: (int(snapshots[item[0]]["height"]), len(item[1])),
    )
    snapshot = snapshots[snapshot_hash]
    return {
        "format": CERTIFICATE_FORMAT,
        "snapshot": snapshot,
        "snapshot_hash": snapshot_hash,
        "quorum": genesis.quorum_size,
        "signatures": [signatures[address] for address in sorted(signatures)],
    }


def verify_snapshot_certificate(
    certificate: dict[str, Any],
    genesis: Genesis,
) -> dict[str, Any]:
    if certificate.get("format") != CERTIFICATE_FORMAT:
        raise LedgerError("unsupported snapshot certificate format")
    snapshot = dict(certificate.get("snapshot") or {})
    snapshot_hash = str(certificate.get("snapshot_hash") or "")
    _validate_snapshot_body(snapshot, genesis)
    if sha256_hex(canonical_json(snapshot)) != snapshot_hash:
        raise LedgerError("snapshot certificate hash mismatch")

    signatures = list(certificate.get("signatures") or [])
    valid_signers: set[str] = set()
    for item in signatures:
        signer = str(item.get("signer") or "")
        public_key = str(item.get("public_key") or "")
        signature = str(item.get("signature") or "")
        if signer in valid_signers:
            raise LedgerError("duplicate signer in snapshot certificate")
        validator = genesis.validator_by_address(signer)
        if validator is None or validator.public_key != public_key:
            raise LedgerError("snapshot certificate contains unknown validator identity")
        signed = {
            "snapshot": snapshot,
            "snapshot_hash": snapshot_hash,
            "signer": signer,
            "public_key": public_key,
        }
        if not verify_signature(public_key, canonical_json(signed), signature):
            raise LedgerError("invalid snapshot certificate signature")
        valid_signers.add(signer)

    if len(valid_signers) < genesis.quorum_size:
        raise LedgerError("snapshot certificate does not meet validator quorum")
    return snapshot


def verify_snapshot_artifact(artifact: dict[str, Any], genesis: Genesis) -> dict[str, Any]:
    if artifact.get("format") == CERTIFICATE_FORMAT:
        return verify_snapshot_certificate(artifact, genesis)
    return verify_snapshot(artifact, genesis)


def snapshot_import_journal_path(ledger: Ledger) -> Path:
    return ledger.db_path.parent / "snapshot-import.journal.json"


def snapshot_import_journal_status(ledger: Ledger) -> dict[str, Any]:
    path = snapshot_import_journal_path(ledger)
    if not path.exists():
        return {"present": False, "path": str(path)}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"present": True, "path": str(path), "valid": False}
    return {"present": True, "path": str(path), "valid": True, **payload}


def _database_snapshot_certificate_hash(ledger: Ledger) -> str | None:
    with ledger.connect() as conn:
        row = conn.execute(
            "SELECT value FROM metadata WHERE key='snapshot_certificate_hash'"
        ).fetchone()
        return str(row["value"]) if row is not None else None


def _write_import_journal(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def import_snapshot_certificate(
    ledger: Ledger,
    certificate: dict[str, Any],
) -> dict[str, Any]:
    """Bootstrap an empty local ledger from a quorum-certified snapshot.

    v0.8 adds a sidecar import journal. SQLite already makes the database mutation atomic;
    the sidecar records intent before the transaction so a process crash can be detected on
    restart. Re-running the same import safely clears a journal left after a successful
    commit or retries an import whose database transaction rolled back.
    """

    snapshot = verify_snapshot_certificate(certificate, ledger.genesis)
    certificate_hash = sha256_hex(canonical_json(certificate))
    journal_path = snapshot_import_journal_path(ledger)

    existing_journal: dict[str, Any] | None = None
    if journal_path.exists():
        try:
            existing_journal = json.loads(journal_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise LedgerError("snapshot import journal is unreadable; operator review required") from exc
        if existing_journal.get("format") != IMPORT_JOURNAL_FORMAT:
            raise LedgerError("unknown snapshot import journal format")
        if existing_journal.get("certificate_hash") != certificate_hash:
            raise LedgerError("unfinished snapshot import journal references a different certificate")

    committed_hash = _database_snapshot_certificate_hash(ledger)
    if committed_hash == certificate_hash:
        if ledger.height != int(snapshot["height"]) or ledger.last_hash != str(snapshot["last_hash"]):
            raise LedgerError("snapshot metadata exists but local height/hash does not match certificate")
        if journal_path.exists():
            journal_path.unlink()
        return snapshot

    if ledger.height != 0 or ledger.last_hash != "0" * 64:
        raise LedgerError("snapshot import requires a fresh height-zero database")

    accounts = _validate_snapshot_body(snapshot, ledger.genesis)
    journal = {
        "format": IMPORT_JOURNAL_FORMAT,
        "state": "prepared",
        "certificate_hash": certificate_hash,
        "target_height": int(snapshot["height"]),
        "target_last_hash": str(snapshot["last_hash"]),
        "accounts_root": str(snapshot["accounts_root"]),
        "prepared_at_ms": int(time.time() * 1000),
    }
    _write_import_journal(journal_path, journal)

    with ledger.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute("DELETE FROM accounts")
            conn.executemany(
                "INSERT INTO accounts(address,balance,nonce) VALUES(?,?,?)",
                [(item["address"], item["balance"], item["nonce"]) for item in accounts],
            )
            conn.execute("DELETE FROM blocks")
            conn.execute("DELETE FROM transactions")
            for table in (
                "local_votes",
                "consensus_rounds",
                "local_view_changes",
                "seen_proposals",
                "equivocation_evidence",
                "local_phase_votes",
                "consensus_locks",
                "consensus_events",
            ):
                conn.execute(f"DELETE FROM {table}")
            conn.execute(
                "UPDATE metadata SET value=? WHERE key='height'",
                (str(int(snapshot["height"])),),
            )
            conn.execute(
                "UPDATE metadata SET value=? WHERE key='last_hash'",
                (str(snapshot["last_hash"]),),
            )
            metadata = {
                "snapshot_base_height": str(int(snapshot["height"])),
                "snapshot_base_hash": str(snapshot["last_hash"]),
                "snapshot_accounts_root": str(snapshot["accounts_root"]),
                "snapshot_certificate_hash": certificate_hash,
            }
            for key, value in metadata.items():
                conn.execute(
                    "INSERT INTO metadata(key,value) VALUES(?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    journal["state"] = "committed"
    journal["committed_at_ms"] = int(time.time() * 1000)
    _write_import_journal(journal_path, journal)
    journal_path.unlink()
    return snapshot
