from __future__ import annotations

import time

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.pow_testnet_v35 import (
    REQUIRED_FAULT_KINDS,
    build_fault_campaign,
    build_host_attestation,
    build_public_testnet_gate,
    build_testnet_freeze,
    evaluate_convergence,
    summarize_soak,
    verify_host_attestation,
    verify_public_testnet_gate,
    verify_testnet_freeze,
)


def _attestation(tmp_path, index: int, commit: str, *, miner: bool = True, pool: bool = False):
    key = KeyPair.generate(); path = tmp_path / f"op{index}.json"; key.save(path)
    return build_host_attestation(
        key_path=path,
        operator_id=f"operator-{index}",
        node_id=f"node-{index}",
        provider="provider-a" if index < 3 else "provider-b",
        region="region-a" if index % 2 else "region-b",
        rpc_url=f"https://node{index}.example.invalid",
        p2p_endpoint=f"node{index}.example.invalid:28444",
        source_commit=commit,
        package_version="0.35.0a1",
        chain_id="crakbit-pow-testnet-v1",
        genesis_hash="ab" * 32,
        independently_managed=True,
        miner_role=miner,
        pool_role=pool,
    )


def test_v35_host_attestation_signatures(tmp_path):
    record = _attestation(tmp_path, 1, "1" * 40)
    assert verify_host_attestation(record)["valid"] is True
    record["manifest"]["provider"] = "tampered"
    with pytest.raises(Exception):
        verify_host_attestation(record)


def test_v35_convergence_detects_same_height_conflict():
    observations = []
    for i in range(4):
        observations.append({
            "format": "crakbit-pow-node-observation-v35/1", "reachable": True,
            "chain_id": "c", "genesis_hash": "aa" * 32, "pow_algo": "crakpow-scrypt-v1",
            "height": 100, "best_block_hash": ("11" * 32 if i < 3 else "22" * 32), "node_id": f"n{i}", "observed_at_unix": 1000,
        })
    result = evaluate_convergence(observations)
    assert result["converged"] is False
    assert result["conflicts"]


def test_v35_soak_requires_real_duration():
    now = int(time.time())
    short = summarize_soak([
        {"observed_at_unix": now, "reachable": True, "node_id": "a"},
        {"observed_at_unix": now + 3600, "reachable": True, "node_id": "a"},
    ], required_level="24h")
    assert short["soak_gate_satisfied"] is False
    long = summarize_soak([
        {"observed_at_unix": now, "reachable": True, "node_id": "a"},
        {"observed_at_unix": now + 24 * 3600, "reachable": True, "node_id": "a"},
    ], required_level="24h")
    assert long["soak_gate_satisfied"] is True


def test_v35_public_testnet_gate_and_freeze(tmp_path):
    commit = "2" * 40
    hosts = [
        _attestation(tmp_path, 1, commit, miner=True, pool=False),
        _attestation(tmp_path, 2, commit, miner=True, pool=False),
        _attestation(tmp_path, 3, commit, miner=False, pool=True),
        _attestation(tmp_path, 4, commit, miner=False, pool=False),
    ]
    observations = [{
        "format": "crakbit-pow-node-observation-v35/1", "reachable": True, "chain_id": "crakbit-pow-testnet-v1",
        "genesis_hash": "ab" * 32, "pow_algo": "crakpow-scrypt-v1", "height": 100,
        "best_block_hash": "cc" * 32, "node_id": f"node-{i}", "observed_at_unix": 1000,
    } for i in range(1, 5)]
    convergence = evaluate_convergence(observations)
    soak = summarize_soak([
        {"observed_at_unix": 1000, "reachable": True, "node_id": "node-1"},
        {"observed_at_unix": 1000 + 24 * 3600, "reachable": True, "node_id": "node-1"},
    ], required_level="24h")
    faults = build_fault_campaign(
        kinds=sorted(REQUIRED_FAULT_KINDS), recovered=True, higher_work_reorg_observed=True,
        partition_convergence_observed=True, invalid_work_rejected=True,
    )
    gate_key = KeyPair.generate(); gate_key_path = tmp_path / "gate.json"; gate_key.save(gate_key_path)
    gate = build_public_testnet_gate(key_path=gate_key_path, host_attestations=hosts, convergence=convergence, soak=soak, fault_campaign=faults)
    verified = verify_public_testnet_gate(gate)
    assert verified["public_testnet_gate_satisfied"] is True
    freeze = build_testnet_freeze(key_path=gate_key_path, gate_record=gate, source_commit=commit)
    assert verify_testnet_freeze(freeze)["valid"] is True
    assert freeze["manifest"]["production_mainnet_ready"] is False
    assert freeze["manifest"]["production_crkbit_launched"] is False


def test_v35_gate_rejects_same_operator_signer_reuse(tmp_path):
    commit = "3" * 40
    key = KeyPair.generate(); key_path = tmp_path / "shared.json"; key.save(key_path)
    hosts = []
    for i in range(4):
        hosts.append(build_host_attestation(
            key_path=key_path, operator_id=f"operator-{i}", node_id=f"node-{i}", provider="p1" if i < 2 else "p2",
            region="r1" if i % 2 else "r2", rpc_url=f"https://n{i}.invalid", p2p_endpoint=f"n{i}.invalid:28444",
            source_commit=commit, package_version="0.35.0a1", chain_id="c", genesis_hash="aa" * 32,
            independently_managed=True, miner_role=True,
        ))
    observations = [{"format":"crakbit-pow-node-observation-v35/1","reachable":True,"chain_id":"c","genesis_hash":"aa"*32,"pow_algo":"crakpow-scrypt-v1","height":10,"best_block_hash":"bb"*32,"node_id":f"node-{i}","observed_at_unix":1000} for i in range(4)]
    convergence = evaluate_convergence(observations)
    soak = summarize_soak([{"observed_at_unix":1000,"reachable":True,"node_id":"n"},{"observed_at_unix":1000+24*3600,"reachable":True,"node_id":"n"}], required_level="24h")
    fault = build_fault_campaign(kinds=sorted(REQUIRED_FAULT_KINDS), recovered=True, higher_work_reorg_observed=True, partition_convergence_observed=True, invalid_work_rejected=True)
    gate = build_public_testnet_gate(key_path=key_path, host_attestations=hosts, convergence=convergence, soak=soak, fault_campaign=fault)
    assert gate["manifest"]["checks"]["unique_evidence_signers"] is False
    assert gate["manifest"]["public_testnet_gate_satisfied"] is False
