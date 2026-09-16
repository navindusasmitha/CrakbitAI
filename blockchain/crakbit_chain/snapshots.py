from __future__ import annotations

from typing import Any

from .crypto import KeyPair, canonical_json, sha256_hex, verify_signature
from .genesis import Genesis
from .storage import Ledger, LedgerError


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
        "format": "crakbit-state-snapshot-v1",
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


def verify_snapshot(envelope: dict[str, Any], genesis: Genesis) -> dict[str, Any]:
    snapshot = dict(envelope.get("snapshot") or {})
    snapshot_hash = str(envelope.get("snapshot_hash") or "")
    signer = str(envelope.get("signer") or "")
    public_key = str(envelope.get("public_key") or "")
    signature = str(envelope.get("signature") or "")

    if snapshot.get("format") != "crakbit-state-snapshot-v1":
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
    for item in accounts:
        address = str(item["address"])
        balance = int(item["balance"])
        nonce = int(item["nonce"])
        if not address.startswith("crk1") or balance < 0 or nonce < 0:
            raise LedgerError("invalid account entry in snapshot")
        if previous and address <= previous:
            raise LedgerError("snapshot accounts are not strictly sorted")
        previous = address
        normalized_accounts.append({"address": address, "balance": balance, "nonce": nonce})

    expected_accounts_root = sha256_hex(canonical_json(normalized_accounts))
    if snapshot.get("accounts_root") != expected_accounts_root:
        raise LedgerError("snapshot accounts root mismatch")
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
