from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable

import httpx

from .crypto import KeyPair, address_from_public_key, canonical_json, sha256_hex, verify_signature


PREFLIGHT_FORMAT = "crakbit-v24-host-preflight/1"
FAULT_PLAN_FORMAT = "crakbit-v24-fault-plan/1"
FAULT_RESULT_FORMAT = "crakbit-v24-fault-result/1"
RECOVERY_FORMAT = "crakbit-v24-recovery-record/1"
SIGNER_FORMAT = "crakbit-v24-remote-signer-record/1"
REDUNDANCY_FORMAT = "crakbit-v24-redundancy-report/1"
READINESS_FORMAT = "crakbit-v24-operational-readiness/1"
EVIDENCE_FORMAT = "crakbit-v24-operations-evidence/1"

FAULT_KINDS = {
    "restart",
    "process-kill",
    "partition",
    "latency",
    "packet-loss",
    "load",
    "storage",
}
RECOVERY_KINDS = {"backup-restore", "clean-host-state-sync"}
MIN_SOAK_SECONDS = {
    "24h": 24 * 3600,
    "72h": 72 * 3600,
    "7d": 7 * 24 * 3600,
}


class OperationsV24Error(ValueError):
    pass


def _read_json(path: str | Path) -> dict[str, Any]:
    try:
        body = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OperationsV24Error(f"invalid JSON artifact: {path}") from exc
    if not isinstance(body, dict):
        raise OperationsV24Error(f"JSON root must be an object: {path}")
    return body


