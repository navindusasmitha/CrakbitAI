from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .comet_lab import build_consensus_genesis
from .crypto import address_from_public_key, sha256_hex


IDENTITY_FORMAT = "crakbit-validator-public-identity/1"
INVENTORY_FORMAT = "crakbit-public-testnet-inventory/1"
GENESIS_BUNDLE_FORMAT = "crakbit-public-testnet-genesis-bundle/1"
DEPLOYMENT_BUNDLE_FORMAT = "crakbit-public-testnet-deployment-bundle/1"
DEFAULT_MAX_SUPPLY = 21_000_000 * 100_000_000
_FORBIDDEN_KEYS = {
    "private_key",
    "privatekey",
    "priv_key",
    "privkey",
    "seed",
    "seed_phrase",
    "mnemonic",
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
}


class PublicTestnetV23Error(ValueError):
    pass


def _read_json(path: str | Path) -> dict[str, Any]:
    try:
        body = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicTestnetV23Error(f"invalid JSON file: {path}") from exc
    if not isinstance(body, dict):
        raise PublicTestnetV23Error(f"JSON root must be an object: {path}")
    return body


def _write_json(path: str | Path, body: dict[str, Any], *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise PublicTestnetV23Error(f"output already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _validate_no_secret_fields(value: Any, *, path: str = "root") -> None:
    if isinstance(value, dict):
        for raw_key, item in value.items():
            key = str(raw_key).strip().lower()
            if key in _FORBIDDEN_KEYS:
                raise PublicTestnetV23Error(
                    f"public testnet metadata must not contain secret field {path}.{raw_key}"
                )
            _validate_no_secret_fields(item, path=f"{path}.{raw_key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_no_secret_fields(item, path=f"{path}[{index}]")


def _is_host(value: str) -> bool:
    host = value.strip()
    if not host or len(host) > 253 or "/" in host or " " in host:
        return False
    if host in {"127.0.0.1", "localhost", "::1"}:
        return True
    if re.fullmatch(r"[0-9a-fA-F:.]+", host):
        return True
    return all(
        part and len(part) <= 63 and re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", part)
        for part in host.rstrip(".").split(".")
    )


def _validate_pubkey(value: str) -> str:
    try:
        raw = base64.b64decode(str(value).encode("ascii"), validate=True)
    except Exception as exc:  # noqa: BLE001
        raise PublicTestnetV23Error("validator public key must be valid base64") from exc
    if len(raw) != 32:
        raise PublicTestnetV23Error("validator Ed25519 public key must be exactly 32 bytes")
    return str(value)


def _validate_hex_address(value: str) -> str:
    address = str(value).strip().upper()
    if len(address) != 40 or any(ch not in "0123456789ABCDEF" for ch in address):
        raise PublicTestnetV23Error("CometBFT validator address must be 40 hexadecimal characters")
    return address


def _validate_node_id(value: str) -> str:
    node_id = str(value).strip().lower()
    if len(node_id) != 40 or any(ch not in "0123456789abcdef" for ch in node_id):
        raise PublicTestnetV23Error("CometBFT node ID must be 40 hexadecimal characters")
    return node_id


def validate_identity(identity: dict[str, Any]) -> dict[str, Any]:
    _validate_no_secret_fields(identity)
    if identity.get("format") != IDENTITY_FORMAT:
        raise PublicTestnetV23Error("unsupported validator public identity format")
    public_key = _validate_pubkey(str(identity.get("public_key", "")))
    address = str(identity.get("crakbit_address", "")).lower()
    if address != address_from_public_key(public_key):
        raise PublicTestnetV23Error("Crakbit validator address does not match public key")
    comet_address = _validate_hex_address(str(identity.get("cometbft_address", "")))
    node_id = _validate_node_id(str(identity.get("node_id", "")))
    p2p_host = str(identity.get("p2p_host", "")).strip()
    if not _is_host(p2p_host):
        raise PublicTestnetV23Error("invalid validator p2p_host")
    p2p_port = int(identity.get("p2p_port", 0))
    if p2p_port < 1 or p2p_port > 65535:
        raise PublicTestnetV23Error("validator p2p_port is out of range")
    rpc_url = str(identity.get("monitor_rpc_url", "")).strip()
    if rpc_url and not (rpc_url.startswith("http://") or rpc_url.startswith("https://")):
        raise PublicTestnetV23Error("monitor_rpc_url must use http:// or https://")
    for required in ("name", "operator_id", "provider", "region"):
        if not str(identity.get(required, "")).strip():
            raise PublicTestnetV23Error(f"validator public identity is missing {required}")
    return {
        "format": IDENTITY_FORMAT,
        "name": str(identity["name"]).strip(),
        "operator_id": str(identity["operator_id"]).strip(),
        "provider": str(identity["provider"]).strip(),
        "region": str(identity["region"]).strip(),
        "node_id": node_id,
        "cometbft_address": comet_address,
        "public_key": public_key,
        "crakbit_address": address,
        "p2p_host": p2p_host,
        "p2p_port": p2p_port,
        "monitor_rpc_url": rpc_url,
        "contains_private_material": False,
    }


def export_validator_public_identity(
    *,
    cometbft_home: str | Path,
    cometbft_binary: str,
    name: str,
    operator_id: str,
    provider: str,
    region: str,
    p2p_host: str,
    p2p_port: int = 26656,
    monitor_rpc_url: str = "",
) -> dict[str, Any]:
    home = Path(cometbft_home)
    key_path = home / "config" / "priv_validator_key.json"
    if not key_path.is_file():
        raise PublicTestnetV23Error(f"CometBFT validator key file not found: {key_path}")
    key_body = _read_json(key_path)
    pub = key_body.get("pub_key") or {}
    key_type = str(pub.get("type", "")).lower()
    if "ed25519" not in key_type:
        raise PublicTestnetV23Error("v0.23 requires an Ed25519 CometBFT validator key")
    public_key = _validate_pubkey(str(pub.get("value", "")))
    comet_address = _validate_hex_address(str(key_body.get("address", "")))

    binary = shutil.which(cometbft_binary) or (
        str(cometbft_binary) if Path(cometbft_binary).is_file() else None
    )
    if not binary:
        raise PublicTestnetV23Error("CometBFT binary not found; pass the pinned binary path")
    completed = subprocess.run(
        [str(binary), "show-node-id", "--home", str(home)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    node_id = _validate_node_id(completed.stdout.strip())
    identity = {
        "format": IDENTITY_FORMAT,
        "name": str(name).strip(),
        "operator_id": str(operator_id).strip(),
        "provider": str(provider).strip(),
        "region": str(region).strip(),
        "node_id": node_id,
        "cometbft_address": comet_address,
        "public_key": public_key,
        "crakbit_address": address_from_public_key(public_key),
        "p2p_host": str(p2p_host).strip(),
        "p2p_port": int(p2p_port),
        "monitor_rpc_url": str(monitor_rpc_url).strip(),
        "contains_private_material": False,
    }
    return validate_identity(identity)


def build_public_testnet_inventory(
    *,
    chain_id: str,
    network_name: str,
    identities: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(identities) < 4:
        raise PublicTestnetV23Error("public-testnet inventory requires at least four validators")
    normalized = [validate_identity(item) for item in identities]
    names = [item["name"] for item in normalized]
    public_keys = [item["public_key"] for item in normalized]
    node_ids = [item["node_id"] for item in normalized]
    comet_addresses = [item["cometbft_address"] for item in normalized]
    p2p_endpoints = [(item["p2p_host"], item["p2p_port"]) for item in normalized]
    for label, values in (
        ("validator names", names),
        ("validator public keys", public_keys),
        ("CometBFT node IDs", node_ids),
        ("CometBFT validator addresses", comet_addresses),
        ("P2P endpoints", p2p_endpoints),
    ):
        if len(set(values)) != len(values):
            raise PublicTestnetV23Error(f"public-testnet inventory contains duplicate {label}")
    chain = str(chain_id).strip()
    if not chain or len(chain) > 80:
        raise PublicTestnetV23Error("invalid chain_id")
    network = str(network_name).strip()
    if not network:
        raise PublicTestnetV23Error("network_name is required")
    operators = sorted({item["operator_id"] for item in normalized})
    providers = sorted({item["provider"] for item in normalized})
    regions = sorted({item["region"] for item in normalized})
    return {
        "format": INVENTORY_FORMAT,
        "chain_id": chain,
        "network_name": network,
        "validators": normalized,
        "validator_count": len(normalized),
        "operator_count": len(operators),
        "provider_count": len(providers),
        "region_count": len(regions),
        "independent_operator_gate_satisfied": len(operators) >= 4,
        "multi_provider_gate_satisfied": len(providers) >= 2,
        "multi_region_gate_satisfied": len(regions) >= 2,
        "contains_private_material": False,
        "production_mainnet_ready": False,
    }


def load_inventory(path: str | Path) -> dict[str, Any]:
    body = _read_json(path)
    if body.get("format") != INVENTORY_FORMAT:
        raise PublicTestnetV23Error("unsupported public-testnet inventory format")
    return build_public_testnet_inventory(
        chain_id=str(body.get("chain_id", "")),
        network_name=str(body.get("network_name", "")),
        identities=list(body.get("validators") or []),
    )


def _validate_crk_address(address: str) -> str:
    value = str(address).strip().lower()
    if not value.startswith("crk1") or len(value) != 44:
        raise PublicTestnetV23Error("treasury address must be a crk1 address")
    if any(ch not in "0123456789abcdef" for ch in value[4:]):
        raise PublicTestnetV23Error("treasury address contains invalid characters")
    return value


def build_genesis_bundle(
    *,
    inventory: dict[str, Any],
    cometbft_genesis_template: str | Path,
    treasury_address: str,
    output_dir: str | Path,
    max_supply: int = DEFAULT_MAX_SUPPLY,
    min_fee: int = 1_000,
    decimals: int = 8,
    block_time_ms: int = 5_000,
    view_timeout_ms: int = 10_000,
    overwrite: bool = False,
) -> dict[str, Any]:
    normalized = build_public_testnet_inventory(
        chain_id=str(inventory["chain_id"]),
        network_name=str(inventory["network_name"]),
        identities=list(inventory["validators"]),
    )
    if int(max_supply) <= 0:
        raise PublicTestnetV23Error("max_supply must be positive")
    if int(decimals) != 8:
        raise PublicTestnetV23Error("current Crakbit development network requires 8 decimals")
    treasury = _validate_crk_address(treasury_address)
    template = _read_json(cometbft_genesis_template)
    comet_validators = [
        {
            "address": item["cometbft_address"],
            "pub_key": {
                "type": "tendermint/PubKeyEd25519",
                "value": item["public_key"],
            },
            "power": "10",
            "name": item["name"],
        }
        for item in normalized["validators"]
    ]
    consensus_genesis = build_consensus_genesis(
        template,
        comet_validators,
        chain_id=normalized["chain_id"],
    )
    application_genesis = {
        "chain_id": normalized["chain_id"],
        "network_name": normalized["network_name"],
        "symbol": "CRKBIT",
        "decimals": int(decimals),
        "max_supply": int(max_supply),
        "block_time_ms": int(block_time_ms),
        "view_timeout_ms": int(view_timeout_ms),
        "min_fee": int(min_fee),
        "validators": [
            {
                "address": item["crakbit_address"],
                "public_key": item["public_key"],
                "name": item["name"],
                "peer_url": f"http://{item['p2p_host']}:{item['p2p_port']}",
            }
            for item in normalized["validators"]
        ],
        "allocations": {treasury: int(max_supply)},
    }

    root = Path(output_dir)
    if root.exists() and any(root.iterdir()) and not overwrite:
        raise PublicTestnetV23Error(f"genesis output directory is not empty: {root}")
    if root.exists() and overwrite:
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    app_path = root / "application-genesis.json"
    consensus_path = root / "cometbft-genesis.json"
    app_path.write_text(json.dumps(application_genesis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    consensus_path.write_text(json.dumps(consensus_genesis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "format": GENESIS_BUNDLE_FORMAT,
        "chain_id": normalized["chain_id"],
        "network_name": normalized["network_name"],
        "validator_count": normalized["validator_count"],
        "application_genesis": app_path.name,
        "application_genesis_sha256": sha256_hex(app_path.read_bytes()),
        "cometbft_genesis": consensus_path.name,
        "cometbft_genesis_sha256": sha256_hex(consensus_path.read_bytes()),
        "treasury_address": treasury,
        "max_supply_atomic_units": int(max_supply),
        "contains_private_material": False,
        "multi_operator_ceremony_completed": False,
        "independent_review_completed": False,
        "production_mainnet_ready": False,
    }
    _write_json(root / "genesis-bundle.json", manifest, overwrite=True)
    return manifest


def _systemd_units(*, repo_dir: str, data_root: str, cometbft_binary: str) -> dict[str, str]:
    execution = f"""[Unit]\nDescription=Crakbit v0.23 governed execution service\nAfter=network-online.target\nWants=network-online.target\n\n[Service]\nType=simple\nUser=crakbit\nGroup=crakbit\nEnvironmentFile=/etc/crakbit/node.env\nWorkingDirectory={repo_dir}/blockchain\nExecStart={repo_dir}/.venv/bin/python {repo_dir}/blockchain/scripts/run_execution_service_v22.py --genesis /etc/crakbit/application-genesis.json --data {data_root}/app --token ${{CRAKBIT_EXECUTION_TOKEN}} --host 127.0.0.1 --port 26659\nRestart=on-failure\nRestartSec=3\nNoNewPrivileges=true\nPrivateTmp=true\nProtectSystem=strict\nReadWritePaths={data_root}/app\n\n[Install]\nWantedBy=multi-user.target\n"""
    bridge = f"""[Unit]\nDescription=Crakbit CometBFT ABCI bridge\nAfter=crakbit-execution.service\nRequires=crakbit-execution.service\n\n[Service]\nType=simple\nUser=crakbit\nGroup=crakbit\nEnvironmentFile=/etc/crakbit/node.env\nWorkingDirectory={repo_dir}/blockchain\nExecStart={repo_dir}/blockchain/cometbft-app/crakbit-cometbft-bridge\nRestart=on-failure\nRestartSec=3\nNoNewPrivileges=true\nPrivateTmp=true\nProtectSystem=strict\n\n[Install]\nWantedBy=multi-user.target\n"""
    comet = f"""[Unit]\nDescription=Crakbit CometBFT validator\nAfter=crakbit-abci-bridge.service\nRequires=crakbit-abci-bridge.service\n\n[Service]\nType=simple\nUser=crakbit\nGroup=crakbit\nWorkingDirectory={data_root}/cometbft\nExecStart={cometbft_binary} start --home {data_root}/cometbft\nRestart=on-failure\nRestartSec=3\nLimitNOFILE=65536\nNoNewPrivileges=true\nPrivateTmp=true\nProtectSystem=strict\nReadWritePaths={data_root}/cometbft\n\n[Install]\nWantedBy=multi-user.target\n"""
    return {
        "crakbit-execution.service": execution,
        "crakbit-abci-bridge.service": bridge,
        "crakbit-cometbft.service": comet,
    }


def render_operator_deployment_bundles(
    *,
    inventory: dict[str, Any],
    genesis_bundle_dir: str | Path,
    output_dir: str | Path,
    repo_dir: str = "/opt/crakbit",
    data_root: str = "/var/lib/crakbit",
    cometbft_binary: str = "/usr/local/bin/cometbft",
    overwrite: bool = False,
) -> dict[str, Any]:
    normalized = build_public_testnet_inventory(
        chain_id=str(inventory["chain_id"]),
        network_name=str(inventory["network_name"]),
        identities=list(inventory["validators"]),
    )
    genesis_root = Path(genesis_bundle_dir)
    app_genesis = genesis_root / "application-genesis.json"
    comet_genesis = genesis_root / "cometbft-genesis.json"
    if not app_genesis.is_file() or not comet_genesis.is_file():
        raise PublicTestnetV23Error("genesis bundle directory is missing required genesis files")
    root = Path(output_dir)
    if root.exists() and any(root.iterdir()) and not overwrite:
        raise PublicTestnetV23Error(f"deployment output directory is not empty: {root}")
    if root.exists() and overwrite:
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    units = _systemd_units(repo_dir=repo_dir, data_root=data_root, cometbft_binary=cometbft_binary)
    records: list[dict[str, Any]] = []
    peers = {
        item["name"]: ",".join(
            f"{other['node_id']}@{other['p2p_host']}:{other['p2p_port']}"
            for other in normalized["validators"]
            if other["name"] != item["name"]
        )
        for item in normalized["validators"]
    }
    for item in normalized["validators"]:
        node_root = root / item["name"]
        node_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(app_genesis, node_root / "application-genesis.json")
        shutil.copy2(comet_genesis, node_root / "cometbft-genesis.json")
        (node_root / "node.env.example").write_text(
            "\n".join(
                [
                    "# Generate this value locally on the validator host. Never commit/share it.",
                    "CRAKBIT_EXECUTION_TOKEN=REPLACE_WITH_LOCAL_RANDOM_32_BYTE_SECRET",
                    "CRAKBIT_EXECUTION_URL=http://127.0.0.1:26659",
                    "CRAKBIT_ABCI_LISTEN=tcp://127.0.0.1:26658",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        for filename, content in units.items():
            (node_root / filename).write_text(content, encoding="utf-8")
        (node_root / "persistent_peers.txt").write_text(peers[item["name"]] + "\n", encoding="utf-8")
        (node_root / "OPERATOR.md").write_text(
            f"""# {item['name']} public-testnet operator bundle\n\nThis bundle contains **no validator private key and no execution token**.\n\n1. Create a dedicated `crakbit` system user.\n2. Clone/install the exact reviewed source release under `{repo_dir}`.\n3. Initialize CometBFT on this host and verify its public identity still matches the inventory.\n4. Place the shared CometBFT genesis at `{data_root}/cometbft/config/genesis.json`.\n5. Configure P2P persistent peers from `persistent_peers.txt`.\n6. Copy `application-genesis.json` to `/etc/crakbit/application-genesis.json`.\n7. Generate `CRAKBIT_EXECUTION_TOKEN` locally and write `/etc/crakbit/node.env` mode 0600.\n8. Keep execution port 26659 and ABCI port 26658 loopback/private only.\n9. Expose P2P `{item['p2p_port']}/tcp`; restrict validator RPC/operator/SSH to authorized management networks.\n10. Install the provided systemd units, run `systemctl daemon-reload`, then enable execution → bridge → CometBFT.\n\nDo not copy another operator's validator private key onto this host. A production candidate still requires protected signer/HSM-equivalent custody and independently reviewed operations.\n""",
            encoding="utf-8",
        )
        records.append(
            {
                "name": item["name"],
                "operator_id": item["operator_id"],
                "provider": item["provider"],
                "region": item["region"],
                "bundle": str(node_root),
                "p2p_endpoint": f"{item['p2p_host']}:{item['p2p_port']}",
                "contains_private_material": False,
            }
        )

    manifest = {
        "format": DEPLOYMENT_BUNDLE_FORMAT,
        "chain_id": normalized["chain_id"],
        "network_name": normalized["network_name"],
        "validator_count": normalized["validator_count"],
        "operator_count": normalized["operator_count"],
        "provider_count": normalized["provider_count"],
        "region_count": normalized["region_count"],
        "nodes": records,
        "application_genesis_sha256": sha256_hex(app_genesis.read_bytes()),
        "cometbft_genesis_sha256": sha256_hex(comet_genesis.read_bytes()),
        "contains_private_material": False,
        "deployment_executed": False,
        "production_mainnet_ready": False,
    }
    _write_json(root / "deployment-manifest.json", manifest, overwrite=True)
    return manifest
