from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .crypto import KeyPair, canonical_json, sha256_hex, verify_signature, address_from_public_key
from .genesis import Genesis


CAMPAIGN_PLAN_FORMAT = "crakbit-validator-governance-campaign/1"
CAMPAIGN_EVIDENCE_FORMAT = "crakbit-validator-governance-campaign-evidence/1"
KINDS = {"join", "remove", "replace"}


class GovernanceCampaignError(ValueError):
    pass


def _validate_commit(value: str) -> str:
    commit = str(value).strip().lower()
    if len(commit) not in {40, 64} or any(ch not in "0123456789abcdef" for ch in commit):
        raise GovernanceCampaignError("source_commit must be an exact hexadecimal Git commit SHA")
    return commit


def build_campaign_plan(
    *,
    genesis_path: str | Path,
    kind: str,
    emit_height: int,
    change_request_path: str | Path,
    restart_boundaries: bool = True,
) -> dict[str, Any]:
    if kind not in KINDS:
        raise GovernanceCampaignError("campaign kind must be join, remove or replace")
    emit_height = int(emit_height)
    if emit_height < 3:
        raise GovernanceCampaignError("campaign emit_height must be at least 3")
    genesis = Genesis.load(genesis_path)
    request_path = Path(change_request_path)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    req = request.get("request") or {}
    if str(req.get("kind")) != kind:
        raise GovernanceCampaignError("campaign kind does not match governance request")
    if int(req.get("emit_height", -1)) != emit_height:
        raise GovernanceCampaignError("campaign emit height does not match governance request")
    if str(req.get("chain_id")) != genesis.chain_id:
        raise GovernanceCampaignError("governance request chain ID does not match genesis")
    if str(req.get("genesis_fingerprint")) != genesis.fingerprint():
        raise GovernanceCampaignError("governance request genesis fingerprint mismatch")

    effective = emit_height + 2
    checkpoints = [
        {
            "name": "pre-emission",
            "height": emit_height - 1,
            "expect_pending_change": False,
            "expect_target_validator_set_active": False,
        },
        {
            "name": "emission",
            "height": emit_height,
            "expect_pending_change": True,
            "expect_target_validator_set_active": False,
            "expect_abci_validator_updates": True,
        },
        {
            "name": "intermediate",
            "height": emit_height + 1,
            "expect_pending_change": True,
            "expect_target_validator_set_active": False,
        },
        {
            "name": "activation",
            "height": effective,
            "expect_pending_change": False,
            "expect_target_validator_set_active": True,
        },
    ]
    restart_heights = [emit_height, emit_height + 1, effective] if restart_boundaries else []
    return {
        "format": CAMPAIGN_PLAN_FORMAT,
        "chain_id": genesis.chain_id,
        "genesis_fingerprint": genesis.fingerprint(),
        "kind": kind,
        "change_id": str(request.get("change_id", "")),
        "change_request_file": str(request_path),
        "change_request_sha256": sha256_hex(request_path.read_bytes()),
        "emit_height": emit_height,
        "effective_height": effective,
        "checkpoints": checkpoints,
        "restart_heights": restart_heights,
        "required_assertions": [
            "all reachable nodes agree on application hash when compared at the same height",
            "all reachable nodes agree on active validator-set hash and pending change IDs",
            "the governance transaction has >2/3 source voting-power approval",
            "ABCI validator updates are emitted only at the scheduled FinalizeBlock height",
            "the application-side target validator set activates at H+2",
            "restart/replay at H, H+1 and H+2 does not create duplicate/conflicting governance state",
            "state-sync bootstrap preserves the trusted application/governance hash",
        ],
        "claims": {
            "testnet_campaign_plan": True,
            "campaign_executed": False,
            "independent_review_completed": False,
            "production_mainnet_ready": False,
        },
    }


