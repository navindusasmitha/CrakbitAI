from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Iterable

from .crypto import KeyPair, address_from_public_key, canonical_json, sha256_hex, verify_signature


FINDINGS_FORMAT = "crakbit-v26-review-findings/1"
RETEST_FORMAT = "crakbit-v26-independent-retest/1"
SUPPLY_ATTESTATION_FORMAT = "crakbit-v26-supply-chain-attestation/1"
EDGE_ATTESTATION_FORMAT = "crakbit-v26-public-edge-attestation/1"
REMEDIATION_GATE_FORMAT = "crakbit-v26-remediation-gate/1"
REFREEZE_FORMAT = "crakbit-v26-review-refreeze/1"

SEVERITIES = {"low", "medium", "high", "critical"}
FINDING_STATUSES = {"open", "remediated", "accepted-risk", "not-applicable"}
RETEST_RESULTS = {"passed", "failed"}


class ReviewRemediationV26Error(ValueError):
    pass


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        body = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewRemediationV26Error(f"invalid JSON artifact: {path}") from exc
    if not isinstance(body, dict):
        raise ReviewRemediationV26Error(f"JSON root must be an object: {path}")
    return body


def save_json(body: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise ReviewRemediationV26Error(f"output already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _file_sha256(path: str | Path) -> str:
    target = Path(path)
    if not target.is_file():
        raise ReviewRemediationV26Error(f"file not found: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_commit(value: str) -> str:
    normalized = str(value).strip().lower()
    if len(normalized) not in {40, 64} or any(ch not in "0123456789abcdef" for ch in normalized):
        raise ReviewRemediationV26Error("commit must be an exact hexadecimal Git commit SHA")
    return normalized


def _valid_sha256(value: str) -> str:
    normalized = str(value).strip().lower()
    if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
        raise ReviewRemediationV26Error("expected a 64-character SHA-256 value")
    return normalized


def _artifact_entries(artifacts: Iterable[tuple[str, str | Path]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    roles: set[str] = set()
    names: set[str] = set()
    for role, raw_path in artifacts:
        normalized_role = str(role).strip().lower()
        if not normalized_role or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for ch in normalized_role):
            raise ReviewRemediationV26Error(f"invalid artifact role: {role}")
        path = Path(raw_path)
        if normalized_role in roles:
            raise ReviewRemediationV26Error(f"duplicate artifact role: {normalized_role}")
        if not path.is_file():
            raise ReviewRemediationV26Error(f"artifact not found: {path}")
        if path.name in names:
            raise ReviewRemediationV26Error(f"duplicate artifact file name: {path.name}")
        roles.add(normalized_role)
        names.add(path.name)
        entries.append({
            "role": normalized_role,
            "name": path.name,
            "size": path.stat().st_size,
            "sha256": _file_sha256(path),
        })
    entries.sort(key=lambda item: (item["role"], item["name"]))
    return entries


def _sign_manifest(manifest: dict[str, Any], signing_key_path: str | Path) -> dict[str, Any]:
    key = KeyPair.load(signing_key_path)
    payload = canonical_json(manifest)
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_hex(payload),
        "signer": key.address,
        "public_key": key.public_key_b64,
        "signature": key.sign(payload),
    }


def _verify_envelope(envelope: dict[str, Any], expected_format: str, *, expected_signer: str | None = None) -> dict[str, Any]:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("manifest"), dict):
        raise ReviewRemediationV26Error("invalid signed envelope")
    manifest = envelope["manifest"]
    if manifest.get("format") != expected_format:
        raise ReviewRemediationV26Error(f"unsupported signed artifact format: {manifest.get('format')}")
    payload = canonical_json(manifest)
    if str(envelope.get("manifest_sha256", "")) != sha256_hex(payload):
        raise ReviewRemediationV26Error("signed artifact manifest hash mismatch")
    public_key = str(envelope.get("public_key", ""))
    signer = str(envelope.get("signer", ""))
    if not public_key or address_from_public_key(public_key) != signer:
        raise ReviewRemediationV26Error("signed artifact signer identity mismatch")
    if expected_signer and signer != str(expected_signer):
        raise ReviewRemediationV26Error("signed artifact signer does not match expected signer")
    if not verify_signature(public_key, payload, str(envelope.get("signature", ""))):
        raise ReviewRemediationV26Error("invalid signed artifact signature")
    return manifest


def _stable_finding_id(review_id: str, external_id: str, component: str, title: str) -> str:
    seed = canonical_json({
        "review_id": review_id.strip(),
        "external_id": external_id.strip(),
        "component": component.strip().lower(),
        "title": title.strip(),
    })
    return "CRK-REV-" + sha256_hex(seed)[:16].upper()


def build_findings_register(
    *,
    signing_key_path: str | Path,
    review_id: str,
    reviewer: str,
    source_commit: str,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    review = str(review_id).strip()
    reviewer_name = str(reviewer).strip()
    if not review or not reviewer_name:
        raise ReviewRemediationV26Error("review_id and reviewer are required")
    commit = _valid_commit(source_commit)
    normalized: list[dict[str, Any]] = []
    ids: set[str] = set()
    for raw in findings:
        if not isinstance(raw, dict):
            raise ReviewRemediationV26Error("each finding must be an object")
        external_id = str(raw.get("external_id", "")).strip()
        component = str(raw.get("component", "")).strip()
        title = str(raw.get("title", "")).strip()
        severity = str(raw.get("severity", "")).strip().lower()
        status = str(raw.get("status", "open")).strip().lower()
        if not external_id or not component or not title:
            raise ReviewRemediationV26Error("finding external_id, component and title are required")
        if severity not in SEVERITIES:
            raise ReviewRemediationV26Error(f"unsupported severity: {severity}")
        if status not in FINDING_STATUSES:
            raise ReviewRemediationV26Error(f"unsupported finding status: {status}")
        affected_commit = _valid_commit(str(raw.get("affected_commit", commit)))
        finding_id = _stable_finding_id(review, external_id, component, title)
        if finding_id in ids:
            raise ReviewRemediationV26Error(f"duplicate stable finding id: {finding_id}")
        ids.add(finding_id)
        remediation_commit = str(raw.get("remediation_commit", "")).strip().lower()
        regression_test = str(raw.get("regression_test", "")).strip()
        config_sha256 = str(raw.get("config_sha256", "")).strip().lower()
        if remediation_commit:
            remediation_commit = _valid_commit(remediation_commit)
        if config_sha256:
            config_sha256 = _valid_sha256(config_sha256)
        if status == "remediated" and (not remediation_commit or not regression_test):
            raise ReviewRemediationV26Error("remediated findings require remediation_commit and regression_test")
        normalized.append({
            "finding_id": finding_id,
            "external_id": external_id,
            "severity": severity,
            "component": component,
            "title": title,
            "status": status,
            "affected_commit": affected_commit,
            "reproduction": str(raw.get("reproduction", "")).strip(),
            "remediation_commit": remediation_commit,
            "config_sha256": config_sha256,
            "regression_test": regression_test,
            "notes": str(raw.get("notes", "")).strip(),
        })
    normalized.sort(key=lambda item: item["finding_id"])
    unresolved_high_critical = [
        item["finding_id"] for item in normalized
        if item["severity"] in {"high", "critical"} and item["status"] != "remediated"
    ]
    manifest = {
        "format": FINDINGS_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "review_id": review,
        "reviewer": reviewer_name,
        "source_commit": commit,
        "findings": normalized,
        "summary": {
            "total": len(normalized),
            "critical": sum(item["severity"] == "critical" for item in normalized),
            "high": sum(item["severity"] == "high" for item in normalized),
            "medium": sum(item["severity"] == "medium" for item in normalized),
            "low": sum(item["severity"] == "low" for item in normalized),
            "unresolved_high_critical": len(unresolved_high_critical),
        },
        "unresolved_high_critical_ids": unresolved_high_critical,
        "release_blocked": bool(unresolved_high_critical),
        "independent_review_claimed_by_signer": True,
        "production_mainnet_ready": False,
    }
    return _sign_manifest(manifest, signing_key_path)


def verify_findings_register(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify_envelope(envelope, FINDINGS_FORMAT, expected_signer=expected_signer)
    _valid_commit(str(manifest.get("source_commit", "")))
    seen: set[str] = set()
    for item in manifest.get("findings", []):
        expected = _stable_finding_id(
            str(manifest.get("review_id", "")),
            str(item.get("external_id", "")),
            str(item.get("component", "")),
            str(item.get("title", "")),
        )
        if item.get("finding_id") != expected or expected in seen:
            raise ReviewRemediationV26Error("finding stable ID mismatch or duplicate")
        seen.add(expected)
    return {
        "valid": True,
        "signer": envelope["signer"],
        "review_id": manifest.get("review_id"),
        "source_commit": manifest.get("source_commit"),
        "finding_count": len(manifest.get("findings", [])),
        "release_blocked": bool(manifest.get("release_blocked")),
        "production_mainnet_ready": False,
    }


def build_retest_record(
    *,
    signing_key_path: str | Path,
    reviewer: str,
    finding_id: str,
    tested_commit: str,
    result: str,
    notes: str = "",
    evidence: Iterable[tuple[str, str | Path]] = (),
) -> dict[str, Any]:
    reviewer_name = str(reviewer).strip()
    finding = str(finding_id).strip().upper()
    normalized_result = str(result).strip().lower()
    if not reviewer_name or not finding.startswith("CRK-REV-"):
        raise ReviewRemediationV26Error("reviewer and a CRK-REV finding_id are required")
    if normalized_result not in RETEST_RESULTS:
        raise ReviewRemediationV26Error("retest result must be passed or failed")
    manifest = {
        "format": RETEST_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "reviewer": reviewer_name,
        "finding_id": finding,
        "tested_commit": _valid_commit(tested_commit),
        "result": normalized_result,
        "notes": str(notes).strip(),
        "evidence": _artifact_entries(evidence),
        "independent_retest_asserted": True,
        "production_mainnet_ready": False,
    }
    return _sign_manifest(manifest, signing_key_path)


def verify_retest_record(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify_envelope(envelope, RETEST_FORMAT, expected_signer=expected_signer)
    _valid_commit(str(manifest.get("tested_commit", "")))
    if manifest.get("result") not in RETEST_RESULTS:
        raise ReviewRemediationV26Error("invalid retest result")
    return {
        "valid": True,
        "signer": envelope["signer"],
        "finding_id": manifest.get("finding_id"),
        "tested_commit": manifest.get("tested_commit"),
        "result": manifest.get("result"),
        "production_mainnet_ready": False,
    }


def build_supply_chain_attestation(
    *,
    signing_key_path: str | Path,
    attestor: str,
    source_commit: str,
    package_version: str,
    dependency_lock_sha256: str,
    sbom_sha256: str,
    python_reproducible: bool,
    go_reproducible: bool,
    dependency_review_complete: bool,
    transitive_sbom_complete: bool,
    evidence: Iterable[tuple[str, str | Path]] = (),
) -> dict[str, Any]:
    name = str(attestor).strip()
    if not name or not str(package_version).strip():
        raise ReviewRemediationV26Error("attestor and package_version are required")
    checks = {
        "python_reproducible": bool(python_reproducible),
        "go_reproducible": bool(go_reproducible),
        "dependency_review_complete": bool(dependency_review_complete),
        "transitive_sbom_complete": bool(transitive_sbom_complete),
    }
    manifest = {
        "format": SUPPLY_ATTESTATION_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "attestor": name,
        "source_commit": _valid_commit(source_commit),
        "package_version": str(package_version).strip(),
        "dependency_lock_sha256": _valid_sha256(dependency_lock_sha256),
        "sbom_sha256": _valid_sha256(sbom_sha256),
        "checks": checks,
        "supply_chain_gate_satisfied": all(checks.values()),
        "evidence": _artifact_entries(evidence),
        "contains_secrets": False,
        "production_mainnet_ready": False,
    }
    return _sign_manifest(manifest, signing_key_path)


def verify_supply_chain_attestation(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify_envelope(envelope, SUPPLY_ATTESTATION_FORMAT, expected_signer=expected_signer)
    _valid_commit(str(manifest.get("source_commit", "")))
    _valid_sha256(str(manifest.get("dependency_lock_sha256", "")))
    _valid_sha256(str(manifest.get("sbom_sha256", "")))
    return {
        "valid": True,
        "signer": envelope["signer"],
        "source_commit": manifest.get("source_commit"),
        "supply_chain_gate_satisfied": bool(manifest.get("supply_chain_gate_satisfied")),
        "production_mainnet_ready": False,
    }


def build_edge_attestation(
    *,
    signing_key_path: str | Path,
    operator: str,
    edge_id: str,
    source_commit: str,
    tls_min_version: str,
    tls_automation: bool,
    waf_enabled: bool,
    ddos_protection_enabled: bool,
    load_test_passed: bool,
    failover_drilled: bool,
    capacity_rps: int,
    sustained_minutes: int,
    evidence: Iterable[tuple[str, str | Path]] = (),
) -> dict[str, Any]:
    operator_name = str(operator).strip()
    edge = str(edge_id).strip()
    tls = str(tls_min_version).strip().upper().replace("TLS", "").strip()
    if not operator_name or not edge:
        raise ReviewRemediationV26Error("operator and edge_id are required")
    if tls not in {"1.2", "1.3"}:
        raise ReviewRemediationV26Error("tls_min_version must be TLS 1.2 or TLS 1.3")
    checks = {
        "tls_minimum_accepted": True,
        "tls_automation": bool(tls_automation),
        "waf_enabled": bool(waf_enabled),
        "ddos_protection_enabled": bool(ddos_protection_enabled),
        "load_test_passed": bool(load_test_passed),
        "failover_drilled": bool(failover_drilled),
        "positive_capacity": int(capacity_rps) > 0,
        "sustained_test_at_least_30m": int(sustained_minutes) >= 30,
    }
    manifest = {
        "format": EDGE_ATTESTATION_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "operator": operator_name,
        "edge_id": edge,
        "source_commit": _valid_commit(source_commit),
        "tls_min_version": tls,
        "capacity_rps": int(capacity_rps),
        "sustained_minutes": int(sustained_minutes),
        "checks": checks,
        "edge_gate_satisfied": all(checks.values()),
        "evidence": _artifact_entries(evidence),
        "contains_provider_secrets": False,
        "production_mainnet_ready": False,
    }
    return _sign_manifest(manifest, signing_key_path)


def verify_edge_attestation(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify_envelope(envelope, EDGE_ATTESTATION_FORMAT, expected_signer=expected_signer)
    _valid_commit(str(manifest.get("source_commit", "")))
    if manifest.get("contains_provider_secrets") is not False:
        raise ReviewRemediationV26Error("edge attestation may not claim provider secrets are included")
    return {
        "valid": True,
        "signer": envelope["signer"],
        "edge_id": manifest.get("edge_id"),
        "source_commit": manifest.get("source_commit"),
        "edge_gate_satisfied": bool(manifest.get("edge_gate_satisfied")),
        "production_mainnet_ready": False,
    }


def _previous_manifest(previous_freeze: dict[str, Any] | None) -> dict[str, Any] | None:
    if previous_freeze is None:
        return None
    if not isinstance(previous_freeze, dict) or not isinstance(previous_freeze.get("manifest"), dict):
        raise ReviewRemediationV26Error("previous freeze must be a signed-envelope-shaped JSON object")
    return previous_freeze["manifest"]


def build_remediation_gate(
    *,
    findings_register: dict[str, Any],
    retest_records: list[dict[str, Any]],
    supply_chain_attestation: dict[str, Any],
    edge_attestations: list[dict[str, Any]],
    candidate_source_commit: str,
    package_version: str,
    cometbft_version: str,
    application_genesis_sha256: str,
    consensus_genesis_sha256: str,
    previous_freeze: dict[str, Any] | None = None,
) -> dict[str, Any]:
    verify_findings_register(findings_register)
    findings_manifest = findings_register["manifest"]
    retests: list[dict[str, Any]] = []
    for envelope in retest_records:
        verify_retest_record(envelope)
        retests.append(envelope)
    verify_supply_chain_attestation(supply_chain_attestation)
    supply = supply_chain_attestation["manifest"]
    edges: list[dict[str, Any]] = []
    for envelope in edge_attestations:
        verify_edge_attestation(envelope)
        edges.append(envelope)

    source_commit = _valid_commit(candidate_source_commit)
    app_genesis = _valid_sha256(application_genesis_sha256)
    consensus_genesis = _valid_sha256(consensus_genesis_sha256)
    high_critical = [item for item in findings_manifest.get("findings", []) if item.get("severity") in {"high", "critical"}]
    unresolved: list[str] = []
    retested: list[str] = []
    for finding in high_critical:
        finding_id = str(finding.get("finding_id", ""))
        remediation_commit = str(finding.get("remediation_commit", ""))
        if finding.get("status") != "remediated" or not remediation_commit:
            unresolved.append(finding_id)
            continue
        matched = [
            env for env in retests
            if env["manifest"].get("finding_id") == finding_id
            and env["manifest"].get("tested_commit") == remediation_commit
            and env["manifest"].get("result") == "passed"
        ]
        if not matched:
            unresolved.append(finding_id)
        else:
            retested.append(finding_id)

    failed_retests = [env["manifest"].get("finding_id") for env in retests if env["manifest"].get("result") == "failed"]
    edge_sources = {str(env["manifest"].get("source_commit", "")) for env in edges}
    checks = {
        "candidate_source_matches_review_source": findings_manifest.get("source_commit") == source_commit,
        "no_unresolved_high_critical_findings": len(unresolved) == 0,
        "no_failed_retests": len(failed_retests) == 0,
        "all_high_critical_independently_retested": len(retested) == len(high_critical),
        "supply_chain_gate_satisfied": supply.get("supply_chain_gate_satisfied") is True,
        "supply_chain_source_matches_candidate": supply.get("source_commit") == source_commit,
        "supply_chain_package_matches_candidate": supply.get("package_version") == str(package_version).strip(),
        "at_least_two_public_edges": len(edges) >= 2,
        "all_public_edge_gates_satisfied": bool(edges) and all(env["manifest"].get("edge_gate_satisfied") is True for env in edges),
        "public_edge_sources_match_candidate": bool(edges) and edge_sources == {source_commit},
    }

    previous = _previous_manifest(previous_freeze)
    supersession_reasons: list[str] = []
    if previous is not None:
        comparisons = {
            "source commit changed": (previous.get("source_commit"), source_commit),
            "package version changed": (previous.get("package_version"), str(package_version).strip()),
            "CometBFT version changed": (previous.get("cometbft_version"), str(cometbft_version).strip()),
            "application genesis changed": (previous.get("application_genesis_sha256"), app_genesis),
            "consensus genesis changed": (previous.get("consensus_genesis_sha256"), consensus_genesis),
        }
        for reason, (old, new) in comparisons.items():
            if old not in (None, "") and str(old) != str(new):
                supersession_reasons.append(reason)
        old_supply = previous.get("dependency_lock_sha256")
        if old_supply and old_supply != supply.get("dependency_lock_sha256"):
            supersession_reasons.append("dependency lock changed")
        supersession_reasons.append("review/remediation evidence changed")

    refreeze_allowed = all(checks.values())
    return {
        "format": REMEDIATION_GATE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "candidate": {
            "source_commit": source_commit,
            "package_version": str(package_version).strip(),
            "cometbft_version": str(cometbft_version).strip(),
            "application_genesis_sha256": app_genesis,
            "consensus_genesis_sha256": consensus_genesis,
            "dependency_lock_sha256": supply.get("dependency_lock_sha256"),
            "sbom_sha256": supply.get("sbom_sha256"),
        },
        "review_id": findings_manifest.get("review_id"),
        "findings_manifest_sha256": findings_register.get("manifest_sha256"),
        "high_critical_count": len(high_critical),
        "high_critical_retested_ids": sorted(retested),
        "unresolved_high_critical_ids": sorted(unresolved),
        "failed_retest_finding_ids": sorted(str(item) for item in failed_retests),
        "supply_chain_manifest_sha256": supply_chain_attestation.get("manifest_sha256"),
        "edge_manifest_sha256s": sorted(str(env.get("manifest_sha256")) for env in edges),
        "checks": checks,
        "previous_candidate_superseded": previous is not None and bool(supersession_reasons),
        "supersession_reasons": supersession_reasons,
        "refreeze_allowed": refreeze_allowed,
        "independent_security_review_completed": False,
        "production_mainnet_ready": False,
        "production_crkbit_launched": False,
    }


def build_refreeze(
    *,
    signing_key_path: str | Path,
    remediation_gate: dict[str, Any],
    artifacts: Iterable[tuple[str, str | Path]],
    reviewer_scope: Iterable[str],
) -> dict[str, Any]:
    if remediation_gate.get("format") != REMEDIATION_GATE_FORMAT:
        raise ReviewRemediationV26Error("unsupported remediation gate format")
    if remediation_gate.get("refreeze_allowed") is not True:
        raise ReviewRemediationV26Error("remediation gate does not allow candidate re-freeze")
    candidate = remediation_gate.get("candidate")
    if not isinstance(candidate, dict):
        raise ReviewRemediationV26Error("remediation gate candidate is missing")
    scopes = sorted({str(item).strip() for item in reviewer_scope if str(item).strip()})
    if not scopes:
        raise ReviewRemediationV26Error("at least one reviewer scope is required")
    manifest = {
        "format": REFREEZE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        **candidate,
        "review_id": remediation_gate.get("review_id"),
        "remediation_gate_sha256": sha256_hex(canonical_json(remediation_gate)),
        "artifacts": _artifact_entries(artifacts),
        "reviewer_scope": scopes,
        "supersedes_previous_candidate": bool(remediation_gate.get("previous_candidate_superseded")),
        "supersession_reasons": list(remediation_gate.get("supersession_reasons") or []),
        "claims": {
            "remediation_gate_passed": True,
            "independent_review_cycle_recorded": True,
            "independent_security_review_completed": False,
            "production_mainnet_ready": False,
            "production_crkbit_launched": False,
        },
    }
    return _sign_manifest(manifest, signing_key_path)


def verify_refreeze(
    envelope: dict[str, Any],
    *,
    remediation_gate: dict[str, Any],
    artifact_directory: str | Path | None = None,
    expected_signer: str | None = None,
) -> dict[str, Any]:
    manifest = _verify_envelope(envelope, REFREEZE_FORMAT, expected_signer=expected_signer)
    if remediation_gate.get("format") != REMEDIATION_GATE_FORMAT or remediation_gate.get("refreeze_allowed") is not True:
        raise ReviewRemediationV26Error("invalid or failing remediation gate")
    expected_gate_hash = sha256_hex(canonical_json(remediation_gate))
    if manifest.get("remediation_gate_sha256") != expected_gate_hash:
        raise ReviewRemediationV26Error("re-freeze remediation gate hash mismatch")
    candidate = remediation_gate.get("candidate") or {}
    for field in (
        "source_commit",
        "package_version",
        "cometbft_version",
        "application_genesis_sha256",
        "consensus_genesis_sha256",
        "dependency_lock_sha256",
        "sbom_sha256",
    ):
        if manifest.get(field) != candidate.get(field):
            raise ReviewRemediationV26Error(f"re-freeze candidate mismatch: {field}")
    claims = manifest.get("claims")
    if not isinstance(claims, dict) or claims.get("production_mainnet_ready") is not False:
        raise ReviewRemediationV26Error("re-freeze may not claim production mainnet readiness")
    if claims.get("production_crkbit_launched") is not False:
        raise ReviewRemediationV26Error("re-freeze may not claim production CRKBIT launch")

    verified_artifacts = 0
    if artifact_directory is not None:
        root = Path(artifact_directory)
        for item in manifest.get("artifacts", []):
            name = str(item.get("name", ""))
            if not name or Path(name).name != name:
                raise ReviewRemediationV26Error("invalid re-freeze artifact file name")
            path = root / name
            if not path.is_file():
                raise ReviewRemediationV26Error(f"re-freeze artifact missing: {name}")
            if path.stat().st_size != int(item.get("size", -1)) or _file_sha256(path) != str(item.get("sha256", "")):
                raise ReviewRemediationV26Error(f"re-freeze artifact mismatch: {name}")
            verified_artifacts += 1
    return {
        "valid": True,
        "signer": envelope["signer"],
        "source_commit": manifest.get("source_commit"),
        "review_id": manifest.get("review_id"),
        "declared_artifacts": len(manifest.get("artifacts", [])),
        "verified_artifacts": verified_artifacts,
        "supersedes_previous_candidate": bool(manifest.get("supersedes_previous_candidate")),
        "independent_security_review_completed": False,
        "production_mainnet_ready": False,
        "production_crkbit_launched": False,
    }
