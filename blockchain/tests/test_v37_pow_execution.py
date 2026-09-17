from __future__ import annotations

import json

import pytest

from crakbit_chain.algorithm_gate_v34 import build_algorithm_decision, build_benchmark_gate, build_benchmark_record
from crakbit_chain.cli_v37_entry import _run
from crakbit_chain.crypto import KeyPair, canonical_json, sha256_hex
from crakbit_chain.pow_execution_v37 import (
    PowExecutionV37Error,
    build_algorithm_review_gate,
    build_deployment_plan,
    build_payout_policy,
    build_review_bundle,
    verify_algorithm_review_gate,
    verify_deployment_plan,
    verify_payout_policy,
    verify_review_bundle,
)
from crakbit_chain.pow_handoff_v36 import HANDOFF_FORMAT


CHAIN_ID = "crakbit-pow-testnet-v1"
GENESIS_HASH = "ab" * 32
V36_COMMIT = "36" * 20
V37_COMMIT = "37" * 20


def _key(tmp_path, name: str) -> str:
    path = tmp_path / f"{name}.json"
    KeyPair.generate().save(path)
    return str(path)


def _nodes() -> list[dict]:
    return [
        {
            "node_id": f"node-{index}",
            "operator_id": f"operator-{index}",
            "provider": "provider-a" if index < 3 else "provider-b",
            "region": "region-a" if index % 2 else "region-b",
            "network_group": "net-a" if index < 3 else "net-b",
            "roles": ["node", "miner"] if index in {1, 2} else ["node"],
            "rpc_url": f"https://node-{index}.example.invalid",
            "p2p_endpoint": f"node-{index}.example.invalid:28444",
        }
        for index in range(1, 5)
    ]


def _signed_v36_handoff(tmp_path) -> dict:
    key_path = _key(tmp_path, "v36-handoff")
    key = KeyPair.load(key_path)
    manifest = {
        "format": HANDOFF_FORMAT,
        "recorded_at_unix": 1_800_000_000,
        "source_commit": V36_COMMIT,
        "package_version": "0.36.0a1",
        "chain_id": CHAIN_ID,
        "genesis_hash": GENESIS_HASH,
        "external_review_handoff_ready": True,
        "independent_security_review_completed": False,
        "production_mainnet_ready": False,
        "production_crkbit_launched": False,
    }
    manifest["handoff_id"] = sha256_hex(canonical_json(manifest))
    payload = canonical_json({"domain": HANDOFF_FORMAT, "manifest": manifest})
    return {
        "manifest": manifest,
        "signer": key.address,
        "public_key": key.public_key_b64,
        "signature": key.sign(payload),
    }


def _benchmark_and_decision(tmp_path, suffix: str = "") -> tuple[dict, dict]:
    machine_a = _key(tmp_path, f"machine-a{suffix}")
    machine_b = _key(tmp_path, f"machine-b{suffix}")
    release = _key(tmp_path, f"release{suffix}")
    records = [
        build_benchmark_record(
            signing_key_path=machine_a,
            machine_id=f"machine-a{suffix}",
            cpu_model="CPU A",
            logical_threads=8,
            ram_mib=8192,
            scrypt_hps=100,
            randomx_hps=500,
            randomx_mode="light",
            randomx_selftest_passed=True,
        ),
        build_benchmark_record(
            signing_key_path=machine_b,
            machine_id=f"machine-b{suffix}",
            cpu_model="CPU B",
            logical_threads=16,
            ram_mib=16384,
            scrypt_hps=200,
            randomx_hps=900,
            randomx_mode="fast",
            randomx_selftest_passed=True,
        ),
    ]
    gate = build_benchmark_gate(signing_key_path=release, records=records)
    decision = build_algorithm_decision(
        signing_key_path=release,
        benchmark_gate=gate,
        decision="scrypt",
        rationale="Regression fixture: keep the active testnet algorithm; no mainnet claim.",
    )
    return gate, decision


