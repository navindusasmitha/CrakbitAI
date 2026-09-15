from __future__ import annotations

import argparse
import json
from pathlib import Path

from crakbit_chain.crypto import KeyPair
from crakbit_chain.models import ATOMIC_UNITS


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a local Crakbit devnet")
    parser.add_argument("--output", default="runtime")
    parser.add_argument("--validators", type=int, default=3)
    parser.add_argument(
        "--treasury",
        default="",
        help="Optional existing CRKBIT address for the genesis allocation",
    )
    args = parser.parse_args()

    if args.validators < 1:
        raise SystemExit("--validators must be at least 1")

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    validators = []
    for index in range(1, args.validators + 1):
        key = KeyPair.generate()
        node_dir = out / f"node{index}"
        key.save(node_dir / "validator.json")
        validators.append(
            {
                "name": f"validator-{index}",
                "address": key.address,
                "public_key": key.public_key_b64,
                "peer_url": f"http://node{index}:9101",
            }
        )

    treasury_address = args.treasury.strip()
    if treasury_address:
        allocations = {treasury_address: 21_000_000 * ATOMIC_UNITS}
        treasury_key_path = None
    else:
        treasury = KeyPair.generate()
        treasury.save(out / "treasury.json")
        treasury_address = treasury.address
        allocations = {treasury_address: 21_000_000 * ATOMIC_UNITS}
        treasury_key_path = str((out / "treasury.json").resolve())

    genesis = {
        "chain_id": "crakbit-devnet-1",
        "network_name": "Crakbit Chain Devnet",
        "symbol": "CRKBIT",
        "decimals": 8,
        "max_supply": 21_000_000 * ATOMIC_UNITS,
        "block_time_ms": 5000,
        "min_fee": 1000,
        "validators": validators,
        "allocations": allocations,
    }

    genesis_path = out / "genesis.json"
    genesis_path.write_text(json.dumps(genesis, indent=2) + "\n", encoding="utf-8")

    print(f"Genesis: {genesis_path.resolve()}")
    print(f"Treasury address: {treasury_address}")
    if treasury_key_path:
        print(f"DEVNET treasury key: {treasury_key_path}")
        print("Never use this generated devnet key for production/mainnet funds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
