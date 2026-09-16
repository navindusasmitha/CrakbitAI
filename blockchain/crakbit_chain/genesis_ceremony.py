from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .crypto import KeyPair, canonical_json, sha256_hex, verify_signature
from .genesis import Genesis


CEREMONY_FORMAT = "crakbit-genesis-ceremony/1"


def _file_sha256(path: str | Path) -> str:
    return sha256_hex(Path(path).read_bytes())


def build_ceremony(genesis_path: str | Path) -> dict[str, Any]:
    genesis = Genesis.load(genesis_path)
    statement = {
        "format": CEREMONY_FORMAT,
        "chain_id": genesis.chain_id,
        "network_name": genesis.network_name,
        "genesis_fingerprint": genesis.fingerprint(),
        "genesis_sha256": _file_sha256(genesis_path),
        "validator_count": len(genesis.validators),
        "quorum_size": genesis.quorum_size,
        "validators": [
            {
                "name": validator.name,
                "address": validator.address,
                "public_key": validator.public_key,
            }
            for validator in genesis.validators
        ],
    }
    return {
        "statement": statement,
        "statement_sha256": sha256_hex(canonical_json(statement)),
        "attestations": [],
    }


def add_attestation(ceremony: dict[str, Any], key_path: str | Path) -> dict[str, Any]:
    statement = ceremony.get("statement")
    if not isinstance(statement, dict):
        raise ValueError("ceremony statement is missing")
    expected_hash = sha256_hex(canonical_json(statement))
    if ceremony.get("statement_sha256") != expected_hash:
        raise ValueError("ceremony statement hash mismatch")

    key = KeyPair.load(key_path)
    validators = {
        str(item["address"]): str(item["public_key"])
        for item in statement.get("validators", [])
    }
    expected_public = validators.get(key.address)
    if expected_public is None:
        raise ValueError("attestation key is not a configured genesis validator")
    if expected_public != key.public_key_b64:
        raise ValueError("attestation key does not match validator public key")

    attestations = list(ceremony.get("attestations", []))
    for existing in attestations:
        if existing.get("validator") == key.address:
            if existing.get("signature") == key.sign(canonical_json(statement)):
                return ceremony
            raise ValueError("validator already has a conflicting ceremony attestation")

    signature = key.sign(canonical_json(statement))
    attestations.append(
        {
            "validator": key.address,
            "public_key": key.public_key_b64,
            "signature": signature,
        }
    )
    return {
        "statement": statement,
        "statement_sha256": expected_hash,
        "attestations": attestations,
    }


def verify_ceremony(
    ceremony: dict[str, Any],
    *,
    genesis_path: str | Path | None = None,
    require_quorum: bool = True,
) -> dict[str, Any]:
    statement = ceremony.get("statement")
    if not isinstance(statement, dict):
        raise ValueError("ceremony statement is missing")
    if statement.get("format") != CEREMONY_FORMAT:
        raise ValueError("unsupported ceremony format")
    statement_hash = sha256_hex(canonical_json(statement))
    if ceremony.get("statement_sha256") != statement_hash:
        raise ValueError("ceremony statement hash mismatch")

    if genesis_path is not None:
        genesis = Genesis.load(genesis_path)
        if statement.get("chain_id") != genesis.chain_id:
            raise ValueError("ceremony chain_id does not match genesis")
        if statement.get("genesis_fingerprint") != genesis.fingerprint():
            raise ValueError("ceremony genesis fingerprint mismatch")
        if statement.get("genesis_sha256") != _file_sha256(genesis_path):
            raise ValueError("ceremony exact genesis SHA-256 mismatch")
        expected_quorum = genesis.quorum_size
    else:
        expected_quorum = int(statement.get("quorum_size", 0))

    validators = {
        str(item["address"]): str(item["public_key"])
        for item in statement.get("validators", [])
    }
    seen: set[str] = set()
    valid = 0
    for attestation in ceremony.get("attestations", []):
        validator = str(attestation.get("validator", ""))
        public_key = str(attestation.get("public_key", ""))
        signature = str(attestation.get("signature", ""))
        if validator in seen:
            raise ValueError("duplicate validator ceremony attestation")
        seen.add(validator)
        if validators.get(validator) != public_key:
            raise ValueError("ceremony attestation from unknown/mismatched validator")
        if not verify_signature(public_key, canonical_json(statement), signature):
            raise ValueError("invalid ceremony attestation signature")
        valid += 1

    if require_quorum and valid < expected_quorum:
        raise ValueError(
            f"insufficient ceremony quorum: have {valid}, need {expected_quorum}"
        )

    return {
        "valid": True,
        "format": CEREMONY_FORMAT,
        "chain_id": statement["chain_id"],
        "statement_sha256": statement_hash,
        "genesis_fingerprint": statement["genesis_fingerprint"],
        "genesis_sha256": statement["genesis_sha256"],
        "valid_attestations": valid,
        "required_quorum": expected_quorum,
        "quorum_reached": valid >= expected_quorum,
    }


def save_ceremony(
    ceremony: dict[str, Any],
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"ceremony file already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(ceremony, indent=2) + "\n", encoding="utf-8")
    return target
