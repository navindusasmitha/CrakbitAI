from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from crakbit_chain.crypto import KeyPair
from crakbit_chain.pow_network_v32 import PowNetworkChain
from crakbit_chain.pow_v31 import COIN, PowConfig


def _save_key(path: Path) -> str:
    key = KeyPair.generate()
    key.save(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return key.address


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize Crakbit zero-budget 4-node local PoW rehearsal")
    parser.add_argument("--root", default="/runtime")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    manifest_path = root / "manifest.json"
    env_path = root / "local.env"

    if args.reset and root.exists():
        shutil.rmtree(root)

    if manifest_path.exists() and env_path.exists():
        print(manifest_path.read_text(encoding="utf-8"))
        return 0

    root.mkdir(parents=True, exist_ok=True)
    shared = root / "shared"
    wallets = root / "wallets"
    pool = root / "pool"
    for directory in (shared, wallets, pool):
        directory.mkdir(parents=True, exist_ok=True)

    config = PowConfig(
        chain_id="crakbit-local-rehearsal-v1",
        network="local-rehearsal",
        target_block_time_seconds=15,
        retarget_interval=20,
        initial_target=(1 << 252) - 1,
        initial_subsidy=50 * COIN,
        halving_interval=210_000,
        coinbase_maturity=5,
        scrypt_n=1024,
        scrypt_r=8,
        scrypt_p=1,
    )

    genesis_db = shared / "genesis.sqlite3"
    if genesis_db.exists():
        genesis_db.unlink()
    chain = PowNetworkChain(genesis_db, config, create=True)
    try:
        genesis_hash = chain.genesis_hash
    finally:
        chain.close()

    nodes: list[dict[str, str | int]] = []
    for index in range(1, 5):
        node_dir = root / f"node{index}"
        node_dir.mkdir(parents=True, exist_ok=True)
        node_db = node_dir / "chain.sqlite3"
        shutil.copy2(genesis_db, node_db)
        p2p_address = _save_key(node_dir / "p2p-key.json")
        nodes.append(
            {
                "name": f"node{index}",
                "rpc_host_port": 28443 + (index - 1) * 1000,
                "p2p_host_port": 28444 + (index - 1) * 1000,
                "p2p_identity": p2p_address,
            }
        )

    pool_address = _save_key(wallets / "pool-hot.json")
    miner1_address = _save_key(wallets / "miner1.json")
    miner2_address = _save_key(wallets / "miner2.json")

    env_lines = [
        f"POOL_ADDRESS={pool_address}",
        f"MINER1_ADDRESS={miner1_address}",
        f"MINER2_ADDRESS={miner2_address}",
        "POOL_HOST=pool",
        "POOL_PORT=3333",
    ]
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    manifest = {
        "format": "crakbit-local-testnet-v37/1",
        "chain_id": config.chain_id,
        "network": config.network,
        "genesis_hash": genesis_hash,
        "nodes": nodes,
        "pool_address": pool_address,
        "miner_addresses": [miner1_address, miner2_address],
        "target_block_time_seconds": config.target_block_time_seconds,
        "coinbase_maturity": config.coinbase_maturity,
        "local_only": True,
        "independent_operator_evidence": False,
        "provider_region_diversity_evidence": False,
        "production_mainnet_ready": False,
        "production_crkbit_launched": False,
        "warning": "Single-PC Docker rehearsal only. Do not use as independent public-testnet evidence or for real-value custody.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
