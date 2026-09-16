from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Iterable

from .crypto import KeyPair, address_from_public_key, canonical_json, sha256_hex, verify_signature


UPGRADE_PLAN_FORMAT = "crakbit-v27-upgrade-plan/1"
GOVERNANCE_POLICY_FORMAT = "crakbit-v27-governance-policy/1"
ECONOMICS_FREEZE_FORMAT = "crakbit-v27-economics-freeze/1"
EXTERNAL_REVIEW_FORMAT = "crakbit-v27-external-review/1"
CANDIDATE_IDENTITY_FORMAT = "crakbit-v27-candidate-identity/1"
RELEASE_APPROVAL_FORMAT = "crakbit-v27-release-approval/1"
FINAL_GATE_FORMAT = "crakbit-v27-final-candidate-gate/1"
FINAL_REPORT_FORMAT = "crakbit-v27-final-readiness-report/1"


class MainnetCandidateV27Error(ValueError):
    pass


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        body = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MainnetCandidateV27Error(f"invalid JSON artifact: {path}") from exc
    if not isinstance(body, dict):
        raise MainnetCandidateV27Error("JSON root must be an object")
    return body


def save_json(body: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise MainnetCandidateV27Error(f"output already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _valid_commit(value: str) -> str:
    normalized = str(value).strip().lower()
    if len(normalized) not in {40, 64} or any(ch not in "0123456789abcdef" for ch in normalized):
        raise MainnetCandidateV27Error("source commit must be an exact hexadecimal Git commit SHA")
    return normalized


def _valid_sha256(value: str) -> str:
    normalized = str(value).strip().lower()
    if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
        raise MainnetCandidateV27Error("expected a 64-character SHA-256 value")
    return normalized


def _sign(signing_key_path: str | Path, manifest: dict[str, Any]) -> dict[str, Any]:
    key = KeyPair.load(signing_key_path)
    payload = canonical_json(manifest)
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_hex(payload),
        "signer": key.address,
        "public_key": key.public_key_b64,
        "signature": key.sign(payload),
    }


def _verify(envelope: dict[str, Any], expected_format: str, *, expected_signer: str | None = None) -> dict[str, Any]:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("manifest"), dict):
        raise MainnetCandidateV27Error("invalid signed envelope")
    manifest = envelope["manifest"]
    if manifest.get("format") != expected_format:
        raise MainnetCandidateV27Error(f"unsupported format: {manifest.get('format')}")
    payload = canonical_json(manifest)
    if str(envelope.get("manifest_sha256", "")) != sha256_hex(payload):
        raise MainnetCandidateV27Error("manifest SHA-256 mismatch")
    public_key = str(envelope.get("public_key", ""))
    signer = str(envelope.get("signer", ""))
    if not public_key or address_from_public_key(public_key) != signer:
        raise MainnetCandidateV27Error("signer identity mismatch")
    if expected_signer and signer != str(expected_signer):
        raise MainnetCandidateV27Error("unexpected signer")
    if not verify_signature(public_key, payload, str(envelope.get("signature", ""))):
        raise MainnetCandidateV27Error("invalid signature")
    return manifest


