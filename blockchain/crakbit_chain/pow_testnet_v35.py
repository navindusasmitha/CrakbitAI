from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

from .crypto import KeyPair, canonical_json, sha256_hex, verify_signature

HOST_ATTESTATION_FORMAT = "crakbit-pow-host-attestation-v35/1"
OBSERVATION_FORMAT = "crakbit-pow-node-observation-v35/1"
SOAK_FORMAT = "crakbit-pow-soak-summary-v35/1"
FAULT_FORMAT = "crakbit-pow-fault-campaign-v35/1"
GATE_FORMAT = "crakbit-pow-public-testnet-gate-v35/1"
FREEZE_FORMAT = "crakbit-pow-testnet-freeze-v35/1"

REQUIRED_FAULT_KINDS = {"restart", "partition", "reconnect", "invalid-block", "invalid-tx", "load"}
SOAK_LEVELS = {"24h": 24 * 3600, "72h": 72 * 3600, "7d": 7 * 24 * 3600}


class PowTestnetV35Error(ValueError):
    pass


def _valid_commit(value: str) -> str:
    value = str(value).strip().lower()
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise PowTestnetV35Error("source commit must be an exact 40-character Git SHA")
    return value


def _signed(manifest: dict[str, Any], key: KeyPair) -> dict[str, Any]:
    payload = canonical_json({"domain": manifest["format"], "manifest": manifest})
    return {"manifest": manifest, "signer": key.address, "public_key": key.public_key_b64, "signature": key.sign(payload)}


def _verify(record: dict[str, Any], expected: str) -> dict[str, Any]:
    manifest = record.get("manifest")
    if not isinstance(manifest, dict) or manifest.get("format") != expected:
        raise PowTestnetV35Error("unexpected evidence format")
    if not verify_signature(str(record.get("public_key", "")), canonical_json({"domain": expected, "manifest": manifest}), str(record.get("signature", ""))):
        raise PowTestnetV35Error("invalid evidence signature")
    return manifest


def build_host_attestation(*, key_path: str | Path, operator_id: str, node_id: str, provider: str, region: str, rpc_url: str, p2p_endpoint: str, source_commit: str, package_version: str, chain_id: str, genesis_hash: str, independently_managed: bool, miner_role: bool = False, pool_role: bool = False) -> dict[str, Any]:
    key = KeyPair.load(key_path)
    values = [operator_id, node_id, provider, region, rpc_url, p2p_endpoint, package_version, chain_id, genesis_hash]
    if not all(str(v).strip() for v in values):
        raise PowTestnetV35Error("host attestation fields may not be empty")
    if not str(rpc_url).startswith(("http://", "https://")):
        raise PowTestnetV35Error("rpc_url must use http(s)")
    if len(str(genesis_hash)) != 64:
        raise PowTestnetV35Error("genesis hash must be 64 hex characters")
    manifest = {
        "format": HOST_ATTESTATION_FORMAT,
        "recorded_at_unix": int(time.time()),
        "operator_id": str(operator_id), "node_id": str(node_id), "provider": str(provider), "region": str(region),
        "rpc_url": str(rpc_url), "p2p_endpoint": str(p2p_endpoint), "source_commit": _valid_commit(source_commit),
        "package_version": str(package_version), "chain_id": str(chain_id), "genesis_hash": str(genesis_hash).lower(),
        "independently_managed": bool(independently_managed), "miner_role": bool(miner_role), "pool_role": bool(pool_role),
        "contains_secrets": False, "operator_self_attested": True, "independently_verified": False, "production_mainnet_ready": False,
    }
    manifest["attestation_id"] = sha256_hex(canonical_json(manifest))
    return _signed(manifest, key)


def verify_host_attestation(record: dict[str, Any]) -> dict[str, Any]:
    m = _verify(record, HOST_ATTESTATION_FORMAT)
    body = dict(m); aid = body.pop("attestation_id", "")
    if aid != sha256_hex(canonical_json(body)):
        raise PowTestnetV35Error("host attestation ID mismatch")
    return {"valid": True, "attestation_id": aid, "operator_id": m["operator_id"], "node_id": m["node_id"], "production_mainnet_ready": False}


