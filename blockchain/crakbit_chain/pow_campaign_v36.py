from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Iterable

from .crypto import KeyPair, canonical_json, sha256_hex, verify_signature
from .pow_testnet_v35 import OBSERVATION_FORMAT, SOAK_LEVELS, evaluate_convergence, probe_node

CAMPAIGN_ENTRY_FORMAT = "crakbit-pow-campaign-entry-v36/1"
CAMPAIGN_SUMMARY_FORMAT = "crakbit-pow-campaign-summary-v36/1"


class PowCampaignV36Error(ValueError):
    pass


def _signed_entry(manifest: dict[str, Any], key: KeyPair) -> dict[str, Any]:
    payload = canonical_json({"domain": CAMPAIGN_ENTRY_FORMAT, "manifest": manifest})
    return {
        "manifest": manifest,
        "signer": key.address,
        "public_key": key.public_key_b64,
        "signature": key.sign(payload),
    }


def _entry_hash(record: dict[str, Any]) -> str:
    return sha256_hex(canonical_json(record))


def verify_campaign_entry(record: dict[str, Any], *, expected_previous_hash: str | None = None) -> dict[str, Any]:
    manifest = record.get("manifest")
    if not isinstance(manifest, dict) or manifest.get("format") != CAMPAIGN_ENTRY_FORMAT:
        raise PowCampaignV36Error("unexpected campaign entry format")
    if not verify_signature(
        str(record.get("public_key", "")),
        canonical_json({"domain": CAMPAIGN_ENTRY_FORMAT, "manifest": manifest}),
        str(record.get("signature", "")),
    ):
        raise PowCampaignV36Error("invalid campaign entry signature")
    body = dict(manifest)
    entry_id = str(body.pop("entry_id", ""))
    if entry_id != sha256_hex(canonical_json(body)):
        raise PowCampaignV36Error("campaign entry ID mismatch")
    if expected_previous_hash is not None and str(manifest.get("previous_entry_hash")) != expected_previous_hash:
        raise PowCampaignV36Error("campaign hash chain mismatch")
    observations = manifest.get("observations")
    if not isinstance(observations, list) or not observations:
        raise PowCampaignV36Error("campaign entry has no observations")
    for observation in observations:
        if not isinstance(observation, dict) or observation.get("format") != OBSERVATION_FORMAT:
            raise PowCampaignV36Error("campaign entry contains an invalid node observation")
    return {
        "valid": True,
        "entry_id": entry_id,
        "entry_hash": _entry_hash(record),
        "observed_at_unix": int(manifest["observed_at_unix"]),
        "observation_count": len(observations),
        "production_mainnet_ready": False,
    }


