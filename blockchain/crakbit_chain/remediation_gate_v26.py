from __future__ import annotations

import time
from typing import Any

from .review_remediation_v26 import (
    REMEDIATION_GATE_FORMAT,
    ReviewRemediationV26Error,
    _previous_manifest,
    _valid_commit,
    _valid_sha256,
    verify_edge_attestation,
    verify_findings_register,
    verify_retest_record,
    verify_supply_chain_attestation,
)


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
    """Build the v0.26 hard release/re-freeze gate.

    The initial review may target an older frozen commit. High/critical fixes are
    therefore accepted only when the latest signed retest for each finding was
    performed against the *candidate_source_commit* being re-frozen.
    """
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
    package = str(package_version).strip()
    comet = str(cometbft_version).strip()
    if not package or not comet:
        raise ReviewRemediationV26Error("package_version and cometbft_version are required")

    high_critical = [
        item for item in findings_manifest.get("findings", [])
        if item.get("severity") in {"high", "critical"}
    ]

    latest_candidate_retest: dict[str, dict[str, Any]] = {}
    for envelope in retests:
        manifest = envelope["manifest"]
        if manifest.get("tested_commit") != source_commit:
            continue
        finding_id = str(manifest.get("finding_id", ""))
        current = latest_candidate_retest.get(finding_id)
        if current is None or int(manifest.get("created_at_ms", 0)) >= int(current["manifest"].get("created_at_ms", 0)):
            latest_candidate_retest[finding_id] = envelope

    unresolved: list[str] = []
    retested: list[str] = []
    failed_latest: list[str] = []
    for finding in high_critical:
        finding_id = str(finding.get("finding_id", ""))
        remediation_declared = (
            finding.get("status") == "remediated"
            and bool(str(finding.get("remediation_commit", "")))
            and bool(str(finding.get("regression_test", "")))
        )
        latest = latest_candidate_retest.get(finding_id)
        if not remediation_declared or latest is None:
            unresolved.append(finding_id)
            continue
        if latest["manifest"].get("result") != "passed":
            unresolved.append(finding_id)
            failed_latest.append(finding_id)
            continue
        retested.append(finding_id)

    edge_sources = {str(env["manifest"].get("source_commit", "")) for env in edges}
    checks = {
        "all_high_critical_declared_remediated_and_retested_on_candidate": len(unresolved) == 0,
        "no_latest_candidate_retest_failures": len(failed_latest) == 0,
        "supply_chain_gate_satisfied": supply.get("supply_chain_gate_satisfied") is True,
        "supply_chain_source_matches_candidate": supply.get("source_commit") == source_commit,
        "supply_chain_package_matches_candidate": supply.get("package_version") == package,
        "at_least_two_public_edges": len(edges) >= 2,
        "all_public_edge_gates_satisfied": bool(edges) and all(env["manifest"].get("edge_gate_satisfied") is True for env in edges),
        "public_edge_sources_match_candidate": bool(edges) and edge_sources == {source_commit},
    }

    previous = _previous_manifest(previous_freeze)
    supersession_reasons: list[str] = []
    if previous is not None:
        comparisons = {
            "source commit changed": (previous.get("source_commit"), source_commit),
            "package version changed": (previous.get("package_version"), package),
            "CometBFT version changed": (previous.get("cometbft_version"), comet),
            "application genesis changed": (previous.get("application_genesis_sha256"), app_genesis),
            "consensus genesis changed": (previous.get("consensus_genesis_sha256"), consensus_genesis),
        }
        for reason, (old, new) in comparisons.items():
            if old not in (None, "") and str(old) != str(new):
                supersession_reasons.append(reason)
        old_lock = previous.get("dependency_lock_sha256")
        if old_lock and old_lock != supply.get("dependency_lock_sha256"):
            supersession_reasons.append("dependency lock changed")
        # A remediation gate/retest set is itself new review evidence. A newly
        # signed re-freeze must supersede the prior candidate rather than silently
        # mutating it in place.
        supersession_reasons.append("review/remediation evidence changed")

    return {
        "format": REMEDIATION_GATE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "candidate": {
            "source_commit": source_commit,
            "package_version": package,
            "cometbft_version": comet,
            "application_genesis_sha256": app_genesis,
            "consensus_genesis_sha256": consensus_genesis,
            "dependency_lock_sha256": supply.get("dependency_lock_sha256"),
            "sbom_sha256": supply.get("sbom_sha256"),
        },
        "initial_review_source_commit": findings_manifest.get("source_commit"),
        "source_changed_since_initial_review": findings_manifest.get("source_commit") != source_commit,
        "review_id": findings_manifest.get("review_id"),
        "findings_manifest_sha256": findings_register.get("manifest_sha256"),
        "high_critical_count": len(high_critical),
        "high_critical_retested_ids": sorted(retested),
        "unresolved_high_critical_ids": sorted(unresolved),
        "failed_latest_candidate_retest_ids": sorted(failed_latest),
        "supply_chain_manifest_sha256": supply_chain_attestation.get("manifest_sha256"),
        "edge_manifest_sha256s": sorted(str(env.get("manifest_sha256")) for env in edges),
        "checks": checks,
        "previous_candidate_superseded": previous is not None and bool(supersession_reasons),
        "supersession_reasons": supersession_reasons,
        "refreeze_allowed": all(checks.values()),
        "independent_security_review_completed": False,
        "production_mainnet_ready": False,
        "production_crkbit_launched": False,
    }
