from __future__ import annotations

import json
from pathlib import Path

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.ops_drill_evidence import (
    OperationsDrillError,
    build_drill_evidence,
    verify_drill_evidence,
)
from crakbit_chain.release_provenance_v19 import (
    ReleaseProvenanceError,
    build_release_provenance,
    verify_release_provenance,
)
from crakbit_chain.reproducible_build import compare_build_outputs
from crakbit_chain.review_findings import build_remediation_matrix, verify_remediation_matrix
from crakbit_chain.sbom_v19 import build_sbom


def _genesis(tmp_path: Path) -> Path:
    validator = KeyPair.generate()
    path = tmp_path / "genesis.json"
    path.write_text(
        json.dumps(
            {
                "chain_id": "crakbit-v19-test",
                "network_name": "Crakbit v0.19 Test",
                "symbol": "CRKBIT",
                "decimals": 8,
                "max_supply": 1_000_000,
                "block_time_ms": 1000,
                "view_timeout_ms": 2000,
                "min_fee": 1,
                "validators": [
                    {
                        "address": validator.address,
                        "public_key": validator.public_key_b64,
                        "name": "validator-1",
                        "peer_url": "http://127.0.0.1:9101",
                    }
                ],
                "allocations": {validator.address: 1_000_000},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_remediation_matrix_blocks_unresolved_high_findings(tmp_path: Path):
    source = tmp_path / "review.json"
    source.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "id": "SEC-001",
                        "title": "Example high finding",
                        "severity": "high",
                        "status": "open",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    matrix = build_remediation_matrix(source_commit="a" * 40, finding_paths=[source])
    result = verify_remediation_matrix(matrix)
    assert result["valid"] is True
    assert result["high_critical_release_gate_clear"] is False
    assert result["high_critical_blockers"] == ["SEC-001"]

    source.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "id": "SEC-001",
                        "title": "Example high finding",
                        "severity": "high",
                        "status": "remediated",
                        "regression_tests": ["tests/test_sec_001.py"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    fixed = build_remediation_matrix(source_commit="b" * 40, finding_paths=[source])
    assert verify_remediation_matrix(fixed)["high_critical_release_gate_clear"] is True


def test_reproducible_artifact_report_detects_mismatch(tmp_path: Path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "artifact.bin").write_bytes(b"same")
    (right / "artifact.bin").write_bytes(b"same")
    report = compare_build_outputs(left_root=left, right_root=right, relative_files=["artifact.bin"])
    assert report["reproducible"] is True

    (right / "artifact.bin").write_bytes(b"different")
    report = compare_build_outputs(left_root=left, right_root=right, relative_files=["artifact.bin"])
    assert report["reproducible"] is False


def test_sbom_is_deterministic_for_same_inputs(tmp_path: Path):
    blockchain = tmp_path / "blockchain"
    comet = blockchain / "cometbft-app"
    comet.mkdir(parents=True)
    (blockchain / "pyproject.toml").write_text(
        '[project]\nname="crakbit-chain"\nversion="0.19.0a1"\ndependencies=["cryptography>=42.0.0"]\n',
        encoding="utf-8",
    )
    (comet / "go.mod").write_text(
        "module example.test/crakbit\n\ngo 1.25.0\n\nrequire github.com/cometbft/cometbft v0.40.0\n",
        encoding="utf-8",
    )
    (comet / "go.sum").write_text("example checksum line\n", encoding="utf-8")
    first = build_sbom(tmp_path)
    second = build_sbom(tmp_path)
    assert first == second
    assert first["bomFormat"] == "CycloneDX"
    assert any(item["name"] == "github.com/cometbft/cometbft" for item in first["components"])


def test_signed_release_provenance_and_tamper_detection(tmp_path: Path):
    genesis = _genesis(tmp_path)
    signer = KeyPair.generate()
    key = tmp_path / "release-key.json"
    signer.save(key)
    artifact = tmp_path / "app.bin"
    artifact.write_bytes(b"release-artifact")
    sbom = tmp_path / "sbom.json"
    sbom.write_text('{"bomFormat":"CycloneDX"}\n', encoding="utf-8")
    repro = tmp_path / "repro.json"
    repro.write_text(
        json.dumps(
            {
                "format": "crakbit-reproducible-build-report/1",
                "reproducible": True,
                "artifact_count": 1,
                "artifacts": [],
            }
        ),
        encoding="utf-8",
    )

    envelope = build_release_provenance(
        genesis_path=genesis,
        signing_key_path=key,
        source_commit="c" * 40,
        package_version="0.19.0a1",
        cometbft_version="v0.40.0",
        artifacts=[("bridge", artifact)],
        sbom_path=sbom,
        reproducibility_report_path=repro,
    )
    result = verify_release_provenance(
        envelope,
        genesis_path=genesis,
        artifact_directory=tmp_path,
        expected_signer=signer.address,
        expected_source_commit="c" * 40,
    )
    assert result["valid"] is True
    assert result["supplied_artifacts_reproducible"] is True
    assert result["production_mainnet_ready"] is False

    tampered = json.loads(json.dumps(envelope))
    tampered["manifest"]["package_version"] = "9.9.9"
    with pytest.raises(ReleaseProvenanceError):
        verify_release_provenance(tampered, genesis_path=genesis)


def test_signed_operations_drill_evidence(tmp_path: Path):
    signer = KeyPair.generate()
    key = tmp_path / "ops-key.json"
    signer.save(key)
    log = tmp_path / "restore.log"
    log.write_text("restore completed\n", encoding="utf-8")
    envelope = build_drill_evidence(
        signing_key_path=key,
        source_commit="d" * 40,
        kind="disaster-recovery",
        started_at_ms=100,
        completed_at_ms=200,
        success=True,
        summary="Restored a disposable test node from verified backup.",
        evidence_paths=[log],
    )
    result = verify_drill_evidence(
        envelope,
        evidence_directory=tmp_path,
        expected_signer=signer.address,
    )
    assert result["valid"] is True
    assert result["success"] is True
    assert result["independently_verified"] is False

    tampered = json.loads(json.dumps(envelope))
    tampered["manifest"]["success"] = False
    with pytest.raises(OperationsDrillError):
        verify_drill_evidence(tampered)
