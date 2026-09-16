from __future__ import annotations

import json
from pathlib import Path

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.public_testnet_evidence_v23 import (
    build_operations_evidence,
    build_readiness_report,
    save_json,
    verify_operations_evidence,
)
from crakbit_chain.public_testnet_monitor_v23 import (
    OBSERVATION_FORMAT,
    summarize_soak,
)
from crakbit_chain.public_testnet_v23 import (
    PublicTestnetV23Error,
    build_genesis_bundle,
    build_public_testnet_inventory,
    render_operator_deployment_bundles,
)


def _identity(index: int, *, same_operator: bool = False) -> dict:
    key = KeyPair.generate()
    return {
        "format": "crakbit-validator-public-identity/1",
        "name": f"validator-{index}",
        "operator_id": "operator-1" if same_operator else f"operator-{index}",
        "provider": f"provider-{1 + (index % 2)}",
        "region": f"region-{1 + (index % 2)}",
        "node_id": f"{index:040x}"[-40:],
        "cometbft_address": f"{index + 100:040X}"[-40:],
        "public_key": key.public_key_b64,
        "crakbit_address": key.address,
        "p2p_host": f"validator-{index}.example.test",
        "p2p_port": 26650 + index,
        "monitor_rpc_url": f"https://validator-{index}.monitor.example.test",
        "contains_private_material": False,
    }


def _inventory(tmp_path: Path, *, same_operator: bool = False):
    body = build_public_testnet_inventory(
        chain_id="crakbit-v23-testnet",
        network_name="Crakbit v0.23 Testnet",
        identities=[_identity(i, same_operator=same_operator) for i in range(1, 5)],
    )
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return path, body


def test_v23_inventory_requires_public_metadata_and_tracks_diversity(tmp_path: Path):
    _path, inventory = _inventory(tmp_path)
    assert inventory["validator_count"] == 4
    assert inventory["operator_count"] == 4
    assert inventory["independent_operator_gate_satisfied"] is True
    assert inventory["multi_provider_gate_satisfied"] is True
    assert inventory["production_mainnet_ready"] is False

    bad = [_identity(i) for i in range(1, 5)]
    bad[0]["token"] = "should-never-be-public"
    with pytest.raises(PublicTestnetV23Error):
        build_public_testnet_inventory(
            chain_id="crakbit-v23-testnet",
            network_name="Crakbit",
            identities=bad,
        )


