from __future__ import annotations

import argparse
import json
import sys

from . import cli_v28
from .real_execution_v29 import (
    build_cluster_observation,
    build_fault_result,
    build_genesis_attestation,
    build_genesis_ceremony_gate,
    build_real_evidence_freeze,
    build_real_execution_gate,
    build_soak_evidence,
    load_json,
    probe_and_build_live_host_observation,
    save_json,
    verify_cluster_observation,
    verify_fault_result,
    verify_genesis_attestation,
    verify_genesis_ceremony_gate,
    verify_live_host_observation,
    verify_real_evidence_freeze,
    verify_soak_evidence,
)


def _artifacts(values: list[str]) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for value in values:
        if "=" not in value:
            raise SystemExit("artifact must use ROLE=PATH")
        role, path = value.split("=", 1)
        if not role.strip() or not path.strip():
            raise SystemExit("artifact must use non-empty ROLE=PATH")
        parsed.append((role.strip(), path.strip()))
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.29 real independent-host execution and corroborated evidence tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    host = sub.add_parser("live-host-v29-probe")
    host.add_argument("--key", required=True)
    host.add_argument("--source-commit", required=True)
    host.add_argument("--candidate-identity-sha256", required=True)
    host.add_argument("--application-genesis-sha256", required=True)
    host.add_argument("--consensus-genesis-sha256", required=True)
    host.add_argument("--validator-id", required=True)
    host.add_argument("--operator-id", required=True)
    host.add_argument("--provider", required=True)
    host.add_argument("--region", required=True)
    host.add_argument("--rpc-endpoint", required=True)
    host.add_argument("--expected-chain-id", required=True)
    host.add_argument("--timeout-seconds", type=float, default=5.0)
    host.add_argument("--execution-private-asserted", action="store_true")
    host.add_argument("--abci-private-asserted", action="store_true")
    host.add_argument("--signer-protected-asserted", action="store_true")
    host.add_argument("--output", required=True)
    host.add_argument("--overwrite", action="store_true")

    host_verify = sub.add_parser("live-host-v29-verify")
    host_verify.add_argument("--record", required=True)
    host_verify.add_argument("--expected-signer", default=None)

    cluster = sub.add_parser("cluster-v29-build")
    cluster.add_argument("--key", required=True)
    cluster.add_argument("--host", action="append", required=True)
    cluster.add_argument("--maximum-height-spread", type=int, default=2)
    cluster.add_argument("--maximum-observation-window-ms", type=int, default=300000)
    cluster.add_argument("--output", required=True)
    cluster.add_argument("--overwrite", action="store_true")

    cluster_verify = sub.add_parser("cluster-v29-verify")
    cluster_verify.add_argument("--record", required=True)
    cluster_verify.add_argument("--expected-signer", default=None)

    genesis = sub.add_parser("genesis-attest-v29-build")
    genesis.add_argument("--key", required=True)
    genesis.add_argument("--source-commit", required=True)
    genesis.add_argument("--candidate-identity-sha256", required=True)
    genesis.add_argument("--application-genesis-sha256", required=True)
    genesis.add_argument("--consensus-genesis-sha256", required=True)
    genesis.add_argument("--chain-id", required=True)
    genesis.add_argument("--operator-id", required=True)
    genesis.add_argument("--validator-id", required=True)
    genesis.add_argument("--validator-address", required=True)
    genesis.add_argument("--node-id", required=True)
    genesis.add_argument("--approve", action="store_true")
    genesis.add_argument("--output", required=True)
    genesis.add_argument("--overwrite", action="store_true")

    genesis_verify = sub.add_parser("genesis-attest-v29-verify")
    genesis_verify.add_argument("--record", required=True)
    genesis_verify.add_argument("--expected-signer", default=None)

    genesis_gate = sub.add_parser("genesis-gate-v29-build")
    genesis_gate.add_argument("--key", required=True)
    genesis_gate.add_argument("--attestation", action="append", required=True)
    genesis_gate.add_argument("--output", required=True)
    genesis_gate.add_argument("--overwrite", action="store_true")

    genesis_gate_verify = sub.add_parser("genesis-gate-v29-verify")
    genesis_gate_verify.add_argument("--record", required=True)
    genesis_gate_verify.add_argument("--expected-signer", default=None)

    soak = sub.add_parser("soak-v29-build")
    soak.add_argument("--key", required=True)
    soak.add_argument("--sample", action="append", required=True)
    soak.add_argument("--minimum-duration-seconds", type=int, default=604800)
    soak.add_argument("--minimum-success-ratio", type=float, default=0.99)
    soak.add_argument("--output", required=True)
    soak.add_argument("--overwrite", action="store_true")

    soak_verify = sub.add_parser("soak-v29-verify")
    soak_verify.add_argument("--record", required=True)
    soak_verify.add_argument("--expected-signer", default=None)

    fault = sub.add_parser("fault-result-v29-build")
    fault.add_argument("--key", required=True)
    fault.add_argument("--source-commit", required=True)
    fault.add_argument("--candidate-identity-sha256", required=True)
    fault.add_argument("--fault-type", required=True)
    fault.add_argument("--campaign-id", required=True)
    fault.add_argument("--authorized", action="store_true")
    fault.add_argument("--passed", action="store_true")
    fault.add_argument("--recovery-verified", action="store_true")
    fault.add_argument("--app-hash-reconverged", action="store_true")
    fault.add_argument("--no-data-loss", action="store_true")
    fault.add_argument("--raw-evidence", required=True)
    fault.add_argument("--output", required=True)
    fault.add_argument("--overwrite", action="store_true")

    fault_verify = sub.add_parser("fault-result-v29-verify")
    fault_verify.add_argument("--record", required=True)
    fault_verify.add_argument("--expected-signer", default=None)

    gate = sub.add_parser("real-gate-v29-build")
    gate.add_argument("--release-freeze-v28", required=True)
    gate.add_argument("--rehearsal-gate-v28", required=True)
    gate.add_argument("--cluster", required=True)
    gate.add_argument("--genesis-gate", required=True)
    gate.add_argument("--soak", required=True)
    gate.add_argument("--fault-result", action="append", required=True)
    gate.add_argument("--output", required=True)
    gate.add_argument("--overwrite", action="store_true")

    freeze = sub.add_parser("real-freeze-v29-build")
    freeze.add_argument("--key", required=True)
    freeze.add_argument("--real-gate", required=True)
    freeze.add_argument("--artifact", action="append", default=[], help="ROLE=PATH")
    freeze.add_argument("--output", required=True)
    freeze.add_argument("--overwrite", action="store_true")

    freeze_verify = sub.add_parser("real-freeze-v29-verify")
    freeze_verify.add_argument("--freeze", required=True)
    freeze_verify.add_argument("--expected-signer", default=None)
    return parser


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "live-host-v29-probe":
        result = probe_and_build_live_host_observation(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            candidate_identity_sha256=args.candidate_identity_sha256,
            application_genesis_sha256=args.application_genesis_sha256,
            consensus_genesis_sha256=args.consensus_genesis_sha256,
            validator_id=args.validator_id,
            operator_id=args.operator_id,
            provider=args.provider,
            region=args.region,
            rpc_endpoint=args.rpc_endpoint,
            expected_chain_id=args.expected_chain_id,
            execution_private_asserted=bool(args.execution_private_asserted),
            abci_private_asserted=bool(args.abci_private_asserted),
            signer_protected_asserted=bool(args.signer_protected_asserted),
            timeout_seconds=args.timeout_seconds,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "validator_id": result["manifest"]["validator_id"], "host_gate_satisfied": result["manifest"]["host_gate_satisfied"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["host_gate_satisfied"] else 2

    if args.command == "live-host-v29-verify":
        print(json.dumps(verify_live_host_observation(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "cluster-v29-build":
        result = build_cluster_observation(
            signing_key_path=args.key,
            host_observations=[load_json(path) for path in args.host],
            maximum_height_spread=args.maximum_height_spread,
            maximum_observation_window_ms=args.maximum_observation_window_ms,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "cluster_gate_satisfied": result["manifest"]["cluster_gate_satisfied"], "height_spread": result["manifest"]["height_spread"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["cluster_gate_satisfied"] else 2

    if args.command == "cluster-v29-verify":
        print(json.dumps(verify_cluster_observation(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "genesis-attest-v29-build":
        result = build_genesis_attestation(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            candidate_identity_sha256=args.candidate_identity_sha256,
            application_genesis_sha256=args.application_genesis_sha256,
            consensus_genesis_sha256=args.consensus_genesis_sha256,
            chain_id=args.chain_id,
            operator_id=args.operator_id,
            validator_id=args.validator_id,
            validator_address=args.validator_address,
            node_id=args.node_id,
            approved=bool(args.approve),
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "operator_id": result["manifest"]["operator_id"], "approved": result["manifest"]["approved"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["approved"] else 2

    if args.command == "genesis-attest-v29-verify":
        print(json.dumps(verify_genesis_attestation(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "genesis-gate-v29-build":
        result = build_genesis_ceremony_gate(signing_key_path=args.key, attestations=[load_json(path) for path in args.attestation])
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "genesis_ceremony_gate_satisfied": result["manifest"]["genesis_ceremony_gate_satisfied"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["genesis_ceremony_gate_satisfied"] else 2

    if args.command == "genesis-gate-v29-verify":
        print(json.dumps(verify_genesis_ceremony_gate(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "soak-v29-build":
        result = build_soak_evidence(
            signing_key_path=args.key,
            cluster_samples=[load_json(path) for path in args.sample],
            minimum_duration_seconds=args.minimum_duration_seconds,
            minimum_success_ratio=args.minimum_success_ratio,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "duration_seconds": result["manifest"]["duration_seconds"], "success_ratio": result["manifest"]["success_ratio"], "soak_gate_satisfied": result["manifest"]["soak_gate_satisfied"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["soak_gate_satisfied"] else 2

    if args.command == "soak-v29-verify":
        print(json.dumps(verify_soak_evidence(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "fault-result-v29-build":
        result = build_fault_result(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            candidate_identity_sha256=args.candidate_identity_sha256,
            fault_type=args.fault_type,
            campaign_id=args.campaign_id,
            authorized=bool(args.authorized),
            passed=bool(args.passed),
            recovery_verified=bool(args.recovery_verified),
            app_hash_reconverged=bool(args.app_hash_reconverged),
            no_data_loss=bool(args.no_data_loss),
            raw_evidence_path=args.raw_evidence,
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "fault_type": result["manifest"]["fault_type"], "fault_gate_satisfied": result["manifest"]["fault_gate_satisfied"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["manifest"]["fault_gate_satisfied"] else 2

    if args.command == "fault-result-v29-verify":
        print(json.dumps(verify_fault_result(load_json(args.record), expected_signer=args.expected_signer), indent=2))
        return 0

    if args.command == "real-gate-v29-build":
        result = build_real_execution_gate(
            release_freeze_v28=load_json(args.release_freeze_v28),
            rehearsal_gate_v28=load_json(args.rehearsal_gate_v28),
            cluster_observation=load_json(args.cluster),
            genesis_ceremony_gate=load_json(args.genesis_gate),
            soak_evidence=load_json(args.soak),
            fault_results=[load_json(path) for path in args.fault_result],
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "real_execution_gate_satisfied": result["real_execution_gate_satisfied"], "covered_fault_types": result["covered_fault_types"], "production_mainnet_ready": False}, indent=2))
        return 0 if result["real_execution_gate_satisfied"] else 2

    if args.command == "real-freeze-v29-build":
        result = build_real_evidence_freeze(
            signing_key_path=args.key,
            real_execution_gate=load_json(args.real_gate),
            artifacts=_artifacts(list(args.artifact)),
        )
        save_json(result, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, "signer": result["signer"], "frozen_from_real_execution_evidence": True, "production_mainnet_ready": False}, indent=2))
        return 0

    print(json.dumps(verify_real_evidence_freeze(load_json(args.freeze), expected_signer=args.expected_signer), indent=2))
    return 0


def main() -> int:
    commands = {
        "live-host-v29-probe", "live-host-v29-verify",
        "cluster-v29-build", "cluster-v29-verify",
        "genesis-attest-v29-build", "genesis-attest-v29-verify",
        "genesis-gate-v29-build", "genesis-gate-v29-verify",
        "soak-v29-build", "soak-v29-verify",
        "fault-result-v29-build", "fault-result-v29-verify",
        "real-gate-v29-build", "real-freeze-v29-build", "real-freeze-v29-verify",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        return _run(sys.argv[1:])
    return int(cli_v28.main())


if __name__ == "__main__":
    raise SystemExit(main())
