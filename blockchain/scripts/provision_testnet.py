from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from crakbit_chain.genesis import Genesis


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate non-secret per-validator public-testnet operator scaffolds"
    )
    parser.add_argument("--genesis", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    genesis = Genesis.load(args.genesis)
    root = Path(args.output)
    if root.exists() and any(root.iterdir()) and not args.overwrite:
        raise SystemExit("output directory is not empty; use --overwrite only for generated non-secret scaffolds")
    root.mkdir(parents=True, exist_ok=True)

    inventory: list[dict] = []
    for index, validator in enumerate(genesis.validators, start=1):
        parsed = urlparse(validator.peer_url)
        host = parsed.hostname or "replace-with-validator-hostname"
        port = parsed.port or 443
        directory = root / f"validator-{index}"
        directory.mkdir(parents=True, exist_ok=True)

        env_text = "\n".join(
            [
                f"CRAKBIT_CHAIN_ID={genesis.chain_id}",
                f"CRAKBIT_VALIDATOR_ADDRESS={validator.address}",
                f"CRAKBIT_VALIDATOR_NAME={validator.name}",
                f"CRAKBIT_PUBLIC_HOST={host}",
                f"CRAKBIT_VALIDATOR_PORT={port}",
                "CRAKBIT_REQUIRE_MTLS=1",
                "CRAKBIT_REQUIRE_PEER_PINS=1",
                "CRAKBIT_MTLS_CA=/run/secrets/validator-ca.crt",
                "CRAKBIT_MTLS_CERT=/run/secrets/validator.crt",
                "CRAKBIT_MTLS_KEY=/run/secrets/validator.key",
                "CRAKBIT_PEER_CERT_PINS=/run/secrets/peer-pins.json",
                "CRAKBIT_MONITORING_BEARER_TOKEN=REPLACE_FROM_SECRET_MANAGER",
                "CRAKBIT_MAX_PUBLIC_BODY_BYTES=262144",
                "CRAKBIT_MAX_INTERNAL_BODY_BYTES=2097152",
                "CRAKBIT_PUBLIC_TX_RPM=60",
                "CRAKBIT_MAX_MEMPOOL_TXS=5000",
                "CRAKBIT_MAX_BLOCK_TXS=1000",
                "CRAKBIT_MAX_TX_BYTES=65536",
                "",
            ]
        )
        (directory / "validator.env.example").write_text(env_text, encoding="utf-8")

        pin_template = {
            peer.address: ["REPLACE_WITH_CURRENT_CERT_SHA256", "OPTIONAL_NEXT_CERT_SHA256"]
            for peer in genesis.validators
            if peer.address != validator.address
        }
        (directory / "peer-pins.json.example").write_text(
            json.dumps(pin_template, indent=2) + "\n", encoding="utf-8"
        )

        readme = f"""# {validator.name} operator scaffold

Validator address: `{validator.address}`
Configured peer URL: `{validator.peer_url}`

This directory intentionally contains **no private keys, certificates or bearer tokens**.
Provision those from an operator-controlled secret manager on the target host.

Minimum deployment sequence:

1. Verify the signed genesis/release artifact before copying it to the host.
2. Provision a dedicated consensus key and separate TLS private key outside the repository.
3. Issue the validator TLS certificate with a SAN matching `{host}`.
4. Publish the current certificate fingerprint to the other validators' pin maps.
5. Keep the validator service behind mTLS and firewall rules; expose public RPC only through a hardened reverse proxy.
6. Configure monitoring over a private operator network and use the bearer token in addition to network controls.
7. Run integrity, backup/restore and fault/soak drills before joining a shared testnet.

Do not use this scaffold for real-value custody. The current chain remains a research/devnet implementation.
"""
        (directory / "README.md").write_text(readme, encoding="utf-8")
        inventory.append(
            {
                "index": index,
                "name": validator.name,
                "address": validator.address,
                "public_key": validator.public_key,
                "peer_url": validator.peer_url,
                "https_peer_url": parsed.scheme.lower() == "https",
                "scaffold": str(directory.name),
            }
        )

    result = {
        "format": "crakbit-testnet-inventory/1",
        "chain_id": genesis.chain_id,
        "genesis_fingerprint": genesis.fingerprint(),
        "validator_count": len(genesis.validators),
        "quorum": genesis.quorum_size,
        "validators": inventory,
        "contains_private_keys": False,
        "production_ready": False,
    }
    (root / "inventory.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
