from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any, Iterable

from .crypto import canonical_json, sha256_hex
from . import mainnet_candidate_v27 as v27


LAUNCH_RUNBOOK_FORMAT = "crakbit-v28-launch-runbook/1"
CUTOVER_REHEARSAL_FORMAT = "crakbit-v28-cutover-rehearsal/1"
EDGE_SLO_FORMAT = "crakbit-v28-edge-slo/1"
SIGNER_DRILL_FORMAT = "crakbit-v28-signer-drill/1"
UPGRADE_REHEARSAL_FORMAT = "crakbit-v28-upgrade-rehearsal/1"
RISK_REGISTER_FORMAT = "crakbit-v28-risk-register/1"
REVIEW_SIGNOFF_FORMAT = "crakbit-v28-review-signoff/1"
REPRO_ATTESTATION_FORMAT = "crakbit-v28-repro-attestation/1"
REHEARSAL_GATE_FORMAT = "crakbit-v28-rehearsal-gate/1"
RELEASE_FREEZE_FORMAT = "crakbit-v28-release-freeze/1"
LAUNCH_DECISION_FORMAT = "crakbit-v28-launch-decision/1"

REQUIRED_TECHNICAL_REVIEW_SCOPES = {
    "consensus-application",
    "network-rpc",
    "cryptography-key-management",
    "browser-wallet",
}
SEVERITIES = {"low", "medium", "high", "critical"}
RISK_STATUSES = {"open", "mitigated", "accepted"}


class LaunchRehearsalV28Error(ValueError):
    pass


def load_json(path: str | Path) -> dict[str, Any]:
    return v27.load_json(path)