def test_v37_execution_review_bundle_is_cross_bound_and_not_a_launch_claim(tmp_path):
    release_key = _key(tmp_path, "v37-release")
    handoff = _signed_v36_handoff(tmp_path)
    benchmark_gate, decision = _benchmark_and_decision(tmp_path)

    deployment = build_deployment_plan(
        key_path=release_key,
        source_commit=V37_COMMIT,
        package_version="0.37.0a1",
        chain_id=CHAIN_ID,
        genesis_hash=GENESIS_HASH,
        nodes=_nodes(),
    )
    assert verify_deployment_plan(deployment)["deployment_gate_satisfied"] is True

    hot = KeyPair.generate().address
    cold = KeyPair.generate().address
    payout = build_payout_policy(
        key_path=release_key,
        hot_wallet_address=hot,
        cold_wallet_address=cold,
        maximum_single_payout_atomic=1_000_000,
        maximum_batch_payout_atomic=5_000_000,
        daily_payout_limit_atomic=10_000_000,
        manual_hold_above_atomic=500_000,
        approvals_required=2,
        minimum_confirmations=6,
    )
    assert verify_payout_policy(payout)["payout_policy_gate_satisfied"] is True

    algorithm = build_algorithm_review_gate(
        key_path=release_key,
        benchmark_gate=benchmark_gate,
        algorithm_decision=decision,
        v36_handoff=handoff,
        activation_proposal=None,
        external_benchmark_review_asserted=True,
        external_consensus_review_asserted=True,
    )
    assert verify_algorithm_review_gate(algorithm)["algorithm_review_gate_satisfied"] is True

    bundle = build_review_bundle(
        key_path=release_key,
        source_commit=V37_COMMIT,
        package_version="0.37.0a1",
        deployment_plan=deployment,
        payout_policy=payout,
        algorithm_review_gate=algorithm,
        v36_handoff=handoff,
    )
    verified = verify_review_bundle(bundle)
    assert verified["public_testnet_review_candidate_ready"] is True
    assert verified["independent_security_review_completed"] is False
    assert verified["production_mainnet_ready"] is False
    assert bundle["manifest"]["supersedes_v36_source_commit"] == V36_COMMIT
    assert bundle["manifest"]["source_commit"] == V37_COMMIT


def test_v37_rejects_secret_metadata_and_cross_artifact_mismatch(tmp_path):
    release_key = _key(tmp_path, "release")
    nodes = _nodes()
    nodes[0]["api_token"] = "must-not-enter-evidence"
    with pytest.raises(PowExecutionV37Error, match="secret-like field"):
        build_deployment_plan(
            key_path=release_key,
            source_commit=V37_COMMIT,
            package_version="0.37.0a1",
            chain_id=CHAIN_ID,
            genesis_hash=GENESIS_HASH,
            nodes=nodes,
        )

    gate_a, _ = _benchmark_and_decision(tmp_path)
    _, decision_b = _benchmark_and_decision(tmp_path, suffix="-b")
    with pytest.raises(PowExecutionV37Error, match="not bound"):
        build_algorithm_review_gate(
            key_path=release_key,
            benchmark_gate=gate_a,
            algorithm_decision=decision_b,
            v36_handoff=_signed_v36_handoff(tmp_path),
            activation_proposal=None,
            external_benchmark_review_asserted=True,
            external_consensus_review_asserted=True,
        )


def test_v37_signature_tamper_and_cli_deployment_round_trip(tmp_path):
    release_key = _key(tmp_path, "release")
    deployment = build_deployment_plan(
        key_path=release_key,
        source_commit=V37_COMMIT,
        package_version="0.37.0a1",
        chain_id=CHAIN_ID,
        genesis_hash=GENESIS_HASH,
        nodes=_nodes(),
    )
    deployment["manifest"]["nodes"][0]["provider"] = "tampered"
    with pytest.raises(PowExecutionV37Error, match="signature"):
        verify_deployment_plan(deployment)

    nodes_path = tmp_path / "nodes.json"
    output_path = tmp_path / "deployment.json"
    nodes_path.write_text(json.dumps({"nodes": _nodes()}), encoding="utf-8")
    exit_code = _run([
        "pow-deployment-v37-build",
        "--key", release_key,
        "--source-commit", V37_COMMIT,
        "--chain-id", CHAIN_ID,
        "--genesis-hash", GENESIS_HASH,
        "--nodes", str(nodes_path),
        "--output", str(output_path),
    ])
    assert exit_code == 0
    assert verify_deployment_plan(json.loads(output_path.read_text(encoding="utf-8")))["valid"] is True
