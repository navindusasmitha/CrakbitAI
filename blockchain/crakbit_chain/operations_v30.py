from __future__ import annotations

import hashlib
import json
import socket
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import httpx

from .crypto import canonical_json, sha256_hex
from . import real_execution_v29 as v29

MONITOR_INVENTORY_FORMAT = "crakbit-v30-monitor-inventory/1"
MONITOR_SAMPLE_FORMAT = "crakbit-v30-monitor-sample/1"
MONITOR_CHECKPOINT_FORMAT = "crakbit-v30-monitor-checkpoint/1"
ARCHIVE_MANIFEST_FORMAT = "crakbit-v30-archive-manifest/1"
EDGE_HEALTH_FORMAT = "crakbit-v30-edge-health/1"
EDGE_GATE_FORMAT = "crakbit-v30-edge-redundancy-gate/1"
SIGNER_MONITOR_FORMAT = "crakbit-v30-signer-monitor/1"
PUBLIC_EVIDENCE_BUNDLE_FORMAT = "crakbit-v30-public-evidence-bundle/1"
OPERATOR_CHECKLIST_FORMAT = "crakbit-v30-operator-checklist/1"

_SECRET_KEYS = {
    "private_key", "privatekey", "seed", "mnemonic", "password", "passwd",
    "secret", "token", "api_key", "apikey", "bearer", "credential", "credentials",
}
_EDGE_ROLES = {"rpc", "explorer", "gateway"}
_CUSTODY_TYPES = {"hsm", "remote-signer", "hardware-backed", "equivalent-protected"}


class OperationsV30Error(ValueError):
    pass


def load_json(path: str | Path) -> dict[str, Any]:
    return v29.load_json(path)