def save_campaign_plan(plan: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise GovernanceCampaignError(f"campaign plan already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def build_campaign_evidence(
    *,
    genesis_path: str | Path,
    signing_key_path: str | Path,
    source_commit: str,
    plan_path: str | Path,
    observation_paths: list[str | Path],
    executed: bool,
    operator_note: str = "",
) -> dict[str, Any]:
    genesis = Genesis.load(genesis_path)
    signer = KeyPair.load(signing_key_path)
    plan_file = Path(plan_path)
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    if plan.get("format") != CAMPAIGN_PLAN_FORMAT:
        raise GovernanceCampaignError("unsupported campaign plan format")
    if str(plan.get("chain_id")) != genesis.chain_id:
        raise GovernanceCampaignError("campaign plan chain ID mismatch")
    if str(plan.get("genesis_fingerprint")) != genesis.fingerprint():
        raise GovernanceCampaignError("campaign plan genesis fingerprint mismatch")

    artifacts: list[dict[str, Any]] = []
    for raw in observation_paths:
        path = Path(raw)
        artifacts.append(
            {
                "name": path.name,
                "path": str(path),
                "size": path.stat().st_size,
                "sha256": sha256_hex(path.read_bytes()),
            }
        )
    artifacts.sort(key=lambda item: item["path"])
    manifest = {
        "format": CAMPAIGN_EVIDENCE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "chain_id": genesis.chain_id,
        "genesis_fingerprint": genesis.fingerprint(),
        "source_commit": _validate_commit(source_commit),
        "campaign_kind": str(plan["kind"]),
        "change_id": str(plan["change_id"]),
        "emit_height": int(plan["emit_height"]),
        "effective_height": int(plan["effective_height"]),
        "plan": {
            "name": plan_file.name,
            "path": str(plan_file),
            "size": plan_file.stat().st_size,
            "sha256": sha256_hex(plan_file.read_bytes()),
        },
        "observations": artifacts,
        "operator_note": str(operator_note),
        "claims": {
            "campaign_executed": bool(executed),
            "operator_reported": True,
            "independent_verification": False,
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


def verify_campaign_evidence(
    envelope: dict[str, Any],
    *,
    genesis_path: str | Path,
    artifact_directory: str | Path | None = None,
    expected_signer: str | None = None,
    expected_source_commit: str | None = None,
) -> dict[str, Any]:
    manifest = envelope.get("manifest")
    if not isinstance(manifest, dict) or manifest.get("format") != CAMPAIGN_EVIDENCE_FORMAT:
        raise GovernanceCampaignError("unsupported campaign evidence format")
    payload = canonical_json(manifest)
    if str(envelope.get("manifest_sha256", "")) != sha256_hex(payload):
        raise GovernanceCampaignError("campaign evidence manifest hash mismatch")
    public_key = str(envelope.get("public_key", ""))
    signer = str(envelope.get("signer", ""))
    if address_from_public_key(public_key) != signer:
        raise GovernanceCampaignError("campaign evidence signer identity mismatch")
    if expected_signer and signer != expected_signer:
        raise GovernanceCampaignError("campaign evidence signer does not match expected signer")
    if not verify_signature(public_key, payload, str(envelope.get("signature", ""))):
        raise GovernanceCampaignError("invalid campaign evidence signature")

    genesis = Genesis.load(genesis_path)
    if str(manifest.get("chain_id")) != genesis.chain_id:
        raise GovernanceCampaignError("campaign evidence chain ID mismatch")
    if str(manifest.get("genesis_fingerprint")) != genesis.fingerprint():
        raise GovernanceCampaignError("campaign evidence genesis fingerprint mismatch")
    if expected_source_commit and str(manifest.get("source_commit")) != _validate_commit(expected_source_commit):
        raise GovernanceCampaignError("campaign evidence source commit mismatch")

    verified_artifacts = 0
    if artifact_directory is not None:
        root = Path(artifact_directory)
        entries = [manifest["plan"], *list(manifest.get("observations") or [])]
        for item in entries:
            candidate = root / str(item["name"])
            if not candidate.is_file():
                raise GovernanceCampaignError(f"campaign evidence artifact missing: {candidate}")
            if candidate.stat().st_size != int(item["size"]):
                raise GovernanceCampaignError(f"campaign evidence artifact size mismatch: {candidate}")
            if sha256_hex(candidate.read_bytes()) != str(item["sha256"]):
                raise GovernanceCampaignError(f"campaign evidence artifact hash mismatch: {candidate}")
            verified_artifacts += 1

    return {
        "valid": True,
        "format": CAMPAIGN_EVIDENCE_FORMAT,
        "chain_id": genesis.chain_id,
        "campaign_kind": manifest["campaign_kind"],
        "change_id": manifest["change_id"],
        "signer": signer,
        "artifact_count": 1 + len(list(manifest.get("observations") or [])),
        "verified_artifact_count": verified_artifacts,
        "campaign_executed": bool((manifest.get("claims") or {}).get("campaign_executed")),
        "independent_verification": False,
        "production_mainnet_ready": False,
    }


def save_campaign_evidence(
    envelope: dict[str, Any], path: str | Path, *, overwrite: bool = False
) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise GovernanceCampaignError(f"campaign evidence already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def load_campaign_evidence(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