class CampaignLogV36:
    """Append-only, signed and hash-chained observation log.

    Timestamps are generated locally at collection time and are never supplied by
    the caller. This prevents the helper from manufacturing elapsed soak duration.
    The evidence key is separate from wallet/mining/P2P keys.
    """

    def __init__(self, log_path: str | Path, key_path: str | Path):
        self.path = Path(log_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.key = KeyPair.load(key_path)

    def _records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line_no, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise PowCampaignV36Error(f"invalid JSONL at line {line_no}") from exc
            if not isinstance(value, dict):
                raise PowCampaignV36Error(f"campaign line {line_no} is not an object")
            records.append(value)
        return records

    def append_observations(self, observations: list[dict[str, Any]], *, label: str = "") -> dict[str, Any]:
        if not observations:
            raise PowCampaignV36Error("at least one observation is required")
        existing = self._records()
        previous_hash: str | None = None
        if existing:
            previous_hash = _entry_hash(existing[-1])
            verify_campaign_log(existing)
        now = int(time.time())
        manifest = {
            "format": CAMPAIGN_ENTRY_FORMAT,
            "observed_at_unix": now,
            "label": str(label)[:256],
            "previous_entry_hash": previous_hash,
            "observations": observations,
            "collector_self_attested": True,
            "independent_operator_status_not_cryptographically_proven": True,
            "production_mainnet_ready": False,
        }
        manifest["entry_id"] = sha256_hex(canonical_json(manifest))
        record = _signed_entry(manifest, self.key)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
        return {
            "saved": str(self.path),
            "entry_id": manifest["entry_id"],
            "entry_hash": _entry_hash(record),
            "observed_at_unix": now,
            "observation_count": len(observations),
            "production_mainnet_ready": False,
        }

    def probe_and_append(
        self,
        rpc_urls: Iterable[str],
        *,
        timeout_seconds: float = 8.0,
        label: str = "",
    ) -> dict[str, Any]:
        observations: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for rpc_url in rpc_urls:
            url = str(rpc_url).strip()
            if not url:
                continue
            try:
                observations.append(probe_node(url, timeout_seconds=timeout_seconds))
            except Exception as exc:
                errors.append({"rpc_url": url, "error": str(exc)[:500]})
                observations.append({
                    "format": OBSERVATION_FORMAT,
                    "observed_at_unix": int(time.time()),
                    "rpc_url": url.rstrip("/"),
                    "reachable": False,
                    "error": str(exc)[:500],
                    "production_mainnet_ready": False,
                })
        result = self.append_observations(observations, label=label)
        result["probe_errors"] = errors
        return result


def load_campaign_log(path: str | Path) -> list[dict[str, Any]]:
    target = Path(path)
    if not target.exists():
        raise PowCampaignV36Error("campaign log does not exist")
    records: list[dict[str, Any]] = []
    for line_no, line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PowCampaignV36Error(f"invalid campaign JSONL at line {line_no}") from exc
        if not isinstance(value, dict):
            raise PowCampaignV36Error(f"campaign line {line_no} is not an object")
        records.append(value)
    return records


def verify_campaign_log(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        raise PowCampaignV36Error("campaign log is empty")
    previous_hash: str | None = None
    previous_time: int | None = None
    signers: set[str] = set()
    for index, record in enumerate(records):
        verified = verify_campaign_entry(record, expected_previous_hash=previous_hash)
        observed_at = int(verified["observed_at_unix"])
        if previous_time is not None and observed_at < previous_time:
            raise PowCampaignV36Error(f"campaign timestamp moved backwards at entry {index}")
        previous_time = observed_at
        previous_hash = verified["entry_hash"]
        signers.add(str(record.get("signer", "")))
    return {
        "valid": True,
        "entry_count": len(records),
        "first_observed_at_unix": int(records[0]["manifest"]["observed_at_unix"]),
        "last_observed_at_unix": int(records[-1]["manifest"]["observed_at_unix"]),
        "last_entry_hash": previous_hash,
        "collector_signer_count": len(signers),
        "production_mainnet_ready": False,
    }


def summarize_campaign(
    records: list[dict[str, Any]],
    *,
    required_level: str = "24h",
    minimum_nodes: int = 4,
    minimum_sample_success_ratio: float = 0.99,
    maximum_height_lag: int = 2,
) -> dict[str, Any]:
    if required_level not in SOAK_LEVELS:
        raise PowCampaignV36Error("required level must be 24h, 72h, or 7d")
    if minimum_nodes < 1:
        raise PowCampaignV36Error("minimum nodes must be positive")
    if not 0 < float(minimum_sample_success_ratio) <= 1:
        raise PowCampaignV36Error("sample success ratio must be in (0,1]")
    verified = verify_campaign_log(records)
    first = int(verified["first_observed_at_unix"])
    last = int(verified["last_observed_at_unix"])
    duration = max(0, last - first)

    sample_results: list[dict[str, Any]] = []
    chain_ids: set[str] = set()
    genesis_hashes: set[str] = set()
    pow_algos: set[str] = set()
    observed_node_ids: set[str] = set()
    successful_samples = 0
    reachable_observations = 0
    total_observations = 0

    for record in records:
        observations = list(record["manifest"]["observations"])
        total_observations += len(observations)
        reachable = [item for item in observations if item.get("reachable")]
        reachable_observations += len(reachable)
        for item in reachable:
            if item.get("chain_id"):
                chain_ids.add(str(item["chain_id"]))
            if item.get("genesis_hash"):
                genesis_hashes.add(str(item["genesis_hash"]))
            if item.get("pow_algo"):
                pow_algos.add(str(item["pow_algo"]))
            if item.get("node_id"):
                observed_node_ids.add(str(item["node_id"]))
        try:
            convergence = evaluate_convergence(reachable, maximum_height_lag=maximum_height_lag)
        except Exception as exc:
            convergence = {"converged": False, "error": str(exc)[:500]}
        sample_ok = len(reachable) >= minimum_nodes and bool(convergence.get("converged"))
        if sample_ok:
            successful_samples += 1
        sample_results.append({
            "observed_at_unix": int(record["manifest"]["observed_at_unix"]),
            "reachable_nodes": len(reachable),
            "sample_ok": sample_ok,
            "converged": bool(convergence.get("converged")),
        })

    sample_ratio = successful_samples / max(1, len(records))
    observation_ratio = reachable_observations / max(1, total_observations)
    checks = {
        "duration_gate": duration >= SOAK_LEVELS[required_level],
        "minimum_unique_nodes": len(observed_node_ids) >= minimum_nodes,
        "sample_success_ratio": sample_ratio >= float(minimum_sample_success_ratio),
        "observation_availability_ratio": observation_ratio >= float(minimum_sample_success_ratio),
        "single_chain_id": len(chain_ids) == 1,
        "single_genesis": len(genesis_hashes) == 1,
        "single_pow_algorithm": len(pow_algos) == 1,
        "hash_chain_valid": bool(verified["valid"]),
    }
    summary = {
        "format": CAMPAIGN_SUMMARY_FORMAT,
        "required_level": required_level,
        "required_seconds": SOAK_LEVELS[required_level],
        "actual_seconds": duration,
        "entry_count": len(records),
        "unique_node_ids": len(observed_node_ids),
        "sample_success_ratio": sample_ratio,
        "observation_availability_ratio": observation_ratio,
        "chain_ids": sorted(chain_ids),
        "genesis_hashes": sorted(genesis_hashes),
        "pow_algorithms": sorted(pow_algos),
        "checks": checks,
        "campaign_gate_satisfied": all(checks.values()),
        "sample_results": sample_results[-200:],
        "last_entry_hash": verified["last_entry_hash"],
        "real_elapsed_time_required": True,
        "production_mainnet_ready": False,
    }
    summary["summary_id"] = sha256_hex(canonical_json(summary))
    return summary
