from __future__ import annotations

from typing import Any

from . import mainnet_candidate_v27 as core


MainnetCandidateV27Error = core.MainnetCandidateV27Error
_original_build_candidate_identity = core.build_candidate_identity


def build_candidate_identity(
    *, operational_readiness: dict[str, Any], remediation_gate: dict[str, Any], governance_policy: dict[str, Any],
    economics_freeze: dict[str, Any], upgrade_plan: dict[str, Any], economic_review: dict[str, Any], legal_review: dict[str, Any],
) -> dict[str, Any]:
    candidate = remediation_gate.get("candidate")
    if not isinstance(candidate, dict):
        raise MainnetCandidateV27Error("v0.26 remediation gate candidate is missing")
    source_commit = core._valid_commit(str(candidate.get("source_commit", "")))
    app_genesis = core._valid_sha256(str(candidate.get("application_genesis_sha256", "")))
    consensus_genesis = core._valid_sha256(str(candidate.get("consensus_genesis_sha256", "")))

    core.verify_governance_policy(governance_policy)
    core.verify_upgrade_plan(upgrade_plan)
    core.verify_economics_freeze(economics_freeze)
    economic_checked = core.verify_external_review(economic_review)
    legal_checked = core.verify_external_review(legal_review)

    if governance_policy["manifest"].get("source_commit") != source_commit:
        raise MainnetCandidateV27Error("governance policy source commit does not match candidate")
    if upgrade_plan["manifest"].get("source_commit") != source_commit:
        raise MainnetCandidateV27Error("upgrade plan source commit does not match candidate")

    economics_manifest = economics_freeze["manifest"]
    if economics_manifest.get("source_commit") != source_commit:
        raise MainnetCandidateV27Error("economics freeze source commit does not match candidate")
    if economics_manifest.get("application_genesis_sha256") != app_genesis:
        raise MainnetCandidateV27Error("economics freeze application genesis does not match candidate")
    if economics_manifest.get("consensus_genesis_sha256") != consensus_genesis:
        raise MainnetCandidateV27Error("economics freeze consensus genesis does not match candidate")

    if economic_checked["review_kind"] != "economic-security":
        raise MainnetCandidateV27Error("economic review has the wrong review kind")
    if legal_checked["review_kind"] != "legal-regulatory":
        raise MainnetCandidateV27Error("legal review has the wrong review kind")
    economics_subject = str(economics_freeze.get("manifest_sha256", ""))
    for label, envelope in (("economic", economic_review), ("legal", legal_review)):
        manifest = envelope["manifest"]
        if manifest.get("source_commit") != source_commit:
            raise MainnetCandidateV27Error(f"{label} review source commit does not match candidate")
        if manifest.get("subject_sha256") != economics_subject:
            raise MainnetCandidateV27Error(f"{label} review does not bind the exact economics freeze")

    return _original_build_candidate_identity(
        operational_readiness=operational_readiness,
        remediation_gate=remediation_gate,
        governance_policy=governance_policy,
        economics_freeze=economics_freeze,
        upgrade_plan=upgrade_plan,
        economic_review=economic_review,
        legal_review=legal_review,
    )
