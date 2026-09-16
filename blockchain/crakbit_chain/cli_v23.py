from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import cli_v22
from .public_testnet_evidence_v23 import (
    build_operations_evidence,
    build_readiness_report,
    save_json,
    verify_operations_evidence,
)
from .public_testnet_monitor_v23 import (
    observe_public_testnet,
    run_soak_collection,
    summarize_soak,
)
from .public_testnet_v23 import (
    build_genesis_bundle,
    build_public_testnet_inventory,
    export_validator_public_identity,
    load_inventory,
    render_operator_deployment_bundles,
)


def _read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crakchain",
        description="Crakbit v0.23 public-testnet deployment, monitoring and evidence tooling",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    identity = sub.add_parser("validator-identity-v23-export")
    identity.add_argument("--home", required=True)
    identity.add_argument("--cometbft", default="cometbft")
    identity.add_argument("--name", required=True)
    identity.add_argument("--operator-id", required=True)
    identity.add_argument("--provider", required=True)
    identity.add_argument("--region", required=True)
    identity.add_argument("--p2p-host", required=True)
    identity.add_argument("--p2p-port", type=int, default=26656)
    identity.add_argument("--monitor-rpc-url", default="")
    identity.add_argument("--output", required=True)
    identity.add_argument("--overwrite", action="store_true")

    inventory = sub.add_parser("public-testnet-inventory-build")
    inventory.add_argument("--chain-id", required=True)
    inventory.add_argument("--network-name", required=True)
    inventory.add_argument("--identity", action="append", required=True)
    inventory.add_argument("--output", required=True)
    inventory.add_argument("--overwrite", action="store_true")

    inventory_check = sub.add_parser("public-testnet-inventory-check")
    inventory_check.add_argument("--inventory", required=True)

    genesis = sub.add_parser("public-testnet-genesis-build")
    genesis.add_argument("--inventory", required=True)
    genesis.add_argument("--cometbft-template", required=True)
    genesis.add_argument("--treasury-address", required=True)
    genesis.add_argument("--output", required=True)
    genesis.add_argument("--max-supply", type=int, default=21_000_000 * 100_000_000)
    genesis.add_argument("--min-fee", type=int, default=1000)
    genesis.add_argument("--overwrite", action="store_true")

    bundles = sub.add_parser("public-testnet-bundles-build")
    bundles.add_argument("--inventory", required=True)
    bundles.add_argument("--genesis-bundle", required=True)
    bundles.add_argument("--output", required=True)
    bundles.add_argument("--repo-dir", default="/opt/crakbit")
    bundles.add_argument("--data-root", default="/var/lib/crakbit")
    bundles.add_argument("--cometbft-binary", default="/usr/local/bin/cometbft")
    bundles.add_argument("--overwrite", action="store_true")

    observe = sub.add_parser("public-testnet-observe")
    observe.add_argument("--inventory", required=True)
    observe.add_argument("--timeout-seconds", type=float, default=4.0)
    observe.add_argument("--max-height-spread", type=int, default=2)
    observe.add_argument("--output", default=None)

    soak = sub.add_parser("public-testnet-soak")
    soak.add_argument("--inventory", required=True)
    soak.add_argument("--output", required=True)
    soak.add_argument("--duration-seconds", type=int, required=True)
    soak.add_argument("--interval-seconds", type=int, default=30)
    soak.add_argument("--timeout-seconds", type=float, default=4.0)
    soak.add_argument("--max-height-spread", type=int, default=2)

    soak_summary = sub.add_parser("public-testnet-soak-summary")
    soak_summary.add_argument("--input", required=True)
    soak_summary.add_argument("--output", default=None)

    readiness = sub.add_parser("public-testnet-readiness")
    readiness.add_argument("--inventory", required=True)
    readiness.add_argument("--genesis-manifest", default=None)
    readiness.add_argument("--deployment-manifest", default=None)
    readiness.add_argument("--soak-summary", default=None)
    readiness.add_argument("--output", required=True)
    readiness.add_argument("--overwrite", action="store_true")

    evidence = sub.add_parser("public-testnet-evidence-build")
    evidence.add_argument("--key", required=True)
    evidence.add_argument("--source-commit", required=True)
    evidence.add_argument("--inventory", required=True)
    evidence.add_argument("--readiness", required=True)
    evidence.add_argument("--artifact", action="append", default=[])
    evidence.add_argument("--operator-note", default="")
    evidence.add_argument("--output", required=True)
    evidence.add_argument("--overwrite", action="store_true")

    evidence_verify = sub.add_parser("public-testnet-evidence-verify")
    evidence_verify.add_argument("--evidence", required=True)
    evidence_verify.add_argument("--artifact-dir", default=None)
    evidence_verify.add_argument("--expected-signer", default=None)
    evidence_verify.add_argument("--expected-source-commit", default=None)
    return parser


