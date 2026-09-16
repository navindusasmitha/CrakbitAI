from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from .crypto import KeyPair, address_from_public_key, canonical_json, sha256_hex, verify_signature
from .genesis import Genesis


FORMAT = "crakbit-validator-lifecycle-plan/1"
KINDS = {"join", "remove", "replace"}


class ValidatorLifecycleError(ValueError):
    pass


def _validate_commit(value: str) -> str:
    commit = value.strip().lower()
    if len(commit) not in {40, 64} or any(ch not in "0123456789abcdef" for ch in commit):
        raise ValidatorLifecycleError("source_commit must be an exact hexadecimal Git commit SHA")
    return commit


def _validate_public_key(value: str) -> str:
    try:
        raw = base64.b64decode(value.encode("ascii"), validate=True)
    except Exception as exc:  # noqa: BLE001
        raise ValidatorLifecycleError("validator public key must be valid base64") from exc
    if len(raw) != 32:
        raise ValidatorLifecycleError("validator Ed25519 public key must be exactly 32 bytes")
    return value


def _set_hash(validators: list[dict[str, Any]]) -> str:
    canonical = sorted(
        (
            str(item["address"]),
            str(item["public_key"]),
            int(item["power"]),
        )
        for item in validators
    )
    return sha256_hex(canonical_json(canonical))


def _genesis_set(genesis: Genesis) -> list[dict[str, Any]]:
    return [
        {
            "address": item.address,
            "public_key": item.public_key,
            "name": item.name,
            "power": 1,
        }
        for item in genesis.validators
    ]


def build_validator_lifecycle_plan(
    *,
    genesis_path: str | Path,
    signing_key_path: str | Path,
    source_commit: str,
    kind: str,
    effective_height: int,
    existing_address: str | None = None,
    new_public_key: str | None = None,
    new_name: str = "validator-new",
    new_power: int = 1,
) -> dict[str, Any]:
    if kind not in KINDS:
        raise ValidatorLifecycleError(f"kind must be one of: {', '.join(sorted(KINDS))}")
    if effective_height < 3:
        raise ValidatorLifecycleError("effective_height must be at least 3 for a CometBFT lifecycle drill")
    if new_power < 1:
        raise ValidatorLifecycleError("new validator power must be positive")

    commit = _validate_commit(source_commit)
    genesis = Genesis.load(genesis_path)
    signer = KeyPair.load(signing_key_path)
    before = _genesis_set(genesis)
    after = [dict(item) for item in before]
    current_by_address = {str(item["address"]): item for item in before}
    updates: list[dict[str, Any]] = []

    if kind in {"remove", "replace"}:
        address = str(existing_address or "").strip().lower()
        if not address or address not in current_by_address:
            raise ValidatorLifecycleError("existing validator address is not present in the modeled set")
        if len(before) <= 1:
            raise ValidatorLifecycleError("lifecycle drill may not remove the final validator")
        removed = current_by_address[address]
        after = [item for item in after if str(item["address"]) != address]
        updates.append(
            {
                "public_key": str(removed["public_key"]),
                "address": address,
                "power": 0,
                "operation": "remove",
            }
        )

    if kind in {"join", "replace"}:
        if not new_public_key:
            raise ValidatorLifecycleError("new_public_key is required for join/replace")
        public_key = _validate_public_key(new_public_key)
        address = address_from_public_key(public_key)
        if any(str(item["address"]) == address for item in after):
            raise ValidatorLifecycleError("new validator already exists in the modeled validator set")
        if any(str(item["public_key"]) == public_key for item in after):
            raise ValidatorLifecycleError("new validator public key already exists")
        added = {
            "address": address,
            "public_key": public_key,
            "name": str(new_name).strip() or "validator-new",
            "power": int(new_power),
        }
        after.append(added)
        updates.append(
            {
                "public_key": public_key,
                "address": address,
                "power": int(new_power),
                "operation": "add",
            }
        )

    if not after:
        raise ValidatorLifecycleError("validator set may not be empty")

    # CometBFT validator updates returned from FinalizeBlock at H affect the set at H+2.
    emit_height = effective_height - 2
    before_hash = _set_hash(before)
    after_hash = _set_hash(after)
    manifest = {
        "format": FORMAT,
        "chain_id": genesis.chain_id,
        "genesis_fingerprint": genesis.fingerprint(),
        "source_commit": commit,
        "kind": kind,
        "emit_height": emit_height,
        "effective_height": int(effective_height),
        "before_validator_set_hash": before_hash,
        "after_validator_set_hash": after_hash,
        "before_validators": sorted(before, key=lambda item: str(item["address"])),
        "after_validators": sorted(after, key=lambda item: str(item["address"])),
        "cometbft_validator_updates": updates,
        "assumptions": {
            "genesis_validators_modeled_with_uniform_power": True,
            "plan_imported_out_of_band": True,
            "live_abci_validator_updates_emitted": False,
        },
        "claims": {
            "testnet_drill_plan": True,
            "consensus_change_applied": False,
            "independent_review_completed": False,
            "production_mainnet_ready": False,
        },
    }
    payload = canonical_json(manifest)
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_hex(payload),
        "signer": signer.address,
        "public_key": signer.public_key_b64,
        "signature": signer.sign(payload),
    }