def probe_node(rpc_url: str, *, timeout_seconds: float = 8.0) -> dict[str, Any]:
    base = str(rpc_url).rstrip("/")
    started = time.time()
    with httpx.Client(timeout=float(timeout_seconds), follow_redirects=False) as client:
        info_response = client.get(base + "/pow/v2/info")
        info_response.raise_for_status()
        peers_response = client.get(base + "/pow/v2/peers")
        peers_response.raise_for_status()
        info = info_response.json(); peers = peers_response.json()
    best_hash = str(info.get("best_block_hash", info.get("block_hash", info.get("tip_hash", ""))))
    return {
        "format": OBSERVATION_FORMAT,
        "observed_at_unix": int(time.time()), "rpc_url": base, "reachable": True,
        "latency_ms": int((time.time() - started) * 1000), "chain_id": str(info.get("chain_id", "")),
        "genesis_hash": str(info.get("genesis_hash", "")), "height": int(info.get("height", 0)),
        "best_block_hash": best_hash,
        "chainwork": str(info.get("chainwork", "0")), "pow_algo": str(info.get("pow_algo", "")),
        "peer_count": int(peers.get("peer_count", 0)), "node_id": str(peers.get("node_id", "")),
        "production_mainnet_ready": False,
    }


def evaluate_convergence(observations: list[dict[str, Any]], *, maximum_height_lag: int = 2) -> dict[str, Any]:
    good = [o for o in observations if o.get("format") == OBSERVATION_FORMAT and o.get("reachable")]
    if not good:
        raise PowTestnetV35Error("no reachable node observations")
    chain_ids = {str(o.get("chain_id")) for o in good}; genesis = {str(o.get("genesis_hash")) for o in good}; algos = {str(o.get("pow_algo")) for o in good}
    heights = [int(o.get("height", 0)) for o in good]
    same_height: dict[int, set[str]] = {}
    for o in good:
        same_height.setdefault(int(o["height"]), set()).add(str(o.get("best_block_hash", "")))
    conflicts = [{"height": h, "hashes": sorted(v)} for h, v in sorted(same_height.items()) if len(v) > 1 and "" not in v]
    checks = {
        "at_least_four_nodes": len(good) >= 4, "single_chain_id": len(chain_ids) == 1,
        "single_genesis": len(genesis) == 1, "single_pow_algorithm": len(algos) == 1,
        "height_lag_within_limit": max(heights) - min(heights) <= int(maximum_height_lag), "same_height_tip_consistent": not conflicts,
    }
    return {"format": "crakbit-pow-convergence-v35/1", "checked_at_unix": int(time.time()), "node_count": len(good), "checks": checks, "conflicts": conflicts, "converged": all(checks.values()), "production_mainnet_ready": False}


def summarize_soak(samples: list[dict[str, Any]], *, required_level: str = "24h") -> dict[str, Any]:
    if required_level not in SOAK_LEVELS or len(samples) < 2:
        raise PowTestnetV35Error("invalid soak level or insufficient samples")
    ordered = sorted(samples, key=lambda x: int(x["observed_at_unix"]))
    duration = int(ordered[-1]["observed_at_unix"]) - int(ordered[0]["observed_at_unix"])
    node_ids = {str(s.get("node_id", "")) for s in ordered if s.get("node_id")}
    failures = [s for s in ordered if not s.get("reachable", True)]
    result = {
        "format": SOAK_FORMAT, "required_level": required_level, "required_seconds": SOAK_LEVELS[required_level],
        "actual_seconds": duration, "sample_count": len(samples), "unique_nodes_observed": len(node_ids),
        "unreachable_samples": len(failures), "duration_gate_satisfied": duration >= SOAK_LEVELS[required_level],
        "availability_gate_satisfied": not failures, "production_mainnet_ready": False,
    }
    result["soak_gate_satisfied"] = result["duration_gate_satisfied"] and result["availability_gate_satisfied"]
    return result


def build_fault_campaign(*, kinds: list[str], recovered: bool, higher_work_reorg_observed: bool, partition_convergence_observed: bool, invalid_work_rejected: bool, notes: str = "") -> dict[str, Any]:
    normalized = {str(k).strip().lower() for k in kinds}
    unknown = normalized - REQUIRED_FAULT_KINDS
    if unknown:
        raise PowTestnetV35Error(f"unsupported fault kinds: {sorted(unknown)}")
    checks = {
        "required_fault_kinds_executed": REQUIRED_FAULT_KINDS.issubset(normalized), "all_faults_recovered": bool(recovered),
        "higher_work_reorg_observed": bool(higher_work_reorg_observed), "partition_convergence_observed": bool(partition_convergence_observed),
        "invalid_work_rejected": bool(invalid_work_rejected),
    }
    return {"format": FAULT_FORMAT, "recorded_at_unix": int(time.time()), "fault_kinds": sorted(normalized), "checks": checks, "fault_gate_satisfied": all(checks.values()), "notes": str(notes), "authorized_infrastructure_only": True, "production_mainnet_ready": False}


