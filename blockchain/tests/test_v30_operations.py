from __future__ import annotations

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain import operations_v30 as v30
from crakbit_chain import real_execution_v29 as v29


def _key(tmp_path, name: str):
    path = tmp_path / f"{name}.json"
    KeyPair.generate().save(path)
    return path


def _hosts():
    return [
        {"validator_id":"validator-1","operator_id":"operator-1","provider":"provider-a","region":"region-a","node_name":"node-1","rpc_endpoint":"https://rpc1.example.invalid"},
        {"validator_id":"validator-2","operator_id":"operator-2","provider":"provider-a","region":"region-b","node_name":"node-2","rpc_endpoint":"https://rpc2.example.invalid"},
        {"validator_id":"validator-3","operator_id":"operator-3","provider":"provider-b","region":"region-a","node_name":"node-3","rpc_endpoint":"https://rpc3.example.invalid"},
        {"validator_id":"validator-4","operator_id":"operator-4","provider":"provider-b","region":"region-b","node_name":"node-4","rpc_endpoint":"https://rpc4.example.invalid"},
    ]


def _inventory(tmp_path):
    result = v30.build_monitor_inventory(
        signing_key_path=_key(tmp_path, "inventory"),
        source_commit="a" * 40,
        candidate_identity_sha256="b" * 64,
        application_genesis_sha256="c" * 64,
        consensus_genesis_sha256="d" * 64,
        chain_id="crakbit-testnet-v30",
        hosts=_hosts(),
    )
    assert result["manifest"]["inventory_gate_satisfied"] is True
    return result


def _sample(tmp_path, inventory, *, observed_at_ms: int, height: int, name: str):
    measurements = []
    for index in range(1, 5):
        measurements.append({
            "validator_id": f"validator-{index}",
            "chain_id": "crakbit-testnet-v30",
            "node_id": f"node-id-{index}",
            "latest_height": height,
            "abci_height": height,
            "app_hash": f"apphash-{height}",
            "catching_up": False,
        })
    result = v30.build_monitor_sample_from_measurements(
        signing_key_path=_key(tmp_path, name),
        inventory=inventory,
        measurements=measurements,
        observed_at_ms=observed_at_ms,
    )
    assert result["manifest"]["sample_gate_satisfied"] is True
    return result


def test_v30_inventory_rejects_secret_fields(tmp_path):
    hosts = _hosts()
    hosts[0]["token"] = "do-not-store-this"
    with pytest.raises(v30.OperationsV30Error):
        v30.build_monitor_inventory(
            signing_key_path=_key(tmp_path, "bad-inventory"),
            source_commit="a" * 40,
            candidate_identity_sha256="b" * 64,
            application_genesis_sha256="c" * 64,
            consensus_genesis_sha256="d" * 64,
            chain_id="crakbit-testnet-v30",
            hosts=hosts,
        )


def test_v30_resumable_checkpoint_reaches_seven_day_gate(tmp_path):
    inventory = _inventory(tmp_path)
    start = 1_800_000_000_000
    first = _sample(tmp_path, inventory, observed_at_ms=start, height=100, name="sample-1")
    checkpoint1 = v30.build_monitor_checkpoint(
        signing_key_path=_key(tmp_path, "checkpoint-1"),
        session_id="seven-day-campaign",
        samples=[first],
        target_duration_seconds=604800,
        minimum_success_ratio=0.99,
    )
    assert checkpoint1["manifest"]["checkpoint_complete"] is False

    second = _sample(tmp_path, inventory, observed_at_ms=start + 604_800_000, height=200, name="sample-2")
    checkpoint2 = v30.build_monitor_checkpoint(
        signing_key_path=_key(tmp_path, "checkpoint-2"),
        session_id="seven-day-campaign",
        samples=[second],
        target_duration_seconds=604800,
        minimum_success_ratio=0.99,
        previous_checkpoint=checkpoint1,
    )
    verified = v30.verify_monitor_checkpoint(checkpoint2)
    assert verified["checkpoint_complete"] is True
    assert verified["sample_count"] == 2
    assert verified["success_ratio"] == 1.0
    assert checkpoint2["manifest"]["previous_checkpoint_manifest_sha256"] == checkpoint1["manifest_sha256"]


