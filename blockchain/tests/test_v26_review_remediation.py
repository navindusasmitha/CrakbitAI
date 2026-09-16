from __future__ import annotations

import copy

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.remediation_gate_v26 import build_remediation_gate
from crakbit_chain.review_remediation_v26 import (
    ReviewRemediationV26Error,
    build_edge_attestation,
    build_findings_register,
    build_refreeze,
    build_retest_record,
    build_supply_chain_attestation,
    verify_findings_register,
    verify_refreeze,
    verify_retest_record,
)


REVIEW_COMMIT = "a" * 40
CANDIDATE_COMMIT = "b" * 40
APP_GENESIS = "c" * 64
COMET_GENESIS = "d" * 64
LOCK_HASH = "e" * 64
SBOM_HASH = "f" * 64


def _key(tmp_path, name: str):
    path = tmp_path / name
    KeyPair.generate().save(path)
    return path


def _registry(tmp_path, *, status="remediated"):
    reviewer_key = _key(tmp_path, "reviewer.json")
    findings = [
        {
            "external_id": "AUD-001",
            "severity": "critical",
            "component": "consensus/application",
            "title": "Candidate-state validation regression",
            "status": status,
            "affected_commit": REVIEW_COMMIT,
            "reproduction": "Independent reviewer reproduction steps are retained out of band.",
            "remediation_commit": CANDIDATE_COMMIT if status == "remediated" else "",
            "regression_test": "tests/test_v26_review_remediation.py::test_refreeze_gate_and_signature" if status == "remediated" else "",
        }
    ]
    return build_findings_register(
        signing_key_path=reviewer_key,
        review_id="review-2026-001",
        reviewer="Independent Review Team",
        source_commit=REVIEW_COMMIT,
        findings=findings,
    )


def _supply(tmp_path, *, complete=True):
    key = _key(tmp_path, "supply.json")
    return build_supply_chain_attestation(
        signing_key_path=key,
        attestor="Independent Build Verifier",
        source_commit=CANDIDATE_COMMIT,
        package_version="0.26.0a1",
        dependency_lock_sha256=LOCK_HASH,
        sbom_sha256=SBOM_HASH,
        python_reproducible=complete,
        go_reproducible=complete,
        dependency_review_complete=complete,
        transitive_sbom_complete=complete,
    )


def _edges(tmp_path):
    outputs = []
    for index in (1, 2):
        key = _key(tmp_path, f"edge-{index}.json")
        outputs.append(
            build_edge_attestation(
                signing_key_path=key,
                operator=f"edge-operator-{index}",
                edge_id=f"public-edge-{index}",
                source_commit=CANDIDATE_COMMIT,
                tls_min_version="1.2",
                tls_automation=True,
                waf_enabled=True,
                ddos_protection_enabled=True,
                load_test_passed=True,
                failover_drilled=True,
                capacity_rps=500,
                sustained_minutes=60,
            )
        )
    return outputs


def test_refreeze_gate_and_signature(tmp_path):
    registry = _registry(tmp_path)
    verify_findings_register(registry)
    finding_id = registry["manifest"]["findings"][0]["finding_id"]

    retest_key = _key(tmp_path, "retest.json")
    retest = build_retest_record(
        signing_key_path=retest_key,
        reviewer="Independent Retest Reviewer",
        finding_id=finding_id,
        tested_commit=CANDIDATE_COMMIT,
        result="passed",
        notes="Regression no longer reproduced on exact candidate commit.",
    )
    assert verify_retest_record(retest)["result"] == "passed"

    previous_freeze = {
        "manifest": {
            "source_commit": REVIEW_COMMIT,
            "package_version": "0.25.0a1",
            "cometbft_version": "v0.40.0",
            "application_genesis_sha256": APP_GENESIS,
            "consensus_genesis_sha256": COMET_GENESIS,
        }
    }
    gate = build_remediation_gate(
        findings_register=registry,
        retest_records=[retest],
        supply_chain_attestation=_supply(tmp_path),
        edge_attestations=_edges(tmp_path),
        candidate_source_commit=CANDIDATE_COMMIT,
        package_version="0.26.0a1",
        cometbft_version="v0.40.0",
        application_genesis_sha256=APP_GENESIS,
        consensus_genesis_sha256=COMET_GENESIS,
        previous_freeze=previous_freeze,
    )
    assert gate["refreeze_allowed"] is True
    assert gate["source_changed_since_initial_review"] is True
    assert gate["previous_candidate_superseded"] is True
    assert "source commit changed" in gate["supersession_reasons"]

    evidence = tmp_path / "review-gate.json"
    evidence.write_text("{}\n", encoding="utf-8")
    freeze_key = _key(tmp_path, "freeze.json")
    freeze = build_refreeze(
        signing_key_path=freeze_key,
        remediation_gate=gate,
        artifacts=[("remediation-gate", evidence)],
        reviewer_scope=["consensus/application", "network/RPC", "browser wallet"],
    )
    verified = verify_refreeze(freeze, remediation_gate=gate, artifact_directory=tmp_path)
    assert verified["valid"] is True
    assert verified["supersedes_previous_candidate"] is True
    assert verified["production_mainnet_ready"] is False


