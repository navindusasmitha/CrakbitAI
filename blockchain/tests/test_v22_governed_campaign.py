from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from crakbit_chain.cluster_monitor_v22 import evaluate_observations
from crakbit_chain.comet_broadcast_v22 import build_broadcast_payload
from crakbit_chain.crypto import KeyPair
from crakbit_chain.genesis import Genesis
from crakbit_chain.governance_campaign_v22 import (
    build_campaign_evidence,
    build_campaign_plan,
    save_campaign_plan,
    verify_campaign_evidence,
)
from crakbit_chain.governed_lab_v22 import build_application_genesis


def _write_fake_comet_key(home: Path, key: KeyPair, index: int) -> None:
    home.joinpath("config").mkdir(parents=True, exist_ok=True)
    private_seed = base64.b64decode(key.private_key_b64)
    public_raw = base64.b64decode(key.public_key_b64)
    body = {
        "address": f"{index:040X}"[-40:],
        "pub_key": {
            "type": "tendermint/PubKeyEd25519",
            "value": key.public_key_b64,
        },
        "priv_key": {
            "type": "tendermint/PrivKeyEd25519",
            "value": base64.b64encode(private_seed + public_raw).decode("ascii"),
        },
    }
    home.joinpath("config", "priv_validator_key.json").write_text(
        json.dumps(body) + "\n", encoding="utf-8"
    )


def test_v22_application_genesis_matches_four_comet_validator_identities(tmp_path: Path):
    nodes = []
    source_keys = []
    for index in range(4):
        key = KeyPair.generate()
        source_keys.append(key)
        home = tmp_path / f"node{index + 1}"
        _write_fake_comet_key(home, key, index + 1)
        nodes.append(
            {
                "name": f"validator-{index + 1}",
                "home": str(home),
                "rpc_port": 28657 + index * 10,
                "execution_port": 28659 + index * 10,
            }
        )
    manifest = {"chain_id": "crakbit-v22-test", "nodes": nodes}
    output = tmp_path / "application-genesis.json"
    built = build_application_genesis(
        base_manifest=manifest,
        output=output,
        treasury_key_path=tmp_path / ".secrets" / "treasury.json",
    )
    loaded = Genesis.load(output)
    assert len(loaded.validators) == 4
    assert {item.public_key for item in loaded.validators} == {key.public_key_b64 for key in source_keys}
    assert {item.address for item in loaded.validators} == {key.address for key in source_keys}
    assert sum(loaded.allocations.values()) == loaded.max_supply
    assert built["treasury_address"] in loaded.allocations
    for index, source in enumerate(source_keys):
        exported = KeyPair.load(
            tmp_path / ".secrets" / f"validator-{index + 1}-DISPOSABLE-governance-key.json"
        )
        assert exported.address == source.address
        assert exported.public_key_b64 == source.public_key_b64


def _observation(name: str, height: int, app_hash: str, gov_hash: str = "g" * 64):
    return {
        "name": name,
        "reachable": True,
        "execution": {
            "height": height,
            "application_hash": app_hash,
            "schema_version": 21,
        },
        "governance": {
            "active_validator_set_hash": gov_hash,
            "pending": [],
        },
        "cometbft": {"catching_up": False, "latest_block_height": height},
    }


def test_v22_cluster_evaluator_detects_same_height_divergence():
    observations = [
        _observation("node1", 10, "a" * 64),
        _observation("node2", 10, "a" * 64),
        _observation("node3", 11, "b" * 64),
        _observation("node4", 11, "b" * 64),
    ]
    good = evaluate_observations(observations, max_height_spread=1)
    assert good["divergence_free"] is True
    assert good["height_spread"] == 1

    broken = json.loads(json.dumps(observations))
    broken[1]["execution"]["application_hash"] = "c" * 64
    bad = evaluate_observations(broken, max_height_spread=1)
    assert bad["divergence_free"] is False
    assert bad["same_height_application_hash_conflicts"][0]["height"] == 10


def _genesis(tmp_path: Path) -> Path:
    validators = [KeyPair.generate() for _ in range(4)]
    treasury = KeyPair.generate()
    path = tmp_path / "genesis.json"
    path.write_text(
        json.dumps(
            {
                "chain_id": "crakbit-v22-campaign",
                "network_name": "Crakbit v0.22 Campaign Test",
                "symbol": "CRKBIT",
                "decimals": 8,
                "max_supply": 1_000_000,
                "block_time_ms": 1000,
                "view_timeout_ms": 2000,
                "min_fee": 1,
                "validators": [
                    {
                        "address": item.address,
                        "public_key": item.public_key_b64,
                        "name": f"validator-{index + 1}",
                        "peer_url": f"http://127.0.0.1:{29000 + index}",
                    }
                    for index, item in enumerate(validators)
                ],
                "allocations": {treasury.address: 1_000_000},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_v22_campaign_plan_and_signed_evidence(tmp_path: Path):
    genesis_path = _genesis(tmp_path)
    genesis = Genesis.load(genesis_path)
    change_request = tmp_path / "join.json"
    change_request.write_text(
        json.dumps(
            {
                "type": "validator_governance",
                "format": "crakbit-validator-governance-tx/1",
                "change_id": "d" * 64,
                "request": {
                    "chain_id": genesis.chain_id,
                    "genesis_fingerprint": genesis.fingerprint(),
                    "kind": "join",
                    "emit_height": 20,
                    "effective_height": 22,
                },
                "approvals": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    plan = build_campaign_plan(
        genesis_path=genesis_path,
        kind="join",
        emit_height=20,
        change_request_path=change_request,
    )
    assert plan["effective_height"] == 22
    assert plan["restart_heights"] == [20, 21, 22]
    plan_path = tmp_path / "campaign.json"
    save_campaign_plan(plan, plan_path)

    observation = tmp_path / "cluster-check.json"
    observation.write_text(
        json.dumps({"format": "crakbit-governed-cluster-observation/1", "divergence_free": True})
        + "\n",
        encoding="utf-8",
    )
    signer = KeyPair.generate()
    signer_path = tmp_path / "campaign-signer.json"
    signer.save(signer_path)
    envelope = build_campaign_evidence(
        genesis_path=genesis_path,
        signing_key_path=signer_path,
        source_commit="a" * 40,
        plan_path=plan_path,
        observation_paths=[observation],
        executed=True,
        operator_note="unit-test campaign evidence",
    )
    verified = verify_campaign_evidence(
        envelope,
        genesis_path=genesis_path,
        artifact_directory=tmp_path,
        expected_signer=signer.address,
        expected_source_commit="a" * 40,
    )
    assert verified["valid"] is True
    assert verified["campaign_executed"] is True
    assert verified["verified_artifact_count"] == 2

    tampered = json.loads(json.dumps(envelope))
    tampered["manifest"]["effective_height"] = 999
    with pytest.raises(Exception):
        verify_campaign_evidence(tampered, genesis_path=genesis_path)


def test_v22_governance_broadcast_payload_uses_base64_json_bytes():
    envelope = {
        "type": "validator_governance",
        "format": "crakbit-validator-governance-tx/1",
        "change_id": "e" * 64,
        "request": {"emit_height": 12},
        "approvals": [],
    }
    payload = build_broadcast_payload(envelope)
    assert payload["method"] == "broadcast_tx_sync"
    decoded = base64.b64decode(payload["params"]["tx"])
    body = json.loads(decoded.decode("utf-8"))
    assert body["type"] == "validator_governance"
    assert body["request"]["emit_height"] == 12