def _write(body: dict, path: str, *, overwrite: bool = False) -> None:
    save_json(body, path, overwrite=overwrite)


def _run(argv: list[str]) -> int:
    args = _parser().parse_args(argv)

    if args.command == "validator-identity-v23-export":
        body = export_validator_public_identity(
            cometbft_home=args.home,
            cometbft_binary=args.cometbft,
            name=args.name,
            operator_id=args.operator_id,
            provider=args.provider,
            region=args.region,
            p2p_host=args.p2p_host,
            p2p_port=args.p2p_port,
            monitor_rpc_url=args.monitor_rpc_url,
        )
        _write(body, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, **body}, indent=2))
        return 0

    if args.command == "public-testnet-inventory-build":
        identities = [_read_json(path) for path in args.identity]
        body = build_public_testnet_inventory(
            chain_id=args.chain_id,
            network_name=args.network_name,
            identities=identities,
        )
        _write(body, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, **body}, indent=2))
        return 0

    if args.command == "public-testnet-inventory-check":
        body = load_inventory(args.inventory)
        print(json.dumps(body, indent=2))
        return 0

    if args.command == "public-testnet-genesis-build":
        inventory = load_inventory(args.inventory)
        body = build_genesis_bundle(
            inventory=inventory,
            cometbft_genesis_template=args.cometbft_template,
            treasury_address=args.treasury_address,
            output_dir=args.output,
            max_supply=args.max_supply,
            min_fee=args.min_fee,
            overwrite=bool(args.overwrite),
        )
        print(json.dumps({"output": args.output, **body}, indent=2))
        return 0

    if args.command == "public-testnet-bundles-build":
        inventory = load_inventory(args.inventory)
        body = render_operator_deployment_bundles(
            inventory=inventory,
            genesis_bundle_dir=args.genesis_bundle,
            output_dir=args.output,
            repo_dir=args.repo_dir,
            data_root=args.data_root,
            cometbft_binary=args.cometbft_binary,
            overwrite=bool(args.overwrite),
        )
        print(json.dumps({"output": args.output, **body}, indent=2))
        return 0

    if args.command == "public-testnet-observe":
        body = observe_public_testnet(
            args.inventory,
            timeout_seconds=args.timeout_seconds,
            max_height_spread=args.max_height_spread,
        )
        if args.output:
            _write(body, args.output, overwrite=True)
        print(json.dumps(body, indent=2))
        return 0 if body["healthy"] else 2

    if args.command == "public-testnet-soak":
        body = run_soak_collection(
            args.inventory,
            output_jsonl=args.output,
            duration_seconds=args.duration_seconds,
            interval_seconds=args.interval_seconds,
            timeout_seconds=args.timeout_seconds,
            max_height_spread=args.max_height_spread,
        )
        print(json.dumps(body, indent=2))
        return 0

    if args.command == "public-testnet-soak-summary":
        body = summarize_soak(args.input)
        if args.output:
            _write(body, args.output, overwrite=True)
        print(json.dumps(body, indent=2))
        return 0

    if args.command == "public-testnet-readiness":
        body = build_readiness_report(
            inventory_path=args.inventory,
            genesis_manifest_path=args.genesis_manifest,
            deployment_manifest_path=args.deployment_manifest,
            soak_summary_path=args.soak_summary,
        )
        _write(body, args.output, overwrite=bool(args.overwrite))
        print(json.dumps({"saved": args.output, **body}, indent=2))
        return 0

    if args.command == "public-testnet-evidence-build":
        body = build_operations_evidence(
            signing_key_path=args.key,
            source_commit=args.source_commit,
            inventory_path=args.inventory,
            readiness_path=args.readiness,
            artifact_paths=list(args.artifact),
            operator_note=args.operator_note,
        )
        _write(body, args.output, overwrite=bool(args.overwrite))
        print(
            json.dumps(
                {
                    "saved": args.output,
                    "manifest_sha256": body["manifest_sha256"],
                    "signer": body["signer"],
                    "production_mainnet_ready": False,
                },
                indent=2,
            )
        )
        return 0

    result = verify_operations_evidence(
        _read_json(args.evidence),
        artifact_directory=args.artifact_dir,
        expected_signer=args.expected_signer,
        expected_source_commit=args.expected_source_commit,
    )
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    commands = {
        "validator-identity-v23-export",
        "public-testnet-inventory-build",
        "public-testnet-inventory-check",
        "public-testnet-genesis-build",
        "public-testnet-bundles-build",
        "public-testnet-observe",
        "public-testnet-soak",
        "public-testnet-soak-summary",
        "public-testnet-readiness",
        "public-testnet-evidence-build",
        "public-testnet-evidence-verify",
    }
    if len(sys.argv) > 1 and sys.argv[1] in commands:
        return _run(sys.argv[1:])
    return int(cli_v22.main())


if __name__ == "__main__":
    raise SystemExit(main())
