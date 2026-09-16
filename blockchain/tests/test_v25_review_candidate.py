from __future__ import annotations

import hashlib
import json

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.ops_hardening_v24 import READINESS_FORMAT
from crakbit_chain.review_candidate_v25 import (
    ReviewCandidateV25Error,
    build_host_attestation,
    build_incident_record,
    build_review_freeze,
    build_review_gate,
    verify_host_attestation,
    verify_review_freeze,
)


FAULTS = ["restart", "process-kill", "partition", "latency", "packet-loss", "load", "storage"]
COMMIT = "a" * 40


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _host(tmp_path, index: int, app_hash: str, consensus_hash: str, *, key=None, all_checks=True):
    evidence_key = key or KeyPair.generate()
    key_path = tmp_path / f"operator-{index}-evidence-key.json"
    evidence_key.save(key_path)
    return build_host_attestation(
        signing_key_path=key_path,
        operator_id=f"operator-{index}",
        validator_id=f"validator-{index}",
        provider="provider-a" if index <= 2 else "provider-b",
        region="region-a" if index % 2 else "region-b",
        node_id=f"node-{index}",
        source_commit=COMMIT,
        package_version="0.25.0a1",
        cometbft_version="v0.40.0",
        application_genesis_sha256=app_hash,
        consensus_genesis_sha256=consensus_hash,
        independent_management_asserted=True,
        protected_signer_drilled=all_checks,
        soak_7d_completed=all_checks,
        backup_restore_drilled=all_checks,
        clean_host_state_sync_drilled=all_checks,
        governance_campaign_completed=all_checks,
        fault_kinds=FAULTS if all_checks else FAULTS[:-1],
    )


def test_incident_record_requires_escalation_for_high_severity():
    with pytest.raises(ReviewCandidateV25Error):
        build_incident_record(
            incident_id="inc-1",
            severity="high",
            started_at_ms=1,
            acknowledged_at_ms=2,
            resolved_at_ms=3,
            alert_source="monitor",
            affected_components=["rpc"],
            escalation_target="",
            summary="test drill",
            recovery_verified=True,
        )


def test_signed_host_attestation_and_tamper_detection(tmp_path):
    app = tmp_path / "application-genesis.json"
    consensus = tmp_path / "consensus-genesis.json"
    app.write_text('{"chain":"app"}\n', encoding="utf-8")
    consensus.write_text('{"chain":"consensus"}\n', encoding="utf-8")

    envelope = _host(tmp_path, 1, _sha(app), _sha(consensus))
    verified = verify_host_attestation(envelope)
    assert verified["valid"] is True
    assert verified["host_gate_satisfied"] is True
    assert verified["operator_self_attested"] is True
    assert verified["independently_verified"] is False

    tampered = json.loads(json.dumps(envelope))
    tampered["manifest"]["provider"] = "tampered-provider"
    with pytest.raises(ReviewCandidateV25Error):
        verify_host_attestation(tampered)


def test_review_gate_requires_four_unique_operators_and_full_evidence(tmp_path):
    app = tmp_path / "application-genesis.json"
    consensus = tmp_path / "consensus-genesis.json"
    app.write_text('{"chain":"app"}\n', encoding="utf-8")
    consensus.write_text('{"chain":"consensus"}\n', encoding="utf-8")
    app_hash = _sha(app)
    consensus_hash = _sha(consensus)

    hosts = [_host(tmp_path, index, app_hash, consensus_hash) for index in range(1, 5)]
    incident = build_incident_record(
        incident_id="inc-drill-1",
        severity="critical",
        started_at_ms=100,
        acknowledged_at_ms=110,
        resolved_at_ms=140,
        alert_source="cluster-monitor",
        affected_components=["rpc", "validator"],
        escalation_target="incident-commander",
        summary="authorized failover drill",
        recovery_verified=True,
    )
    readiness = {"format": READINESS_FORMAT, "operational_review_candidate": True}

    gate = build_review_gate(
        operational_readiness=readiness,
        host_attestations=hosts,
        incident_records=[incident],
    )
    assert gate["candidate_freeze_allowed"] is True
    assert gate["host_count"] == 4
    assert gate["operator_count"] == 4
    assert gate["provider_count"] == 2
    assert gate["region_count"] == 2
    assert gate["independent_security_review_completed"] is False

    same_key = KeyPair.generate()
    duplicated_signer_hosts = [
        _host(tmp_path, index + 10, app_hash, consensus_hash, key=same_key)
        for index in range(1, 5)
    ]
    blocked = build_review_gate(
        operational_readiness=readiness,
        host_attestations=duplicated_signer_hosts,
        incident_records=[incident],
    )
    assert blocked["candidate_freeze_allowed"] is False
    assert blocked["checks"]["unique_operator_signers"] is False


