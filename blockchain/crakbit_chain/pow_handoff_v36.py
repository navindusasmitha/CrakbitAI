from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .crypto import KeyPair, canonical_json, sha256_hex, verify_signature
from .pow_activation_v36 import ACTIVATION_FORMAT, verify_activation_proposal
from .pow_campaign_v36 import CAMPAIGN_SUMMARY_FORMAT
from .pow_testnet_v35 import verify_testnet_freeze

HANDOFF_FORMAT = "crakbit-pow-independent-review-handoff-v36/1"


class PowHandoffV36Error(ValueError):
    pass


def _commit(value: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 40 or any(ch not in "0123456789abcdef" for ch in text):
        raise PowHandoffV36Error("source commit must be an exact 40-character Git SHA")
    return text


def _hash64(value: str, field: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise PowHandoffV36Error(f"{field} must be 64 hexadecimal characters")
    return text


def build_review_handoff(
    *,
    key_path: str | Path,
    source_commit: str,
    package_version: str,
    chain_id: str,
    genesis_hash: str,
    v35_freeze: dict[str, Any],
    campaign_summary: dict[str, Any],
    undo_rehearsal: dict[str, Any],
    activation_proposal: dict[str, Any] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    key = KeyPair.load(key_path)
    freeze_verified = verify_testnet_freeze(v35_freeze)
    freeze_manifest = v35_freeze["manifest"]
    if str(freeze_manifest.get("chain_id")) != str(chain_id):
        raise PowHandoffV36Error("handoff chain ID differs from v0.35 freeze")
    if str(freeze_manifest.get("genesis_hash")).lower() != _hash64(genesis_hash, "genesis hash"):
        raise PowHandoffV36Error("handoff genesis differs from v0.35 freeze")

    if campaign_summary.get("format") != CAMPAIGN_SUMMARY_FORMAT:
        raise PowHandoffV36Error("unexpected campaign summary format")
    campaign_body = dict(campaign_summary)
    summary_id = str(campaign_body.pop("summary_id", ""))
    if summary_id != sha256_hex(canonical_json(campaign_body)):
        raise PowHandoffV36Error("campaign summary ID mismatch")

    if undo_rehearsal.get("format") != "crakbit-incremental-undo-rehearsal-v36/1":
        raise PowHandoffV36Error("unexpected undo rehearsal format")
    undo_body = dict(undo_rehearsal)
    rehearsal_id = str(undo_body.pop("rehearsal_id", ""))
    if rehearsal_id != sha256_hex(canonical_json(undo_body)):
        raise PowHandoffV36Error("undo rehearsal ID mismatch")

    activation_id: str | None = None
    activation_decision: str | None = None
    if activation_proposal is not None:
        if activation_proposal.get("manifest", {}).get("format") != ACTIVATION_FORMAT:
            raise PowHandoffV36Error("unexpected activation proposal format")
        activation_verified = verify_activation_proposal(activation_proposal)
        activation_id = str(activation_verified["proposal_id"])
        activation_decision = str(activation_verified["decision"])

    checks = {
        "v35_public_testnet_freeze_valid": bool(freeze_verified["valid"]),
        "campaign_gate_satisfied": bool(campaign_summary.get("campaign_gate_satisfied")),
        "seven_day_campaign": str(campaign_summary.get("required_level")) == "7d" and int(campaign_summary.get("actual_seconds", 0)) >= 7 * 24 * 3600,
        "minimum_four_unique_nodes": int(campaign_summary.get("unique_node_ids", 0)) >= 4,
        "undo_rehearsal_passed": bool(undo_rehearsal.get("rehearsal_passed")),
        "live_reorg_engine_not_falsely_claimed": not bool(undo_rehearsal.get("live_reorg_engine_switched_to_incremental_undo")),
        "activation_is_proposal_only_if_present": activation_proposal is None or not bool(activation_proposal["manifest"].get("consensus_activated")),
    }
    manifest = {
        "format": HANDOFF_FORMAT,
        "recorded_at_unix": int(time.time()),
        "source_commit": _commit(source_commit),
        "package_version": str(package_version),
        "chain_id": str(chain_id),
        "genesis_hash": _hash64(genesis_hash, "genesis hash"),
        "supersedes_v35_source_commit": str(freeze_manifest.get("source_commit")),
        "v35_freeze_id": str(freeze_verified["freeze_id"]),
        "campaign_summary_id": summary_id,
        "undo_rehearsal_id": rehearsal_id,
        "activation_proposal_id": activation_id,
        "activation_decision": activation_decision,
        "checks": checks,
        "external_review_handoff_ready": all(checks.values()),
        "notes": str(notes)[:4000],
        "independent_security_review_completed": False,
        "production_mainnet_ready": False,
        "production_crkbit_launched": False,
    }
    manifest["handoff_id"] = sha256_hex(canonical_json(manifest))
    payload = canonical_json({"domain": HANDOFF_FORMAT, "manifest": manifest})
    return {
        "manifest": manifest,
        "signer": key.address,
        "public_key": key.public_key_b64,
        "signature": key.sign(payload),
    }


def verify_review_handoff(record: dict[str, Any]) -> dict[str, Any]:
    manifest = record.get("manifest")
    if not isinstance(manifest, dict) or manifest.get("format") != HANDOFF_FORMAT:
        raise PowHandoffV36Error("unexpected review handoff format")
    payload = canonical_json({"domain": HANDOFF_FORMAT, "manifest": manifest})
    if not verify_signature(str(record.get("public_key", "")), payload, str(record.get("signature", ""))):
        raise PowHandoffV36Error("invalid review handoff signature")
    body = dict(manifest)
    handoff_id = str(body.pop("handoff_id", ""))
    if handoff_id != sha256_hex(canonical_json(body)):
        raise PowHandoffV36Error("review handoff ID mismatch")
    if manifest.get("independent_security_review_completed") or manifest.get("production_mainnet_ready") or manifest.get("production_crkbit_launched"):
        raise PowHandoffV36Error("review handoff contains prohibited completion/launch claims")
    return {
        "valid": True,
        "handoff_id": handoff_id,
        "external_review_handoff_ready": bool(manifest.get("external_review_handoff_ready")),
        "independent_security_review_completed": False,
        "production_mainnet_ready": False,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PowHandoffV36Error("JSON file must contain an object")
    return value