def test_v30_public_bundle_requires_monitor_edges_archive_and_signer(tmp_path):
    inventory = _inventory(tmp_path)
    start = 1_800_000_000_000
    first = _sample(tmp_path, inventory, observed_at_ms=start, height=100, name="bundle-sample-1")
    checkpoint1 = v30.build_monitor_checkpoint(
        signing_key_path=_key(tmp_path, "bundle-checkpoint-1"),
        session_id="bundle-session",
        samples=[first],
        target_duration_seconds=604800,
        minimum_success_ratio=0.99,
    )
    second = _sample(tmp_path, inventory, observed_at_ms=start + 604_800_000, height=200, name="bundle-sample-2")
    checkpoint2 = v30.build_monitor_checkpoint(
        signing_key_path=_key(tmp_path, "bundle-checkpoint-2"),
        session_id="bundle-session",
        samples=[second],
        target_duration_seconds=604800,
        minimum_success_ratio=0.99,
        previous_checkpoint=checkpoint1,
    )

    evidence_file = tmp_path / "raw-evidence.jsonl"
    evidence_file.write_text('{"ok":true}\n', encoding="utf-8")
    archive = v30.build_archive_manifest(
        signing_key_path=_key(tmp_path, "archive"),
        source_commit="a" * 40,
        candidate_identity_sha256="b" * 64,
        artifacts=[("monitor-log", evidence_file)],
        retention_days=90,
    )

    edge_records = []
    for role in ("rpc", "explorer", "gateway"):
        for index in (1, 2):
            edge_records.append(v30.build_edge_health_record(
                signing_key_path=_key(tmp_path, f"edge-{role}-{index}"),
                source_commit="a" * 40,
                candidate_identity_sha256="b" * 64,
                edge_id=f"{role}-{index}",
                role=role,
                url=f"https://{role}{index}.example.invalid/health",
                measurement={"status_code": 200, "latency_ms": 50, "reachable": True},
                max_latency_ms=1000,
            ))
    edge_gate = v30.build_edge_redundancy_gate(
        signing_key_path=_key(tmp_path, "edge-gate"),
        records=edge_records,
        minimum_per_role=2,
    )
    assert edge_gate["manifest"]["edge_redundancy_gate_satisfied"] is True

    signer = v30.build_signer_monitor_record(
        signing_key_path=_key(tmp_path, "signer-monitor"),
        source_commit="a" * 40,
        candidate_identity_sha256="b" * 64,
        signer_id="validator-signer-1",
        custody_type="remote-signer",
        host="signer.internal",
        port=1234,
        reachable=True,
        rotation_drill_manifest_sha256="e" * 64,
        no_private_key_read=True,
    )

    minimal_real_gate = {
        "format": v29.REAL_EXECUTION_GATE_FORMAT,
        "source_commit": "a" * 40,
        "candidate_identity_sha256": "b" * 64,
        "real_execution_gate_satisfied": True,
        "production_mainnet_ready": False,
    }
    real_freeze = v29.build_real_evidence_freeze(
        signing_key_path=_key(tmp_path, "real-freeze"),
        real_execution_gate=minimal_real_gate,
    )

    bundle = v30.build_public_evidence_bundle(
        signing_key_path=_key(tmp_path, "public-bundle"),
        real_freeze_v29=real_freeze,
        monitor_checkpoint=checkpoint2,
        archive_manifest=archive,
        edge_gate=edge_gate,
        signer_records=[signer],
        artifacts=[("raw-monitor-evidence", evidence_file)],
    )
    assert bundle["manifest"]["public_evidence_bundle_gate_satisfied"] is True
    assert bundle["manifest"]["production_mainnet_ready"] is False
    assert bundle["manifest"]["automatic_launch"] is False

    checklist = v30.build_operator_checklist(
        signing_key_path=_key(tmp_path, "operator-checklist"),
        public_evidence_bundle=bundle,
        operator_id="operator-1",
        checks={
            "validator_services_verified": True,
            "backups_verified": True,
            "alerts_verified": True,
            "rollback_path_verified": True,
            "incident_contacts_verified": True,
            "dns_change_requires_manual_action": True,
            "treasury_move_requires_manual_action": True,
            "launch_requires_manual_approval": True,
        },
    )
    assert checklist["manifest"]["operator_checklist_complete"] is True
    assert checklist["manifest"]["production_mainnet_launched"] is False


def test_v30_edge_gate_requires_two_healthy_edges_per_role(tmp_path):
    records = []
    for role in ("rpc", "explorer", "gateway"):
        records.append(v30.build_edge_health_record(
            signing_key_path=_key(tmp_path, f"single-{role}"),
            source_commit="a" * 40,
            candidate_identity_sha256="b" * 64,
            edge_id=f"{role}-1",
            role=role,
            url=f"https://{role}1.example.invalid/health",
            measurement={"status_code": 200, "latency_ms": 10, "reachable": True},
        ))
    gate = v30.build_edge_redundancy_gate(
        signing_key_path=_key(tmp_path, "weak-edge-gate"),
        records=records,
        minimum_per_role=2,
    )
    assert gate["manifest"]["edge_redundancy_gate_satisfied"] is False