def test_review_freeze_binds_gate_genesis_artifacts_and_signature(tmp_path):
    app = tmp_path / "application-genesis.json"
    consensus = tmp_path / "consensus-genesis.json"
    readiness_file = tmp_path / "readiness-v24.json"
    gate_file = tmp_path / "review-gate-v25.json"
    app.write_text('{"chain":"app"}\n', encoding="utf-8")
    consensus.write_text('{"chain":"consensus"}\n', encoding="utf-8")
    app_hash = _sha(app)
    consensus_hash = _sha(consensus)

    hosts = [_host(tmp_path, index, app_hash, consensus_hash) for index in range(1, 5)]
    incident = build_incident_record(
        incident_id="inc-drill-2",
        severity="high",
        started_at_ms=100,
        acknowledged_at_ms=105,
        resolved_at_ms=130,
        alert_source="alertmanager",
        affected_components=["explorer"],
        escalation_target="on-call-operator",
        summary="authorized recovery drill",
        recovery_verified=True,
    )
    readiness = {"format": READINESS_FORMAT, "operational_review_candidate": True}
    readiness_file.write_text(json.dumps(readiness), encoding="utf-8")
    gate = build_review_gate(
        operational_readiness=readiness,
        host_attestations=hosts,
        incident_records=[incident],
    )
    gate_file.write_text(json.dumps(gate), encoding="utf-8")

    freeze_key = KeyPair.generate()
    freeze_key_path = tmp_path / "review-freeze-key.json"
    freeze_key.save(freeze_key_path)
    envelope = build_review_freeze(
        signing_key_path=freeze_key_path,
        source_commit=COMMIT,
        package_version="0.25.0a1",
        cometbft_version="v0.40.0",
        application_genesis_path=app,
        consensus_genesis_path=consensus,
        review_gate=gate,
        artifacts=[("operational-readiness", readiness_file), ("review-gate", gate_file)],
        reviewer_scope=["consensus/application", "validator governance", "network/RPC", "cryptography/key custody", "browser wallet"],
    )
    verified = verify_review_freeze(
        envelope,
        review_gate=gate,
        application_genesis_path=app,
        consensus_genesis_path=consensus,
        artifact_directory=tmp_path,
        expected_signer=freeze_key.address,
        expected_source_commit=COMMIT,
    )
    assert verified["valid"] is True
    assert verified["verified_artifacts"] == 2
    assert verified["candidate_frozen_for_independent_review"] is True
    assert verified["independent_security_review_completed"] is False
    assert verified["production_mainnet_ready"] is False


def test_freeze_rejects_unsatisfied_review_gate(tmp_path):
    key = KeyPair.generate()
    key_path = tmp_path / "key.json"
    key.save(key_path)
    app = tmp_path / "app.json"
    consensus = tmp_path / "consensus.json"
    artifact = tmp_path / "artifact.json"
    app.write_text("{}", encoding="utf-8")
    consensus.write_text("{}", encoding="utf-8")
    artifact.write_text("{}", encoding="utf-8")

    with pytest.raises(ReviewCandidateV25Error):
        build_review_freeze(
            signing_key_path=key_path,
            source_commit=COMMIT,
            package_version="0.25.0a1",
            cometbft_version="v0.40.0",
            application_genesis_path=app,
            consensus_genesis_path=consensus,
            review_gate={"format": "crakbit-v25-review-gate/1", "candidate_freeze_allowed": False},
            artifacts=[("evidence", artifact)],
            reviewer_scope=["consensus/application"],
        )
