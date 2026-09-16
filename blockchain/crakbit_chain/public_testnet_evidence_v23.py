from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .crypto import KeyPair, address_from_public_key, canonical_json, sha256_hex, verify_signature
from .public_testnet_monitor_v23 import SOAK_SUMMARY_FORMAT
from .public_testnet_v23 import (
    DEPLOYMENT_BUNDLE_FORMAT,
    GENESIS_BUNDLE_FORMAT,
    INVENTORY_FORMAT,
    load_inventory,
)


READINESS_FORMAT = "crakbit-public-testnet-readiness/1"
EVIDENCE_FORMAT = "crakbit-public-testnet-operations-evidence/1"


class PublicTestnetEvidenceError(ValueError):
    pass


def _load(path: str | Path) -> dict[str, Any]:
    try:
        body = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicTestnetEvidenceError(f"invalid JSON artifact: {path}") from exc
    if not isinstance(body, dict):
        raise PublicTestnetEvidenceError(f"artifact root must be an object: {path}")
    return body


def _artifact(path: str | Path, *, label: str) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        raise PublicTestnetEvidenceError(f"missing {label} artifact: {target}")
    return {
        "label": label,
        "name": target.name,
        "path": str(target),
        "size": target.stat().st_size,
        "sha256": sha256_hex(target.read_bytes()),
    }


def build_readiness_report(
    *,
    inventory_path: str | Path,
    genesis_manifest_path: str | Path | None = None,
    deployment_manifest_path: str | Path | None = None,
    soak_summary_path: str | Path | None = None,
) -> dict[str, Any]:
    inventory = load_inventory(inventory_path)
    checks: dict[str, bool] = {
        "at_least_four_validators": int(inventory["validator_count"]) >= 4,
        "four_independent_operators": bool(inventory["independent_operator_gate_satisfied"]),
        "at_least_two_providers": bool(inventory["multi_provider_gate_satisfied"]),
        "at_least_two_regions": bool(inventory["multi_region_gate_satisfied"]),
        "monitor_rpc_configured_for_all": all(
            bool(str(item.get("monitor_rpc_url", "")).strip()) for item in inventory["validators"]
        ),
    }
    details: dict[str, Any] = {
        "validator_count": inventory["validator_count"],
        "operator_count": inventory["operator_count"],
        "provider_count": inventory["provider_count"],
        "region_count": inventory["region_count"],
    }

    if genesis_manifest_path is not None:
        genesis = _load(genesis_manifest_path)
        checks["genesis_bundle_present"] = genesis.get("format") == GENESIS_BUNDLE_FORMAT
        checks["genesis_has_no_private_material"] = genesis.get("contains_private_material") is False
        details["genesis_manifest"] = str(genesis_manifest_path)
    else:
        checks["genesis_bundle_present"] = False
        checks["genesis_has_no_private_material"] = False

    if deployment_manifest_path is not None:
        deployment = _load(deployment_manifest_path)
        checks["deployment_bundle_present"] = deployment.get("format") == DEPLOYMENT_BUNDLE_FORMAT
        checks["deployment_has_no_private_material"] = deployment.get("contains_private_material") is False
        details["deployment_manifest"] = str(deployment_manifest_path)
    else:
        checks["deployment_bundle_present"] = False
        checks["deployment_has_no_private_material"] = False

    soak = None
    if soak_summary_path is not None:
        soak = _load(soak_summary_path)
        checks["soak_summary_present"] = soak.get("format") == SOAK_SUMMARY_FORMAT
        checks["soak_divergence_free"] = bool(soak.get("divergence_free"))
        checks["soak_full_reachability"] = float(soak.get("all_reachable_ratio", 0.0)) == 1.0
        checks["soak_health_ratio_at_least_99_percent"] = float(soak.get("healthy_ratio", 0.0)) >= 0.99
        details["soak_summary"] = str(soak_summary_path)
        details["soak_observed_duration_seconds"] = float(soak.get("observed_duration_seconds", 0.0))
    else:
        checks["soak_summary_present"] = False
        checks["soak_divergence_free"] = False
        checks["soak_full_reachability"] = False
        checks["soak_health_ratio_at_least_99_percent"] = False
        details["soak_observed_duration_seconds"] = 0.0

    # A public-testnet launch candidate can exist before 24h evidence, but the long-lived
    # operations gate stays open until actual soak evidence is collected.
    launch_candidate_checks = [
        "at_least_four_validators",
        "genesis_bundle_present",
        "genesis_has_no_private_material",
        "deployment_bundle_present",
        "deployment_has_no_private_material",
    ]
    public_testnet_launch_candidate = all(checks.get(key, False) for key in launch_candidate_checks)
    independent_host_gate = all(
        checks.get(key, False)
        for key in (
            "four_independent_operators",
            "at_least_two_providers",
            "at_least_two_regions",
        )
    )
    long_lived_evidence_gate = (
        soak is not None
        and float(soak.get("observed_duration_seconds", 0.0)) >= 24 * 3600
        and checks["soak_divergence_free"]
        and checks["soak_full_reachability"]
        and checks["soak_health_ratio_at_least_99_percent"]
    )
    return {
        "format": READINESS_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "chain_id": inventory["chain_id"],
        "network_name": inventory["network_name"],
        "checks": checks,
        "details": details,
        "public_testnet_launch_candidate": public_testnet_launch_candidate,
        "independent_host_diversity_gate_satisfied": independent_host_gate,
        "minimum_24h_soak_gate_satisfied": bool(long_lived_evidence_gate),
        "independent_security_review_completed": False,
        "production_mainnet_ready": False,
        "production_crkbit_launched": False,
    }