def save_json(body: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    return v27.save_json(body, path, overwrite=overwrite)


def _valid_commit(value: str) -> str:
    try:
        return v27._valid_commit(value)
    except Exception as exc:
        raise LaunchRehearsalV28Error(str(exc)) from exc


def _valid_sha(value: str) -> str:
    try:
        return v27._valid_sha256(value)
    except Exception as exc:
        raise LaunchRehearsalV28Error(str(exc)) from exc


def _sign(key: str | Path, manifest: dict[str, Any]) -> dict[str, Any]:
    return v27._sign(key, manifest)


def _verify(envelope: dict[str, Any], expected_format: str, *, expected_signer: str | None = None) -> dict[str, Any]:
    try:
        return v27._verify(envelope, expected_format, expected_signer=expected_signer)
    except Exception as exc:
        raise LaunchRehearsalV28Error(str(exc)) from exc


def _clean_values(values: Iterable[str]) -> list[str]:
    return [item for item in dict.fromkeys(str(v).strip() for v in values) if item]


def _artifact_entries(artifacts: Iterable[tuple[str, str | Path]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    roles: set[str] = set()
    names: set[str] = set()
    for role, raw_path in artifacts:
        normalized_role = str(role).strip().lower()
        if not normalized_role or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for ch in normalized_role):
            raise LaunchRehearsalV28Error(f"invalid artifact role: {role}")
        if normalized_role in roles:
            raise LaunchRehearsalV28Error(f"duplicate artifact role: {normalized_role}")
        path = Path(raw_path)
        if not path.is_file():
            raise LaunchRehearsalV28Error(f"artifact not found: {path}")
        if path.name in names:
            raise LaunchRehearsalV28Error(f"duplicate artifact file name: {path.name}")
        roles.add(normalized_role)
        names.add(path.name)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append({"role": normalized_role, "name": path.name, "size": path.stat().st_size, "sha256": digest})
    return sorted(entries, key=lambda item: (item["role"], item["name"]))


def build_launch_runbook(
    *, signing_key_path: str | Path, source_commit: str, candidate_identity_sha256: str,
    validator_ids: Iterable[str], genesis_ceremony_steps: Iterable[str], validator_start_order: Iterable[str],
    rollback_steps: Iterable[str], cutover_window_minutes: int,
) -> dict[str, Any]:
    validators = _clean_values(validator_ids)
    ceremony = _clean_values(genesis_ceremony_steps)
    start_order = _clean_values(validator_start_order)
    rollback = _clean_values(rollback_steps)
    window = int(cutover_window_minutes)
    if len(validators) < 4:
        raise LaunchRehearsalV28Error("launch rehearsal requires at least four unique validators")
    if len(start_order) != len(validators) or set(start_order) != set(validators):
        raise LaunchRehearsalV28Error("validator start order must contain every validator exactly once")
    if not ceremony or not rollback or window < 15:
        raise LaunchRehearsalV28Error("genesis ceremony, rollback steps and a >=15 minute cutover window are required")
    manifest = {
        "format": LAUNCH_RUNBOOK_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": _valid_commit(source_commit),
        "candidate_identity_sha256": _valid_sha(candidate_identity_sha256),
        "validator_ids": validators,
        "genesis_ceremony_steps": ceremony,
        "validator_start_order": start_order,
        "rollback_steps": rollback,
        "cutover_window_minutes": window,
        "dry_run_only": True,
        "automatic_network_mutation": False,
        "automatic_dns_change": False,
        "automatic_fund_movement": False,
        "runbook_gate_satisfied": True,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_launch_runbook(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, LAUNCH_RUNBOOK_FORMAT, expected_signer=expected_signer)
    if manifest.get("runbook_gate_satisfied") is not True or manifest.get("dry_run_only") is not True:
        raise LaunchRehearsalV28Error("launch runbook gate is not satisfied")
    if manifest.get("automatic_network_mutation") is not False:
        raise LaunchRehearsalV28Error("launch runbook may not automatically mutate the network")
    return {"valid": True, "candidate_identity_sha256": manifest["candidate_identity_sha256"], "production_mainnet_ready": False}


def build_cutover_rehearsal(
    *, signing_key_path: str | Path, source_commit: str, candidate_identity_sha256: str,
    dns_names: Iterable[str], rpc_endpoints: Iterable[str], explorer_endpoints: Iterable[str],
    dns_ttl_seconds: int, rollback_verified: bool, rpc_failover_verified: bool,
    explorer_failover_verified: bool, no_production_dns_changed: bool,
) -> dict[str, Any]:
    dns = _clean_values(dns_names)
    rpcs = _clean_values(rpc_endpoints)
    explorers = _clean_values(explorer_endpoints)
    ttl = int(dns_ttl_seconds)
    if not dns or len(rpcs) < 2 or len(explorers) < 2:
        raise LaunchRehearsalV28Error("cutover rehearsal requires DNS names and at least two RPC/explorer endpoints")
    if ttl < 30 or ttl > 86400:
        raise LaunchRehearsalV28Error("dns_ttl_seconds must be between 30 and 86400")
    checks = {
        "rollback_verified": bool(rollback_verified),
        "rpc_failover_verified": bool(rpc_failover_verified),
        "explorer_failover_verified": bool(explorer_failover_verified),
        "no_production_dns_changed": bool(no_production_dns_changed),
    }
    manifest = {
        "format": CUTOVER_REHEARSAL_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": _valid_commit(source_commit),
        "candidate_identity_sha256": _valid_sha(candidate_identity_sha256),
        "dns_names": dns,
        "rpc_endpoints": rpcs,
        "explorer_endpoints": explorers,
        "dns_ttl_seconds": ttl,
        "checks": checks,
        "cutover_gate_satisfied": all(checks.values()),
        "rehearsal_only": True,
        "automatic_dns_change": False,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_cutover_rehearsal(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, CUTOVER_REHEARSAL_FORMAT, expected_signer=expected_signer)
    if manifest.get("cutover_gate_satisfied") is not True or manifest.get("automatic_dns_change") is not False:
        raise LaunchRehearsalV28Error("cutover rehearsal gate is not satisfied")
    return {"valid": True, "candidate_identity_sha256": manifest["candidate_identity_sha256"], "production_mainnet_ready": False}


def build_edge_slo_evidence(
    *, signing_key_path: str | Path, source_commit: str, candidate_identity_sha256: str, edge_id: str,
    availability_percent: float, p95_latency_ms: float, error_rate_percent: float, capacity_rps: int,
    sustained_minutes: int, failover_seconds: float, min_availability_percent: float,
    max_p95_latency_ms: float, max_error_rate_percent: float, min_capacity_rps: int, max_failover_seconds: float,
) -> dict[str, Any]:
    edge = str(edge_id).strip()
    if not edge:
        raise LaunchRehearsalV28Error("edge_id is required")
    availability = float(availability_percent)
    latency = float(p95_latency_ms)
    error_rate = float(error_rate_percent)
    capacity = int(capacity_rps)
    duration = int(sustained_minutes)
    failover = float(failover_seconds)
    if not (0 <= availability <= 100 and latency >= 0 and 0 <= error_rate <= 100 and capacity > 0 and duration > 0 and failover >= 0):
        raise LaunchRehearsalV28Error("invalid SLO measurements")
    thresholds = {
        "min_availability_percent": float(min_availability_percent),
        "max_p95_latency_ms": float(max_p95_latency_ms),
        "max_error_rate_percent": float(max_error_rate_percent),
        "min_capacity_rps": int(min_capacity_rps),
        "max_failover_seconds": float(max_failover_seconds),
    }
    checks = {
        "availability_met": availability >= thresholds["min_availability_percent"],
        "latency_met": latency <= thresholds["max_p95_latency_ms"],
        "error_rate_met": error_rate <= thresholds["max_error_rate_percent"],
        "capacity_met": capacity >= thresholds["min_capacity_rps"],
        "failover_met": failover <= thresholds["max_failover_seconds"],
        "sustained_window_present": duration >= 30,
    }
    manifest = {
        "format": EDGE_SLO_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": _valid_commit(source_commit),
        "candidate_identity_sha256": _valid_sha(candidate_identity_sha256),
        "edge_id": edge,
        "measurements": {
            "availability_percent": availability,
            "p95_latency_ms": latency,
            "error_rate_percent": error_rate,
            "capacity_rps": capacity,
            "sustained_minutes": duration,
            "failover_seconds": failover,
        },
        "thresholds": thresholds,
        "checks": checks,
        "slo_gate_satisfied": all(checks.values()),
        "operator_reported": True,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_edge_slo_evidence(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, EDGE_SLO_FORMAT, expected_signer=expected_signer)
    return {"valid": True, "edge_id": manifest["edge_id"], "slo_gate_satisfied": bool(manifest.get("slo_gate_satisfied")), "candidate_identity_sha256": manifest["candidate_identity_sha256"], "production_mainnet_ready": False}


def build_signer_drill(
    *, signing_key_path: str | Path, source_commit: str, candidate_identity_sha256: str,
    signer_id: str, custody_type: str, no_key_export: bool, rotation_successful: bool,
    old_key_revoked: bool, backup_recovery_successful: bool, catastrophic_recovery_drilled: bool,
    validator_quorum_preserved: bool,
) -> dict[str, Any]:
    signer = str(signer_id).strip()
    custody = str(custody_type).strip().lower()
    if not signer or custody not in {"hsm", "remote-signer", "hardware-backed", "equivalent-protected"}:
        raise LaunchRehearsalV28Error("a signer_id and protected custody_type are required")
    checks = {
        "no_key_export": bool(no_key_export),
        "rotation_successful": bool(rotation_successful),
        "old_key_revoked": bool(old_key_revoked),
        "backup_recovery_successful": bool(backup_recovery_successful),
        "catastrophic_recovery_drilled": bool(catastrophic_recovery_drilled),
        "validator_quorum_preserved": bool(validator_quorum_preserved),
    }
    manifest = {
        "format": SIGNER_DRILL_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": _valid_commit(source_commit),
        "candidate_identity_sha256": _valid_sha(candidate_identity_sha256),
        "signer_id": signer,
        "custody_type": custody,
        "checks": checks,
        "signer_drill_gate_satisfied": all(checks.values()),
        "contains_private_key": False,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_signer_drill(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, SIGNER_DRILL_FORMAT, expected_signer=expected_signer)
    return {"valid": True, "signer_id": manifest["signer_id"], "signer_drill_gate_satisfied": bool(manifest.get("signer_drill_gate_satisfied")), "candidate_identity_sha256": manifest["candidate_identity_sha256"], "production_mainnet_ready": False}


def build_upgrade_rehearsal(
    *, signing_key_path: str | Path, source_commit: str, candidate_identity_sha256: str,
    upgrade_plan: dict[str, Any], validator_count: int, validators_successful: int,
    upgrade_completed: bool, application_hash_converged: bool, rollback_exercised: bool,
    rollback_hash_converged: bool, no_data_loss: bool,
) -> dict[str, Any]:
    checked = v27.verify_upgrade_plan(upgrade_plan)
    total = int(validator_count)
    successful = int(validators_successful)
    if total < 4 or successful < 0 or successful > total:
        raise LaunchRehearsalV28Error("invalid validator rehearsal counts")
    checks = {
        "strict_supermajority_successful": successful * 3 > total * 2,
        "upgrade_completed": bool(upgrade_completed),
        "application_hash_converged": bool(application_hash_converged),
        "rollback_exercised": bool(rollback_exercised),
        "rollback_hash_converged": bool(rollback_hash_converged),
        "no_data_loss": bool(no_data_loss),
    }
    manifest = {
        "format": UPGRADE_REHEARSAL_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": _valid_commit(source_commit),
        "candidate_identity_sha256": _valid_sha(candidate_identity_sha256),
        "upgrade_plan_manifest_sha256": checked["manifest_sha256"],
        "validator_count": total,
        "validators_successful": successful,
        "checks": checks,
        "upgrade_rehearsal_gate_satisfied": all(checks.values()),
        "automatic_upgrade": False,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_upgrade_rehearsal(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, UPGRADE_REHEARSAL_FORMAT, expected_signer=expected_signer)
    return {"valid": True, "upgrade_rehearsal_gate_satisfied": bool(manifest.get("upgrade_rehearsal_gate_satisfied")), "candidate_identity_sha256": manifest["candidate_identity_sha256"], "production_mainnet_ready": False}


def build_risk_register(
    *, signing_key_path: str | Path, source_commit: str, candidate_identity_sha256: str, risks: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    blockers: list[str] = []
    for raw in risks:
        risk_id = str(raw.get("risk_id", "")).strip()
        severity = str(raw.get("severity", "")).strip().lower()
        status = str(raw.get("status", "")).strip().lower()
        owner = str(raw.get("owner", "")).strip()
        description = str(raw.get("description", "")).strip()
        rationale = str(raw.get("rationale", "")).strip()
        if not risk_id or risk_id in seen:
            raise LaunchRehearsalV28Error("risk IDs must be non-empty and unique")
        if severity not in SEVERITIES or status not in RISK_STATUSES or not owner or not description:
            raise LaunchRehearsalV28Error(f"invalid risk entry: {risk_id}")
        if status == "accepted" and not rationale:
            raise LaunchRehearsalV28Error(f"accepted risk requires rationale: {risk_id}")
        evidence_sha = str(raw.get("evidence_sha256", "")).strip().lower()
        if evidence_sha:
            evidence_sha = _valid_sha(evidence_sha)
        if severity in {"high", "critical"} and status != "mitigated":
            blockers.append(risk_id)
        seen.add(risk_id)
        normalized.append({
            "risk_id": risk_id,
            "severity": severity,
            "status": status,
            "owner": owner,
            "description": description,
            "rationale": rationale,
            "evidence_sha256": evidence_sha,
        })
    normalized.sort(key=lambda item: item["risk_id"])
    manifest = {
        "format": RISK_REGISTER_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": _valid_commit(source_commit),
        "candidate_identity_sha256": _valid_sha(candidate_identity_sha256),
        "risks": normalized,
        "blocking_risk_ids": sorted(blockers),
        "risk_gate_satisfied": len(blockers) == 0,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_risk_register(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, RISK_REGISTER_FORMAT, expected_signer=expected_signer)
    return {"valid": True, "risk_gate_satisfied": bool(manifest.get("risk_gate_satisfied")), "blocking_risk_ids": list(manifest.get("blocking_risk_ids", [])), "candidate_identity_sha256": manifest["candidate_identity_sha256"], "production_mainnet_ready": False}


def build_review_signoff(
    *, signing_key_path: str | Path, reviewer: str, scope: str, source_commit: str,
    candidate_identity_sha256: str, subject_sha256: str, decision: str,
    independent_reviewer_asserted: bool, conditions: Iterable[str] = (),
) -> dict[str, Any]:
    reviewer_name = str(reviewer).strip()
    normalized_scope = str(scope).strip().lower()
    normalized_decision = str(decision).strip().lower()
    if not reviewer_name or not normalized_scope or normalized_decision not in {"passed", "conditional", "failed"}:
        raise LaunchRehearsalV28Error("reviewer, scope and valid decision are required")
    conds = _clean_values(conditions)
    if normalized_decision == "conditional" and not conds:
        raise LaunchRehearsalV28Error("conditional signoff requires at least one condition")
    manifest = {
        "format": REVIEW_SIGNOFF_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "reviewer": reviewer_name,
        "scope": normalized_scope,
        "source_commit": _valid_commit(source_commit),
        "candidate_identity_sha256": _valid_sha(candidate_identity_sha256),
        "subject_sha256": _valid_sha(subject_sha256),
        "decision": normalized_decision,
        "conditions": conds,
        "independent_reviewer_asserted": bool(independent_reviewer_asserted),
        "signoff_gate_satisfied": normalized_decision == "passed" and bool(independent_reviewer_asserted),
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_review_signoff(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, REVIEW_SIGNOFF_FORMAT, expected_signer=expected_signer)
    return {"valid": True, "reviewer": manifest["reviewer"], "scope": manifest["scope"], "decision": manifest["decision"], "signoff_gate_satisfied": bool(manifest.get("signoff_gate_satisfied")), "candidate_identity_sha256": manifest["candidate_identity_sha256"], "production_mainnet_ready": False}


def build_repro_attestation(
    *, signing_key_path: str | Path, attestor: str, source_commit: str, candidate_identity_sha256: str,
    package_version: str, dependency_lock_sha256: str, sbom_sha256: str,
    python_wheel_sha256: str, go_binary_sha256: str, python_reproducible: bool,
    go_reproducible: bool, transitive_dependencies_reviewed: bool, source_tag_verified: bool,
) -> dict[str, Any]:
    name = str(attestor).strip()
    package = str(package_version).strip()
    if not name or not package:
        raise LaunchRehearsalV28Error("attestor and package_version are required")
    checks = {
        "python_reproducible": bool(python_reproducible),
        "go_reproducible": bool(go_reproducible),
        "transitive_dependencies_reviewed": bool(transitive_dependencies_reviewed),
        "source_tag_verified": bool(source_tag_verified),
    }
    manifest = {
        "format": REPRO_ATTESTATION_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "attestor": name,
        "source_commit": _valid_commit(source_commit),
        "candidate_identity_sha256": _valid_sha(candidate_identity_sha256),
        "package_version": package,
        "dependency_lock_sha256": _valid_sha(dependency_lock_sha256),
        "sbom_sha256": _valid_sha(sbom_sha256),
        "python_wheel_sha256": _valid_sha(python_wheel_sha256),
        "go_binary_sha256": _valid_sha(go_binary_sha256),
        "checks": checks,
        "repro_gate_satisfied": all(checks.values()),
        "external_attestation": True,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_repro_attestation(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, REPRO_ATTESTATION_FORMAT, expected_signer=expected_signer)
    return {"valid": True, "attestor": manifest["attestor"], "repro_gate_satisfied": bool(manifest.get("repro_gate_satisfied")), "candidate_identity_sha256": manifest["candidate_identity_sha256"], "production_mainnet_ready": False}


def build_rehearsal_gate(
    *, final_report_v27: dict[str, Any], launch_runbook: dict[str, Any], cutover_rehearsal: dict[str, Any],
    edge_slo_evidence: list[dict[str, Any]], signer_drill: dict[str, Any], upgrade_rehearsal: dict[str, Any],
    risk_register: dict[str, Any], reviewer_signoffs: list[dict[str, Any]], repro_attestation: dict[str, Any],
    minimum_edge_slos: int = 2, minimum_unique_review_signers: int = 3,
) -> dict[str, Any]:
    final_checked = v27.verify_final_report(final_report_v27)
    runbook = _verify(launch_runbook, LAUNCH_RUNBOOK_FORMAT)
    cutover = _verify(cutover_rehearsal, CUTOVER_REHEARSAL_FORMAT)
    signer = _verify(signer_drill, SIGNER_DRILL_FORMAT)
    upgrade = _verify(upgrade_rehearsal, UPGRADE_REHEARSAL_FORMAT)
    risks = _verify(risk_register, RISK_REGISTER_FORMAT)
    repro = _verify(repro_attestation, REPRO_ATTESTATION_FORMAT)

    source_commit = _valid_commit(str(final_checked["source_commit"]))
    candidate_identity = _valid_sha(str(final_checked["candidate_identity_sha256"]))

    envelopes = [launch_runbook, cutover_rehearsal, signer_drill, upgrade_rehearsal, risk_register, repro_attestation]
    manifests = [runbook, cutover, signer, upgrade, risks, repro]
    identity_match = all(m.get("source_commit") == source_commit and m.get("candidate_identity_sha256") == candidate_identity for m in manifests)

    edge_manifests: list[dict[str, Any]] = []
    edge_ids: set[str] = set()
    for envelope in edge_slo_evidence:
        manifest = _verify(envelope, EDGE_SLO_FORMAT)
        edge_manifests.append(manifest)
        edge_ids.add(str(manifest.get("edge_id", "")))
    edge_identity_match = bool(edge_manifests) and all(m.get("source_commit") == source_commit and m.get("candidate_identity_sha256") == candidate_identity for m in edge_manifests)

    signoff_manifests: list[dict[str, Any]] = []
    signoff_signers: set[str] = set()
    scopes: set[str] = set()
    subject = str(final_report_v27.get("manifest_sha256", ""))
    for envelope in reviewer_signoffs:
        manifest = _verify(envelope, REVIEW_SIGNOFF_FORMAT)
        signoff_manifests.append(manifest)
        signoff_signers.add(str(envelope.get("signer", "")))
        scopes.add(str(manifest.get("scope", "")))
    signoff_identity_match = bool(signoff_manifests) and all(
        m.get("source_commit") == source_commit
        and m.get("candidate_identity_sha256") == candidate_identity
        and m.get("subject_sha256") == subject
        for m in signoff_manifests
    )

    checks = {
        "v27_mainnet_candidate_gate_satisfied": final_report_v27.get("manifest", {}).get("mainnet_candidate_gate_satisfied") is True,
        "all_core_artifacts_match_candidate": identity_match,
        "launch_runbook_satisfied": runbook.get("runbook_gate_satisfied") is True,
        "cutover_rehearsal_satisfied": cutover.get("cutover_gate_satisfied") is True,
        "minimum_unique_passing_edge_slos": len(edge_manifests) >= int(minimum_edge_slos) and len(edge_ids) == len(edge_manifests) and all(m.get("slo_gate_satisfied") is True for m in edge_manifests),
        "edge_slos_match_candidate": edge_identity_match,
        "protected_signer_recovery_drill_satisfied": signer.get("signer_drill_gate_satisfied") is True,
        "coordinated_upgrade_rollback_rehearsal_satisfied": upgrade.get("upgrade_rehearsal_gate_satisfied") is True,
        "risk_register_has_no_high_critical_blockers": risks.get("risk_gate_satisfied") is True,
        "reproducible_build_attestation_satisfied": repro.get("repro_gate_satisfied") is True,
        "review_signoffs_match_exact_final_report": signoff_identity_match,
        "required_technical_review_scopes_passed": REQUIRED_TECHNICAL_REVIEW_SCOPES.issubset(scopes) and all(m.get("signoff_gate_satisfied") is True for m in signoff_manifests),
        "minimum_unique_review_signers": len(signoff_signers) >= int(minimum_unique_review_signers),
    }
    return {
        "format": REHEARSAL_GATE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": source_commit,
        "candidate_identity_sha256": candidate_identity,
        "v27_final_report_manifest_sha256": subject,
        "core_manifest_sha256s": sorted(str(env.get("manifest_sha256", "")) for env in envelopes),
        "edge_slo_manifest_sha256s": sorted(str(env.get("manifest_sha256", "")) for env in edge_slo_evidence),
        "review_signoff_manifest_sha256s": sorted(str(env.get("manifest_sha256", "")) for env in reviewer_signoffs),
        "review_scopes": sorted(scopes),
        "review_signers": sorted(signoff_signers),
        "checks": checks,
        "launch_rehearsal_gate_satisfied": all(checks.values()),
        "independent_corroboration_required": True,
        "manual_launch_decision_required": True,
        "automatic_launch": False,
        "production_mainnet_ready": False,
        "production_mainnet_launched": False,
        "production_crkbit_launched": False,
    }


def build_release_freeze(
    *, signing_key_path: str | Path, rehearsal_gate: dict[str, Any], artifacts: Iterable[tuple[str, str | Path]] = (),
) -> dict[str, Any]:
    if rehearsal_gate.get("format") != REHEARSAL_GATE_FORMAT or rehearsal_gate.get("launch_rehearsal_gate_satisfied") is not True:
        raise LaunchRehearsalV28Error("launch rehearsal gate is not satisfied")
    manifest = {
        "format": RELEASE_FREEZE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": _valid_commit(str(rehearsal_gate.get("source_commit", ""))),
        "candidate_identity_sha256": _valid_sha(str(rehearsal_gate.get("candidate_identity_sha256", ""))),
        "rehearsal_gate_sha256": sha256_hex(canonical_json(rehearsal_gate)),
        "artifacts": _artifact_entries(artifacts),
        "frozen_for_manual_launch_review": True,
        "independently_corroborated_evidence_required": True,
        "manual_launch_decision_required": True,
        "automatic_launch": False,
        "production_mainnet_ready": False,
        "production_mainnet_launched": False,
        "production_crkbit_launched": False,
    }
    return _sign(signing_key_path, manifest)


def verify_release_freeze(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, RELEASE_FREEZE_FORMAT, expected_signer=expected_signer)
    if manifest.get("frozen_for_manual_launch_review") is not True or manifest.get("automatic_launch") is not False:
        raise LaunchRehearsalV28Error("invalid release-freeze claims")
    return {"valid": True, "candidate_identity_sha256": manifest["candidate_identity_sha256"], "source_commit": manifest["source_commit"], "production_mainnet_ready": False, "production_mainnet_launched": False}


def build_launch_decision(
    *, signing_key_path: str | Path, release_freeze: dict[str, Any], decision_maker: str,
    decision: str, rationale: str,
) -> dict[str, Any]:
    verify_release_freeze(release_freeze)
    maker = str(decision_maker).strip()
    normalized = str(decision).strip().lower()
    reason = str(rationale).strip()
    if not maker or normalized not in {"hold", "approve-launch-window"} or not reason:
        raise LaunchRehearsalV28Error("decision maker, hold/approve-launch-window decision and rationale are required")
    freeze_manifest = release_freeze["manifest"]
    manifest = {
        "format": LAUNCH_DECISION_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "decision_maker": maker,
        "decision": normalized,
        "rationale": reason,
        "source_commit": freeze_manifest["source_commit"],
        "candidate_identity_sha256": freeze_manifest["candidate_identity_sha256"],
        "release_freeze_manifest_sha256": str(release_freeze.get("manifest_sha256", "")),
        "automatic_execution": False,
        "does_not_change_dns": True,
        "does_not_start_validators": True,
        "does_not_move_funds": True,
        "production_mainnet_ready": False,
        "production_mainnet_launched": False,
        "production_crkbit_launched": False,
    }
    return _sign(signing_key_path, manifest)


def verify_launch_decision(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, LAUNCH_DECISION_FORMAT, expected_signer=expected_signer)
    if manifest.get("automatic_execution") is not False or manifest.get("production_mainnet_launched") is not False:
        raise LaunchRehearsalV28Error("launch decision artifact may not claim automatic or completed launch")
    return {"valid": True, "decision": manifest["decision"], "decision_maker": manifest["decision_maker"], "candidate_identity_sha256": manifest["candidate_identity_sha256"], "production_mainnet_ready": False, "production_mainnet_launched": False}
