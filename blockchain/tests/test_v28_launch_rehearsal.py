from __future__ import annotations

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain import mainnet_candidate_v27 as v27
from crakbit_chain import launch_rehearsal_v28 as v28


def _key(tmp_path, name: str):
    path = tmp_path / f"{name}.json"
    KeyPair.generate().save(path)
    return path


def _signed_v27_final_report(tmp_path, source: str, candidate_identity: str):
    manifest = {
        "format": v27.FINAL_REPORT_FORMAT,
        "created_at_ms": 1,
        "candidate_identity_sha256": candidate_identity,
        "source_commit": source,
        "final_gate_sha256": "8" * 64,
        "artifacts": [],
        "mainnet_candidate_gate_satisfied": True,
        "production_mainnet_ready": False,
        "production_mainnet_launched": False,
        "production_crkbit_launched": False,
    }
    return v27._sign(_key(tmp_path, "v27-final"), manifest)


def _passing_artifacts(tmp_path):
    source = "a" * 40
    candidate = "9" * 64
    final_report = _signed_v27_final_report(tmp_path, source, candidate)

    upgrade_plan = v27.build_upgrade_plan(
        signing_key_path=_key(tmp_path, "upgrade-plan"),
        source_commit=source,
        from_package="0.27.0a1",
        to_package="0.28.0a1",
        from_schema=21,
        to_schema=21,
        activation_height=2000,
        rollback_deadline_height=2100,
        migration_artifact_sha256="1" * 64,
        rollback_artifact_sha256="2" * 64,
        minimum_ready_validators=3,
        total_validators=4,
    )

    validators = ["validator-1", "validator-2", "validator-3", "validator-4"]
    runbook = v28.build_launch_runbook(
        signing_key_path=_key(tmp_path, "runbook"),
        source_commit=source,
        candidate_identity_sha256=candidate,
        validator_ids=validators,
        genesis_ceremony_steps=["verify hashes", "collect operator attestations", "freeze genesis"],
        validator_start_order=validators,
        rollback_steps=["halt cutover", "restore previous public endpoints"],
        cutover_window_minutes=60,
    )
    cutover = v28.build_cutover_rehearsal(
        signing_key_path=_key(tmp_path, "cutover"),
        source_commit=source,
        candidate_identity_sha256=candidate,
        dns_names=["rpc.example.test", "explorer.example.test"],
        rpc_endpoints=["https://rpc-a.example.test", "https://rpc-b.example.test"],
        explorer_endpoints=["https://explorer-a.example.test", "https://explorer-b.example.test"],
        dns_ttl_seconds=300,
        rollback_verified=True,
        rpc_failover_verified=True,
        explorer_failover_verified=True,
        no_production_dns_changed=True,
    )
    edges = []
    for index in (1, 2):
        edges.append(v28.build_edge_slo_evidence(
            signing_key_path=_key(tmp_path, f"edge-{index}"),
            source_commit=source,
            candidate_identity_sha256=candidate,
            edge_id=f"edge-{index}",
            availability_percent=99.99,
            p95_latency_ms=120,
            error_rate_percent=0.05,
            capacity_rps=1000,
            sustained_minutes=60,
            failover_seconds=20,
            min_availability_percent=99.9,
            max_p95_latency_ms=250,
            max_error_rate_percent=0.5,
            min_capacity_rps=500,
            max_failover_seconds=60,
        ))
    signer = v28.build_signer_drill(
        signing_key_path=_key(tmp_path, "signer-drill"),
        source_commit=source,
        candidate_identity_sha256=candidate,
        signer_id="validator-signer-1",
        custody_type="remote-signer",
        no_key_export=True,
        rotation_successful=True,
        old_key_revoked=True,
        backup_recovery_successful=True,
        catastrophic_recovery_drilled=True,
        validator_quorum_preserved=True,
    )
    upgrade = v28.build_upgrade_rehearsal(
        signing_key_path=_key(tmp_path, "upgrade-rehearsal"),
        source_commit=source,
        candidate_identity_sha256=candidate,
        upgrade_plan=upgrade_plan,
        validator_count=4,
        validators_successful=4,
        upgrade_completed=True,
        application_hash_converged=True,
        rollback_exercised=True,
        rollback_hash_converged=True,
        no_data_loss=True,
    )
    risks = v28.build_risk_register(
        signing_key_path=_key(tmp_path, "risk-register"),
        source_commit=source,
        candidate_identity_sha256=candidate,
        risks=[{
            "risk_id": "RISK-001",
            "severity": "medium",
            "status": "accepted",
            "owner": "release-team",
            "description": "Residual operational rehearsal risk",
            "rationale": "Accepted for rehearsal candidate only",
        }],
    )
    repro = v28.build_repro_attestation(
        signing_key_path=_key(tmp_path, "repro"),
        attestor="Independent Build Verifier",
        source_commit=source,
        candidate_identity_sha256=candidate,
        package_version="0.28.0a1",
        dependency_lock_sha256="3" * 64,
        sbom_sha256="4" * 64,
        python_wheel_sha256="5" * 64,
        go_binary_sha256="6" * 64,
        python_reproducible=True,
        go_reproducible=True,
        transitive_dependencies_reviewed=True,
        source_tag_verified=True,
    )
    scopes = [
        "consensus-application",
        "network-rpc",
        "cryptography-key-management",
        "browser-wallet",
    ]
    signoffs = []
    for index, scope in enumerate(scopes, start=1):
        signoffs.append(v28.build_review_signoff(
            signing_key_path=_key(tmp_path, f"reviewer-{index}"),
            reviewer=f"Independent Reviewer {index}",
            scope=scope,
            source_commit=source,
            candidate_identity_sha256=candidate,
            subject_sha256=final_report["manifest_sha256"],
            decision="passed",
            independent_reviewer_asserted=True,
        ))
    return source, candidate, final_report, runbook, cutover, edges, signer, upgrade, risks, signoffs, repro


