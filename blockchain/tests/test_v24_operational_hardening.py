from __future__ import annotations

import json
from pathlib import Path

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.ops_hardening_v24 import (
    FAULT_RESULT_FORMAT,
    OperationsV24Error,
    build_fault_plan,
    build_fault_result,
    build_readiness,
    build_recovery_record,
    build_remote_signer_record,
    build_signed_evidence,
    evaluate_host_preflight,
    evaluate_redundancy,
    verify_signed_evidence,
)


def _soak(seconds: int) -> dict:
    return {
        "observed_duration_seconds": float(seconds),
        "divergence_free": True,
        "all_reachable_ratio": 1.0,
        "healthy_ratio": 1.0,
    }


def test_v24_host_preflight_requires_exact_versions_hashes_private_binds_and_space():
    good = evaluate_host_preflight(
        node_name="validator-1",
        package_version="0.24.0a1",
        expected_package_version="0.24.0a1",
        cometbft_version="v0.40.0",
        expected_cometbft_version="v0.40.0",
        application_genesis_sha256="a" * 64,
        expected_application_genesis_sha256="a" * 64,
        consensus_genesis_sha256="b" * 64,
        expected_consensus_genesis_sha256="b" * 64,
        execution_bind="127.0.0.1:26659",
        abci_bind="tcp://127.0.0.1:26658",
        execution_token_present=True,
        data_dir_writable=True,
        free_bytes=10_000,
        minimum_free_bytes=1_000,
    )
    assert good["ready_to_start"] is True
    assert good["secrets_included"] is False
    assert good["production_mainnet_ready"] is False

    bad = evaluate_host_preflight(
        node_name="validator-1",
        package_version="0.23.0a1",
        expected_package_version="0.24.0a1",
        cometbft_version="v0.40.0",
        expected_cometbft_version="v0.40.0",
        application_genesis_sha256="a" * 64,
        expected_application_genesis_sha256="a" * 64,
        consensus_genesis_sha256="b" * 64,
        expected_consensus_genesis_sha256="b" * 64,
        execution_bind="0.0.0.0:26659",
        abci_bind="tcp://0.0.0.0:26658",
        execution_token_present=False,
        data_dir_writable=True,
        free_bytes=100,
        minimum_free_bytes=1_000,
    )
    assert bad["ready_to_start"] is False
    assert bad["checks"]["package_version_matches"] is False
    assert bad["checks"]["execution_bind_is_loopback"] is False


def test_v24_fault_plan_requires_recovery_and_explicit_executed_result():
    with pytest.raises(OperationsV24Error):
        build_fault_plan(
            name="bad",
            steps=[{"name": "restart", "kind": "restart", "command": ["systemctl", "stop", "x"]}],
        )

    plan = build_fault_plan(
        name="restart campaign",
        steps=[
            {
                "name": "restart-node-2",
                "kind": "restart",
                "target": "validator-2",
                "command": ["systemctl", "restart", "crakbit-cometbft"],
                "recovery_command": ["systemctl", "start", "crakbit-cometbft"],
            }
        ],
    )
    assert plan["safe_default"] == "dry-run"
    with pytest.raises(OperationsV24Error):
        build_fault_result(plan=plan, campaign_result={"execute": False, "steps": []})

    result = build_fault_result(
        plan=plan,
        campaign_result={
            "execute": True,
            "steps": [
                {
                    "name": "restart-node-2",
                    "fault_command": {"returncode": 0},
                    "recovery_command_result": {"returncode": 0},
                    "recovered_healthy": True,
                }
            ],
        },
    )
    assert result["format"] == FAULT_RESULT_FORMAT
    assert result["fault_kinds_executed"] == ["restart"]
    assert result["all_steps_recovered"] is True


def test_v24_recovery_records_require_state_identity_and_clean_host_for_state_sync():
    backup = build_recovery_record(
        kind="backup-restore",
        source_height=120,
        restored_height=120,
        source_application_hash="abc",
        restored_application_hash="abc",
        source_state_root="root",
        restored_state_root="root",
    )
    assert backup["success"] is True

    not_clean = build_recovery_record(
        kind="clean-host-state-sync",
        source_height=120,
        restored_height=120,
        source_application_hash="abc",
        restored_application_hash="abc",
        clean_host=False,
    )
    assert not_clean["success"] is False

    clean = build_recovery_record(
        kind="clean-host-state-sync",
        source_height=120,
        restored_height=120,
        source_application_hash="abc",
        restored_application_hash="abc",
        clean_host=True,
    )
    assert clean["success"] is True