def test_v23_genesis_and_operator_bundles_contain_no_private_material(tmp_path: Path):
    _inventory_path, inventory = _inventory(tmp_path)
    treasury = KeyPair.generate()
    template = tmp_path / "template-genesis.json"
    template.write_text(
        json.dumps(
            {
                "genesis_time": "",
                "chain_id": "template",
                "initial_height": "0",
                "consensus_params": {},
                "validators": [],
                "app_hash": "",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    genesis_dir = tmp_path / "genesis-bundle"
    manifest = build_genesis_bundle(
        inventory=inventory,
        cometbft_genesis_template=template,
        treasury_address=treasury.address,
        output_dir=genesis_dir,
    )
    assert manifest["contains_private_material"] is False
    app = json.loads((genesis_dir / "application-genesis.json").read_text(encoding="utf-8"))
    consensus = json.loads((genesis_dir / "cometbft-genesis.json").read_text(encoding="utf-8"))
    assert len(app["validators"]) == 4
    assert len(consensus["validators"]) == 4
    assert app["allocations"] == {treasury.address: app["max_supply"]}

    deployment_dir = tmp_path / "deploy"
    deployment = render_operator_deployment_bundles(
        inventory=inventory,
        genesis_bundle_dir=genesis_dir,
        output_dir=deployment_dir,
    )
    assert deployment["contains_private_material"] is False
    assert deployment["deployment_executed"] is False
    env_text = (deployment_dir / "validator-1" / "node.env.example").read_text(encoding="utf-8")
    assert "REPLACE_WITH_LOCAL_RANDOM_32_BYTE_SECRET" in env_text
    assert "private_key" not in env_text


def test_v23_soak_summary_and_readiness_do_not_claim_mainnet(tmp_path: Path):
    inventory_path, _inventory_body = _inventory(tmp_path)
    jsonl = tmp_path / "soak.jsonl"
    samples = [
        {
            "format": OBSERVATION_FORMAT,
            "observed_at_ms": 1_000,
            "chain_id": "crakbit-v23-testnet",
            "healthy": True,
            "all_reachable": True,
            "height_spread": 0,
            "same_height_application_hash_conflicts": [],
            "catching_up_nodes": [],
            "observations": [
                {"reachable": True, "latency_ms": 10.0},
                {"reachable": True, "latency_ms": 20.0},
            ],
        },
        {
            "format": OBSERVATION_FORMAT,
            "observed_at_ms": 86_401_000,
            "chain_id": "crakbit-v23-testnet",
            "healthy": True,
            "all_reachable": True,
            "height_spread": 1,
            "same_height_application_hash_conflicts": [],
            "catching_up_nodes": [],
            "observations": [{"reachable": True, "latency_ms": 15.0}],
        },
    ]
    jsonl.write_text("".join(json.dumps(item) + "\n" for item in samples), encoding="utf-8")
    summary = summarize_soak(jsonl)
    assert summary["observed_duration_seconds"] == 86_400.0
    assert summary["divergence_free"] is True
    assert summary["production_mainnet_ready"] is False

    genesis_manifest = tmp_path / "genesis-bundle.json"
    genesis_manifest.write_text(
        json.dumps(
            {
                "format": "crakbit-public-testnet-genesis-bundle/1",
                "contains_private_material": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    deployment_manifest = tmp_path / "deployment-manifest.json"
    deployment_manifest.write_text(
        json.dumps(
            {
                "format": "crakbit-public-testnet-deployment-bundle/1",
                "contains_private_material": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    summary_path = tmp_path / "soak-summary.json"
    summary_path.write_text(json.dumps(summary) + "\n", encoding="utf-8")
    readiness = build_readiness_report(
        inventory_path=inventory_path,
        genesis_manifest_path=genesis_manifest,
        deployment_manifest_path=deployment_manifest,
        soak_summary_path=summary_path,
    )
    assert readiness["public_testnet_launch_candidate"] is True
    assert readiness["minimum_24h_soak_gate_satisfied"] is True
    assert readiness["production_mainnet_ready"] is False


def test_v23_signed_operations_evidence_verifies_artifacts(tmp_path: Path):
    inventory_path, _inventory_body = _inventory(tmp_path)
    readiness = build_readiness_report(inventory_path=inventory_path)
    readiness_path = tmp_path / "readiness.json"
    save_json(readiness, readiness_path)
    note = tmp_path / "operator-note.json"
    note.write_text(json.dumps({"result": "test-only"}) + "\n", encoding="utf-8")
    signer = KeyPair.generate()
    signer_path = tmp_path / "signer.json"
    signer.save(signer_path)
    envelope = build_operations_evidence(
        signing_key_path=signer_path,
        source_commit="a" * 40,
        inventory_path=inventory_path,
        readiness_path=readiness_path,
        artifact_paths=[note],
        operator_note="unit test",
    )
    verified = verify_operations_evidence(
        envelope,
        artifact_directory=tmp_path,
        expected_signer=signer.address,
        expected_source_commit="a" * 40,
    )
    assert verified["valid"] is True
    assert verified["verified_artifact_count"] == 3
    assert verified["production_mainnet_ready"] is False


def test_v23_single_operator_inventory_does_not_satisfy_independence_gate(tmp_path: Path):
    _path, inventory = _inventory(tmp_path, same_operator=True)
    assert inventory["operator_count"] == 1
    assert inventory["independent_operator_gate_satisfied"] is False
