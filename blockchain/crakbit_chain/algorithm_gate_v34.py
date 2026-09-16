from __future__ import annotations

import json
import platform
import time
from pathlib import Path
from typing import Any

from .crypto import KeyPair, canonical_json, sha256_hex, verify_signature

BENCHMARK_FORMAT = "crakbit-pow-benchmark-v34/1"
BENCHMARK_GATE_FORMAT = "crakbit-pow-benchmark-gate-v34/1"
ALGORITHM_DECISION_FORMAT = "crakbit-pow-algorithm-decision-v34/1"


class AlgorithmGateV34Error(ValueError):
    pass


def _signed_manifest(manifest: dict[str, Any], key: KeyPair) -> dict[str, Any]:
    payload = canonical_json({"domain": manifest["format"], "manifest": manifest})
    return {
        "manifest": manifest,
        "signer": key.address,
        "public_key": key.public_key_b64,
        "signature": key.sign(payload),
    }


def _verify_signed(record: dict[str, Any], expected_format: str) -> dict[str, Any]:
    manifest = record.get("manifest")
    if not isinstance(manifest, dict) or str(manifest.get("format")) != expected_format:
        raise AlgorithmGateV34Error("invalid signed record format")
    public_key = str(record.get("public_key", ""))
    signature = str(record.get("signature", ""))
    payload = canonical_json({"domain": expected_format, "manifest": manifest})
    if not verify_signature(public_key, payload, signature):
        raise AlgorithmGateV34Error("invalid evidence signature")
    return manifest


def build_benchmark_record(
    *,
    signing_key_path: str | Path,
    machine_id: str,
    cpu_model: str,
    logical_threads: int,
    ram_mib: int,
    scrypt_hps: float,
    randomx_hps: float | None,
    randomx_mode: str | None,
    randomx_selftest_passed: bool,
    randomx_library_sha256: str | None = None,
    gpu_model: str | None = None,
    gpu_randomx_hps: float | None = None,
    notes: str = "",
) -> dict[str, Any]:
    key = KeyPair.load(signing_key_path)
    machine_id = str(machine_id).strip()
    cpu_model = str(cpu_model).strip()
    logical_threads = int(logical_threads)
    ram_mib = int(ram_mib)
    scrypt_hps = float(scrypt_hps)
    if not machine_id or not cpu_model:
        raise AlgorithmGateV34Error("machine ID and CPU model are required")
    if logical_threads < 1 or ram_mib < 256 or scrypt_hps <= 0:
        raise AlgorithmGateV34Error("invalid benchmark hardware/scrypt measurements")
    if randomx_hps is not None and float(randomx_hps) <= 0:
        raise AlgorithmGateV34Error("RandomX hashrate must be positive when provided")
    if gpu_randomx_hps is not None and float(gpu_randomx_hps) < 0:
        raise AlgorithmGateV34Error("GPU RandomX hashrate may not be negative")
    if randomx_hps is not None and randomx_mode not in {"light", "fast"}:
        raise AlgorithmGateV34Error("RandomX mode must be light or fast when RandomX is benchmarked")
    if randomx_hps is not None and not randomx_selftest_passed:
        raise AlgorithmGateV34Error("RandomX benchmark evidence requires a passing native self-test")
    if randomx_library_sha256 is not None:
        value = str(randomx_library_sha256).lower()
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise AlgorithmGateV34Error("RandomX library SHA-256 must be 64 hex characters")

    manifest = {
        "format": BENCHMARK_FORMAT,
        "recorded_at_unix": int(time.time()),
        "machine_id": machine_id,
        "platform": platform.system().lower(),
        "platform_release": platform.release(),
        "machine_arch": platform.machine(),
        "cpu_model": cpu_model,
        "logical_threads": logical_threads,
        "ram_mib": ram_mib,
        "gpu_model": None if not gpu_model else str(gpu_model),
        "scrypt_hps": scrypt_hps,
        "randomx_hps": None if randomx_hps is None else float(randomx_hps),
        "randomx_mode": randomx_mode,
        "randomx_selftest_passed": bool(randomx_selftest_passed),
        "randomx_library_sha256": randomx_library_sha256,
        "gpu_randomx_hps": None if gpu_randomx_hps is None else float(gpu_randomx_hps),
        "notes": str(notes)[:2000],
        "measurement_self_attested": True,
        "production_mainnet_ready": False,
    }
    manifest["benchmark_id"] = sha256_hex(canonical_json(manifest))
    return _signed_manifest(manifest, key)