def build_public_testnet_gate(*, key_path: str | Path, host_attestations: list[dict[str, Any]], convergence: dict[str, Any], soak: dict[str, Any], fault_campaign: dict[str, Any], minimum_hosts: int = 4) -> dict[str, Any]:
    key = KeyPair.load(key_path)
    manifests = []
    for record in host_attestations:
        verify_host_attestation(record); manifests.append(record["manifest"])
    operators = {m["operator_id"] for m in manifests}; nodes = {m["node_id"] for m in manifests}; signers = {r["signer"] for r in host_attestations}
    providers = {m["provider"] for m in manifests}; regions = {m["region"] for m in manifests}
    commits = {m["source_commit"] for m in manifests}; packages = {m["package_version"] for m in manifests}; chains = {m["chain_id"] for m in manifests}; genesis = {m["genesis_hash"] for m in manifests}
    miner_ops = {m["operator_id"] for m in manifests if m.get("miner_role")}; pool_ops = {m["operator_id"] for m in manifests if m.get("pool_role")}
    checks = {
        "minimum_hosts": len(manifests) >= int(minimum_hosts), "unique_nodes": len(nodes) == len(manifests),
        "unique_operators": len(operators) == len(manifests), "unique_evidence_signers": len(signers) == len(manifests),
        "provider_diversity": len(providers) >= 2, "region_diversity": len(regions) >= 2,
        "independent_management_asserted": all(bool(m["independently_managed"]) for m in manifests),
        "single_source_commit": len(commits) == 1, "single_package": len(packages) == 1, "single_chain": len(chains) == 1, "single_genesis": len(genesis) == 1,
        "convergence_gate": bool(convergence.get("converged")), "soak_gate": bool(soak.get("soak_gate_satisfied")),
        "fault_gate": bool(fault_campaign.get("fault_gate_satisfied")), "multiple_miner_operators": len(miner_ops) >= 2,
        "pool_or_solo_diversity": len(pool_ops | miner_ops) >= 2,
    }
    manifest = {
        "format": GATE_FORMAT, "recorded_at_unix": int(time.time()), "checks": checks, "public_testnet_gate_satisfied": all(checks.values()),
        "host_attestation_ids": sorted(m["attestation_id"] for m in manifests), "source_commit": next(iter(commits)) if len(commits) == 1 else None,
        "package_version": next(iter(packages)) if len(packages) == 1 else None, "chain_id": next(iter(chains)) if len(chains) == 1 else None,
        "genesis_hash": next(iter(genesis)) if len(genesis) == 1 else None, "operator_self_attestations_used": True,
        "independent_security_review_completed": False, "production_mainnet_ready": False,
    }
    manifest["gate_id"] = sha256_hex(canonical_json(manifest))
    return _signed(manifest, key)


def verify_public_testnet_gate(record: dict[str, Any]) -> dict[str, Any]:
    m = _verify(record, GATE_FORMAT); body = dict(m); gid = body.pop("gate_id", "")
    if gid != sha256_hex(canonical_json(body)):
        raise PowTestnetV35Error("public-testnet gate ID mismatch")
    return {"valid": True, "gate_id": gid, "public_testnet_gate_satisfied": bool(m["public_testnet_gate_satisfied"]), "production_mainnet_ready": False}


def build_testnet_freeze(*, key_path: str | Path, gate_record: dict[str, Any], source_commit: str, notes: str = "") -> dict[str, Any]:
    key = KeyPair.load(key_path); gate = verify_public_testnet_gate(gate_record)
    if not gate["public_testnet_gate_satisfied"]:
        raise PowTestnetV35Error("cannot freeze an unsatisfied public-testnet gate")
    gm = gate_record["manifest"]
    if _valid_commit(source_commit) != gm["source_commit"]:
        raise PowTestnetV35Error("freeze source commit differs from public-testnet gate")
    manifest = {
        "format": FREEZE_FORMAT, "recorded_at_unix": int(time.time()), "source_commit": gm["source_commit"],
        "package_version": gm["package_version"], "chain_id": gm["chain_id"], "genesis_hash": gm["genesis_hash"],
        "public_testnet_gate_id": gate["gate_id"], "notes": str(notes), "candidate_frozen_for_public_testnet_review": True,
        "independent_security_review_completed": False, "production_mainnet_ready": False, "production_crkbit_launched": False,
    }
    manifest["freeze_id"] = sha256_hex(canonical_json(manifest))
    return _signed(manifest, key)


def verify_testnet_freeze(record: dict[str, Any]) -> dict[str, Any]:
    m = _verify(record, FREEZE_FORMAT); body = dict(m); fid = body.pop("freeze_id", "")
    if fid != sha256_hex(canonical_json(body)):
        raise PowTestnetV35Error("testnet freeze ID mismatch")
    if m.get("production_mainnet_ready") or m.get("production_crkbit_launched") or m.get("independent_security_review_completed"):
        raise PowTestnetV35Error("freeze contains prohibited production/review claims")
    return {"valid": True, "freeze_id": fid, "candidate_frozen_for_public_testnet_review": True, "production_mainnet_ready": False}


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PowTestnetV35Error("JSON file must contain an object")
    return value