def test_high_critical_requires_candidate_commit_retest(tmp_path):
    registry = _registry(tmp_path)
    finding_id = registry["manifest"]["findings"][0]["finding_id"]
    retest_key = _key(tmp_path, "retest-old.json")
    old_retest = build_retest_record(
        signing_key_path=retest_key,
        reviewer="Reviewer",
        finding_id=finding_id,
        tested_commit=REVIEW_COMMIT,
        result="passed",
    )
    gate = build_remediation_gate(
        findings_register=registry,
        retest_records=[old_retest],
        supply_chain_attestation=_supply(tmp_path),
        edge_attestations=_edges(tmp_path),
        candidate_source_commit=CANDIDATE_COMMIT,
        package_version="0.26.0a1",
        cometbft_version="v0.40.0",
        application_genesis_sha256=APP_GENESIS,
        consensus_genesis_sha256=COMET_GENESIS,
    )
    assert gate["refreeze_allowed"] is False
    assert finding_id in gate["unresolved_high_critical_ids"]


def test_latest_failed_candidate_retest_blocks_refreeze(tmp_path):
    registry = _registry(tmp_path)
    finding_id = registry["manifest"]["findings"][0]["finding_id"]
    key1 = _key(tmp_path, "pass.json")
    key2 = _key(tmp_path, "fail.json")
    passed = build_retest_record(
        signing_key_path=key1,
        reviewer="Reviewer A",
        finding_id=finding_id,
        tested_commit=CANDIDATE_COMMIT,
        result="passed",
    )
    failed = build_retest_record(
        signing_key_path=key2,
        reviewer="Reviewer B",
        finding_id=finding_id,
        tested_commit=CANDIDATE_COMMIT,
        result="failed",
    )
    # Guarantee deterministic ordering if both records were created in the same ms.
    failed["manifest"]["created_at_ms"] = passed["manifest"]["created_at_ms"] + 1
    from crakbit_chain.crypto import canonical_json, sha256_hex
    fail_key = KeyPair.load(key2)
    payload = canonical_json(failed["manifest"])
    failed["manifest_sha256"] = sha256_hex(payload)
    failed["signature"] = fail_key.sign(payload)

    gate = build_remediation_gate(
        findings_register=registry,
        retest_records=[passed, failed],
        supply_chain_attestation=_supply(tmp_path),
        edge_attestations=_edges(tmp_path),
        candidate_source_commit=CANDIDATE_COMMIT,
        package_version="0.26.0a1",
        cometbft_version="v0.40.0",
        application_genesis_sha256=APP_GENESIS,
        consensus_genesis_sha256=COMET_GENESIS,
    )
    assert gate["refreeze_allowed"] is False
    assert finding_id in gate["failed_latest_candidate_retest_ids"]


def test_incomplete_supply_chain_attestation_blocks_refreeze(tmp_path):
    registry = _registry(tmp_path, status="open")
    gate = build_remediation_gate(
        findings_register=registry,
        retest_records=[],
        supply_chain_attestation=_supply(tmp_path, complete=False),
        edge_attestations=_edges(tmp_path),
        candidate_source_commit=CANDIDATE_COMMIT,
        package_version="0.26.0a1",
        cometbft_version="v0.40.0",
        application_genesis_sha256=APP_GENESIS,
        consensus_genesis_sha256=COMET_GENESIS,
    )
    assert gate["checks"]["supply_chain_gate_satisfied"] is False
    assert gate["refreeze_allowed"] is False


def test_signed_findings_tamper_is_rejected(tmp_path):
    registry = _registry(tmp_path)
    tampered = copy.deepcopy(registry)
    tampered["manifest"]["findings"][0]["title"] = "tampered title"
    with pytest.raises(ReviewRemediationV26Error):
        verify_findings_register(tampered)