def save_json(body: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    return v29.save_json(body, path, overwrite=overwrite)


def _valid_commit(value: str) -> str:
    try:
        return v29._valid_commit(value)
    except Exception as exc:
        raise OperationsV30Error(str(exc)) from exc


def _valid_sha(value: str) -> str:
    try:
        return v29._valid_sha(value)
    except Exception as exc:
        raise OperationsV30Error(str(exc)) from exc


def _sign(key: str | Path, manifest: dict[str, Any]) -> dict[str, Any]:
    return v29._sign(key, manifest)


def _verify(envelope: dict[str, Any], expected_format: str, *, expected_signer: str | None = None) -> dict[str, Any]:
    try:
        return v29._verify(envelope, expected_format, expected_signer=expected_signer)
    except Exception as exc:
        raise OperationsV30Error(str(exc)) from exc


def _clean(value: Any, label: str) -> str:
    result = str(value).strip()
    if not result:
        raise OperationsV30Error(f"{label} is required")
    return result


def _contains_secret_fields(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _SECRET_KEYS:
                return True
            if _contains_secret_fields(item):
                return True
    elif isinstance(value, list):
        return any(_contains_secret_fields(item) for item in value)
    return False


def _safe_http_endpoint(value: str, label: str = "endpoint") -> str:
    endpoint = _clean(value, label).rstrip("/")
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise OperationsV30Error(f"{label} must be http(s) with a hostname")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise OperationsV30Error(f"{label} may not contain credentials, query or fragment")
    return endpoint


def _artifact_entries(artifacts: Iterable[tuple[str, str | Path]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    roles: set[str] = set()
    names: set[str] = set()
    for role, raw_path in artifacts:
        normalized_role = str(role).strip().lower()
        if not normalized_role or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for ch in normalized_role):
            raise OperationsV30Error(f"invalid artifact role: {role}")
        if normalized_role in roles:
            raise OperationsV30Error(f"duplicate artifact role: {normalized_role}")
        path = Path(raw_path)
        if not path.is_file():
            raise OperationsV30Error(f"artifact not found: {path}")
        if path.name in names:
            raise OperationsV30Error(f"duplicate artifact file name: {path.name}")
        roles.add(normalized_role)
        names.add(path.name)
        entries.append({
            "role": normalized_role,
            "name": path.name,
            "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    return sorted(entries, key=lambda item: (item["role"], item["name"]))


def build_monitor_inventory(
    *, signing_key_path: str | Path, source_commit: str, candidate_identity_sha256: str,
    application_genesis_sha256: str, consensus_genesis_sha256: str, chain_id: str,
    hosts: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(hosts) < 4:
        raise OperationsV30Error("monitor inventory requires at least four validators")
    if _contains_secret_fields(hosts):
        raise OperationsV30Error("monitor inventory may not contain secret-bearing fields")

    normalized: list[dict[str, str]] = []
    validators: set[str] = set()
    operators: set[str] = set()
    providers: set[str] = set()
    regions: set[str] = set()
    endpoints: set[str] = set()
    for raw in hosts:
        validator_id = _clean(raw.get("validator_id", ""), "validator_id")
        operator_id = _clean(raw.get("operator_id", ""), "operator_id")
        provider = _clean(raw.get("provider", ""), "provider")
        region = _clean(raw.get("region", ""), "region")
        rpc_endpoint = _safe_http_endpoint(str(raw.get("rpc_endpoint", "")), "rpc_endpoint")
        node_name = _clean(raw.get("node_name", validator_id), "node_name")
        if validator_id in validators:
            raise OperationsV30Error(f"duplicate validator_id: {validator_id}")
        if rpc_endpoint in endpoints:
            raise OperationsV30Error(f"duplicate rpc_endpoint: {rpc_endpoint}")
        validators.add(validator_id)
        operators.add(operator_id)
        providers.add(provider)
        regions.add(region)
        endpoints.add(rpc_endpoint)
        normalized.append({
            "validator_id": validator_id,
            "operator_id": operator_id,
            "provider": provider,
            "region": region,
            "node_name": node_name,
            "rpc_endpoint": rpc_endpoint,
        })
    checks = {
        "minimum_four_unique_validators": len(validators) >= 4,
        "minimum_four_unique_operators": len(operators) >= 4,
        "provider_diversity": len(providers) >= 2,
        "region_diversity": len(regions) >= 2,
        "no_duplicate_rpc_endpoints": len(endpoints) == len(normalized),
        "contains_no_secret_fields": True,
    }
    manifest = {
        "format": MONITOR_INVENTORY_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": _valid_commit(source_commit),
        "candidate_identity_sha256": _valid_sha(candidate_identity_sha256),
        "application_genesis_sha256": _valid_sha(application_genesis_sha256),
        "consensus_genesis_sha256": _valid_sha(consensus_genesis_sha256),
        "chain_id": _clean(chain_id, "chain_id"),
        "hosts": sorted(normalized, key=lambda item: item["validator_id"]),
        "checks": checks,
        "inventory_gate_satisfied": all(checks.values()),
        "central_monitoring_only": True,
        "does_not_replace_operator_attestations": True,
        "contains_private_keys": False,
        "contains_provider_secrets": False,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_monitor_inventory(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, MONITOR_INVENTORY_FORMAT, expected_signer=expected_signer)
    if _contains_secret_fields(manifest.get("hosts", [])):
        raise OperationsV30Error("signed monitor inventory contains secret-bearing fields")
    return {
        "valid": True,
        "inventory_gate_satisfied": bool(manifest.get("inventory_gate_satisfied")),
        "host_count": len(manifest.get("hosts", [])),
        "candidate_identity_sha256": manifest["candidate_identity_sha256"],
        "production_mainnet_ready": False,
    }


def build_monitor_sample_from_measurements(
    *, signing_key_path: str | Path, inventory: dict[str, Any], measurements: list[dict[str, Any]],
    observed_at_ms: int | None = None, maximum_height_spread: int = 2,
) -> dict[str, Any]:
    inventory_manifest = _verify(inventory, MONITOR_INVENTORY_FORMAT)
    if inventory_manifest.get("inventory_gate_satisfied") is not True:
        raise OperationsV30Error("monitor inventory gate is not satisfied")
    if len(measurements) != len(inventory_manifest["hosts"]):
        raise OperationsV30Error("measurement count must match inventory host count")

    by_validator = {str(item.get("validator_id", "")): item for item in measurements}
    if len(by_validator) != len(measurements):
        raise OperationsV30Error("measurements require unique validator_id values")
    rows: list[dict[str, Any]] = []
    heights: list[int] = []
    hashes_by_height: dict[int, set[str]] = {}
    all_host_checks = True
    for host in inventory_manifest["hosts"]:
        validator_id = host["validator_id"]
        if validator_id not in by_validator:
            raise OperationsV30Error(f"missing measurement for {validator_id}")
        measurement = by_validator[validator_id]
        latest_height = int(measurement.get("latest_height", 0))
        abci_height = int(measurement.get("abci_height", 0))
        app_hash = _clean(measurement.get("app_hash", ""), "app_hash").lower()
        chain_id = _clean(measurement.get("chain_id", ""), "chain_id")
        node_id = _clean(measurement.get("node_id", ""), "node_id")
        catching_up = bool(measurement.get("catching_up", False))
        host_ok = (
            chain_id == inventory_manifest["chain_id"]
            and latest_height > 0
            and abci_height > 0
            and abs(latest_height - abci_height) <= 1
            and not catching_up
        )
        all_host_checks = all_host_checks and host_ok
        heights.append(latest_height)
        hashes_by_height.setdefault(abci_height, set()).add(app_hash)
        rows.append({
            "validator_id": validator_id,
            "operator_id": host["operator_id"],
            "provider": host["provider"],
            "region": host["region"],
            "node_id": node_id,
            "latest_height": latest_height,
            "abci_height": abci_height,
            "app_hash": app_hash,
            "catching_up": catching_up,
            "host_ok": host_ok,
        })
    spread = max(heights) - min(heights)
    divergence = any(len(values) > 1 for values in hashes_by_height.values())
    checks = {
        "all_hosts_healthy": all_host_checks,
        "height_spread_within_limit": spread <= int(maximum_height_spread),
        "no_same_height_app_hash_divergence": not divergence,
    }
    manifest = {
        "format": MONITOR_SAMPLE_FORMAT,
        "observed_at_ms": int(time.time() * 1000) if observed_at_ms is None else int(observed_at_ms),
        "source_commit": inventory_manifest["source_commit"],
        "candidate_identity_sha256": inventory_manifest["candidate_identity_sha256"],
        "application_genesis_sha256": inventory_manifest["application_genesis_sha256"],
        "consensus_genesis_sha256": inventory_manifest["consensus_genesis_sha256"],
        "chain_id": inventory_manifest["chain_id"],
        "inventory_manifest_sha256": inventory.get("manifest_sha256", ""),
        "measurements": sorted(rows, key=lambda item: item["validator_id"]),
        "height_min": min(heights),
        "height_max": max(heights),
        "height_spread": spread,
        "same_height_app_hash_divergence": divergence,
        "checks": checks,
        "sample_gate_satisfied": all(checks.values()),
        "read_only_probe": True,
        "central_monitoring_sample": True,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def probe_monitor_sample(
    *, signing_key_path: str | Path, inventory: dict[str, Any], timeout_seconds: float = 5.0,
    maximum_height_spread: int = 2,
) -> dict[str, Any]:
    inventory_manifest = _verify(inventory, MONITOR_INVENTORY_FORMAT)
    measurements: list[dict[str, Any]] = []
    for host in inventory_manifest.get("hosts", []):
        measurement = v29.probe_cometbft_rpc(host["rpc_endpoint"], timeout_seconds=timeout_seconds)
        measurements.append({"validator_id": host["validator_id"], **measurement})
    return build_monitor_sample_from_measurements(
        signing_key_path=signing_key_path,
        inventory=inventory,
        measurements=measurements,
        maximum_height_spread=maximum_height_spread,
    )


def verify_monitor_sample(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, MONITOR_SAMPLE_FORMAT, expected_signer=expected_signer)
    return {
        "valid": True,
        "sample_gate_satisfied": bool(manifest.get("sample_gate_satisfied")),
        "observed_at_ms": int(manifest["observed_at_ms"]),
        "height_spread": int(manifest["height_spread"]),
        "candidate_identity_sha256": manifest["candidate_identity_sha256"],
        "production_mainnet_ready": False,
    }


def build_monitor_checkpoint(
    *, signing_key_path: str | Path, session_id: str, samples: list[dict[str, Any]],
    target_duration_seconds: int = 604800, minimum_success_ratio: float = 0.99,
    previous_checkpoint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not samples:
        raise OperationsV30Error("checkpoint requires at least one new monitor sample")
    target = int(target_duration_seconds)
    ratio_target = float(minimum_success_ratio)
    if target < 86400:
        raise OperationsV30Error("target_duration_seconds must be at least 86400")
    if ratio_target < 0.99 or ratio_target > 1.0:
        raise OperationsV30Error("minimum_success_ratio must be between 0.99 and 1.0")

    manifests = [_verify(item, MONITOR_SAMPLE_FORMAT) for item in samples]
    first_new = manifests[0]
    identity_fields = (
        "source_commit", "candidate_identity_sha256", "application_genesis_sha256",
        "consensus_genesis_sha256", "chain_id", "inventory_manifest_sha256",
    )
    if not all(all(m[field] == first_new[field] for field in identity_fields) for m in manifests):
        raise OperationsV30Error("monitor samples do not share the same candidate/inventory identity")
    times = [int(m["observed_at_ms"]) for m in manifests]
    if times != sorted(times) or len(set(times)) != len(times):
        raise OperationsV30Error("new monitor samples must have unique increasing timestamps")

    previous_count = 0
    previous_success = 0
    first_observed = times[0]
    previous_head = "0" * 64
    previous_manifest_sha = ""
    last_previous_observed = -1
    if previous_checkpoint is not None:
        previous = _verify(previous_checkpoint, MONITOR_CHECKPOINT_FORMAT)
        if previous["session_id"] != _clean(session_id, "session_id"):
            raise OperationsV30Error("previous checkpoint belongs to a different session")
        for field in identity_fields:
            if previous[field] != first_new[field]:
                raise OperationsV30Error("previous checkpoint identity does not match new samples")
        previous_count = int(previous["sample_count"])
        previous_success = int(previous["successful_sample_count"])
        first_observed = int(previous["first_observed_at_ms"])
        previous_head = _valid_sha(previous["hash_chain_head"])
        previous_manifest_sha = str(previous_checkpoint.get("manifest_sha256", ""))
        last_previous_observed = int(previous["last_observed_at_ms"])
        if times[0] <= last_previous_observed:
            raise OperationsV30Error("new samples must be newer than the previous checkpoint")
        if int(previous["target_duration_seconds"]) != target or float(previous["minimum_success_ratio"]) != ratio_target:
            raise OperationsV30Error("checkpoint target parameters may not change during a session")

    head = previous_head
    new_hashes: list[str] = []
    for envelope in samples:
        sample_hash = _valid_sha(str(envelope.get("manifest_sha256", "")))
        new_hashes.append(sample_hash)
        head = hashlib.sha256((head + sample_hash).encode("ascii")).hexdigest()

    successful_new = sum(1 for m in manifests if m.get("sample_gate_satisfied") is True)
    sample_count = previous_count + len(manifests)
    successful_count = previous_success + successful_new
    last_observed = times[-1]
    duration_seconds = max(0.0, (last_observed - first_observed) / 1000.0)
    success_ratio = successful_count / sample_count
    complete = duration_seconds >= target and success_ratio >= ratio_target
    manifest = {
        "format": MONITOR_CHECKPOINT_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "session_id": _clean(session_id, "session_id"),
        "source_commit": first_new["source_commit"],
        "candidate_identity_sha256": first_new["candidate_identity_sha256"],
        "application_genesis_sha256": first_new["application_genesis_sha256"],
        "consensus_genesis_sha256": first_new["consensus_genesis_sha256"],
        "chain_id": first_new["chain_id"],
        "inventory_manifest_sha256": first_new["inventory_manifest_sha256"],
        "previous_checkpoint_manifest_sha256": previous_manifest_sha,
        "new_sample_manifest_sha256s": new_hashes,
        "sample_count": sample_count,
        "successful_sample_count": successful_count,
        "first_observed_at_ms": first_observed,
        "last_observed_at_ms": last_observed,
        "duration_seconds": duration_seconds,
        "minimum_success_ratio": ratio_target,
        "success_ratio": success_ratio,
        "target_duration_seconds": target,
        "hash_chain_head": head,
        "checkpoint_complete": complete,
        "resumable": True,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_monitor_checkpoint(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, MONITOR_CHECKPOINT_FORMAT, expected_signer=expected_signer)
    return {
        "valid": True,
        "session_id": manifest["session_id"],
        "sample_count": int(manifest["sample_count"]),
        "duration_seconds": float(manifest["duration_seconds"]),
        "success_ratio": float(manifest["success_ratio"]),
        "checkpoint_complete": bool(manifest.get("checkpoint_complete")),
        "hash_chain_head": manifest["hash_chain_head"],
        "production_mainnet_ready": False,
    }


def build_archive_manifest(
    *, signing_key_path: str | Path, source_commit: str, candidate_identity_sha256: str,
    artifacts: Iterable[tuple[str, str | Path]], retention_days: int = 90,
) -> dict[str, Any]:
    retention = int(retention_days)
    if retention < 30:
        raise OperationsV30Error("evidence retention must be at least 30 days")
    entries = _artifact_entries(artifacts)
    if not entries:
        raise OperationsV30Error("archive manifest requires at least one artifact")
    manifest = {
        "format": ARCHIVE_MANIFEST_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": _valid_commit(source_commit),
        "candidate_identity_sha256": _valid_sha(candidate_identity_sha256),
        "artifacts": entries,
        "artifact_count": len(entries),
        "total_bytes": sum(int(item["size"]) for item in entries),
        "retention_days": retention,
        "raw_evidence_hashes_published": True,
        "contains_private_keys": False,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_archive_manifest(
    envelope: dict[str, Any], *, expected_signer: str | None = None, artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    manifest = _verify(envelope, ARCHIVE_MANIFEST_FORMAT, expected_signer=expected_signer)
    verified_files = 0
    if artifact_dir is not None:
        root = Path(artifact_dir)
        for item in manifest.get("artifacts", []):
            path = root / item["name"]
            if not path.is_file():
                raise OperationsV30Error(f"archive artifact missing: {path}")
            data = path.read_bytes()
            if len(data) != int(item["size"]) or hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise OperationsV30Error(f"archive artifact mismatch: {path.name}")
            verified_files += 1
    return {
        "valid": True,
        "artifact_count": int(manifest["artifact_count"]),
        "verified_files": verified_files,
        "retention_days": int(manifest["retention_days"]),
        "production_mainnet_ready": False,
    }


def probe_http_health(url: str, *, timeout_seconds: float = 5.0) -> dict[str, Any]:
    endpoint = _safe_http_endpoint(url, "edge_url")
    timeout = float(timeout_seconds)
    if timeout <= 0 or timeout > 30:
        raise OperationsV30Error("timeout_seconds must be >0 and <=30")
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            response = client.get(endpoint)
        latency_ms = (time.perf_counter() - started) * 1000.0
        return {"status_code": int(response.status_code), "latency_ms": latency_ms, "reachable": True}
    except Exception:
        latency_ms = (time.perf_counter() - started) * 1000.0
        return {"status_code": 0, "latency_ms": latency_ms, "reachable": False}


def build_edge_health_record(
    *, signing_key_path: str | Path, source_commit: str, candidate_identity_sha256: str,
    edge_id: str, role: str, url: str, measurement: dict[str, Any], max_latency_ms: float = 2000.0,
    observed_at_ms: int | None = None,
) -> dict[str, Any]:
    normalized_role = str(role).strip().lower()
    if normalized_role not in _EDGE_ROLES:
        raise OperationsV30Error(f"edge role must be one of {sorted(_EDGE_ROLES)}")
    latency = float(measurement.get("latency_ms", -1))
    status_code = int(measurement.get("status_code", 0))
    reachable = bool(measurement.get("reachable", False))
    limit = float(max_latency_ms)
    if latency < 0 or limit <= 0:
        raise OperationsV30Error("latency values must be non-negative and limit must be positive")
    checks = {
        "reachable": reachable,
        "http_status_2xx": 200 <= status_code < 300,
        "latency_within_limit": latency <= limit,
    }
    manifest = {
        "format": EDGE_HEALTH_FORMAT,
        "observed_at_ms": int(time.time() * 1000) if observed_at_ms is None else int(observed_at_ms),
        "source_commit": _valid_commit(source_commit),
        "candidate_identity_sha256": _valid_sha(candidate_identity_sha256),
        "edge_id": _clean(edge_id, "edge_id"),
        "role": normalized_role,
        "url": _safe_http_endpoint(url, "edge_url"),
        "measurement": {"status_code": status_code, "latency_ms": latency, "reachable": reachable},
        "max_latency_ms": limit,
        "checks": checks,
        "edge_gate_satisfied": all(checks.values()),
        "read_only_probe": True,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def probe_and_build_edge_health_record(**kwargs: Any) -> dict[str, Any]:
    url = kwargs["url"]
    timeout = float(kwargs.pop("timeout_seconds", 5.0))
    measurement = probe_http_health(url, timeout_seconds=timeout)
    return build_edge_health_record(measurement=measurement, **kwargs)


def verify_edge_health_record(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, EDGE_HEALTH_FORMAT, expected_signer=expected_signer)
    return {
        "valid": True,
        "edge_id": manifest["edge_id"],
        "role": manifest["role"],
        "edge_gate_satisfied": bool(manifest.get("edge_gate_satisfied")),
        "production_mainnet_ready": False,
    }


def build_edge_redundancy_gate(
    *, signing_key_path: str | Path, records: list[dict[str, Any]], minimum_per_role: int = 2,
) -> dict[str, Any]:
    minimum = int(minimum_per_role)
    if minimum < 2:
        raise OperationsV30Error("minimum_per_role must be at least 2")
    if not records:
        raise OperationsV30Error("edge redundancy gate requires records")
    manifests = [_verify(item, EDGE_HEALTH_FORMAT) for item in records]
    source = manifests[0]["source_commit"]
    candidate = manifests[0]["candidate_identity_sha256"]
    if not all(m["source_commit"] == source and m["candidate_identity_sha256"] == candidate for m in manifests):
        raise OperationsV30Error("edge records do not match the same candidate")
    role_ids: dict[str, set[str]] = {role: set() for role in _EDGE_ROLES}
    for manifest in manifests:
        if manifest.get("edge_gate_satisfied") is True:
            role_ids[manifest["role"]].add(manifest["edge_id"])
    checks = {f"minimum_{role}_edges": len(role_ids[role]) >= minimum for role in sorted(_EDGE_ROLES)}
    manifest = {
        "format": EDGE_GATE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": source,
        "candidate_identity_sha256": candidate,
        "minimum_per_role": minimum,
        "passing_edge_ids_by_role": {role: sorted(values) for role, values in sorted(role_ids.items())},
        "record_manifest_sha256s": sorted(str(item.get("manifest_sha256", "")) for item in records),
        "checks": checks,
        "edge_redundancy_gate_satisfied": all(checks.values()),
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_edge_redundancy_gate(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, EDGE_GATE_FORMAT, expected_signer=expected_signer)
    return {
        "valid": True,
        "edge_redundancy_gate_satisfied": bool(manifest.get("edge_redundancy_gate_satisfied")),
        "passing_edge_ids_by_role": manifest.get("passing_edge_ids_by_role", {}),
        "production_mainnet_ready": False,
    }


def probe_signer_tcp(host: str, port: int, *, timeout_seconds: float = 3.0) -> bool:
    hostname = _clean(host, "host")
    port_number = int(port)
    timeout = float(timeout_seconds)
    if not (1 <= port_number <= 65535) or timeout <= 0 or timeout > 10:
        raise OperationsV30Error("invalid signer host/port/timeout")
    try:
        with socket.create_connection((hostname, port_number), timeout=timeout):
            return True
    except OSError:
        return False


def build_signer_monitor_record(
    *, signing_key_path: str | Path, source_commit: str, candidate_identity_sha256: str,
    signer_id: str, custody_type: str, host: str, port: int, reachable: bool,
    rotation_drill_manifest_sha256: str, no_private_key_read: bool = True,
) -> dict[str, Any]:
    custody = str(custody_type).strip().lower()
    if custody not in _CUSTODY_TYPES:
        raise OperationsV30Error(f"custody_type must be one of {sorted(_CUSTODY_TYPES)}")
    port_number = int(port)
    if not 1 <= port_number <= 65535:
        raise OperationsV30Error("signer port must be between 1 and 65535")
    checks = {
        "connectivity_verified": bool(reachable),
        "protected_custody_type": True,
        "private_key_not_read": bool(no_private_key_read),
        "rotation_drill_bound": bool(rotation_drill_manifest_sha256),
    }
    manifest = {
        "format": SIGNER_MONITOR_FORMAT,
        "observed_at_ms": int(time.time() * 1000),
        "source_commit": _valid_commit(source_commit),
        "candidate_identity_sha256": _valid_sha(candidate_identity_sha256),
        "signer_id": _clean(signer_id, "signer_id"),
        "custody_type": custody,
        "host": _clean(host, "host"),
        "port": port_number,
        "rotation_drill_manifest_sha256": _valid_sha(rotation_drill_manifest_sha256),
        "checks": checks,
        "signer_monitor_gate_satisfied": all(checks.values()),
        "private_key_read_attempted": False,
        "contains_private_key": False,
        "production_mainnet_ready": False,
    }
    return _sign(signing_key_path, manifest)


def verify_signer_monitor_record(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, SIGNER_MONITOR_FORMAT, expected_signer=expected_signer)
    return {
        "valid": True,
        "signer_id": manifest["signer_id"],
        "signer_monitor_gate_satisfied": bool(manifest.get("signer_monitor_gate_satisfied")),
        "production_mainnet_ready": False,
    }


def build_public_evidence_bundle(
    *, signing_key_path: str | Path, real_freeze_v29: dict[str, Any], monitor_checkpoint: dict[str, Any],
    archive_manifest: dict[str, Any], edge_gate: dict[str, Any], signer_records: list[dict[str, Any]],
    artifacts: Iterable[tuple[str, str | Path]] = (),
) -> dict[str, Any]:
    frozen = v29.verify_real_evidence_freeze(real_freeze_v29)
    checkpoint = _verify(monitor_checkpoint, MONITOR_CHECKPOINT_FORMAT)
    archive = _verify(archive_manifest, ARCHIVE_MANIFEST_FORMAT)
    edges = _verify(edge_gate, EDGE_GATE_FORMAT)
    signers = [_verify(record, SIGNER_MONITOR_FORMAT) for record in signer_records]
    source = frozen["source_commit"]
    candidate = frozen["candidate_identity_sha256"]
    identity_match = (
        checkpoint["source_commit"] == source
        and archive["source_commit"] == source
        and edges["source_commit"] == source
        and checkpoint["candidate_identity_sha256"] == candidate
        and archive["candidate_identity_sha256"] == candidate
        and edges["candidate_identity_sha256"] == candidate
        and all(m["source_commit"] == source and m["candidate_identity_sha256"] == candidate for m in signers)
    )
    checks = {
        "v29_real_freeze_valid": True,
        "all_v30_artifacts_match_candidate": identity_match,
        "seven_day_monitor_checkpoint_complete": bool(checkpoint.get("checkpoint_complete")) and float(checkpoint.get("duration_seconds", 0)) >= 604800,
        "monitor_success_ratio_at_least_099": float(checkpoint.get("success_ratio", 0)) >= 0.99,
        "archive_retention_at_least_30_days": int(archive.get("retention_days", 0)) >= 30,
        "edge_redundancy_gate_satisfied": edges.get("edge_redundancy_gate_satisfied") is True,
        "protected_signer_monitors_present": len(signers) >= 1 and all(m.get("signer_monitor_gate_satisfied") is True for m in signers),
    }
    manifest = {
        "format": PUBLIC_EVIDENCE_BUNDLE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": source,
        "candidate_identity_sha256": candidate,
        "v29_real_freeze_manifest_sha256": str(real_freeze_v29.get("manifest_sha256", "")),
        "monitor_checkpoint_manifest_sha256": str(monitor_checkpoint.get("manifest_sha256", "")),
        "archive_manifest_sha256": str(archive_manifest.get("manifest_sha256", "")),
        "edge_gate_manifest_sha256": str(edge_gate.get("manifest_sha256", "")),
        "signer_monitor_manifest_sha256s": sorted(str(item.get("manifest_sha256", "")) for item in signer_records),
        "artifacts": _artifact_entries(artifacts),
        "checks": checks,
        "public_evidence_bundle_gate_satisfied": all(checks.values()),
        "publication_contains_hashes_not_secrets": True,
        "manual_launch_decision_required": True,
        "automatic_launch": False,
        "production_mainnet_ready": False,
        "production_mainnet_launched": False,
        "production_crkbit_launched": False,
    }
    return _sign(signing_key_path, manifest)


def verify_public_evidence_bundle(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, PUBLIC_EVIDENCE_BUNDLE_FORMAT, expected_signer=expected_signer)
    if manifest.get("automatic_launch") is not False:
        raise OperationsV30Error("public evidence bundle may not authorize automatic launch")
    return {
        "valid": True,
        "public_evidence_bundle_gate_satisfied": bool(manifest.get("public_evidence_bundle_gate_satisfied")),
        "candidate_identity_sha256": manifest["candidate_identity_sha256"],
        "production_mainnet_ready": False,
        "production_mainnet_launched": False,
    }


def build_operator_checklist(
    *, signing_key_path: str | Path, public_evidence_bundle: dict[str, Any], operator_id: str,
    checks: dict[str, bool], notes: str = "",
) -> dict[str, Any]:
    bundle = _verify(public_evidence_bundle, PUBLIC_EVIDENCE_BUNDLE_FORMAT)
    required = {
        "validator_services_verified", "backups_verified", "alerts_verified", "rollback_path_verified",
        "incident_contacts_verified", "dns_change_requires_manual_action", "treasury_move_requires_manual_action",
        "launch_requires_manual_approval",
    }
    normalized = {str(key): bool(value) for key, value in checks.items()}
    missing = sorted(required - set(normalized))
    if missing:
        raise OperationsV30Error(f"operator checklist missing required checks: {', '.join(missing)}")
    checklist_complete = all(normalized[key] for key in required)
    manifest = {
        "format": OPERATOR_CHECKLIST_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "operator_id": _clean(operator_id, "operator_id"),
        "source_commit": bundle["source_commit"],
        "candidate_identity_sha256": bundle["candidate_identity_sha256"],
        "public_evidence_bundle_manifest_sha256": str(public_evidence_bundle.get("manifest_sha256", "")),
        "checks": normalized,
        "notes": str(notes).strip(),
        "operator_checklist_complete": checklist_complete,
        "manual_launch_decision_required": True,
        "automatic_launch": False,
        "production_mainnet_ready": False,
        "production_mainnet_launched": False,
        "production_crkbit_launched": False,
    }
    return _sign(signing_key_path, manifest)


def verify_operator_checklist(envelope: dict[str, Any], *, expected_signer: str | None = None) -> dict[str, Any]:
    manifest = _verify(envelope, OPERATOR_CHECKLIST_FORMAT, expected_signer=expected_signer)
    return {
        "valid": True,
        "operator_id": manifest["operator_id"],
        "operator_checklist_complete": bool(manifest.get("operator_checklist_complete")),
        "production_mainnet_ready": False,
        "production_mainnet_launched": False,
    }
