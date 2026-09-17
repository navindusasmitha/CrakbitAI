from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from .algorithm_gate_v34 import verify_algorithm_decision, verify_benchmark_gate
from .crypto import KeyPair, canonical_json, sha256_hex, verify_signature
from .pow_activation_v36 import verify_activation_proposal
from .pow_handoff_v36 import verify_review_handoff

DEPLOYMENT_FORMAT = "crakbit-pow-deployment-plan-v37/1"
PAYOUT_POLICY_FORMAT = "crakbit-pow-payout-policy-v37/1"
ALGORITHM_REVIEW_FORMAT = "crakbit-pow-algorithm-review-gate-v37/1"
REVIEW_BUNDLE_FORMAT = "crakbit-pow-public-testnet-review-bundle-v37/1"

_SECRET_KEY_RE = re.compile(r"(private|secret|password|passwd|token|seed|mnemonic|api[_-]?key|tls[_-]?key)", re.I)


class PowExecutionV37Error(ValueError):
    pass


def _commit(value: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 40 or any(ch not in "0123456789abcdef" for ch in text):
        raise PowExecutionV37Error("source commit must be an exact 40-character Git SHA")
    return text


def _hash64(value: str, field: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise PowExecutionV37Error(f"{field} must be 64 hexadecimal characters")
    return text


def _signed(manifest: dict[str, Any], key: KeyPair) -> dict[str, Any]:
    payload = canonical_json({"domain": manifest["format"], "manifest": manifest})
    return {
        "manifest": manifest,
        "signer": key.address,
        "public_key": key.public_key_b64,
        "signature": key.sign(payload),
    }


def _verify_signed(record: dict[str, Any], expected_format: str, id_field: str) -> dict[str, Any]:
    manifest = record.get("manifest")
    if not isinstance(manifest, dict) or manifest.get("format") != expected_format:
        raise PowExecutionV37Error(f"unexpected {expected_format} format")
    payload = canonical_json({"domain": expected_format, "manifest": manifest})
    if not verify_signature(str(record.get("public_key", "")), payload, str(record.get("signature", ""))):
        raise PowExecutionV37Error("invalid evidence signature")
    body = dict(manifest)
    record_id = str(body.pop(id_field, ""))
    if record_id != sha256_hex(canonical_json(body)):
        raise PowExecutionV37Error(f"{id_field} mismatch")
    return manifest


def _assert_no_secrets(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if _SECRET_KEY_RE.search(str(key)):
                raise PowExecutionV37Error(f"secret-like field rejected at {path}.{key}")
            _assert_no_secrets(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_no_secrets(item, f"{path}[{index}]")


def _validate_rpc_url(value: str) -> str:
    text = str(value).strip()
    if not text.startswith(("http://", "https://")):
        raise PowExecutionV37Error("RPC URL must use http(s)")
    if "@" in text.split("://", 1)[1].split("/", 1)[0]:
        raise PowExecutionV37Error("RPC URL must not embed credentials")
    return text.rstrip("/")


def _validate_endpoint(value: str) -> str:
    text = str(value).strip()
    if not text or ":" not in text:
        raise PowExecutionV37Error("P2P endpoint must be host:port")
    host, port_text = text.rsplit(":", 1)
    if not host:
        raise PowExecutionV37Error("P2P host is empty")
    try:
        port = int(port_text)
    except ValueError as exc:
        raise PowExecutionV37Error("P2P port must be numeric") from exc
    if port < 1 or port > 65535:
        raise PowExecutionV37Error("P2P port is out of range")
    return f"{host}:{port}"


def build_deployment_plan(
    *,
    key_path: str | Path,
    source_commit: str,
    package_version: str,
    chain_id: str,
    genesis_hash: str,
    nodes: list[dict[str, Any]],
    minimum_nodes: int = 4,
    minimum_providers: int = 2,
    minimum_regions: int = 2,
    minimum_network_groups: int = 2,
    minimum_miner_operators: int = 2,
    notes: str = "",
) -> dict[str, Any]:
    key = KeyPair.load(key_path)
    minimum_nodes = max(4, int(minimum_nodes))
    minimum_providers = max(2, int(minimum_providers))
    minimum_regions = max(2, int(minimum_regions))
    minimum_network_groups = max(2, int(minimum_network_groups))
    minimum_miner_operators = max(2, int(minimum_miner_operators))
    if len(nodes) < minimum_nodes:
        raise PowExecutionV37Error("deployment plan requires at least four nodes")
    _assert_no_secrets(nodes, "nodes")

    normalized: list[dict[str, Any]] = []
    for raw in nodes:
        node_id = str(raw.get("node_id", "")).strip()
        operator_id = str(raw.get("operator_id", "")).strip()
        provider = str(raw.get("provider", "")).strip()
        region = str(raw.get("region", "")).strip()
        network_group = str(raw.get("network_group", "")).strip()
        roles = sorted({str(role).strip().lower() for role in raw.get("roles", []) if str(role).strip()})
        if not all([node_id, operator_id, provider, region, network_group]):
            raise PowExecutionV37Error("node_id/operator_id/provider/region/network_group are required")
        if not roles:
            raise PowExecutionV37Error("every node needs at least one role")
        rpc_url = _validate_rpc_url(str(raw.get("rpc_url", "")))
        p2p_endpoint = _validate_endpoint(str(raw.get("p2p_endpoint", "")))
        bundle = {
            "node_id": node_id,
            "operator_id": operator_id,
            "provider": provider,
            "region": region,
            "network_group": network_group,
            "roles": roles,
            "rpc_url": rpc_url,
            "p2p_endpoint": p2p_endpoint,
            "runbook": {
                "node_start": "crakchain pow-node-v36-run --db <CHAIN_DB> --network-key <P2P_KEY> --peer-db <PEER_DB> --rpc-port <RPC_PORT> --p2p-port <P2P_PORT>",
                "campaign_probe": f"crakchain pow-campaign-v36-probe --key <EVIDENCE_KEY> --log <CAMPAIGN_LOG> --rpc-url {rpc_url}",
                "health_check": f"GET {rpc_url}/pow/v2/info",
            },
        }
        normalized.append(bundle)

    node_ids = {item["node_id"] for item in normalized}
    operators = {item["operator_id"] for item in normalized}
    providers = {item["provider"] for item in normalized}
    regions = {item["region"] for item in normalized}
    network_groups = {item["network_group"] for item in normalized}
    miner_operators = {item["operator_id"] for item in normalized if "miner" in item["roles"] or "pool" in item["roles"]}
    checks = {
        "minimum_nodes": len(normalized) >= minimum_nodes,
        "unique_node_ids": len(node_ids) == len(normalized),
        "unique_operators": len(operators) == len(normalized),
        "provider_diversity": len(providers) >= minimum_providers,
        "region_diversity": len(regions) >= minimum_regions,
        "network_group_diversity": len(network_groups) >= minimum_network_groups,
        "miner_operator_diversity": len(miner_operators) >= minimum_miner_operators,
        "contains_no_secret_fields": True,
    }
    manifest = {
        "format": DEPLOYMENT_FORMAT,
        "recorded_at_unix": int(time.time()),
        "source_commit": _commit(source_commit),
        "package_version": str(package_version),
        "chain_id": str(chain_id).strip(),
        "genesis_hash": _hash64(genesis_hash, "genesis hash"),
        "nodes": sorted(normalized, key=lambda item: item["node_id"]),
        "counts": {
            "nodes": len(normalized),
            "operators": len(operators),
            "providers": len(providers),
            "regions": len(regions),
            "network_groups": len(network_groups),
            "miner_operators": len(miner_operators),
        },
        "requirements": {
            "minimum_nodes": minimum_nodes,
            "minimum_providers": minimum_providers,
            "minimum_regions": minimum_regions,
            "minimum_network_groups": minimum_network_groups,
            "minimum_miner_operators": minimum_miner_operators,
        },
        "checks": checks,
        "deployment_gate_satisfied": all(checks.values()),
        "operator_metadata_self_attested": True,
        "external_network_metadata_review_required": True,
        "launches_or_mutates_hosts": False,
        "notes": str(notes)[:4000],
        "production_mainnet_ready": False,
        "production_crkbit_launched": False,
    }
    if not manifest["chain_id"]:
        raise PowExecutionV37Error("chain ID is required")
    manifest["deployment_id"] = sha256_hex(canonical_json(manifest))
    return _signed(manifest, key)


def verify_deployment_plan(record: dict[str, Any]) -> dict[str, Any]:
    manifest = _verify_signed(record, DEPLOYMENT_FORMAT, "deployment_id")
    if manifest.get("production_mainnet_ready") or manifest.get("production_crkbit_launched"):
        raise PowExecutionV37Error("deployment plan contains prohibited production claims")
    _commit(str(manifest.get("source_commit", "")))
    _hash64(str(manifest.get("genesis_hash", "")), "genesis hash")
    if not str(manifest.get("chain_id", "")).strip():
        raise PowExecutionV37Error("deployment plan chain ID is empty")

    nodes = manifest.get("nodes")
    requirements = manifest.get("requirements")
    if not isinstance(nodes, list) or not isinstance(requirements, dict):
        raise PowExecutionV37Error("deployment plan nodes/requirements are malformed")
    _assert_no_secrets(nodes, "nodes")
    normalized_ids: list[str] = []
    operators: set[str] = set()
    providers: set[str] = set()
    regions: set[str] = set()
    network_groups: set[str] = set()
    miner_operators: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise PowExecutionV37Error("deployment plan node must be an object")
        node_id = str(node.get("node_id", "")).strip()
        operator_id = str(node.get("operator_id", "")).strip()
        provider = str(node.get("provider", "")).strip()
        region = str(node.get("region", "")).strip()
        network_group = str(node.get("network_group", "")).strip()
        roles = {str(role).strip().lower() for role in node.get("roles", []) if str(role).strip()}
        if not all([node_id, operator_id, provider, region, network_group]) or not roles:
            raise PowExecutionV37Error("deployment plan node metadata is incomplete")
        _validate_rpc_url(str(node.get("rpc_url", "")))
        _validate_endpoint(str(node.get("p2p_endpoint", "")))
        normalized_ids.append(node_id)
        operators.add(operator_id)
        providers.add(provider)
        regions.add(region)
        network_groups.add(network_group)
        if roles.intersection({"miner", "pool"}):
            miner_operators.add(operator_id)

    minimum_nodes = max(4, int(requirements.get("minimum_nodes", 4)))
    minimum_providers = max(2, int(requirements.get("minimum_providers", 2)))
    minimum_regions = max(2, int(requirements.get("minimum_regions", 2)))
    minimum_network_groups = max(2, int(requirements.get("minimum_network_groups", 2)))
    minimum_miner_operators = max(2, int(requirements.get("minimum_miner_operators", 2)))
    expected_counts = {
        "nodes": len(nodes),
        "operators": len(operators),
        "providers": len(providers),
        "regions": len(regions),
        "network_groups": len(network_groups),
        "miner_operators": len(miner_operators),
    }
    expected_checks = {
        "minimum_nodes": len(nodes) >= minimum_nodes,
        "unique_node_ids": len(set(normalized_ids)) == len(nodes),
        "unique_operators": len(operators) == len(nodes),
        "provider_diversity": len(providers) >= minimum_providers,
        "region_diversity": len(regions) >= minimum_regions,
        "network_group_diversity": len(network_groups) >= minimum_network_groups,
        "miner_operator_diversity": len(miner_operators) >= minimum_miner_operators,
        "contains_no_secret_fields": True,
    }
    if manifest.get("counts") != expected_counts or manifest.get("checks") != expected_checks:
        raise PowExecutionV37Error("deployment plan derived counts/checks mismatch")
    if bool(manifest.get("deployment_gate_satisfied")) != all(expected_checks.values()):
        raise PowExecutionV37Error("deployment gate result mismatch")
    return {
        "valid": True,
        "deployment_id": manifest["deployment_id"],
        "deployment_gate_satisfied": bool(manifest.get("deployment_gate_satisfied")),
        "node_count": int(manifest.get("counts", {}).get("nodes", 0)),
        "production_mainnet_ready": False,
    }


def build_payout_policy(
    *,
    key_path: str | Path,
    hot_wallet_address: str,
    cold_wallet_address: str,
    maximum_single_payout_atomic: int,
    maximum_batch_payout_atomic: int,
    daily_payout_limit_atomic: int,
    manual_hold_above_atomic: int,
    approvals_required: int = 2,
    minimum_confirmations: int = 6,
    notes: str = "",
) -> dict[str, Any]:
    key = KeyPair.load(key_path)
    hot = str(hot_wallet_address).strip()
    cold = str(cold_wallet_address).strip()
    if not hot.startswith("crk1") or not cold.startswith("crk1"):
        raise PowExecutionV37Error("hot/cold wallets must be Crakbit addresses")
    if hot == cold:
        raise PowExecutionV37Error("hot and cold wallet addresses must differ")
    maximum_single_payout_atomic = int(maximum_single_payout_atomic)
    maximum_batch_payout_atomic = int(maximum_batch_payout_atomic)
    daily_payout_limit_atomic = int(daily_payout_limit_atomic)
    manual_hold_above_atomic = int(manual_hold_above_atomic)
    approvals_required = int(approvals_required)
    minimum_confirmations = int(minimum_confirmations)
    if min(maximum_single_payout_atomic, maximum_batch_payout_atomic, daily_payout_limit_atomic, manual_hold_above_atomic) <= 0:
        raise PowExecutionV37Error("payout policy limits must be positive")
    if maximum_single_payout_atomic > maximum_batch_payout_atomic:
        raise PowExecutionV37Error("single payout cap cannot exceed batch cap")
    if maximum_batch_payout_atomic > daily_payout_limit_atomic:
        raise PowExecutionV37Error("batch cap cannot exceed daily limit")
    if manual_hold_above_atomic > maximum_single_payout_atomic:
        raise PowExecutionV37Error("manual hold threshold cannot exceed single payout cap")
    if approvals_required < 2:
        raise PowExecutionV37Error("at least two operator approvals are required")
    if minimum_confirmations < 2:
        raise PowExecutionV37Error("minimum confirmations must be >= 2")

    checks = {
        "separate_hot_and_cold_wallets": hot != cold,
        "multi_operator_approval": approvals_required >= 2,
        "manual_hold_enabled": manual_hold_above_atomic > 0,
        "single_cap_within_batch": maximum_single_payout_atomic <= maximum_batch_payout_atomic,
        "batch_cap_within_daily": maximum_batch_payout_atomic <= daily_payout_limit_atomic,
        "confirmation_depth": minimum_confirmations >= 2,
        "automatic_payouts_disabled": True,
        "private_keys_not_embedded": True,
    }
    manifest = {
        "format": PAYOUT_POLICY_FORMAT,
        "recorded_at_unix": int(time.time()),
        "hot_wallet_address": hot,
        "cold_wallet_address": cold,
        "maximum_single_payout_atomic": maximum_single_payout_atomic,
        "maximum_batch_payout_atomic": maximum_batch_payout_atomic,
        "daily_payout_limit_atomic": daily_payout_limit_atomic,
        "manual_hold_above_atomic": manual_hold_above_atomic,
        "approvals_required": approvals_required,
        "minimum_confirmations": minimum_confirmations,
        "automatic_payouts_enabled": False,
        "checks": checks,
        "payout_policy_gate_satisfied": all(checks.values()),
        "notes": str(notes)[:4000],
        "production_mainnet_ready": False,
    }
    manifest["policy_id"] = sha256_hex(canonical_json(manifest))
    return _signed(manifest, key)


def verify_payout_policy(record: dict[str, Any]) -> dict[str, Any]:
    manifest = _verify_signed(record, PAYOUT_POLICY_FORMAT, "policy_id")
    if manifest.get("automatic_payouts_enabled") or manifest.get("production_mainnet_ready"):
        raise PowExecutionV37Error("payout policy contains unsafe/production claims")
    hot = str(manifest.get("hot_wallet_address", ""))
    cold = str(manifest.get("cold_wallet_address", ""))
    if not hot.startswith("crk1") or not cold.startswith("crk1") or hot == cold:
        raise PowExecutionV37Error("payout policy wallet separation is invalid")
    single = int(manifest.get("maximum_single_payout_atomic", 0))
    batch = int(manifest.get("maximum_batch_payout_atomic", 0))
    daily = int(manifest.get("daily_payout_limit_atomic", 0))
    hold = int(manifest.get("manual_hold_above_atomic", 0))
    approvals = int(manifest.get("approvals_required", 0))
    confirmations = int(manifest.get("minimum_confirmations", 0))
    expected_checks = {
        "separate_hot_and_cold_wallets": hot != cold,
        "multi_operator_approval": approvals >= 2,
        "manual_hold_enabled": hold > 0,
        "single_cap_within_batch": 0 < single <= batch,
        "batch_cap_within_daily": 0 < batch <= daily,
        "confirmation_depth": confirmations >= 2,
        "automatic_payouts_disabled": True,
        "private_keys_not_embedded": True,
    }
    if hold > single or manifest.get("checks") != expected_checks:
        raise PowExecutionV37Error("payout policy derived checks mismatch")
    if bool(manifest.get("payout_policy_gate_satisfied")) != all(expected_checks.values()):
        raise PowExecutionV37Error("payout policy gate result mismatch")
    return {
        "valid": True,
        "policy_id": manifest["policy_id"],
        "payout_policy_gate_satisfied": bool(manifest.get("payout_policy_gate_satisfied")),
        "production_mainnet_ready": False,
    }


def build_algorithm_review_gate(
    *,
    key_path: str | Path,
    benchmark_gate: dict[str, Any],
    algorithm_decision: dict[str, Any],
    v36_handoff: dict[str, Any],
    activation_proposal: dict[str, Any] | None,
    external_benchmark_review_asserted: bool,
    external_consensus_review_asserted: bool,
    notes: str = "",
) -> dict[str, Any]:
    key = KeyPair.load(key_path)
    benchmark = verify_benchmark_gate(benchmark_gate)
    decision = verify_algorithm_decision(algorithm_decision)
    handoff = verify_review_handoff(v36_handoff)
    decision_name = str(decision["decision"])
    if str(algorithm_decision.get("manifest", {}).get("benchmark_gate_id")) != str(benchmark["gate_id"]):
        raise PowExecutionV37Error("algorithm decision is not bound to the supplied benchmark gate")
    if decision_name == "hold":
        raise PowExecutionV37Error("algorithm review gate cannot pass while decision is hold")

    activation_verified: dict[str, Any] | None = None
    if activation_proposal is not None:
        activation_verified = verify_activation_proposal(activation_proposal)
        if str(activation_verified["decision"]) != decision_name:
            raise PowExecutionV37Error("activation proposal decision differs from algorithm decision")
        if str(activation_proposal.get("manifest", {}).get("algorithm_decision_id")) != str(decision["decision_id"]):
            raise PowExecutionV37Error("activation proposal is not bound to the supplied algorithm decision")
    if decision_name == "randomx" and activation_verified is None:
        raise PowExecutionV37Error("RandomX decision requires a versioned testnet activation proposal")

    checks = {
        "benchmark_gate_satisfied": bool(benchmark["benchmark_gate_satisfied"]),
        "v36_review_handoff_ready": bool(handoff["external_review_handoff_ready"]),
        "external_benchmark_review_asserted": bool(external_benchmark_review_asserted),
        "external_consensus_review_asserted": bool(external_consensus_review_asserted),
        "algorithm_decision_not_hold": decision_name in {"scrypt", "randomx"},
        "activation_proposal_bound_if_randomx": decision_name != "randomx" or activation_verified is not None,
        "no_consensus_auto_activation": activation_verified is None or not bool(activation_verified.get("consensus_activated")),
    }
    manifest = {
        "format": ALGORITHM_REVIEW_FORMAT,
        "recorded_at_unix": int(time.time()),
        "benchmark_gate_id": benchmark["gate_id"],
        "algorithm_decision_id": decision["decision_id"],
        "v36_handoff_id": handoff["handoff_id"],
        "decision": decision_name,
        "activation_proposal_id": None if activation_verified is None else activation_verified["proposal_id"],
        "checks": checks,
        "algorithm_review_gate_satisfied": all(checks.values()),
        "review_assertions_are_not_cryptographic_proof_of_independence": True,
        "testnet_only": True,
        "consensus_activated": False,
        "notes": str(notes)[:4000],
        "production_mainnet_ready": False,
        "production_crkbit_launched": False,
    }
    manifest["algorithm_review_id"] = sha256_hex(canonical_json(manifest))
    return _signed(manifest, key)


def verify_algorithm_review_gate(record: dict[str, Any]) -> dict[str, Any]:
    manifest = _verify_signed(record, ALGORITHM_REVIEW_FORMAT, "algorithm_review_id")
    if manifest.get("consensus_activated") or manifest.get("production_mainnet_ready") or manifest.get("production_crkbit_launched"):
        raise PowExecutionV37Error("algorithm review gate contains prohibited activation/launch claims")
    decision = str(manifest.get("decision", ""))
    if decision not in {"scrypt", "randomx"}:
        raise PowExecutionV37Error("algorithm review decision is unsupported")
    if decision == "randomx" and not manifest.get("activation_proposal_id"):
        raise PowExecutionV37Error("RandomX review gate is missing its activation proposal")
    checks = manifest.get("checks")
    required_checks = {
        "benchmark_gate_satisfied",
        "v36_review_handoff_ready",
        "external_benchmark_review_asserted",
        "external_consensus_review_asserted",
        "algorithm_decision_not_hold",
        "activation_proposal_bound_if_randomx",
        "no_consensus_auto_activation",
    }
    if not isinstance(checks, dict) or set(checks) != required_checks:
        raise PowExecutionV37Error("algorithm review checks are malformed")
    if bool(manifest.get("algorithm_review_gate_satisfied")) != all(bool(value) for value in checks.values()):
        raise PowExecutionV37Error("algorithm review gate result mismatch")
    if not manifest.get("testnet_only") or not manifest.get("review_assertions_are_not_cryptographic_proof_of_independence"):
        raise PowExecutionV37Error("algorithm review safety boundary is missing")
    return {
        "valid": True,
        "algorithm_review_id": manifest["algorithm_review_id"],
        "decision": manifest["decision"],
        "algorithm_review_gate_satisfied": bool(manifest.get("algorithm_review_gate_satisfied")),
        "production_mainnet_ready": False,
    }


def build_review_bundle(
    *,
    key_path: str | Path,
    source_commit: str,
    package_version: str,
    deployment_plan: dict[str, Any],
    payout_policy: dict[str, Any],
    algorithm_review_gate: dict[str, Any],
    v36_handoff: dict[str, Any],
    notes: str = "",
) -> dict[str, Any]:
    key = KeyPair.load(key_path)
    deployment = verify_deployment_plan(deployment_plan)
    payout = verify_payout_policy(payout_policy)
    algorithm = verify_algorithm_review_gate(algorithm_review_gate)
    handoff = verify_review_handoff(v36_handoff)

    dep_manifest = deployment_plan["manifest"]
    handoff_manifest = v36_handoff["manifest"]
    algorithm_manifest = algorithm_review_gate["manifest"]
    if str(dep_manifest.get("source_commit")) != _commit(source_commit):
        raise PowExecutionV37Error("deployment plan source commit differs from review bundle")
    if str(dep_manifest.get("package_version")) != str(package_version):
        raise PowExecutionV37Error("deployment package version differs from review bundle")
    if str(handoff_manifest.get("chain_id")) != str(dep_manifest.get("chain_id")):
        raise PowExecutionV37Error("v0.36 handoff chain ID differs from deployment plan")
    if str(handoff_manifest.get("genesis_hash")).lower() != str(dep_manifest.get("genesis_hash")).lower():
        raise PowExecutionV37Error("v0.36 handoff genesis differs from deployment plan")
    if str(algorithm_manifest.get("v36_handoff_id")) != str(handoff["handoff_id"]):
        raise PowExecutionV37Error("algorithm review gate is not bound to the supplied v0.36 handoff")

    checks = {
        "deployment_gate_satisfied": bool(deployment["deployment_gate_satisfied"]),
        "payout_policy_gate_satisfied": bool(payout["payout_policy_gate_satisfied"]),
        "algorithm_review_gate_satisfied": bool(algorithm["algorithm_review_gate_satisfied"]),
        "v36_external_review_handoff_ready": bool(handoff["external_review_handoff_ready"]),
        "minimum_four_nodes": int(deployment["node_count"]) >= 4,
        "production_launch_not_claimed": True,
    }
    manifest = {
        "format": REVIEW_BUNDLE_FORMAT,
        "recorded_at_unix": int(time.time()),
        "source_commit": _commit(source_commit),
        "package_version": str(package_version),
        "chain_id": dep_manifest["chain_id"],
        "genesis_hash": dep_manifest["genesis_hash"],
        "supersedes_v36_source_commit": _commit(str(handoff_manifest.get("source_commit", ""))),
        "deployment_id": deployment["deployment_id"],
        "payout_policy_id": payout["policy_id"],
        "algorithm_review_id": algorithm["algorithm_review_id"],
        "v36_handoff_id": handoff["handoff_id"],
        "checks": checks,
        "public_testnet_review_candidate_ready": all(checks.values()),
        "independent_security_review_completed": False,
        "mainnet_launch_authorized": False,
        "production_mainnet_ready": False,
        "production_crkbit_launched": False,
        "notes": str(notes)[:4000],
    }
    manifest["review_bundle_id"] = sha256_hex(canonical_json(manifest))
    return _signed(manifest, key)


def verify_review_bundle(record: dict[str, Any]) -> dict[str, Any]:
    manifest = _verify_signed(record, REVIEW_BUNDLE_FORMAT, "review_bundle_id")
    if manifest.get("independent_security_review_completed") or manifest.get("mainnet_launch_authorized") or manifest.get("production_mainnet_ready") or manifest.get("production_crkbit_launched"):
        raise PowExecutionV37Error("review bundle contains prohibited completion/launch claims")
    _commit(str(manifest.get("source_commit", "")))
    _commit(str(manifest.get("supersedes_v36_source_commit", "")))
    _hash64(str(manifest.get("genesis_hash", "")), "genesis hash")
    if not str(manifest.get("chain_id", "")).strip():
        raise PowExecutionV37Error("review bundle chain ID is empty")
    checks = manifest.get("checks")
    required_checks = {
        "deployment_gate_satisfied",
        "payout_policy_gate_satisfied",
        "algorithm_review_gate_satisfied",
        "v36_external_review_handoff_ready",
        "minimum_four_nodes",
        "production_launch_not_claimed",
    }
    if not isinstance(checks, dict) or set(checks) != required_checks:
        raise PowExecutionV37Error("review bundle checks are malformed")
    if bool(manifest.get("public_testnet_review_candidate_ready")) != all(bool(value) for value in checks.values()):
        raise PowExecutionV37Error("review bundle candidate result mismatch")
    return {
        "valid": True,
        "review_bundle_id": manifest["review_bundle_id"],
        "public_testnet_review_candidate_ready": bool(manifest.get("public_testnet_review_candidate_ready")),
        "independent_security_review_completed": False,
        "production_mainnet_ready": False,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PowExecutionV37Error("JSON file must contain an object")
    return value