def _validate_commit(value: str) -> str:
    commit = str(value).strip().lower()
    if len(commit) not in {40, 64} or any(ch not in "0123456789abcdef" for ch in commit):
        raise PublicTestnetEvidenceError("source_commit must be an exact hexadecimal Git commit SHA")
    return commit


def build_operations_evidence(
    *,
    signing_key_path: str | Path,
    source_commit: str,
    inventory_path: str | Path,
    readiness_path: str | Path,
    artifact_paths: list[str | Path],
    operator_note: str = "",
) -> dict[str, Any]:
    inventory = load_inventory(inventory_path)
    readiness = _load(readiness_path)
    if readiness.get("format") != READINESS_FORMAT:
        raise PublicTestnetEvidenceError("unsupported readiness report format")
    if str(readiness.get("chain_id")) != inventory["chain_id"]:
        raise PublicTestnetEvidenceError("readiness report chain ID does not match inventory")
    signer = KeyPair.load(signing_key_path)
    artifacts = [_artifact(inventory_path, label="inventory"), _artifact(readiness_path, label="readiness")]
    for path in artifact_paths:
        artifacts.append(_artifact(path, label="evidence"))
    artifacts.sort(key=lambda item: (item["label"], item["name"], item["sha256"]))
    manifest = {
        "format": EVIDENCE_FORMAT,
        "created_at_ms": int(time.time() * 1000),
        "source_commit": _validate_commit(source_commit),
        "chain_id": inventory["chain_id"],
        "network_name": inventory["network_name"],
        "artifacts": artifacts,
        "operator_note": str(operator_note),
        "readiness_claims": {
            "public_testnet_launch_candidate": bool(readiness.get("public_testnet_launch_candidate")),
            "independent_host_diversity_gate_satisfied": bool(
                readiness.get("independent_host_diversity_gate_satisfied")
            ),
            "minimum_24h_soak_gate_satisfied": bool(readiness.get("minimum_24h_soak_gate_satisfied")),
            "independent_security_review_completed": False,
            "production_mainnet_ready": False,
            "production_crkbit_launched": False,
        },
    }
    payload = canonical_json(manifest)
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_hex(payload),
        "signer": signer.address,
        "public_key": signer.public_key_b64,
        "signature": signer.sign(payload),
    }


def verify_operations_evidence(
    envelope: dict[str, Any],
    *,
    artifact_directory: str | Path | None = None,
    expected_signer: str | None = None,
    expected_source_commit: str | None = None,
) -> dict[str, Any]:
    manifest = envelope.get("manifest")
    if not isinstance(manifest, dict) or manifest.get("format") != EVIDENCE_FORMAT:
        raise PublicTestnetEvidenceError("unsupported public-testnet operations evidence format")
    payload = canonical_json(manifest)
    if sha256_hex(payload) != str(envelope.get("manifest_sha256", "")):
        raise PublicTestnetEvidenceError("operations evidence manifest hash mismatch")
    public_key = str(envelope.get("public_key", ""))
    signer = str(envelope.get("signer", ""))
    if address_from_public_key(public_key) != signer:
        raise PublicTestnetEvidenceError("operations evidence signer identity mismatch")
    if expected_signer and signer != expected_signer:
        raise PublicTestnetEvidenceError("operations evidence signer does not match expected signer")
    if expected_source_commit and manifest.get("source_commit") != _validate_commit(expected_source_commit):
        raise PublicTestnetEvidenceError("operations evidence source commit mismatch")
    if not verify_signature(public_key, payload, str(envelope.get("signature", ""))):
        raise PublicTestnetEvidenceError("invalid operations evidence signature")

    verified_artifacts = 0
    if artifact_directory is not None:
        root = Path(artifact_directory)
        for item in list(manifest.get("artifacts") or []):
            candidate = root / str(item["name"])
            if not candidate.is_file():
                raise PublicTestnetEvidenceError(f"operations evidence artifact missing: {candidate}")
            if candidate.stat().st_size != int(item["size"]):
                raise PublicTestnetEvidenceError(f"operations evidence artifact size mismatch: {candidate}")
            if sha256_hex(candidate.read_bytes()) != str(item["sha256"]):
                raise PublicTestnetEvidenceError(f"operations evidence artifact hash mismatch: {candidate}")
            verified_artifacts += 1
    claims = manifest.get("readiness_claims") or {}
    if claims.get("production_mainnet_ready") is not False:
        raise PublicTestnetEvidenceError("v0.23 evidence must not claim production mainnet readiness")
    return {
        "valid": True,
        "format": EVIDENCE_FORMAT,
        "chain_id": str(manifest.get("chain_id", "")),
        "signer": signer,
        "artifact_count": len(list(manifest.get("artifacts") or [])),
        "verified_artifact_count": verified_artifacts,
        "public_testnet_launch_candidate": bool(claims.get("public_testnet_launch_candidate")),
        "minimum_24h_soak_gate_satisfied": bool(claims.get("minimum_24h_soak_gate_satisfied")),
        "production_mainnet_ready": False,
    }


def save_json(body: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise PublicTestnetEvidenceError(f"output already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target
