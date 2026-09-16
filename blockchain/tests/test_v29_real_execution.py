from __future__ import annotations

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain import launch_rehearsal_v28 as v28
from crakbit_chain import real_execution_v29 as v29


def _key(tmp_path, name: str):
    path = tmp_path / f"{name}.json"
    KeyPair.generate().save(path)
    return path


def _host(tmp_path, index: int, *, observed_at_ms: int, height: int, provider: str, region: str):
    return v29.build_live_host_observation(
        signing_key_path=_key(tmp_path, f"host-{index}-{observed_at_ms}"),
        source_commit="a" * 40,
        candidate_identity_sha256="b" * 64,
        application_genesis_sha256="c" * 64,
        consensus_genesis_sha256="d" * 64,
        validator_id=f"validator-{index}",
        operator_id=f"operator-{index}",
        provider=provider,
        region=region,
        rpc_endpoint=f"https://rpc{index}.example.invalid",
        expected_chain_id="crakbit-testnet-v29",
        measurement={
            "chain_id": "crakbit-testnet-v29",
            "node_id": f"node-{index}",
            "latest_height": height,
            "abci_height": height,
            "app_hash": f"apphash-{height}",
            "catching_up": False,
        },
        execution_private_asserted=True,
        abci_private_asserted=True,
        signer_protected_asserted=True,
        observed_at_ms=observed_at_ms,
    )


def _cluster(tmp_path, *, observed_at_ms: int, height: int):
    hosts = [
        _host(tmp_path, 1, observed_at_ms=observed_at_ms, height=height, provider="provider-a", region="region-a"),
        _host(tmp_path, 2, observed_at_ms=observed_at_ms + 1000, height=height, provider="provider-a", region="region-b"),
        _host(tmp_path, 3, observed_at_ms=observed_at_ms + 2000, height=height, provider="provider-b", region="region-a"),
        _host(tmp_path, 4, observed_at_ms=observed_at_ms + 3000, height=height, provider="provider-b", region="region-b"),
    ]
    result = v29.build_cluster_observation(
        signing_key_path=_key(tmp_path, f"cluster-{observed_at_ms}"),
        host_observations=hosts,
    )
    assert result["manifest"]["cluster_gate_satisfied"] is True
    return result


def _genesis_gate(tmp_path):
    attestations = []
    for index in range(1, 5):
        attestations.append(v29.build_genesis_attestation(
            signing_key_path=_key(tmp_path, f"genesis-{index}"),
            source_commit="a" * 40,
            candidate_identity_sha256="b" * 64,
            application_genesis_sha256="c" * 64,
            consensus_genesis_sha256="d" * 64,
            chain_id="crakbit-testnet-v29",
            operator_id=f"operator-{index}",
            validator_id=f"validator-{index}",
            validator_address=f"crk-validator-{index}",
            node_id=f"node-{index}",
            approved=True,
        ))
    gate = v29.build_genesis_ceremony_gate(
        signing_key_path=_key(tmp_path, "genesis-gate"),
        attestations=attestations,
    )
    assert gate["manifest"]["genesis_ceremony_gate_satisfied"] is True
    return gate


