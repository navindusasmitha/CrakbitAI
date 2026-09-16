from __future__ import annotations

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain import mainnet_candidate_v27 as core
from crakbit_chain.mainnet_candidate_gate_v27 import build_candidate_identity as hardened_identity


def _key(tmp_path, name: str):
    path = tmp_path / f"{name}.json"
    KeyPair.generate().save(path)
    return path


def _artifacts(tmp_path):
    source = "a" * 40
    app_genesis = "b" * 64
    consensus_genesis = "c" * 64

    upgrade = core.build_upgrade_plan(
        signing_key_path=_key(tmp_path, "upgrade"),
        source_commit=source,
        from_package="0.26.0a1",
        to_package="0.27.0a1",
        from_schema=21,
        to_schema=21,
        activation_height=1000,
        rollback_deadline_height=1100,
        migration_artifact_sha256="1" * 64,
        rollback_artifact_sha256="2" * 64,
        minimum_ready_validators=3,
        total_validators=4,
    )
    governance = core.build_governance_policy(
        signing_key_path=_key(tmp_path, "governance"),
        source_commit=source,
        normal_timelock_blocks=100,
        emergency_timelock_blocks=10,
        cancel_until_blocks_before_activation=5,
        emergency_approval_numerator=3,
        emergency_approval_denominator=4,
    )
    economics = core.build_economics_freeze(
        signing_key_path=_key(tmp_path, "economics"),
        source_commit=source,
        application_genesis_sha256=app_genesis,
        consensus_genesis_sha256=consensus_genesis,
        parameters={
            "symbol": "CRKBIT",
            "decimals": 8,
            "max_supply_atomic": 21_000_000 * 100_000_000,
            "initial_supply_atomic": 21_000_000 * 100_000_000,
            "minimum_fee_atomic": 1,
            "validator_incentive_model": "candidate-fee-policy",
            "distribution_commitment_sha256": "f" * 64,
        },
    )
    subject = economics["manifest_sha256"]
    economic_review = core.build_external_review(
        signing_key_path=_key(tmp_path, "economic-review"),
        review_kind="economic-security",
        reviewer="Independent Economic Reviewer",
        source_commit=source,
        subject_sha256=subject,
        decision="passed",
        scope=["supply", "fees", "validator incentives"],
    )
    legal_review = core.build_external_review(
        signing_key_path=_key(tmp_path, "legal-review"),
        review_kind="legal-regulatory",
        reviewer="Independent Legal Reviewer",
        source_commit=source,
        subject_sha256=subject,
        decision="passed",
        scope=["launch structure", "asset treatment"],
    )
    operational = {
        "format": "crakbit-v24-readiness/1",
        "operational_review_candidate": True,
        "production_mainnet_ready": False,
    }
    remediation = {
        "format": "crakbit-v26-remediation-gate/1",
        "candidate": {
            "source_commit": source,
            "package_version": "0.27.0a1",
            "cometbft_version": "v0.40.0",
            "application_genesis_sha256": app_genesis,
            "consensus_genesis_sha256": consensus_genesis,
            "dependency_lock_sha256": "d" * 64,
            "sbom_sha256": "e" * 64,
        },
        "refreeze_allowed": True,
        "unresolved_high_critical_ids": [],
        "production_mainnet_ready": False,
    }
    return source, operational, remediation, governance, economics, upgrade, economic_review, legal_review


def test_v27_final_candidate_gate_requires_multi_party_approval(tmp_path):
    source, operational, remediation, governance, economics, upgrade, economic_review, legal_review = _artifacts(tmp_path)
    identity = hardened_identity(
        operational_readiness=operational,
        remediation_gate=remediation,
        governance_policy=governance,
        economics_freeze=economics,
        upgrade_plan=upgrade,
        economic_review=economic_review,
        legal_review=legal_review,
    )

    approvals = []
    for index, role in enumerate(("release", "operations", "security"), start=1):
        approvals.append(core.build_release_approval(
            signing_key_path=_key(tmp_path, f"approver-{index}"),
            approver_id=f"approver-{index}",
            role=role,
            source_commit=source,
            candidate_identity_sha256=identity["candidate_identity_sha256"],
            decision="approve",
        ))

    original = core.build_candidate_identity
    core.build_candidate_identity = hardened_identity
    try:
        gate = core.build_final_candidate_gate(
            identity=identity,
            operational_readiness=operational,
            remediation_gate=remediation,
            governance_policy=governance,
            economics_freeze=economics,
            upgrade_plan=upgrade,
            economic_review=economic_review,
            legal_review=legal_review,
            release_approvals=approvals,
            minimum_approvals=3,
        )
    finally:
        core.build_candidate_identity = original

    assert gate["mainnet_candidate_gate_satisfied"] is True
    assert gate["production_mainnet_ready"] is False
    assert gate["production_mainnet_launched"] is False
    assert len(gate["release_approval_signers"]) == 3

    report = core.build_final_report(
        signing_key_path=_key(tmp_path, "final-report"),
        final_gate=gate,
    )
    assert core.verify_final_report(report)["valid"] is True
    assert report["manifest"]["production_crkbit_launched"] is False


def test_v27_rejects_review_not_bound_to_exact_economics_freeze(tmp_path):
    _, operational, remediation, governance, economics, upgrade, economic_review, legal_review = _artifacts(tmp_path)
    tampered = dict(legal_review)
    tampered["manifest"] = dict(legal_review["manifest"])
    tampered["manifest"]["subject_sha256"] = "9" * 64
    # Re-signing is deliberately omitted; even a valid signature for a different
    # subject would fail the exact-subject binding in hardened_identity.
    with pytest.raises(core.MainnetCandidateV27Error):
        hardened_identity(
            operational_readiness=operational,
            remediation_gate=remediation,
            governance_policy=governance,
            economics_freeze=economics,
            upgrade_plan=upgrade,
            economic_review=economic_review,
            legal_review=tampered,
        )


def test_v27_upgrade_threshold_is_strict_supermajority(tmp_path):
    with pytest.raises(core.MainnetCandidateV27Error):
        core.build_upgrade_plan(
            signing_key_path=_key(tmp_path, "bad-upgrade"),
            source_commit="a" * 40,
            from_package="0.26.0a1",
            to_package="0.27.0a1",
            from_schema=21,
            to_schema=21,
            activation_height=100,
            rollback_deadline_height=120,
            migration_artifact_sha256="1" * 64,
            rollback_artifact_sha256="2" * 64,
            minimum_ready_validators=2,
            total_validators=4,
        )
