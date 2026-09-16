from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import httpx

from .crypto import canonical_json, sha256_hex
from . import launch_rehearsal_v28 as v28

HOST_OBSERVATION_FORMAT = "crakbit-v29-live-host-observation/1"
CLUSTER_OBSERVATION_FORMAT = "crakbit-v29-cluster-observation/1"
GENESIS_ATTESTATION_FORMAT = "crakbit-v29-genesis-attestation/1"
GENESIS_GATE_FORMAT = "crakbit-v29-genesis-ceremony-gate/1"
SOAK_EVIDENCE_FORMAT = "crakbit-v29-soak-evidence/1"
FAULT_RESULT_FORMAT = "crakbit-v29-fault-result/1"
REAL_EXECUTION_GATE_FORMAT = "crakbit-v29-real-execution-gate/1"
REAL_EVIDENCE_FREEZE_FORMAT = "crakbit-v29-real-evidence-freeze/1"

REQUIRED_FAULT_TYPES = {
    "restart", "process-kill", "partition", "latency", "packet-loss",
    "load", "storage", "state-sync", "governance", "upgrade",
}


class RealExecutionV29Error(ValueError):
    pass


def load_json(path: str | Path) -> dict[str, Any]:
    return v28.load_json(path)


def save_json(body: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    return v28.save_json(body, path, overwrite=overwrite)


def _valid_commit(value: str) -> str:
    try:
        return v28._valid_commit(value)
    except Exception as exc:
        raise RealExecutionV29Error(str(exc)) from exc


def _valid_sha(value: str) -> str:
    try:
        return v28._valid_sha(value)
    except Exception as exc:
        raise RealExecutionV29Error(str(exc)) from exc


def _sign(key: str | Path, manifest: dict[str, Any]) -> dict[str, Any]:
    return v28._sign(key, manifest)


def _verify(envelope: dict[str, Any], expected_format: str, *, expected_signer: str | None = None) -> dict[str, Any]:
    try:
        return v28._verify(envelope, expected_format, expected_signer=expected_signer)
    except Exception as exc:
        raise RealExecutionV29Error(str(exc)) from exc


def _clean(value: str, label: str) -> str:
    result = str(value).strip()
    if not result:
        raise RealExecutionV29Error(f"{label} is required")
    return result


def _safe_rpc_endpoint(value: str) -> str:
    endpoint = _clean(value, "rpc_endpoint").rstrip("/")
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RealExecutionV29Error("rpc_endpoint must be http(s) with a hostname")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RealExecutionV29Error("rpc_endpoint may not contain credentials, query or fragment")
    return endpoint


def probe_cometbft_rpc(rpc_endpoint: str, *, timeout_seconds: float = 5.0) -> dict[str, Any]:
    endpoint = _safe_rpc_endpoint(rpc_endpoint)
    timeout = float(timeout_seconds)
    if timeout <= 0 or timeout > 30:
        raise RealExecutionV29Error("timeout_seconds must be >0 and <=30")
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            status_response = client.get(f"{endpoint}/status")
            status_response.raise_for_status()
            abci_response = client.get(f"{endpoint}/abci_info")
            abci_response.raise_for_status()
            status = status_response.json().get("result", {})
            abci = abci_response.json().get("result", {}).get("response", {})
    except Exception as exc:
        raise RealExecutionV29Error(f"CometBFT RPC probe failed: {exc}") from exc

    sync = status.get("sync_info", {})
    node = status.get("node_info", {})
    try:
        latest_height = int(sync.get("latest_block_height", 0))
        abci_height = int(abci.get("last_block_height", 0))
    except Exception as exc:
        raise RealExecutionV29Error("RPC returned invalid block heights") from exc
    app_hash = str(abci.get("last_block_app_hash", "")).strip().lower()
    if latest_height <= 0 or abci_height <= 0 or not app_hash:
        raise RealExecutionV29Error("RPC is not yet serving a committed application state")
    return {
        "chain_id": _clean(str(node.get("network", "")), "chain_id"),
        "node_id": _clean(str(node.get("id", "")), "node_id"),
        "latest_height": latest_height,
        "abci_height": abci_height,
        "app_hash": app_hash,
        "catching_up": bool(sync.get("catching_up", False)),
    }


def build_live_host_observation(
    *, signing_key_path: str | Path, source_commit: str, candidate_identity_sha256: str,
    application_genesis_sha256: str, consensus_genesis_sha256: str,
    validator_id: str, operator_id: str, provider: str, region: str,
    rpc_endpoint: str, expected_chain_id: str, measurement: dict[str, Any],
    execution_private_asserted: bool, abci_private_asserted: bool,
    signer_protected_asserted: bool, observed_at_ms: int | None = None,
) -> dict[str, Any]:
    observed = int(time.time() * 1000) if observed_at_ms is None else int(observed_at_ms)
    latest_height = int(measurement.get("latest_height", 0))
    abci_height = int(measurement.get("abci_height", 0))
    chain_id = _clean(str(measurement.get("chain_id", "")), "measurement.chain_id")
    node_id = _clean(str(measurement.get("node_id", "")), "measurement.node_id")
    app_hash = _clean(str(measurement.get("app_hash", "")), "measurement.app_hash").lower()
    if latest_height <= 0 or abci_height <= 0:
        raise RealExecutionV29Error("live observation requires positive committed heights")
    checks = {
        "expected_chain_id_matches": chain_id == _clean(expected_chain_id, "expected_chain_id"),
        "not_catching_up": not bool(measurement.get("catching_up", False)),
        "height_gap_at_most_one": abs(latest_height - abci_height) <= 1,
        "execution_surface_private_asserted": bool(execution_private_asserted),
        "abci_surface_private_asserted": bool(abci_private_asserted),
        "protected_signer_asserted": bool(signer_protected_asserted),
    }
    manifest = {
        "format": HOST_OBSERVATION_FORMAT,
        "observed_at_ms": observed,
        "source_commit": _valid_commit(source_commit),
        "candidate_identity_sha256": _valid_sha(candidate_identity_sha256),
        "application_genesis_sha256": _valid_sha(application_genesis_sha256),
        "consensus_genesis_sha256": _valid_sha(consensus_genesis_sha256),
        "validator_id": _clean(validator_id, "validator_id"),
        "operator_id": _clean(operator_id, "operator_id"),
        "provider": _clean(provider, "provider"),
        "region": _clean(region, "region"),
        "rpc_endpoint": _safe_rpc_endpoint(rpc_endpoint),
        "chain_id": chain_id,
        "node_id": node_id,
        "latest_height": latest_height,
        "abci_height": abci_height,
        "app_hash": app_hash,
        "checks": checks,
        "live_rpc_probe_performed": True,
        "host_gate_satisfied": all(checks.values()),
        "contains_private_key": False,
        "contains_provider_secret": False,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def probe_and_build_live_host_observation(**kwargs: Any) -> dict[str, Any]:
    endpoint = kwargs["rpc_endpoint"]
    timeout_seconds = float(kwargs.pop("timeout_seconds", 5.0))
    measurement = probe_cometbft_rpc(endpoint, timeout_seconds=timeout_seconds)
    return build_live_host_observation(measurement=measurement, **kwargs)


def verify_live_host_observation(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, HOST_OBSERVATION_FORMAT, expected_signer=expected_signer)
    if manifest.get("live_rpc_probe_performed") is not True:
        raise RealExecutionV29Error("host record is not a live RPC observation")
    return {
        "valid": True,
        "validator_id": manifest["validator_id"],
        "operator_id": manifest["operator_id"],
        "host_gate_satisfied": bool(manifest.get("host_gate_satisfied")),
        "latest_height": int(manifest["latest_height"]),
        "app_hash": manifest["app_hash"],
        "production_mainnet_ready": False,
    }


def build_cluster_observation(
    *, signing_key_path: str | Path, host_observations: list[dict[str, Any]],
    maximum_height_spread: int = 2, maximum_observation_window_ms: int = 300_000,
) -> dict[str, Any]:
    if len(host_observations) < 4:
        raise RealExecutionV29Error("cluster observation requires at least four host observations")
    manifests = [_verify(item, HOST_OBSERVATION_FORMAT) for item in host_observations]
    source_commit = manifests[0]["source_commit"]
    candidate = manifests[0]["candidate_identity_sha256"]
    app_genesis = manifests[0]["application_genesis_sha256"]
    consensus_genesis = manifests[0]["consensus_genesis_sha256"]
    chain_id = manifests[0]["chain_id"]
    identities_match = all(
        m["source_commit"] == source_commit
        and m["candidate_identity_sha256"] == candidate
        and m["application_genesis_sha256"] == app_genesis
        and m["consensus_genesis_sha256"] == consensus_genesis
        and m["chain_id"] == chain_id
        for m in manifests
    )
    validators = {m["validator_id"] for m in manifests}
    operators = {m["operator_id"] for m in manifests}
    providers = {m["provider"] for m in manifests}
    regions = {m["region"] for m in manifests}
    signers = {item.get("signer", "") for item in host_observations}
    heights = [int(m["latest_height"]) for m in manifests]
    observed = [int(m["observed_at_ms"]) for m in manifests]
    spread = max(heights) - min(heights)
    observation_window = max(observed) - min(observed)
    hashes_by_height: dict[int, set[str]] = {}
    for m in manifests:
        hashes_by_height.setdefault(int(m["abci_height"]), set()).add(str(m["app_hash"]))
    same_height_divergence = any(len(values) > 1 for values in hashes_by_height.values())
    checks = {
        "all_host_gates_satisfied": all(m.get("host_gate_satisfied") is True for m in manifests),
        "exact_candidate_and_genesis_match": identities_match,
        "minimum_four_unique_validators": len(validators) >= 4 and len(validators) == len(manifests),
        "minimum_four_unique_operators": len(operators) >= 4,
        "minimum_four_unique_evidence_signers": len(signers) >= 4 and "" not in signers,
        "provider_diversity": len(providers) >= 2,
        "region_diversity": len(regions) >= 2,
        "height_spread_within_limit": spread <= int(maximum_height_spread),
        "observation_window_within_limit": observation_window <= int(maximum_observation_window_ms),
        "no_same_height_app_hash_divergence": not same_height_divergence,
    }
    manifest = {
        "format": CLUSTER_OBSERVATION_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "observed_at_ms": max(observed),
        "source_commit": source_commit,
        "candidate_identity_sha256": candidate,
        "application_genesis_sha256": app_genesis,
        "consensus_genesis_sha256": consensus_genesis,
        "chain_id": chain_id,
        "validator_ids": sorted(validators),
        "operator_ids": sorted(operators),
        "providers": sorted(providers),
        "regions": sorted(regions),
        "host_manifest_sha256s": sorted(str(item.get("manifest_sha256", "")) for item in host_observations),
        "height_min": min(heights),
        "height_max": max(heights),
        "height_spread": spread,
        "observation_window_ms": observation_window,
        "same_height_app_hash_divergence": same_height_divergence,
        "checks": checks,
        "cluster_gate_satisfied": all(checks.values()),
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_cluster_observation(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, CLUSTER_OBSERVATION_FORMAT, expected_signer=expected_signer)
    return {
        "valid": True,
        "cluster_gate_satisfied": bool(manifest.get("cluster_gate_satisfied")),
        "candidate_identity_sha256": manifest["candidate_identity_sha256"],
        "height_spread": int(manifest["height_spread"]),
        "production_mainnet_ready": False,
    }


def build_genesis_attestation(
    *, signing_key_path: str | Path, source_commit: str, candidate_identity_sha256: str,
    application_genesis_sha256: str, consensus_genesis_sha256: str, chain_id: str,
    operator_id: str, validator_id: str, validator_address: str, node_id: str, approved: bool,
) -> dict[str, Any]:
    manifest = {
        "format": GENESIS_ATTESTATION_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": _valid_commit(source_commit),
        "candidate_identity_sha256": _valid_sha(candidate_identity_sha256),
        "application_genesis_sha256": _valid_sha(application_genesis_sha256),
        "consensus_genesis_sha256": _valid_sha(consensus_genesis_sha256),
        "chain_id": _clean(chain_id, "chain_id"),
        "operator_id": _clean(operator_id, "operator_id"),
        "validator_id": _clean(validator_id, "validator_id"),
        "validator_address": _clean(validator_address, "validator_address"),
        "node_id": _clean(node_id, "node_id"),
        "approved": bool(approved),
        "contains_private_key": False,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_genesis_attestation(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, GENESIS_ATTESTATION_FORMAT, expected_signer=expected_signer)
    return {"valid": True, "operator_id": manifest["operator_id"], "validator_id": manifest["validator_id"], "approved": bool(manifest.get("approved")), "production_mainnet_ready": False}


def build_genesis_ceremony_gate(*, signing_key_path: str | Path, attestations: list[dict[str, Any]]) -> dict[str, Any]:
    if len(attestations) < 4:
        raise RealExecutionV29Error("genesis ceremony requires at least four operator attestations")
    manifests = [_verify(item, GENESIS_ATTESTATION_FORMAT) for item in attestations]
    first = manifests[0]
    exact_match = all(
        m["source_commit"] == first["source_commit"]
        and m["candidate_identity_sha256"] == first["candidate_identity_sha256"]
        and m["application_genesis_sha256"] == first["application_genesis_sha256"]
        and m["consensus_genesis_sha256"] == first["consensus_genesis_sha256"]
        and m["chain_id"] == first["chain_id"]
        for m in manifests
    )
    validators = {m["validator_id"] for m in manifests}
    operators = {m["operator_id"] for m in manifests}
    signers = {item.get("signer", "") for item in attestations}
    checks = {
        "exact_genesis_and_candidate_match": exact_match,
        "minimum_four_unique_validators": len(validators) >= 4 and len(validators) == len(manifests),
        "minimum_four_unique_operators": len(operators) >= 4,
        "minimum_four_unique_signers": len(signers) >= 4 and "" not in signers,
        "all_operators_approved": all(m.get("approved") is True for m in manifests),
    }
    manifest = {
        "format": GENESIS_GATE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": first["source_commit"],
        "candidate_identity_sha256": first["candidate_identity_sha256"],
        "application_genesis_sha256": first["application_genesis_sha256"],
        "consensus_genesis_sha256": first["consensus_genesis_sha256"],
        "chain_id": first["chain_id"],
        "operator_ids": sorted(operators),
        "validator_ids": sorted(validators),
        "attestation_manifest_sha256s": sorted(str(item.get("manifest_sha256", "")) for item in attestations),
        "checks": checks,
        "genesis_ceremony_gate_satisfied": all(checks.values()),
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_genesis_ceremony_gate(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, GENESIS_GATE_FORMAT, expected_signer=expected_signer)
    return {"valid": True, "genesis_ceremony_gate_satisfied": bool(manifest.get("genesis_ceremony_gate_satisfied")), "candidate_identity_sha256": manifest["candidate_identity_sha256"], "production_mainnet_ready": False}


def build_soak_evidence(
    *, signing_key_path: str | Path, cluster_samples: list[dict[str, Any]],
    minimum_duration_seconds: int = 604_800, minimum_success_ratio: float = 0.99,
) -> dict[str, Any]:
    if len(cluster_samples) < 2:
        raise RealExecutionV29Error("soak evidence requires at least two signed cluster samples")
    minimum_duration = int(minimum_duration_seconds)
    ratio_target = float(minimum_success_ratio)
    if minimum_duration < 86_400 or not (0.99 <= ratio_target <= 1.0):
        raise RealExecutionV29Error("soak gate requires >=24h duration and success ratio >=0.99")
    manifests = [_verify(item, CLUSTER_OBSERVATION_FORMAT) for item in cluster_samples]
    manifests.sort(key=lambda m: int(m["observed_at_ms"]))
    first = manifests[0]
    identity_match = all(
        m["source_commit"] == first["source_commit"]
        and m["candidate_identity_sha256"] == first["candidate_identity_sha256"]
        and m["application_genesis_sha256"] == first["application_genesis_sha256"]
        and m["consensus_genesis_sha256"] == first["consensus_genesis_sha256"]
        and m["chain_id"] == first["chain_id"]
        for m in manifests
    )
    duration_seconds = max(0, (int(manifests[-1]["observed_at_ms"]) - int(first["observed_at_ms"])) // 1000)
    passing = sum(1 for m in manifests if m.get("cluster_gate_satisfied") is True)
    success_ratio = passing / len(manifests)
    divergence_samples = sum(1 for m in manifests if m.get("same_height_app_hash_divergence") is True)
    checks = {
        "exact_candidate_and_genesis_match": identity_match,
        "minimum_duration_met": duration_seconds >= minimum_duration,
        "success_ratio_met": success_ratio >= ratio_target,
        "no_same_height_app_hash_divergence": divergence_samples == 0,
    }
    manifest = {
        "format": SOAK_EVIDENCE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": first["source_commit"],
        "candidate_identity_sha256": first["candidate_identity_sha256"],
        "application_genesis_sha256": first["application_genesis_sha256"],
        "consensus_genesis_sha256": first["consensus_genesis_sha256"],
        "chain_id": first["chain_id"],
        "sample_count": len(manifests),
        "passing_sample_count": passing,
        "first_observed_at_ms": int(first["observed_at_ms"]),
        "last_observed_at_ms": int(manifests[-1]["observed_at_ms"]),
        "duration_seconds": duration_seconds,
        "minimum_duration_seconds": minimum_duration,
        "success_ratio": success_ratio,
        "minimum_success_ratio": ratio_target,
        "divergence_samples": divergence_samples,
        "sample_manifest_sha256s": [str(item.get("manifest_sha256", "")) for item in cluster_samples],
        "checks": checks,
        "soak_gate_satisfied": all(checks.values()),
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_soak_evidence(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, SOAK_EVIDENCE_FORMAT, expected_signer=expected_signer)
    return {"valid": True, "soak_gate_satisfied": bool(manifest.get("soak_gate_satisfied")), "duration_seconds": int(manifest["duration_seconds"]), "success_ratio": float(manifest["success_ratio"]), "production_mainnet_ready": False}


def build_fault_result(
    *, signing_key_path: str | Path, source_commit: str, candidate_identity_sha256: str,
    fault_type: str, campaign_id: str, authorized: bool, passed: bool,
    recovery_verified: bool, app_hash_reconverged: bool, no_data_loss: bool,
    raw_evidence_path: str | Path,
) -> dict[str, Any]:
    normalized = _clean(fault_type, "fault_type").lower()
    if normalized not in REQUIRED_FAULT_TYPES:
        raise RealExecutionV29Error(f"unsupported fault_type: {normalized}")
    path = Path(raw_evidence_path)
    if not path.is_file():
        raise RealExecutionV29Error(f"raw evidence file not found: {path}")
    checks = {
        "authorized": bool(authorized),
        "passed": bool(passed),
        "recovery_verified": bool(recovery_verified),
        "app_hash_reconverged": bool(app_hash_reconverged),
        "no_data_loss": bool(no_data_loss),
    }
    manifest = {
        "format": FAULT_RESULT_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": _valid_commit(source_commit),
        "candidate_identity_sha256": _valid_sha(candidate_identity_sha256),
        "fault_type": normalized,
        "campaign_id": _clean(campaign_id, "campaign_id"),
        "raw_evidence": {"name": path.name, "size": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()},
        "checks": checks,
        "fault_gate_satisfied": all(checks.values()),
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_fault_result(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, FAULT_RESULT_FORMAT, expected_signer=expected_signer)
    return {"valid": True, "fault_type": manifest["fault_type"], "fault_gate_satisfied": bool(manifest.get("fault_gate_satisfied")), "candidate_identity_sha256": manifest["candidate_identity_sha256"], "production_mainnet_ready": False}


def build_real_execution_gate(
    *, release_freeze_v28: dict[str, Any], rehearsal_gate_v28: dict[str, Any],
    cluster_observation: dict[str, Any], genesis_ceremony_gate: dict[str, Any],
    soak_evidence: dict[str, Any], fault_results: list[dict[str, Any]],
) -> dict[str, Any]:
    freeze_checked = v28.verify_release_freeze(release_freeze_v28)
    freeze_manifest = _verify(release_freeze_v28, v28.RELEASE_FREEZE_FORMAT)
    if rehearsal_gate_v28.get("format") != v28.REHEARSAL_GATE_FORMAT:
        raise RealExecutionV29Error("invalid v0.28 rehearsal gate format")
    if rehearsal_gate_v28.get("launch_rehearsal_gate_satisfied") is not True:
        raise RealExecutionV29Error("v0.28 rehearsal gate is not satisfied")
    if freeze_manifest.get("rehearsal_gate_sha256") != sha256_hex(canonical_json(rehearsal_gate_v28)):
        raise RealExecutionV29Error("v0.28 release freeze does not bind the supplied rehearsal gate")

    cluster = _verify(cluster_observation, CLUSTER_OBSERVATION_FORMAT)
    genesis = _verify(genesis_ceremony_gate, GENESIS_GATE_FORMAT)
    soak = _verify(soak_evidence, SOAK_EVIDENCE_FORMAT)
    source_commit = freeze_checked["source_commit"]
    candidate = freeze_checked["candidate_identity_sha256"]
    manifests = [cluster, genesis, soak]
    identity_match = all(m.get("source_commit") == source_commit and m.get("candidate_identity_sha256") == candidate for m in manifests)

    fault_manifests = [_verify(item, FAULT_RESULT_FORMAT) for item in fault_results]
    covered = {m["fault_type"] for m in fault_manifests if m.get("fault_gate_satisfied") is True}
    faults_match = bool(fault_manifests) and all(m.get("source_commit") == source_commit and m.get("candidate_identity_sha256") == candidate for m in fault_manifests)
    checks = {
        "v28_release_freeze_valid_and_bound": True,
        "v28_rehearsal_gate_satisfied": rehearsal_gate_v28.get("launch_rehearsal_gate_satisfied") is True,
        "v29_core_artifacts_match_candidate": identity_match,
        "live_cluster_observation_satisfied": cluster.get("cluster_gate_satisfied") is True,
        "multi_operator_genesis_ceremony_satisfied": genesis.get("genesis_ceremony_gate_satisfied") is True,
        "long_lived_soak_satisfied": soak.get("soak_gate_satisfied") is True,
        "fault_results_match_candidate": faults_match,
        "all_required_fault_campaigns_satisfied": REQUIRED_FAULT_TYPES.issubset(covered),
    }
    return {
        "format": REAL_EXECUTION_GATE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": source_commit,
        "candidate_identity_sha256": candidate,
        "v28_release_freeze_manifest_sha256": release_freeze_v28.get("manifest_sha256", ""),
        "v28_rehearsal_gate_sha256": sha256_hex(canonical_json(rehearsal_gate_v28)),
        "cluster_manifest_sha256": cluster_observation.get("manifest_sha256", ""),
        "genesis_gate_manifest_sha256": genesis_ceremony_gate.get("manifest_sha256", ""),
        "soak_manifest_sha256": soak_evidence.get("manifest_sha256", ""),
        "fault_manifest_sha256s": sorted(str(item.get("manifest_sha256", "")) for item in fault_results),
        "covered_fault_types": sorted(covered),
        "checks": checks,
        "real_execution_gate_satisfied": all(checks.values()),
        "manual_launch_decision_required": True,
        "automatic_launch": False,
        "production_mainnet_ready": False,
        "production_mainnet_launched": False,
        "production_crakbit_launched": False,
    }


def build_real_evidence_freeze(
    *, signing_key_path: str | Path, real_execution_gate: dict[str, Any],
    artifacts: Iterable[tuple[str, str | Path]] = (),
) -> dict[str, Any]:
    if real_execution_gate.get("format") != REAL_EXECUTION_GATE_FORMAT or real_execution_gate.get("real_execution_gate_satisfied") is not True:
        raise RealExecutionV29Error("real execution gate is not satisfied")
    entries = v28._artifact_entries(artifacts)
    manifest = {
        "format": REAL_EVIDENCE_FREEZE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": _valid_commit(str(real_execution_gate["source_commit"])),
        "candidate_identity_sha256": _valid_sha(str(real_execution_gate["candidate_identity_sha256"])),
        "real_execution_gate_sha256": sha256_hex(canonical_json(real_execution_gate)),
        "artifacts": entries,
        "frozen_from_real_execution_evidence": True,
        "manual_launch_decision_required": True,
        "automatic_launch": False,
        "production_mainnet_ready": False,
        "production_mainnet_launched": False,
        "production_crakbit_launched": False,
    }
    return _sign(signing_key_path, manifest)


def verify_real_evidence_freeze(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, REAL_EVIDENCE_FREEZE_FORMAT, expected_signer=expected_signer)
    if manifest.get("frozen_from_real_execution_evidence") is not True or manifest.get("automatic_launch") is not False:
        raise RealExecutionV29Error("invalid real-evidence freeze claims")
    return {"valid": True, "candidate_identity_sha256": manifest["candidate_identity_sha256"], "source_commit": manifest["source_commit"], "production_mainnet_ready": False, "production_mainnet_launched": False}