def test_v28_full_rehearsal_gate_and_manual_freeze(tmp_path):
    source, candidate, final_report, runbook, cutover, edges, signer, upgrade, risks, signoffs, repro = _passing_artifacts(tmp_path)
    gate = v28.build_rehearsal_gate(
        final_report_v27=final_report,
        launch_runbook=runbook,
        cutover_rehearsal=cutover,
        edge_slo_evidence=edges,
        signer_drill=signer,
        upgrade_rehearsal=upgrade,
        risk_register=risks,
        reviewer_signoffs=signoffs,
        repro_attestation=repro,
    )
    assert gate["launch_rehearsal_gate_satisfied"] is True
    assert gate["automatic_launch"] is False
    assert gate["production_mainnet_ready"] is False

    freeze = v28.build_release_freeze(
        signing_key_path=_key(tmp_path, "release-freeze"),
        rehearsal_gate=gate,
    )
    assert v28.verify_release_freeze(freeze)["valid"] is True
    assert freeze["manifest"]["production_mainnet_launched"] is False

    decision = v28.build_launch_decision(
        signing_key_path=_key(tmp_path, "human-decision"),
        release_freeze=freeze,
        decision_maker="Release Council",
        decision="approve-launch-window",
        rationale="Rehearsal gate passed; external execution remains manual.",
    )
    checked = v28.verify_launch_decision(decision)
    assert checked["decision"] == "approve-launch-window"
    assert checked["production_mainnet_launched"] is False


def test_v28_high_or_critical_risk_blocks_release(tmp_path):
    register = v28.build_risk_register(
        signing_key_path=_key(tmp_path, "risk-block"),
        source_commit="a" * 40,
        candidate_identity_sha256="9" * 64,
        risks=[{
            "risk_id": "RISK-CRIT-1",
            "severity": "critical",
            "status": "accepted",
            "owner": "security",
            "description": "Unresolved catastrophic-risk example",
            "rationale": "Acceptance is not sufficient for high/critical launch risk",
        }],
    )
    assert register["manifest"]["risk_gate_satisfied"] is False
    assert register["manifest"]["blocking_risk_ids"] == ["RISK-CRIT-1"]


def test_v28_review_signoffs_must_bind_exact_v27_final_report(tmp_path):
    _, _, final_report, runbook, cutover, edges, signer, upgrade, risks, signoffs, repro = _passing_artifacts(tmp_path)
    bad = dict(signoffs[0])
    bad["manifest"] = dict(signoffs[0]["manifest"])
    bad["manifest"]["subject_sha256"] = "0" * 64
    with pytest.raises(v28.LaunchRehearsalV28Error):
        v28.build_rehearsal_gate(
            final_report_v27=final_report,
            launch_runbook=runbook,
            cutover_rehearsal=cutover,
            edge_slo_evidence=edges,
            signer_drill=signer,
            upgrade_rehearsal=upgrade,
            risk_register=risks,
            reviewer_signoffs=[bad, *signoffs[1:]],
            repro_attestation=repro,
        )