def verify_benchmark_record(record: dict[str, Any]) -> dict[str, Any]:
    manifest = _verify_signed(record, BENCHMARK_FORMAT)
    benchmark_id = str(manifest.get("benchmark_id", ""))
    body = dict(manifest)
    body.pop("benchmark_id", None)
    if benchmark_id != sha256_hex(canonical_json(body)):
        raise AlgorithmGateV34Error("benchmark ID mismatch")
    return {
        "valid": True,
        "benchmark_id": benchmark_id,
        "machine_id": manifest["machine_id"],
        "randomx_measured": manifest.get("randomx_hps") is not None,
        "production_mainnet_ready": False,
    }


def build_benchmark_gate(
    *,
    signing_key_path: str | Path,
    records: list[dict[str, Any]],
    minimum_unique_machines: int = 2,
    require_randomx_on_every_machine: bool = True,
) -> dict[str, Any]:
    key = KeyPair.load(signing_key_path)
    if not records:
        raise AlgorithmGateV34Error("benchmark gate requires benchmark records")
    manifests: list[dict[str, Any]] = []
    for record in records:
        verify_benchmark_record(record)
        manifests.append(record["manifest"])
    machine_ids = {str(item["machine_id"]) for item in manifests}
    signers = {str(record["signer"]) for record in records}
    randomx_count = sum(1 for item in manifests if item.get("randomx_hps") is not None and item.get("randomx_selftest_passed"))
    platform_count = len({str(item.get("platform")) for item in manifests})
    minimum_unique_machines = max(1, int(minimum_unique_machines))
    satisfied = len(machine_ids) >= minimum_unique_machines
    if require_randomx_on_every_machine:
        satisfied = satisfied and randomx_count == len(manifests)
    manifest = {
        "format": BENCHMARK_GATE_FORMAT,
        "recorded_at_unix": int(time.time()),
        "benchmark_ids": sorted(str(item["benchmark_id"]) for item in manifests),
        "unique_machines": len(machine_ids),
        "unique_evidence_signers": len(signers),
        "unique_platforms": platform_count,
        "randomx_benchmark_count": randomx_count,
        "minimum_unique_machines": minimum_unique_machines,
        "require_randomx_on_every_machine": bool(require_randomx_on_every_machine),
        "benchmark_gate_satisfied": bool(satisfied),
        "algorithm_selected": False,
        "human_algorithm_decision_required": True,
        "production_mainnet_ready": False,
    }
    manifest["gate_id"] = sha256_hex(canonical_json(manifest))
    return _signed_manifest(manifest, key)


def verify_benchmark_gate(record: dict[str, Any]) -> dict[str, Any]:
    manifest = _verify_signed(record, BENCHMARK_GATE_FORMAT)
    gate_id = str(manifest.get("gate_id", ""))
    body = dict(manifest)
    body.pop("gate_id", None)
    if gate_id != sha256_hex(canonical_json(body)):
        raise AlgorithmGateV34Error("benchmark gate ID mismatch")
    return {
        "valid": True,
        "gate_id": gate_id,
        "benchmark_gate_satisfied": bool(manifest.get("benchmark_gate_satisfied")),
        "human_algorithm_decision_required": True,
        "production_mainnet_ready": False,
    }


def build_algorithm_decision(
    *,
    signing_key_path: str | Path,
    benchmark_gate: dict[str, Any],
    decision: str,
    rationale: str,
) -> dict[str, Any]:
    key = KeyPair.load(signing_key_path)
    gate = verify_benchmark_gate(benchmark_gate)
    decision = str(decision).lower()
    if decision not in {"hold", "scrypt", "randomx"}:
        raise AlgorithmGateV34Error("decision must be hold, scrypt, or randomx")
    if decision != "hold" and not gate["benchmark_gate_satisfied"]:
        raise AlgorithmGateV34Error("cannot select an algorithm before the benchmark gate is satisfied")
    manifest = {
        "format": ALGORITHM_DECISION_FORMAT,
        "recorded_at_unix": int(time.time()),
        "benchmark_gate_id": gate["gate_id"],
        "decision": decision,
        "rationale": str(rationale)[:4000],
        "consensus_activation_authorized": False,
        "requires_separate_versioned_activation": decision == "randomx",
        "production_mainnet_ready": False,
    }
    manifest["decision_id"] = sha256_hex(canonical_json(manifest))
    return _signed_manifest(manifest, key)


def verify_algorithm_decision(record: dict[str, Any]) -> dict[str, Any]:
    manifest = _verify_signed(record, ALGORITHM_DECISION_FORMAT)
    decision_id = str(manifest.get("decision_id", ""))
    body = dict(manifest)
    body.pop("decision_id", None)
    if decision_id != sha256_hex(canonical_json(body)):
        raise AlgorithmGateV34Error("algorithm decision ID mismatch")
    return {
        "valid": True,
        "decision_id": decision_id,
        "decision": manifest["decision"],
        "consensus_activation_authorized": False,
        "production_mainnet_ready": False,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AlgorithmGateV34Error("JSON file must contain an object")
    return value