def test_v29_real_execution_gate_requires_live_multi_host_soak_and_faults(tmp_path):
    start = 1_800_000_000_000
    first_cluster = _cluster(tmp_path, observed_at_ms=start, height=100)
    second_cluster = _cluster(tmp_path, observed_at_ms=start + 604_800_000, height=200)
    soak = v29.build_soak_evidence(
        signing_key_path=_key(tmp_path, "soak"),
        cluster_samples=[first_cluster, second_cluster],
        minimum_duration_seconds=604800,
        minimum_success_ratio=0.99,
    )
    assert soak["manifest"]["soak_gate_satisfied"] is True

    genesis_gate = _genesis_gate(tmp_path)
    raw = tmp_path / "fault-evidence.jsonl"
    raw.write_text('{"result":"passed"}\n', encoding="utf-8")
    faults = []
    for fault_type in sorted(v29.REQUIRED_FAULT_TYPES):
        faults.append(v29.build_fault_result(
            signing_key_path=_key(tmp_path, f"fault-{fault_type}"),
            source_commit="a" * 40,
            candidate_identity_sha256="b" * 64,
            fault_type=fault_type,
            campaign_id=f"campaign-{fault_type}",
            authorized=True,
            passed=True,
            recovery_verified=True,
            app_hash_reconverged=True,
            no_data_loss=True,
            raw_evidence_path=raw,
        ))

    rehearsal_gate = {
        "format": v28.REHEARSAL_GATE_FORMAT,
        "created_at_ms": start,
        "source_commit": "a" * 40,
        "candidate_identity_sha256": "b" * 64,
        "launch_rehearsal_gate_satisfied": True,
        "production_mainnet_ready": False,
    }
    release_freeze = v28.build_release_freeze(
        signing_key_path=_key(tmp_path, "v28-freeze"),
        rehearsal_gate=rehearsal_gate,
    )

    gate = v29.build_real_execution_gate(
        release_freeze_v28=release_freeze,
        rehearsal_gate_v28=rehearsal_gate,
        cluster_observation=second_cluster,
        genesis_ceremony_gate=genesis_gate,
        soak_evidence=soak,
        fault_results=faults,
    )
    assert gate["real_execution_gate_satisfied"] is True
    assert gate["production_mainnet_ready"] is False
    assert gate["automatic_launch"] is False
    assert set(gate["covered_fault_types"]) == v29.REQUIRED_FAULT_TYPES

    freeze = v29.build_real_evidence_freeze(
        signing_key_path=_key(tmp_path, "v29-freeze"),
        real_execution_gate=gate,
    )
    verified = v29.verify_real_evidence_freeze(freeze)
    assert verified["valid"] is True
    assert verified["production_mainnet_ready"] is False


def test_v29_cluster_requires_operator_provider_region_and_signer_diversity(tmp_path):
    observed = 1_800_000_000_000
    hosts = [
        _host(tmp_path, i, observed_at_ms=observed + i * 1000, height=100, provider="one-provider", region="one-region")
        for i in range(1, 5)
    ]
    cluster = v29.build_cluster_observation(
        signing_key_path=_key(tmp_path, "weak-cluster"),
        host_observations=hosts,
    )
    assert cluster["manifest"]["cluster_gate_satisfied"] is False
    assert cluster["manifest"]["checks"]["provider_diversity"] is False
    assert cluster["manifest"]["checks"]["region_diversity"] is False


def test_v29_soak_rejects_short_or_weak_thresholds(tmp_path):
    cluster1 = _cluster(tmp_path, observed_at_ms=1_800_000_000_000, height=100)
    cluster2 = _cluster(tmp_path, observed_at_ms=1_800_003_600_000, height=101)
    with pytest.raises(v29.RealExecutionV29Error):
        v29.build_soak_evidence(
            signing_key_path=_key(tmp_path, "bad-soak"),
            cluster_samples=[cluster1, cluster2],
            minimum_duration_seconds=3600,
            minimum_success_ratio=0.98,
        )


def test_v29_rpc_endpoint_rejects_embedded_credentials(tmp_path):
    with pytest.raises(v29.RealExecutionV29Error):
        v29.build_live_host_observation(
            signing_key_path=_key(tmp_path, "credential-host"),
            source_commit="a" * 40,
            candidate_identity_sha256="b" * 64,
            application_genesis_sha256="c" * 64,
            consensus_genesis_sha256="d" * 64,
            validator_id="validator-1",
            operator_id="operator-1",
            provider="provider-a",
            region="region-a",
            rpc_endpoint="https://user:secret@example.invalid",
            expected_chain_id="crakbit-testnet-v29",
            measurement={"chain_id":"crakbit-testnet-v29","node_id":"node-1","latest_height":1,"abci_height":1,"app_hash":"hash","catching_up":False},
            execution_private_asserted=True,
            abci_private_asserted=True,
            signer_protected_asserted=True,
        )
