from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Iterable

from .crypto import KeyPair, address_from_public_key, canonical_json, sha256_hex, verify_signature
from .ops_hardening_v24 import READINESS_FORMAT


INCIDENT_FORMAT = "crakbit-v25-incident/1"
HOST_ATTESTATION_FORMAT = "crakbit-v25-host-attestation/1"
REVIEW_GATE_FORMAT = "crakbit-v25-review-gate/1"
REVIEW_FREEZE_FORMAT = "crakbit-v25-review-freeze/1"

SEVERITIES = {"low", "medium", "high", "critical"}
REQUIRED_FAULT_KINDS = {
    "restart",
    "process-kill",
    "partition",
    "latency",
    "packet-loss",
    "load",
    "storage",
}


class ReviewCandidateV25Error(ValueError):
    pass


def _read_json(path: str | Path) -> dict[str, Any]:
    try:
        body = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewCandidateV25Error(f"invalid JSON artifact: {path}") from exc
    if not isinstance(body, dict):
        raise ReviewCandidateV25Error(f"JSON root must be an object: {path}")
    return body


def save_json(body: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise ReviewCandidateV25Error(f"output already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _file_sha256(path: str | Path) -> str:
    target = Path(path)
    if not target.is_file():
        raise ReviewCandidateV25Error(f"file not found: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_hex(value: str, length: int) -> str:
    normalized = str(value).strip().lower()
    if len(normalized) != length or any(ch not in "0123456789abcdef" for ch in normalized):
        raise ReviewCandidateV25Error(f"expected {length}-character hexadecimal value")
    return normalized


def _valid_commit(value: str) -> str:
    normalized = str(value).strip().lower()
    if len(normalized) not in {40, 64} or any(ch not in "0123456789abcdef" for ch in normalized):
        raise ReviewCandidateV25Error("source_commit must be an exact hexadecimal Git commit SHA")
    return normalized


def _artifact_entries(artifacts: Iterable[tuple[str, str | Path]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen_roles: set[str] = set()
    seen_names: set[str] = set()
    for role, raw_path in artifacts:
        normalized_role = str(role).strip().lower()
        if not normalized_role or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for ch in normalized_role):
            raise ReviewCandidateV25Error(f"invalid artifact role: {role}")
        if normalized_role in seen_roles:
            raise ReviewCandidateV25Error(f"duplicate artifact role: {normalized_role}")
        path = Path(raw_path)
        if not path.is_file():
            raise ReviewCandidateV25Error(f"artifact not found: {path}")
        if path.name in seen_names:
            raise ReviewCandidateV25Error(f"duplicate artifact file name: {path.name}")
        seen_roles.add(normalized_role)
        seen_names.add(path.name)
        entries.append(
            {
                "role": normalized_role,
                "name": path.name,
                "size": path.stat().st_size,
                "sha256": _file_sha256(path),
            }
        )
    entries.sort(key=lambda item: (item["role"], item["name"]))
    return entries


def build_incident_record(
    *,
    incident_id: str,
    severity: str,
    started_at_ms: int,
    acknowledged_at_ms: int,
    resolved_at_ms: int,
    alert_source: str,
    affected_components: list[str],
    escalation_target: str,
    summary: str,
    recovery_verified: bool,
    evidence: Iterable[tuple[str, str | Path]] = (),
) -> dict[str, Any]:
    ident = str(incident_id).strip()
    if not ident:
        raise ReviewCandidateV25Error("incident_id is required")
    normalized_severity = str(severity).strip().lower()
    if normalized_severity not in SEVERITIES:
        raise ReviewCandidateV25Error(f"unsupported incident severity: {severity}")
    started = int(started_at_ms)
    acknowledged = int(acknowledged_at_ms)
    resolved = int(resolved_at_ms)
    if started <= 0:
        raise ReviewCandidateV25Error("started_at_ms must be positive")
    if acknowledged and acknowledged < started:
        raise ReviewCandidateV25Error("acknowledged_at_ms cannot precede started_at_ms")
    if resolved and (not acknowledged or resolved < acknowledged):
        raise ReviewCandidateV25Error("resolved incident requires acknowledgement and monotonic timestamps")
    components = sorted({str(item).strip() for item in affected_components if str(item).strip()})
    if not components:
        raise ReviewCandidateV25Error("at least one affected component is required")
    escalation = str(escalation_target).strip()
    if normalized_severity in {"high", "critical"} and not escalation:
        raise ReviewCandidateV25Error("high/critical incidents require an escalation target")
    closed = bool(resolved and recovery_verified)
    return {
        "format": INCIDENT_FORMAT,
        "incident_id": ident,
        "severity": normalized_severity,
        "started_at_ms": started,
        "acknowledged_at_ms": acknowledged,
        "resolved_at_ms": resolved,
        "alert_source": str(alert_source).strip(),
        "affected_components": components,
        "escalation_target": escalation,
        "summary": str(summary).strip(),
        "recovery_verified": bool(recovery_verified),
        "closed": closed,
        "evidence": _artifact_entries(evidence),
        "contains_secrets": False,
        "independently_verified": False,
        "production_mainnet_ready": False,
    }


def build_host_attestation(
    *,
    signing_key_path: str | Path,
    operator_id: str,
    validator_id: str,
    provider: str,
    region: str,
    node_id: str,
    source_commit: str,
    package_version: str,
    cometbft_version: str,
    application_genesis_sha256: str,
    consensus_genesis_sha256: str,
    independent_management_asserted: bool,
    protected_signer_drilled: bool,
    soak_7d_completed: bool,
    backup_restore_drilled: bool,
    clean_host_state_sync_drilled: bool,
    governance_campaign_completed: bool,
    fault_kinds: Iterable[str],
    evidence: Iterable[tuple[str, str | Path]] = (),
) -> dict[str, Any]:
    operator = str(operator_id).strip()
    validator = str(validator_id).strip()
    provider_name = str(provider).strip()
    region_name = str(region).strip()
    node = str(node_id).strip()
    if not all((operator, validator, provider_name, region_name, node)):
        raise ReviewCandidateV25Error("operator_id, validator_id, provider, region and node_id are required")
    commit = _valid_commit(source_commit)
    app_genesis = _valid_hex(application_genesis_sha256, 64)
    consensus_genesis = _valid_hex(consensus_genesis_sha256, 64)
    faults = sorted({str(item).strip().lower() for item in fault_kinds if str(item).strip()})
    unsupported = set(faults) - REQUIRED_FAULT_KINDS
    if unsupported:
        raise ReviewCandidateV25Error(f"unsupported fault kinds: {sorted(unsupported)}")
    checks = {
        "independent_management_asserted": bool(independent_management_asserted),
        "protected_signer_drilled": bool(protected_signer_drilled),
        "seven_day_soak_completed": bool(soak_7d_completed),
        "backup_restore_drilled": bool(backup_restore_drilled),
        "clean_host_state_sync_drilled": bool(clean_host_state_sync_drilled),
        "governance_campaign_completed": bool(governance_campaign_completed),
        "all_required_fault_kinds_executed": REQUIRED_FAULT_KINDS.issubset(set(faults)),
    }
    manifest = {
        "format": HOST_ATTESTATION_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "operator_id": operator,
        "validator_id": validator,
        "provider": provider_name,
        "region": region_name,
        "node_id": node,
        "source_commit": commit,
        "package_version": str(package_version).strip(),
        "cometbft_version": str(cometbft_version).strip(),
        "application_genesis_sha256": app_genesis,
        "consensus_genesis_sha256": consensus_genesis,
        "fault_kinds": faults,
        "checks": checks,
        "evidence": _artifact_entries(evidence),
        "host_gate_satisfied": all(checks.values()),
        "operator_self_attested": True,
        "independently_verified": False,
        "contains_private_keys": False,
        "production_mainnet_ready": False,
    }
    key = KeyPair.load(signing_key_path)
    payload = canonical_json(manifest)
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_hex(payload),
        "signer": key.address,
        "public_key": key.public_key_b64,
        "signature": key.sign(payload),
    }


def verify_host_attestation(
    envelope: dict[str, Any],
    *,
    artifact_directory: str | Path | None = None,
    expected_signer: str | None = None,
) -> dict[str, Any]:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("manifest"), dict):
        raise ReviewCandidateV25Error("invalid host-attestation envelope")
    manifest = envelope["manifest"]
    if manifest.get("format") != HOST_ATTESTATION_FORMAT:
        raise ReviewCandidateV25Error("unsupported host-attestation format")
    payload = canonical_json(manifest)
    if str(envelope.get("manifest_sha256", "")) != sha256_hex(payload):
        raise ReviewCandidateV25Error("host-attestation manifest hash mismatch")
    public_key = str(envelope.get("public_key", ""))
    signer = str(envelope.get("signer", ""))
    if not public_key or address_from_public_key(public_key) != signer:
        raise ReviewCandidateV25Error("host-attestation signer identity mismatch")
    if expected_signer and signer != str(expected_signer):
        raise ReviewCandidateV25Error("host-attestation signer does not match expected signer")
    if not verify_signature(public_key, payload, str(envelope.get("signature", ""))):
        raise ReviewCandidateV25Error("invalid host-attestation signature")
    _valid_commit(str(manifest.get("source_commit", "")))
    _valid_hex(str(manifest.get("application_genesis_sha256", "")), 64)
    _valid_hex(str(manifest.get("consensus_genesis_sha256", "")), 64)
    if manifest.get("production_mainnet_ready") is not False:
        raise ReviewCandidateV25Error("host attestation may not claim production readiness")
    verified_artifacts = 0
    if artifact_directory is not None:
        root = Path(artifact_directory)
        for item in manifest.get("evidence", []):
            name = str(item.get("name", ""))
            if not name or Path(name).name != name:
                raise ReviewCandidateV25Error("invalid evidence file name")
            path = root / name
            if not path.is_file():
                raise ReviewCandidateV25Error(f"evidence artifact missing: {name}")
            if path.stat().st_size != int(item.get("size", -1)):
                raise ReviewCandidateV25Error(f"evidence artifact size mismatch: {name}")
            if _file_sha256(path) != str(item.get("sha256", "")):
                raise ReviewCandidateV25Error(f"evidence artifact hash mismatch: {name}")
            verified_artifacts += 1
    return {
        "valid": True,
        "signer": signer,
        "operator_id": manifest.get("operator_id"),
        "validator_id": manifest.get("validator_id"),
        "source_commit": manifest.get("source_commit"),
        "host_gate_satisfied": bool(manifest.get("host_gate_satisfied")),
        "declared_artifacts": len(manifest.get("evidence", [])),
        "verified_artifacts": verified_artifacts,
        "operator_self_attested": True,
        "independently_verified": False,
        "production_mainnet_ready": False,
    }


def build_review_gate(
    *,
    operational_readiness: dict[str, Any],
    host_attestations: list[dict[str, Any]],
    incident_records: list[dict[str, Any]],
    minimum_hosts: int = 4,
) -> dict[str, Any]:
    if int(minimum_hosts) < 4:
        raise ReviewCandidateV25Error("minimum_hosts cannot be below four")
    if operational_readiness.get("format") != READINESS_FORMAT:
        raise ReviewCandidateV25Error("unsupported v0.24 operational-readiness format")

    manifests: list[dict[str, Any]] = []
    signers: set[str] = set()
    for envelope in host_attestations:
        verified = verify_host_attestation(envelope)
        if not verified["valid"]:
            raise ReviewCandidateV25Error("invalid host attestation")
        manifest = envelope["manifest"]
        manifests.append(manifest)
        signers.add(str(envelope.get("signer", "")))

    operators = {str(item.get("operator_id", "")) for item in manifests}
    validators = {str(item.get("validator_id", "")) for item in manifests}
    providers = {str(item.get("provider", "")) for item in manifests}
    regions = {str(item.get("region", "")) for item in manifests}
    commits = {str(item.get("source_commit", "")) for item in manifests}
    package_versions = {str(item.get("package_version", "")) for item in manifests}
    comet_versions = {str(item.get("cometbft_version", "")) for item in manifests}
    app_genesis_hashes = {str(item.get("application_genesis_sha256", "")) for item in manifests}
    consensus_genesis_hashes = {str(item.get("consensus_genesis_sha256", "")) for item in manifests}

    for record in incident_records:
        if record.get("format") != INCIDENT_FORMAT:
            raise ReviewCandidateV25Error("unsupported incident-record format")

    checks = {
        "v24_operational_review_candidate": operational_readiness.get("operational_review_candidate") is True,
        "minimum_host_attestations": len(manifests) >= int(minimum_hosts),
        "unique_validator_ids": len(validators) == len(manifests) and len(validators) >= int(minimum_hosts),
        "unique_operator_ids": len(operators) == len(manifests) and len(operators) >= int(minimum_hosts),
        "unique_operator_signers": len(signers) == len(manifests) and len(signers) >= int(minimum_hosts),
        "provider_diversity": len(providers) >= 2,
        "region_diversity": len(regions) >= 2,
        "all_host_gates_satisfied": bool(manifests) and all(bool(item.get("host_gate_satisfied")) for item in manifests),
        "single_source_commit": len(commits) == 1,
        "single_package_version": len(package_versions) == 1,
        "single_cometbft_version": len(comet_versions) == 1,
        "single_application_genesis": len(app_genesis_hashes) == 1,
        "single_consensus_genesis": len(consensus_genesis_hashes) == 1,
        "incident_drill_present": bool(incident_records),
        "all_incidents_closed_and_recovery_verified": bool(incident_records)
        and all(bool(item.get("closed")) and bool(item.get("recovery_verified")) for item in incident_records),
    }
    candidate = all(checks.values())
    return {
        "format": REVIEW_GATE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "checks": checks,
        "candidate_freeze_allowed": candidate,
        "host_count": len(manifests),
        "operator_count": len(operators),
        "provider_count": len(providers),
        "region_count": len(regions),
        "source_commit": next(iter(commits)) if len(commits) == 1 else "",
        "package_version": next(iter(package_versions)) if len(package_versions) == 1 else "",
        "cometbft_version": next(iter(comet_versions)) if len(comet_versions) == 1 else "",
        "application_genesis_sha256": next(iter(app_genesis_hashes)) if len(app_genesis_hashes) == 1 else "",
        "consensus_genesis_sha256": next(iter(consensus_genesis_hashes)) if len(consensus_genesis_hashes) == 1 else "",
        "incident_count": len(incident_records),
        "operator_self_attestations_only": True,
        "independent_security_review_completed": False,
        "production_mainnet_ready": False,
    }


def build_review_freeze(
    *,
    signing_key_path: str | Path,
    source_commit: str,
    package_version: str,
    cometbft_version: str,
    application_genesis_path: str | Path,
    consensus_genesis_path: str | Path,
    review_gate: dict[str, Any],
    artifacts: Iterable[tuple[str, str | Path]],
    reviewer_scope: list[str],
) -> dict[str, Any]:
    if review_gate.get("format") != REVIEW_GATE_FORMAT:
        raise ReviewCandidateV25Error("unsupported v0.25 review-gate format")
    if review_gate.get("candidate_freeze_allowed") is not True:
        raise ReviewCandidateV25Error("review candidate cannot be frozen before every v0.25 gate is satisfied")
    commit = _valid_commit(source_commit)
    if commit != str(review_gate.get("source_commit", "")):
        raise ReviewCandidateV25Error("freeze source commit does not match review gate")
    if str(package_version).strip() != str(review_gate.get("package_version", "")):
        raise ReviewCandidateV25Error("freeze package version does not match review gate")
    if str(cometbft_version).strip() != str(review_gate.get("cometbft_version", "")):
        raise ReviewCandidateV25Error("freeze CometBFT version does not match review gate")

    app_hash = _file_sha256(application_genesis_path)
    consensus_hash = _file_sha256(consensus_genesis_path)
    if app_hash != str(review_gate.get("application_genesis_sha256", "")):
        raise ReviewCandidateV25Error("application genesis hash does not match review gate")
    if consensus_hash != str(review_gate.get("consensus_genesis_sha256", "")):
        raise ReviewCandidateV25Error("consensus genesis hash does not match review gate")
    scope = sorted({str(item).strip() for item in reviewer_scope if str(item).strip()})
    if not scope:
        raise ReviewCandidateV25Error("at least one independent-review scope item is required")

    gate_payload = canonical_json(review_gate)
    manifest = {
        "format": REVIEW_FREEZE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": commit,
        "package_version": str(package_version).strip(),
        "cometbft_version": str(cometbft_version).strip(),
        "application_genesis": {
            "name": Path(application_genesis_path).name,
            "sha256": app_hash,
        },
        "consensus_genesis": {
            "name": Path(consensus_genesis_path).name,
            "sha256": consensus_hash,
        },
        "review_gate_sha256": sha256_hex(gate_payload),
        "reviewer_scope": scope,
        "artifacts": _artifact_entries(artifacts),
        "claims": {
            "operational_evidence_gate_satisfied": True,
            "candidate_frozen_for_independent_review": True,
            "operator_self_attestations_used": True,
            "independent_security_review_completed": False,
            "production_mainnet_ready": False,
            "production_crkbit_launched": False,
        },
    }
    key = KeyPair.load(signing_key_path)
    payload = canonical_json(manifest)
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_hex(payload),
        "signer": key.address,
        "public_key": key.public_key_b64,
        "signature": key.sign(payload),
    }


def verify_review_freeze(
    envelope: dict[str, Any],
    *,
    review_gate: dict[str, Any],
    application_genesis_path: str | Path,
    consensus_genesis_path: str | Path,
    artifact_directory: str | Path | None = None,
    expected_signer: str | None = None,
    expected_source_commit: str | None = None,
) -> dict[str, Any]:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("manifest"), dict):
        raise ReviewCandidateV25Error("invalid v0.25 review-freeze envelope")
    manifest = envelope["manifest"]
    if manifest.get("format") != REVIEW_FREEZE_FORMAT:
        raise ReviewCandidateV25Error("unsupported v0.25 review-freeze format")
    if review_gate.get("format") != REVIEW_GATE_FORMAT or review_gate.get("candidate_freeze_allowed") is not True:
        raise ReviewCandidateV25Error("valid satisfied v0.25 review gate is required")
    source_commit = _valid_commit(str(manifest.get("source_commit", "")))
    if expected_source_commit and source_commit != _valid_commit(expected_source_commit):
        raise ReviewCandidateV25Error("review-freeze source commit does not match expected commit")
    payload = canonical_json(manifest)
    if str(envelope.get("manifest_sha256", "")) != sha256_hex(payload):
        raise ReviewCandidateV25Error("review-freeze manifest hash mismatch")
    public_key = str(envelope.get("public_key", ""))
    signer = str(envelope.get("signer", ""))
    if not public_key or address_from_public_key(public_key) != signer:
        raise ReviewCandidateV25Error("review-freeze signer identity mismatch")
    if expected_signer and signer != str(expected_signer):
        raise ReviewCandidateV25Error("review-freeze signer does not match expected signer")
    if not verify_signature(public_key, payload, str(envelope.get("signature", ""))):
        raise ReviewCandidateV25Error("invalid review-freeze signature")

    if str(manifest.get("review_gate_sha256", "")) != sha256_hex(canonical_json(review_gate)):
        raise ReviewCandidateV25Error("review-freeze is not bound to the supplied review gate")
    if str((manifest.get("application_genesis") or {}).get("sha256", "")) != _file_sha256(application_genesis_path):
        raise ReviewCandidateV25Error("application genesis hash mismatch")
    if str((manifest.get("consensus_genesis") or {}).get("sha256", "")) != _file_sha256(consensus_genesis_path):
        raise ReviewCandidateV25Error("consensus genesis hash mismatch")
    claims = manifest.get("claims") or {}
    if claims.get("independent_security_review_completed") is not False:
        raise ReviewCandidateV25Error("freeze may not claim completed independent review")
    if claims.get("production_mainnet_ready") is not False:
        raise ReviewCandidateV25Error("freeze may not claim production-mainnet readiness")
    if claims.get("production_crkbit_launched") is not False:
        raise ReviewCandidateV25Error("freeze may not claim production CRKBIT launch")

    verified_artifacts = 0
    if artifact_directory is not None:
        root = Path(artifact_directory)
        for item in manifest.get("artifacts", []):
            name = str(item.get("name", ""))
            if not name or Path(name).name != name:
                raise ReviewCandidateV25Error("invalid review artifact file name")
            path = root / name
            if not path.is_file():
                raise ReviewCandidateV25Error(f"review artifact missing: {name}")
            if path.stat().st_size != int(item.get("size", -1)):
                raise ReviewCandidateV25Error(f"review artifact size mismatch: {name}")
            if _file_sha256(path) != str(item.get("sha256", "")):
                raise ReviewCandidateV25Error(f"review artifact hash mismatch: {name}")
            verified_artifacts += 1

    return {
        "valid": True,
        "format": REVIEW_FREEZE_FORMAT,
        "source_commit": source_commit,
        "signer": signer,
        "declared_artifacts": len(manifest.get("artifacts", [])),
        "verified_artifacts": verified_artifacts,
        "candidate_frozen_for_independent_review": True,
        "independent_security_review_completed": False,
        "production_mainnet_ready": False,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    return _read_json(path)