def build_upgrade_plan(
    *, signing_key_path: str | Path, source_commit: str, from_package: str, to_package: str,
    from_schema: int, to_schema: int, activation_height: int, rollback_deadline_height: int,
    migration_artifact_sha256: str, rollback_artifact_sha256: str,
    minimum_ready_validators: int, total_validators: int,
) -> dict[str, Any]:
    commit = _valid_commit(source_commit)
    if not from_package.strip() or not to_package.strip() or from_package == to_package:
        raise MainnetCandidateV27Error("distinct from/to package versions are required")
    if int(from_schema) < 1 or int(to_schema) < int(from_schema):
        raise MainnetCandidateV27Error("schema versions are invalid")
    if int(activation_height) <= 0 or int(rollback_deadline_height) < int(activation_height):
        raise MainnetCandidateV27Error("activation/rollback heights are invalid")
    total = int(total_validators)
    ready = int(minimum_ready_validators)
    if total < 4 or ready < 1 or ready > total or ready * 3 <= total * 2:
        raise MainnetCandidateV27Error("upgrade readiness threshold must be strict >2/3 of at least four validators")
    manifest = {
        "format": UPGRADE_PLAN_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": commit,
        "from_package": from_package.strip(),
        "to_package": to_package.strip(),
        "from_schema": int(from_schema),
        "to_schema": int(to_schema),
        "activation_height": int(activation_height),
        "rollback_deadline_height": int(rollback_deadline_height),
        "migration_artifact_sha256": _valid_sha256(migration_artifact_sha256),
        "rollback_artifact_sha256": _valid_sha256(rollback_artifact_sha256),
        "minimum_ready_validators": ready,
        "total_validators": total,
        "checks": {
            "strict_supermajority_readiness": ready * 3 > total * 2,
            "rollback_window_declared": int(rollback_deadline_height) >= int(activation_height),
            "migration_and_rollback_bound": True,
        },
        "plan_only": True,
        "automatic_network_mutation": False,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_upgrade_plan(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, UPGRADE_PLAN_FORMAT, expected_signer=expected_signer)
    total = int(manifest.get("total_validators", 0))
    ready = int(manifest.get("minimum_ready_validators", 0))
    if total < 4 or ready * 3 <= total * 2:
        raise MainnetCandidateV27Error("upgrade plan no longer satisfies strict supermajority readiness")
    return {"valid": True, "manifest_sha256": envelope["manifest_sha256"], "activation_height": manifest["activation_height"], "production_mainnet_ready": False}


def build_governance_policy(
    *, signing_key_path: str | Path, source_commit: str, normal_timelock_blocks: int,
    emergency_timelock_blocks: int, cancel_until_blocks_before_activation: int,
    emergency_approval_numerator: int, emergency_approval_denominator: int,
) -> dict[str, Any]:
    commit = _valid_commit(source_commit)
    normal = int(normal_timelock_blocks)
    emergency = int(emergency_timelock_blocks)
    cancel = int(cancel_until_blocks_before_activation)
    num = int(emergency_approval_numerator)
    den = int(emergency_approval_denominator)
    if normal < 10 or emergency < 1 or emergency > normal:
        raise MainnetCandidateV27Error("timelock block values are invalid")
    if cancel < 1 or cancel >= normal:
        raise MainnetCandidateV27Error("cancellation window is invalid")
    if den <= 0 or num <= 0 or num > den or num * 3 <= den * 2:
        raise MainnetCandidateV27Error("emergency approval threshold must be strict >2/3")
    checks = {
        "normal_timelock_present": normal >= 10,
        "emergency_still_delayed": emergency >= 1,
        "cancellation_before_activation": cancel >= 1,
        "emergency_requires_strict_supermajority": num * 3 > den * 2,
        "emergency_cannot_mint_or_reassign_user_balances": True,
        "supply_change_requires_separate_economic_review": True,
    }
    manifest = {
        "format": GOVERNANCE_POLICY_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": commit,
        "normal_timelock_blocks": normal,
        "emergency_timelock_blocks": emergency,
        "cancel_until_blocks_before_activation": cancel,
        "emergency_approval": {"numerator": num, "denominator": den},
        "checks": checks,
        "policy_gate_satisfied": all(checks.values()),
        "research_policy_only": True,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_governance_policy(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, GOVERNANCE_POLICY_FORMAT, expected_signer=expected_signer)
    if manifest.get("policy_gate_satisfied") is not True:
        raise MainnetCandidateV27Error("governance policy gate is not satisfied")
    return {"valid": True, "manifest_sha256": envelope["manifest_sha256"], "production_mainnet_ready": False}


def build_economics_freeze(
    *, signing_key_path: str | Path, source_commit: str, application_genesis_sha256: str,
    consensus_genesis_sha256: str, parameters: dict[str, Any],
) -> dict[str, Any]:
    commit = _valid_commit(source_commit)
    required = {"symbol", "decimals", "max_supply_atomic", "initial_supply_atomic", "minimum_fee_atomic", "validator_incentive_model", "distribution_commitment_sha256"}
    missing = sorted(required - set(parameters))
    if missing:
        raise MainnetCandidateV27Error(f"economics parameters missing fields: {missing}")
    symbol = str(parameters["symbol"]).strip().upper()
    decimals = int(parameters["decimals"])
    maximum = int(parameters["max_supply_atomic"])
    initial = int(parameters["initial_supply_atomic"])
    fee = int(parameters["minimum_fee_atomic"])
    if symbol != "CRKBIT":
        raise MainnetCandidateV27Error("production-candidate symbol must be CRKBIT")
    if not 0 <= decimals <= 18 or maximum <= 0 or initial < 0 or initial > maximum or fee < 0:
        raise MainnetCandidateV27Error("economics numeric parameters are invalid")
    distribution = _valid_sha256(str(parameters["distribution_commitment_sha256"]))
    normalized = dict(parameters)
    normalized.update({"symbol": symbol, "decimals": decimals, "max_supply_atomic": maximum, "initial_supply_atomic": initial, "minimum_fee_atomic": fee, "distribution_commitment_sha256": distribution})
    manifest = {
        "format": ECONOMICS_FREEZE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": commit,
        "application_genesis_sha256": _valid_sha256(application_genesis_sha256),
        "consensus_genesis_sha256": _valid_sha256(consensus_genesis_sha256),
        "parameters": normalized,
        "parameters_sha256": sha256_hex(canonical_json(normalized)),
        "investment_return_promised": False,
        "token_sale_authorized_by_this_artifact": False,
        "requires_independent_economic_and_legal_review": True,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_economics_freeze(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, ECONOMICS_FREEZE_FORMAT, expected_signer=expected_signer)
    params = manifest.get("parameters")
    if not isinstance(params, dict) or manifest.get("parameters_sha256") != sha256_hex(canonical_json(params)):
        raise MainnetCandidateV27Error("economics parameter hash mismatch")
    if manifest.get("investment_return_promised") is not False or manifest.get("token_sale_authorized_by_this_artifact") is not False:
        raise MainnetCandidateV27Error("invalid economics claims")
    return {"valid": True, "manifest_sha256": envelope["manifest_sha256"], "parameters_sha256": manifest["parameters_sha256"], "production_mainnet_ready": False}


def build_external_review(
    *, signing_key_path: str | Path, review_kind: str, reviewer: str, source_commit: str,
    subject_sha256: str, decision: str, scope: Iterable[str], conditions: Iterable[str] = (),
) -> dict[str, Any]:
    kind = str(review_kind).strip().lower()
    if kind not in {"economic-security", "legal-regulatory"}:
        raise MainnetCandidateV27Error("review_kind must be economic-security or legal-regulatory")
    normalized_decision = str(decision).strip().lower()
    if normalized_decision not in {"passed", "failed"}:
        raise MainnetCandidateV27Error("review decision must be passed or failed")
    scopes = sorted({str(item).strip() for item in scope if str(item).strip()})
    if not scopes:
        raise MainnetCandidateV27Error("at least one review scope is required")
    manifest = {
        "format": EXTERNAL_REVIEW_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "review_kind": kind,
        "reviewer": str(reviewer).strip(),
        "source_commit": _valid_commit(source_commit),
        "subject_sha256": _valid_sha256(subject_sha256),
        "decision": normalized_decision,
        "scope": scopes,
        "conditions": sorted({str(item).strip() for item in conditions if str(item).strip()}),
        "independent_external_attestation": True,
        "production_mainnet_ready": False,
    }
    if not manifest["reviewer"]:
        raise MainnetCandidateV27Error("reviewer is required")
    return _sign(signing_key_path, manifest)


def verify_external_review(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, EXTERNAL_REVIEW_FORMAT, expected_signer=expected_signer)
    return {"valid": True, "review_kind": manifest["review_kind"], "decision": manifest["decision"], "manifest_sha256": envelope["manifest_sha256"], "production_mainnet_ready": False}


def build_candidate_identity(
    *, operational_readiness: dict[str, Any], remediation_gate: dict[str, Any], governance_policy: dict[str, Any],
    economics_freeze: dict[str, Any], upgrade_plan: dict[str, Any], economic_review: dict[str, Any], legal_review: dict[str, Any],
) -> dict[str, Any]:
    verify_governance_policy(governance_policy)
    verify_economics_freeze(economics_freeze)
    verify_upgrade_plan(upgrade_plan)
    econ = verify_external_review(economic_review)
    legal = verify_external_review(legal_review)
    if econ["review_kind"] != "economic-security" or legal["review_kind"] != "legal-regulatory":
        raise MainnetCandidateV27Error("external review kinds do not match required roles")
    candidate = remediation_gate.get("candidate")
    if not isinstance(candidate, dict):
        raise MainnetCandidateV27Error("v0.26 remediation gate candidate is missing")
    source_commit = _valid_commit(str(candidate.get("source_commit", "")))
    identity = {
        "format": CANDIDATE_IDENTITY_FORMAT,
        "source_commit": source_commit,
        "package_version": str(candidate.get("package_version", "")),
        "cometbft_version": str(candidate.get("cometbft_version", "")),
        "application_genesis_sha256": _valid_sha256(str(candidate.get("application_genesis_sha256", ""))),
        "consensus_genesis_sha256": _valid_sha256(str(candidate.get("consensus_genesis_sha256", ""))),
        "dependency_lock_sha256": _valid_sha256(str(candidate.get("dependency_lock_sha256", ""))),
        "sbom_sha256": _valid_sha256(str(candidate.get("sbom_sha256", ""))),
        "operational_readiness_sha256": sha256_hex(canonical_json(operational_readiness)),
        "remediation_gate_sha256": sha256_hex(canonical_json(remediation_gate)),
        "governance_policy_manifest_sha256": str(governance_policy.get("manifest_sha256", "")),
        "economics_manifest_sha256": str(economics_freeze.get("manifest_sha256", "")),
        "upgrade_plan_manifest_sha256": str(upgrade_plan.get("manifest_sha256", "")),
        "economic_review_manifest_sha256": str(economic_review.get("manifest_sha256", "")),
        "legal_review_manifest_sha256": str(legal_review.get("manifest_sha256", "")),
    }
    return {"identity": identity, "candidate_identity_sha256": sha256_hex(canonical_json(identity)), "production_mainnet_ready": False}


def build_release_approval(
    *, signing_key_path: str | Path, approver_id: str, role: str, source_commit: str,
    candidate_identity_sha256: str, decision: str, note: str = "",
) -> dict[str, Any]:
    normalized_decision = str(decision).strip().lower()
    if normalized_decision not in {"approve", "reject"}:
        raise MainnetCandidateV27Error("decision must be approve or reject")
    manifest = {
        "format": RELEASE_APPROVAL_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "approver_id": str(approver_id).strip(),
        "role": str(role).strip(),
        "source_commit": _valid_commit(source_commit),
        "candidate_identity_sha256": _valid_sha256(candidate_identity_sha256),
        "decision": normalized_decision,
        "note": str(note).strip(),
        "single_signature_is_not_sufficient_for_release": True,
        "production_mainnet_ready": False,
    }
    if not manifest["approver_id"] or not manifest["role"]:
        raise MainnetCandidateV27Error("approver_id and role are required")
    return _sign(signing_key_path, manifest)


def verify_release_approval(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, RELEASE_APPROVAL_FORMAT, expected_signer=expected_signer)
    return {"valid": True, "approver_id": manifest["approver_id"], "decision": manifest["decision"], "candidate_identity_sha256": manifest["candidate_identity_sha256"], "signer": envelope["signer"], "production_mainnet_ready": False}


def build_final_candidate_gate(
    *, identity: dict[str, Any], operational_readiness: dict[str, Any], remediation_gate: dict[str, Any],
    governance_policy: dict[str, Any], economics_freeze: dict[str, Any], upgrade_plan: dict[str, Any],
    economic_review: dict[str, Any], legal_review: dict[str, Any], release_approvals: list[dict[str, Any]], minimum_approvals: int = 3,
) -> dict[str, Any]:
    computed = build_candidate_identity(
        operational_readiness=operational_readiness,
        remediation_gate=remediation_gate,
        governance_policy=governance_policy,
        economics_freeze=economics_freeze,
        upgrade_plan=upgrade_plan,
        economic_review=economic_review,
        legal_review=legal_review,
    )
    if identity.get("candidate_identity_sha256") != computed["candidate_identity_sha256"] or identity.get("identity") != computed["identity"]:
        raise MainnetCandidateV27Error("candidate identity does not match supplied gate artifacts")
    minimum = int(minimum_approvals)
    if minimum < 3:
        raise MainnetCandidateV27Error("minimum release approvals cannot be below three")
    approvals = []
    signers: set[str] = set()
    approvers: set[str] = set()
    for envelope in release_approvals:
        checked = verify_release_approval(envelope)
        if checked["candidate_identity_sha256"] != computed["candidate_identity_sha256"]:
            raise MainnetCandidateV27Error("release approval targets a different candidate identity")
        if envelope["manifest"].get("source_commit") != computed["identity"]["source_commit"]:
            raise MainnetCandidateV27Error("release approval source commit mismatch")
        approvals.append(envelope)
        signers.add(str(envelope.get("signer", "")))
        approvers.add(str(envelope["manifest"].get("approver_id", "")))
    econ = verify_external_review(economic_review)
    legal = verify_external_review(legal_review)
    checks = {
        "operational_review_candidate": operational_readiness.get("operational_review_candidate") is True,
        "v26_remediation_gate_passed": remediation_gate.get("refreeze_allowed") is True and len(remediation_gate.get("unresolved_high_critical_ids", [])) == 0,
        "governance_policy_passed": governance_policy["manifest"].get("policy_gate_satisfied") is True,
        "upgrade_plan_strict_supermajority": upgrade_plan["manifest"]["checks"].get("strict_supermajority_readiness") is True,
        "economic_security_review_passed": econ["decision"] == "passed",
        "legal_regulatory_review_passed": legal["decision"] == "passed",
        "minimum_unique_release_approvals": len(approvals) >= minimum and len(signers) == len(approvals) and len(approvers) == len(approvals),
        "all_release_decisions_approve": bool(approvals) and all(env["manifest"].get("decision") == "approve" for env in approvals),
    }
    return {
        "format": FINAL_GATE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "candidate_identity_sha256": computed["candidate_identity_sha256"],
        "source_commit": computed["identity"]["source_commit"],
        "checks": checks,
        "release_approval_manifest_sha256s": sorted(str(env.get("manifest_sha256", "")) for env in approvals),
        "release_approval_signers": sorted(signers),
        "release_approver_ids": sorted(approvers),
        "mainnet_candidate_gate_satisfied": all(checks.values()),
        "production_mainnet_ready": False,
        "production_mainnet_launched": False,
        "production_crkbit_launched": False,
        "note": "Passing this gate creates a final mainnet-candidate evidence state only; it does not launch a network or authorize custody of real value.",
    }


def build_final_report(
    *, signing_key_path: str | Path, final_gate: dict[str, Any], artifacts: Iterable[tuple[str, str | Path]] = (),
) -> dict[str, Any]:
    if final_gate.get("format") != FINAL_GATE_FORMAT or final_gate.get("mainnet_candidate_gate_satisfied") is not True:
        raise MainnetCandidateV27Error("final candidate gate is not satisfied")
    entries = []
    seen = set()
    for role, raw_path in artifacts:
        normalized = str(role).strip().lower()
        path = Path(raw_path)
        if not normalized or normalized in seen or not path.is_file():
            raise MainnetCandidateV27Error("invalid or duplicate final report artifact")
        seen.add(normalized)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append({"role": normalized, "name": path.name, "size": path.stat().st_size, "sha256": digest})
    entries.sort(key=lambda item: (item["role"], item["name"]))
    manifest = {
        "format": FINAL_REPORT_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "candidate_identity_sha256": final_gate["candidate_identity_sha256"],
        "source_commit": final_gate["source_commit"],
        "final_gate_sha256": sha256_hex(canonical_json(final_gate)),
        "artifacts": entries,
        "mainnet_candidate_gate_satisfied": True,
        "production_mainnet_ready": False,
        "production_mainnet_launched": False,
        "production_crkbit_launched": False,
    }
    return _sign(signing_key_path, manifest)


def verify_final_report(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, FINAL_REPORT_FORMAT, expected_signer=expected_signer)
    if manifest.get("mainnet_candidate_gate_satisfied") is not True or manifest.get("production_mainnet_ready") is not False:
        raise MainnetCandidateV27Error("invalid final readiness report claims")
    return {"valid": True, "candidate_identity_sha256": manifest["candidate_identity_sha256"], "source_commit": manifest["source_commit"], "mainnet_candidate_gate_satisfied": True, "production_mainnet_ready": False}
