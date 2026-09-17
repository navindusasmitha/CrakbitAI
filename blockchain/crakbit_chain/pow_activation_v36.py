from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .algorithm_gate_v34 import ALGORITHM_DECISION_FORMAT, verify_algorithm_decision
from .crypto import KeyPair, canonical_json, sha256_hex, verify_signature
from .randomx_v33 import RANDOMX_ALGO_CANDIDATE, RANDOMX_KEY_DELAY, RANDOMX_KEY_INTERVAL, RANDOMX_UPSTREAM_TAG

ACTIVATION_FORMAT = "crakbit-pow-algorithm-activation-proposal-v36/1"
CURRENT_SCRYPT_ALGO = "crakpow-scrypt-v1"


class PowActivationV36Error(ValueError):
    pass


def _sha256(value: str, field: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise PowActivationV36Error(f"{field} must be 64 hexadecimal characters")
    return text


def _commit(value: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 40 or any(ch not in "0123456789abcdef" for ch in text):
        raise PowActivationV36Error("source commit must be an exact 40-character Git SHA")
    return text


def build_activation_proposal(
    *,
    key_path: str | Path,
    algorithm_decision: dict[str, Any],
    source_commit: str,
    chain_id: str,
    genesis_hash: str,
    current_height: int,
    activation_height: int | None,
    consensus_vectors_sha256: str | None = None,
    randomx_library_sha256: str | None = None,
    minimum_notice_blocks: int = 1000,
    notes: str = "",
) -> dict[str, Any]:
    key = KeyPair.load(key_path)
    verified = verify_algorithm_decision(algorithm_decision)
    manifest_decision = algorithm_decision.get("manifest", {})
    if manifest_decision.get("format") != ALGORITHM_DECISION_FORMAT:
        raise PowActivationV36Error("unexpected algorithm decision format")
    decision = str(verified["decision"])
    if decision == "hold":
        raise PowActivationV36Error("cannot build activation proposal while algorithm decision is hold")
    current_height = int(current_height)
    minimum_notice_blocks = max(100, int(minimum_notice_blocks))
    if current_height < 0:
        raise PowActivationV36Error("current height may not be negative")

    if decision == "randomx":
        if activation_height is None:
            raise PowActivationV36Error("RandomX proposal requires an activation height")
        activation_height = int(activation_height)
        if activation_height < current_height + minimum_notice_blocks:
            raise PowActivationV36Error("activation height does not provide the minimum notice window")
        if consensus_vectors_sha256 is None or randomx_library_sha256 is None:
            raise PowActivationV36Error("RandomX proposal requires consensus-vector and native-library SHA-256 values")
        next_algorithm = RANDOMX_ALGO_CANDIDATE
        vectors_hash = _sha256(consensus_vectors_sha256, "consensus vectors SHA-256")
        library_hash = _sha256(randomx_library_sha256, "RandomX library SHA-256")
        randomx = {
            "upstream_tag": RANDOMX_UPSTREAM_TAG,
            "key_interval": RANDOMX_KEY_INTERVAL,
            "key_delay": RANDOMX_KEY_DELAY,
        }
    elif decision == "scrypt":
        activation_height = None
        next_algorithm = CURRENT_SCRYPT_ALGO
        vectors_hash = None if consensus_vectors_sha256 is None else _sha256(consensus_vectors_sha256, "consensus vectors SHA-256")
        library_hash = None
        randomx = None
    else:
        raise PowActivationV36Error("unsupported algorithm decision")

    chain_id = str(chain_id).strip()
    if not chain_id:
        raise PowActivationV36Error("chain ID is required")
    manifest = {
        "format": ACTIVATION_FORMAT,
        "recorded_at_unix": int(time.time()),
        "source_commit": _commit(source_commit),
        "chain_id": chain_id,
        "genesis_hash": _sha256(genesis_hash, "genesis hash"),
        "algorithm_decision_id": str(verified["decision_id"]),
        "current_algorithm": CURRENT_SCRYPT_ALGO,
        "decision": decision,
        "next_algorithm": next_algorithm,
        "current_height": current_height,
        "activation_height": activation_height,
        "minimum_notice_blocks": minimum_notice_blocks,
        "consensus_vectors_sha256": vectors_hash,
        "randomx_library_sha256": library_hash,
        "randomx": randomx,
        "notes": str(notes)[:4000],
        "testnet_proposal_only": True,
        "consensus_activated": False,
        "requires_separate_node_release": decision == "randomx",
        "requires_multi_node_fork_reorg_tests": True,
        "requires_independent_consensus_review": True,
        "production_mainnet_ready": False,
        "production_crkbit_launched": False,
    }
    manifest["proposal_id"] = sha256_hex(canonical_json(manifest))
    payload = canonical_json({"domain": ACTIVATION_FORMAT, "manifest": manifest})
    return {
        "manifest": manifest,
        "signer": key.address,
        "public_key": key.public_key_b64,
        "signature": key.sign(payload),
    }


def verify_activation_proposal(record: dict[str, Any]) -> dict[str, Any]:
    manifest = record.get("manifest")
    if not isinstance(manifest, dict) or manifest.get("format") != ACTIVATION_FORMAT:
        raise PowActivationV36Error("unexpected activation proposal format")
    payload = canonical_json({"domain": ACTIVATION_FORMAT, "manifest": manifest})
    if not verify_signature(str(record.get("public_key", "")), payload, str(record.get("signature", ""))):
        raise PowActivationV36Error("invalid activation proposal signature")
    body = dict(manifest)
    proposal_id = str(body.pop("proposal_id", ""))
    if proposal_id != sha256_hex(canonical_json(body)):
        raise PowActivationV36Error("activation proposal ID mismatch")
    if manifest.get("consensus_activated") or manifest.get("production_mainnet_ready") or manifest.get("production_crkbit_launched"):
        raise PowActivationV36Error("activation proposal contains prohibited launch claims")
    decision = str(manifest.get("decision"))
    if decision == "randomx":
        if str(manifest.get("next_algorithm")) != RANDOMX_ALGO_CANDIDATE:
            raise PowActivationV36Error("RandomX proposal algorithm mismatch")
        if int(manifest["activation_height"]) < int(manifest["current_height"]) + int(manifest["minimum_notice_blocks"]):
            raise PowActivationV36Error("RandomX activation notice window is invalid")
        _sha256(str(manifest.get("consensus_vectors_sha256")), "consensus vectors SHA-256")
        _sha256(str(manifest.get("randomx_library_sha256")), "RandomX library SHA-256")
    elif decision == "scrypt":
        if manifest.get("activation_height") is not None or str(manifest.get("next_algorithm")) != CURRENT_SCRYPT_ALGO:
            raise PowActivationV36Error("scrypt continuation proposal is malformed")
    else:
        raise PowActivationV36Error("activation proposal decision is unsupported")
    return {
        "valid": True,
        "proposal_id": proposal_id,
        "decision": decision,
        "next_algorithm": manifest["next_algorithm"],
        "activation_height": manifest["activation_height"],
        "consensus_activated": False,
        "testnet_proposal_only": True,
        "production_mainnet_ready": False,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PowActivationV36Error("JSON file must contain an object")
    return value