def test_v24_remote_signer_gate_never_contains_private_key():
    failed = build_remote_signer_record(
        validator_name="validator-1",
        signer_type="remote-signer",
        key_exported=True,
        double_sign_protection=True,
        restart_recovery_drilled=True,
        failover_drilled=True,
        signer_endpoint_private=True,
    )
    assert failed["protected_signer_gate_satisfied"] is False
    assert failed["contains_private_key"] is False

    good = build_remote_signer_record(
        validator_name="validator-1",
        signer_type="hsm-backed-remote-signer",
        key_exported=False,
        double_sign_protection=True,
        restart_recovery_drilled=True,
        failover_drilled=True,
        signer_endpoint_private=True,
    )
    assert good["protected_signer_gate_satisfied"] is True


def test_v24_redundancy_requires_two_endpoints_and_detects_same_height_conflicts():
    rpc = [
        {"reachable": True, "chain_id": "crakbit-testnet", "height": 100, "application_hash": "aa"},
        {"reachable": True, "chain_id": "crakbit-testnet", "height": 100, "application_hash": "aa"},
    ]
    explorer = [{"reachable": True}, {"reachable": True}]
    good = evaluate_redundancy(rpc_records=rpc, explorer_records=explorer, expected_chain_id="crakbit-testnet")
    assert good["redundancy_gate_satisfied"] is True

    rpc[1]["application_hash"] = "bb"
    bad = evaluate_redundancy(rpc_records=rpc, explorer_records=explorer, expected_chain_id="crakbit-testnet")
    assert bad["redundancy_gate_satisfied"] is False
    assert bad["same_height_application_hash_conflicts"]


def test_v24_readiness_has_real_24h_72h_7d_gates_and_never_claims_mainnet():
    all_faults = {
        "format": FAULT_RESULT_FORMAT,
        "all_steps_recovered": True,
        "fault_kinds_executed": [
            "restart",
            "process-kill",
            "partition",
            "latency",
            "packet-loss",
            "load",
            "storage",
        ],
    }
    recoveries = [
        build_recovery_record(
            kind="backup-restore",
            source_height=50,
            restored_height=50,
            source_application_hash="hash",
            restored_application_hash="hash",
        ),
        build_recovery_record(
            kind="clean-host-state-sync",
            source_height=50,
            restored_height=50,
            source_application_hash="hash",
            restored_application_hash="hash",
            clean_host=True,
        ),
    ]
    signer = build_remote_signer_record(
        validator_name="validator-1",
        signer_type="remote-signer",
        key_exported=False,
        double_sign_protection=True,
        restart_recovery_drilled=True,
        failover_drilled=True,
        signer_endpoint_private=True,
    )
    redundancy = evaluate_redundancy(
        rpc_records=[
            {"reachable": True, "chain_id": "c", "height": 5, "application_hash": "h"},
            {"reachable": True, "chain_id": "c", "height": 5, "application_hash": "h"},
        ],
        explorer_records=[{"reachable": True}, {"reachable": True}],
        expected_chain_id="c",
    )

    short = build_readiness(
        soak_24h=_soak(24 * 3600),
        soak_72h=_soak(71 * 3600),
        soak_7d=_soak(7 * 24 * 3600),
        fault_results=[all_faults],
        recovery_records=recoveries,
        signer_records=[signer],
        redundancy_report=redundancy,
    )
    assert short["checks"]["soak_72h"] is False
    assert short["operational_review_candidate"] is False

    complete = build_readiness(
        soak_24h=_soak(24 * 3600),
        soak_72h=_soak(72 * 3600),
        soak_7d=_soak(7 * 24 * 3600),
        fault_results=[all_faults],
        recovery_records=recoveries,
        signer_records=[signer],
        redundancy_report=redundancy,
    )
    assert complete["operational_review_candidate"] is True
    assert complete["independent_security_review_completed"] is False
    assert complete["production_mainnet_ready"] is False
    assert complete["production_crkbit_launched"] is False


def test_v24_signed_evidence_binds_artifacts_and_rejects_tamper(tmp_path: Path):
    key = KeyPair.generate()
    key_path = tmp_path / "ops-key.json"
    key.save(key_path)
    artifact = tmp_path / "readiness.json"
    artifact.write_text(json.dumps({"production_mainnet_ready": False}) + "\n", encoding="utf-8")

    envelope = build_signed_evidence(
        signing_key_path=key_path,
        source_commit="a" * 40,
        package_version="0.24.0a1",
        cometbft_version="v0.40.0",
        artifact_paths=[artifact],
        operator_note="unit test",
    )
    verified = verify_signed_evidence(
        envelope,
        artifact_directory=tmp_path,
        expected_signer=key.address,
        expected_source_commit="a" * 40,
    )
    assert verified["valid"] is True
    assert verified["verified_artifacts"] == 1
    assert verified["production_mainnet_ready"] is False

    artifact.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(OperationsV24Error):
        verify_signed_evidence(envelope, artifact_directory=tmp_path)