def verify_validator_lifecycle_plan(
    envelope: dict[str, Any],
    *,
    genesis_path: str | Path,
    expected_signer: str | None = None,
    expected_source_commit: str | None = None,
) -> dict[str, Any]:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("manifest"), dict):
        raise ValidatorLifecycleError("invalid validator lifecycle plan")
    manifest = envelope["manifest"]
    if manifest.get("format") != FORMAT:
        raise ValidatorLifecycleError("unsupported validator lifecycle plan format")
    payload = canonical_json(manifest)
    if str(envelope.get("manifest_sha256", "")) != sha256_hex(payload):
        raise ValidatorLifecycleError("validator lifecycle plan hash mismatch")
    public_key = str(envelope.get("public_key", ""))
    signer = str(envelope.get("signer", ""))
    if not public_key or address_from_public_key(public_key) != signer:
        raise ValidatorLifecycleError("validator lifecycle signer identity mismatch")
    if expected_signer and signer != expected_signer:
        raise ValidatorLifecycleError("validator lifecycle signer does not match expected signer")
    if not verify_signature(public_key, payload, str(envelope.get("signature", ""))):
        raise ValidatorLifecycleError("invalid validator lifecycle signature")

    genesis = Genesis.load(genesis_path)
    if manifest.get("chain_id") != genesis.chain_id:
        raise ValidatorLifecycleError("validator lifecycle chain ID mismatch")
    if manifest.get("genesis_fingerprint") != genesis.fingerprint():
        raise ValidatorLifecycleError("validator lifecycle genesis fingerprint mismatch")
    if expected_source_commit and manifest.get("source_commit") != _validate_commit(expected_source_commit):
        raise ValidatorLifecycleError("validator lifecycle source commit mismatch")

    before = list(manifest.get("before_validators") or [])
    after = list(manifest.get("after_validators") or [])
    if _set_hash(before) != manifest.get("before_validator_set_hash"):
        raise ValidatorLifecycleError("before validator-set hash mismatch")
    if _set_hash(after) != manifest.get("after_validator_set_hash"):
        raise ValidatorLifecycleError("after validator-set hash mismatch")
    if int(manifest.get("effective_height", 0)) != int(manifest.get("emit_height", -2)) + 2:
        raise ValidatorLifecycleError("invalid CometBFT validator-update height relationship")
    if manifest.get("claims", {}).get("consensus_change_applied") is not False:
        raise ValidatorLifecycleError("v0.20 lifecycle plan must not claim a live consensus change")

    return {
        "valid": True,
        "format": FORMAT,
        "chain_id": genesis.chain_id,
        "kind": manifest["kind"],
        "emit_height": int(manifest["emit_height"]),
        "effective_height": int(manifest["effective_height"]),
        "before_validator_count": len(before),
        "after_validator_count": len(after),
        "validator_update_count": len(manifest.get("cometbft_validator_updates", [])),
        "signer": signer,
        "consensus_change_applied": False,
        "production_mainnet_ready": False,
    }


def save_validator_lifecycle_plan(
    envelope: dict[str, Any], path: str | Path, *, overwrite: bool = False
) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise ValidatorLifecycleError(f"validator lifecycle plan already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    return target


def load_validator_lifecycle_plan(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