def save_json(body: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise OperationsV24Error(f"output already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _file_sha256(path: str | Path) -> str:
    target = Path(path)
    if not target.is_file():
        raise OperationsV24Error(f"file not found: {target}")
    digest = __import__("hashlib").sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_commit(value: str) -> str:
    commit = str(value).strip().lower()
    if len(commit) not in {40, 64} or any(ch not in "0123456789abcdef" for ch in commit):
        raise OperationsV24Error("source_commit must be an exact hexadecimal Git commit SHA")
    return commit


def _loopback_bind(value: str) -> bool:
    raw = str(value).strip().lower()
    return raw.startswith(("127.0.0.1:", "localhost:", "[::1]:", "tcp://127.0.0.1:", "tcp://localhost:", "tcp://[::1]:", "http://127.0.0.1:", "http://localhost:"))


def evaluate_host_preflight(
    *,
    node_name: str,
    package_version: str,
    expected_package_version: str,
    cometbft_version: str,
    expected_cometbft_version: str,
    application_genesis_sha256: str,
    expected_application_genesis_sha256: str,
    consensus_genesis_sha256: str,
    expected_consensus_genesis_sha256: str,
    execution_bind: str,
    abci_bind: str,
    execution_token_present: bool,
    data_dir_writable: bool,
    free_bytes: int,
    minimum_free_bytes: int = 5 * 1024 * 1024 * 1024,
) -> dict[str, Any]:
    checks = {
        "package_version_matches": str(package_version) == str(expected_package_version),
        "cometbft_version_matches": str(cometbft_version).strip() == str(expected_cometbft_version).strip(),
        "application_genesis_hash_matches": str(application_genesis_sha256).lower() == str(expected_application_genesis_sha256).lower(),
        "consensus_genesis_hash_matches": str(consensus_genesis_sha256).lower() == str(expected_consensus_genesis_sha256).lower(),
        "execution_bind_is_loopback": _loopback_bind(execution_bind),
        "abci_bind_is_loopback": _loopback_bind(abci_bind),
        "execution_token_present": bool(execution_token_present),
        "data_directory_writable": bool(data_dir_writable),
        "minimum_free_space_available": int(free_bytes) >= int(minimum_free_bytes),
    }
    return {
        "format": PREFLIGHT_FORMAT,
        "node_name": str(node_name),
        "checked_at_ms": int(time.time() * 1000),
        "checks": checks,
        "ready_to_start": all(checks.values()),
        "free_bytes": int(free_bytes),
        "minimum_free_bytes": int(minimum_free_bytes),
        "secrets_included": False,
        "production_mainnet_ready": False,
    }


def run_host_preflight(
    *,
    node_name: str,
    application_genesis: str | Path,
    expected_application_genesis_sha256: str,
    consensus_genesis: str | Path,
    expected_consensus_genesis_sha256: str,
    data_dir: str | Path,
    token_file: str | Path,
    execution_bind: str,
    abci_bind: str,
    package_version: str,
    expected_package_version: str,
    cometbft_binary: str,
    expected_cometbft_version: str,
    minimum_free_bytes: int = 5 * 1024 * 1024 * 1024,
) -> dict[str, Any]:
    binary = shutil.which(cometbft_binary) or (str(cometbft_binary) if Path(cometbft_binary).is_file() else None)
    comet_version = ""
    if binary:
        try:
            completed = subprocess.run(
                [str(binary), "version"],
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                shell=False,
            )
            comet_version = (completed.stdout or completed.stderr).strip().splitlines()[0].strip()
        except Exception:  # noqa: BLE001
            comet_version = ""

    data = Path(data_dir)
    data.mkdir(parents=True, exist_ok=True)
    writable = os.access(data, os.W_OK)
    try:
        free_bytes = shutil.disk_usage(data).free
    except OSError:
        free_bytes = 0
    return evaluate_host_preflight(
        node_name=node_name,
        package_version=package_version,
        expected_package_version=expected_package_version,
        cometbft_version=comet_version,
        expected_cometbft_version=expected_cometbft_version,
        application_genesis_sha256=_file_sha256(application_genesis),
        expected_application_genesis_sha256=expected_application_genesis_sha256,
        consensus_genesis_sha256=_file_sha256(consensus_genesis),
        expected_consensus_genesis_sha256=expected_consensus_genesis_sha256,
        execution_bind=execution_bind,
        abci_bind=abci_bind,
        execution_token_present=Path(token_file).is_file(),
        data_dir_writable=writable,
        free_bytes=free_bytes,
        minimum_free_bytes=minimum_free_bytes,
    )


def build_fault_plan(*, name: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    if not steps:
        raise OperationsV24Error("fault plan requires at least one step")
    normalized: list[dict[str, Any]] = []
    names: set[str] = set()
    for index, raw in enumerate(steps):
        kind = str(raw.get("kind", "")).strip().lower()
        if kind not in FAULT_KINDS:
            raise OperationsV24Error(f"unsupported fault kind: {kind}")
        step_name = str(raw.get("name") or f"step-{index + 1}").strip()
        if not step_name or step_name in names:
            raise OperationsV24Error("fault step names must be unique and non-empty")
        names.add(step_name)
        command = raw.get("command")
        recovery = raw.get("recovery_command")
        if not isinstance(command, list) or not command or not all(isinstance(item, str) and item for item in command):
            raise OperationsV24Error("fault command must be a non-empty argv list")
        if not isinstance(recovery, list) or not recovery or not all(isinstance(item, str) and item for item in recovery):
            raise OperationsV24Error("every fault step requires a non-empty recovery argv list")
        normalized.append(
            {
                "name": step_name,
                "kind": kind,
                "command": command,
                "recovery_command": recovery,
                "target": str(raw.get("target", "")).strip(),
                "expected_impact": str(raw.get("expected_impact", "")).strip(),
            }
        )
    return {
        "format": FAULT_PLAN_FORMAT,
        "name": str(name).strip() or "Crakbit v0.24 fault campaign",
        "created_at_ms": int(time.time() * 1000),
        "safe_default": "dry-run",
        "requires_explicit_execute": True,
        "steps": normalized,
        "production_mainnet_ready": False,
    }


def build_fault_result(*, plan: dict[str, Any], campaign_result: dict[str, Any]) -> dict[str, Any]:
    if plan.get("format") != FAULT_PLAN_FORMAT:
        raise OperationsV24Error("unsupported v0.24 fault plan format")
    planned = list(plan.get("steps") or [])
    executed = list(campaign_result.get("steps") or [])
    if not bool(campaign_result.get("execute")):
        raise OperationsV24Error("fault result must come from an explicitly executed campaign")
    if len(executed) != len(planned):
        raise OperationsV24Error("executed fault step count does not match plan")
    results: list[dict[str, Any]] = []
    for expected, observed in zip(planned, executed):
        if str(observed.get("name")) != str(expected.get("name")):
            raise OperationsV24Error("executed fault step order/name does not match plan")
        results.append(
            {
                "name": expected["name"],
                "kind": expected["kind"],
                "target": expected.get("target", ""),
                "fault_command_succeeded": int((observed.get("fault_command") or {}).get("returncode", -1) or 0) == 0,
                "recovery_command_succeeded": int((observed.get("recovery_command_result") or {}).get("returncode", -1) or 0) == 0,
                "recovered_healthy": bool(observed.get("recovered_healthy")),
            }
        )
    return {
        "format": FAULT_RESULT_FORMAT,
        "name": plan.get("name"),
        "created_at_ms": int(time.time() * 1000),
        "executed": True,
        "steps": results,
        "fault_kinds_executed": sorted({item["kind"] for item in results}),
        "all_steps_recovered": bool(results) and all(item["recovered_healthy"] and item["recovery_command_succeeded"] for item in results),
        "production_mainnet_ready": False,
    }


def build_recovery_record(
    *,
    kind: str,
    source_height: int,
    restored_height: int,
    source_application_hash: str,
    restored_application_hash: str,
    source_state_root: str = "",
    restored_state_root: str = "",
    clean_host: bool = False,
    notes: str = "",
) -> dict[str, Any]:
    normalized = str(kind).strip().lower()
    if normalized not in RECOVERY_KINDS:
        raise OperationsV24Error(f"unsupported recovery kind: {normalized}")
    hashes_match = bool(source_application_hash) and source_application_hash == restored_application_hash
    roots_match = (not source_state_root and not restored_state_root) or (
        bool(source_state_root) and source_state_root == restored_state_root
    )
    success = (
        int(source_height) == int(restored_height)
        and hashes_match
        and roots_match
        and (normalized != "clean-host-state-sync" or bool(clean_host))
    )
    return {
        "format": RECOVERY_FORMAT,
        "kind": normalized,
        "created_at_ms": int(time.time() * 1000),
        "source_height": int(source_height),
        "restored_height": int(restored_height),
        "source_application_hash": str(source_application_hash),
        "restored_application_hash": str(restored_application_hash),
        "source_state_root": str(source_state_root),
        "restored_state_root": str(restored_state_root),
        "clean_host": bool(clean_host),
        "success": success,
        "notes": str(notes),
        "production_mainnet_ready": False,
    }


def build_remote_signer_record(
    *,
    validator_name: str,
    signer_type: str,
    key_exported: bool,
    double_sign_protection: bool,
    restart_recovery_drilled: bool,
    failover_drilled: bool,
    signer_endpoint_private: bool,
    operator_note: str = "",
) -> dict[str, Any]:
    checks = {
        "validator_key_not_exported": not bool(key_exported),
        "double_sign_protection": bool(double_sign_protection),
        "restart_recovery_drilled": bool(restart_recovery_drilled),
        "failover_drilled": bool(failover_drilled),
        "signer_endpoint_private": bool(signer_endpoint_private),
    }
    return {
        "format": SIGNER_FORMAT,
        "validator_name": str(validator_name),
        "signer_type": str(signer_type),
        "created_at_ms": int(time.time() * 1000),
        "checks": checks,
        "protected_signer_gate_satisfied": all(checks.values()),
        "operator_note": str(operator_note),
        "contains_private_key": False,
        "independently_verified": False,
        "production_mainnet_ready": False,
    }


def evaluate_redundancy(*, rpc_records: list[dict[str, Any]], explorer_records: list[dict[str, Any]], expected_chain_id: str) -> dict[str, Any]:
    rpc_up = [item for item in rpc_records if bool(item.get("reachable"))]
    explorer_up = [item for item in explorer_records if bool(item.get("reachable"))]
    networks = sorted({str(item.get("chain_id", "")) for item in rpc_up if item.get("chain_id")})
    grouped: dict[int, set[str]] = {}
    for item in rpc_up:
        height = item.get("height")
        app_hash = str(item.get("application_hash", ""))
        if height is not None and app_hash:
            grouped.setdefault(int(height), set()).add(app_hash)
    conflicts = [
        {"height": height, "application_hashes": sorted(values)}
        for height, values in sorted(grouped.items())
        if len(values) > 1
    ]
    checks = {
        "at_least_two_rpc_endpoints_reachable": len(rpc_up) >= 2,
        "at_least_two_explorer_endpoints_reachable": len(explorer_up) >= 2,
        "rpc_chain_id_consistent": bool(rpc_up) and networks == [str(expected_chain_id)],
        "same_height_application_hash_consistent": not conflicts,
    }
    return {
        "format": REDUNDANCY_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "expected_chain_id": str(expected_chain_id),
        "checks": checks,
        "rpc_reachable": len(rpc_up),
        "explorer_reachable": len(explorer_up),
        "same_height_application_hash_conflicts": conflicts,
        "redundancy_gate_satisfied": all(checks.values()),
        "production_mainnet_ready": False,
    }


def probe_redundancy(*, rpc_urls: Iterable[str], explorer_urls: Iterable[str], expected_chain_id: str, timeout_seconds: float = 4.0) -> dict[str, Any]:
    rpc_records: list[dict[str, Any]] = []
    explorer_records: list[dict[str, Any]] = []
    with httpx.Client(timeout=timeout_seconds) as client:
        for raw in rpc_urls:
            url = str(raw).rstrip("/")
            record: dict[str, Any] = {"url": url, "reachable": False}
            try:
                status = (client.get(url + "/status").json().get("result") or {})
                sync = status.get("sync_info") or {}
                node = status.get("node_info") or {}
                abci = ((client.get(url + "/abci_info").json().get("result") or {}).get("response") or {})
                record.update(
                    {
                        "reachable": True,
                        "chain_id": str(node.get("network", "")),
                        "height": int(sync.get("latest_block_height", 0) or 0),
                        "application_hash": str(abci.get("last_block_app_hash", "")),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                record["error"] = f"{type(exc).__name__}: {exc}"
            rpc_records.append(record)
        for raw in explorer_urls:
            url = str(raw).rstrip("/")
            record = {"url": url, "reachable": False}
            try:
                response = client.get(url + "/health")
                response.raise_for_status()
                record["reachable"] = True
            except Exception as exc:  # noqa: BLE001
                record["error"] = f"{type(exc).__name__}: {exc}"
            explorer_records.append(record)
    report = evaluate_redundancy(
        rpc_records=rpc_records,
        explorer_records=explorer_records,
        expected_chain_id=expected_chain_id,
    )
    report["rpc_records"] = rpc_records
    report["explorer_records"] = explorer_records
    return report


def _soak_gate(summary: dict[str, Any], minimum_seconds: int) -> bool:
    return (
        float(summary.get("observed_duration_seconds", 0.0)) >= float(minimum_seconds)
        and bool(summary.get("divergence_free"))
        and float(summary.get("all_reachable_ratio", 0.0)) == 1.0
        and float(summary.get("healthy_ratio", 0.0)) >= 0.99
    )


def build_readiness(
    *,
    soak_24h: dict[str, Any] | None = None,
    soak_72h: dict[str, Any] | None = None,
    soak_7d: dict[str, Any] | None = None,
    fault_results: Iterable[dict[str, Any]] = (),
    recovery_records: Iterable[dict[str, Any]] = (),
    signer_records: Iterable[dict[str, Any]] = (),
    redundancy_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fault_list = list(fault_results)
    recovery_list = list(recovery_records)
    signer_list = list(signer_records)
    completed_fault_kinds = {
        kind
        for artifact in fault_list
        if artifact.get("format") == FAULT_RESULT_FORMAT and bool(artifact.get("all_steps_recovered"))
        for kind in artifact.get("fault_kinds_executed", [])
    }
    recovery_success = {
        str(item.get("kind"))
        for item in recovery_list
        if item.get("format") == RECOVERY_FORMAT and bool(item.get("success"))
    }
    checks = {
        "soak_24h": soak_24h is not None and _soak_gate(soak_24h, MIN_SOAK_SECONDS["24h"]),
        "soak_72h": soak_72h is not None and _soak_gate(soak_72h, MIN_SOAK_SECONDS["72h"]),
        "soak_7d": soak_7d is not None and _soak_gate(soak_7d, MIN_SOAK_SECONDS["7d"]),
        "restart_fault_recovered": "restart" in completed_fault_kinds,
        "process_kill_fault_recovered": "process-kill" in completed_fault_kinds,
        "partition_fault_recovered": "partition" in completed_fault_kinds,
        "latency_fault_recovered": "latency" in completed_fault_kinds,
        "packet_loss_fault_recovered": "packet-loss" in completed_fault_kinds,
        "load_fault_recovered": "load" in completed_fault_kinds,
        "storage_fault_recovered": "storage" in completed_fault_kinds,
        "backup_restore_success": "backup-restore" in recovery_success,
        "clean_host_state_sync_success": "clean-host-state-sync" in recovery_success,
        "rpc_explorer_redundancy": bool(redundancy_report and redundancy_report.get("redundancy_gate_satisfied")),
        "protected_remote_signer_drill": bool(signer_list) and all(
            item.get("format") == SIGNER_FORMAT and bool(item.get("protected_signer_gate_satisfied"))
            for item in signer_list
        ),
    }
    operational_review_candidate = all(checks.values())
    return {
        "format": READINESS_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "checks": checks,
        "fault_kinds_completed": sorted(completed_fault_kinds),
        "recovery_kinds_completed": sorted(recovery_success),
        "operational_review_candidate": operational_review_candidate,
        "independent_security_review_completed": False,
        "production_mainnet_ready": False,
        "production_crkbit_launched": False,
    }


def _artifact(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        raise OperationsV24Error(f"evidence artifact not found: {target}")
    return {"name": target.name, "size": target.stat().st_size, "sha256": _file_sha256(target)}


def build_signed_evidence(
    *,
    signing_key_path: str | Path,
    source_commit: str,
    package_version: str,
    cometbft_version: str,
    artifact_paths: Iterable[str | Path],
    operator_note: str = "",
) -> dict[str, Any]:
    key = KeyPair.load(signing_key_path)
    artifacts = [_artifact(path) for path in artifact_paths]
    names = [item["name"] for item in artifacts]
    if len(names) != len(set(names)):
        raise OperationsV24Error("signed evidence artifacts must have unique filenames")
    artifacts.sort(key=lambda item: item["name"])
    manifest = {
        "format": EVIDENCE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": _valid_commit(source_commit),
        "package_version": str(package_version),
        "cometbft_version": str(cometbft_version),
        "artifacts": artifacts,
        "operator_note": str(operator_note),
        "claims": {
            "operator_generated_evidence": True,
            "independently_verified": False,
            "production_mainnet_ready": False,
            "production_crkbit_launched": False,
        },
    }
    payload = canonical_json(manifest)
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_hex(payload),
        "signer": key.address,
        "public_key": key.public_key_b64,
        "signature": key.sign(payload),
    }


def verify_signed_evidence(
    envelope: dict[str, Any],
    *,
    artifact_directory: str | Path | None = None,
    expected_signer: str | None = None,
    expected_source_commit: str | None = None,
) -> dict[str, Any]:
    manifest = envelope.get("manifest")
    if not isinstance(manifest, dict) or manifest.get("format") != EVIDENCE_FORMAT:
        raise OperationsV24Error("unsupported v0.24 operations evidence format")
    payload = canonical_json(manifest)
    if sha256_hex(payload) != str(envelope.get("manifest_sha256", "")):
        raise OperationsV24Error("operations evidence manifest hash mismatch")
    public_key = str(envelope.get("public_key", ""))
    signer = str(envelope.get("signer", ""))
    if address_from_public_key(public_key) != signer:
        raise OperationsV24Error("operations evidence signer identity mismatch")
    if expected_signer and signer != expected_signer:
        raise OperationsV24Error("operations evidence signer does not match expected signer")
    if expected_source_commit and manifest.get("source_commit") != _valid_commit(expected_source_commit):
        raise OperationsV24Error("operations evidence source commit mismatch")
    if not verify_signature(public_key, payload, str(envelope.get("signature", ""))):
        raise OperationsV24Error("invalid operations evidence signature")
    claims = manifest.get("claims") or {}
    if claims.get("production_mainnet_ready") is not False or claims.get("production_crkbit_launched") is not False:
        raise OperationsV24Error("v0.24 evidence may not claim production launch/readiness")
    verified = 0
    if artifact_directory is not None:
        root = Path(artifact_directory)
        for item in list(manifest.get("artifacts") or []):
            name = str(item.get("name", ""))
            if not name or Path(name).name != name:
                raise OperationsV24Error("invalid evidence artifact filename")
            path = root / name
            if not path.is_file():
                raise OperationsV24Error(f"evidence artifact missing: {name}")
            if path.stat().st_size != int(item.get("size", -1)):
                raise OperationsV24Error(f"evidence artifact size mismatch: {name}")
            if _file_sha256(path) != str(item.get("sha256", "")):
                raise OperationsV24Error(f"evidence artifact hash mismatch: {name}")
            verified += 1
    return {
        "valid": True,
        "format": EVIDENCE_FORMAT,
        "source_commit": manifest["source_commit"],
        "signer": signer,
        "verified_artifacts": verified,
        "independently_verified": False,
        "production_mainnet_ready": False,
    }
