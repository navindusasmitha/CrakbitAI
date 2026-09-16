from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LAB_FORMAT = "crakbit-cometbft-lab-v1"


def _run(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def _set_section_value(text: str, section: str, key: str, value: str) -> str:
    """Replace one TOML key inside a named top-level section without a TOML writer."""
    lines = text.splitlines()
    current = ""
    replaced = False
    rendered: list[str] = []
    section_header = f"[{section}]"
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped
        if current == section_header and re.match(rf"^\s*{re.escape(key)}\s*=", line):
            rendered.append(f'{key} = {json.dumps(value)}')
            replaced = True
        else:
            rendered.append(line)
    if not replaced:
        raise ValueError(f"CometBFT config is missing {section}.{key}")
    return "\n".join(rendered) + "\n"


def rewrite_config(
    text: str,
    *,
    rpc_port: int,
    p2p_port: int,
    abci_port: int,
    persistent_peers: str,
) -> str:
    result = text
    result = _set_section_value(result, "rpc", "laddr", f"tcp://127.0.0.1:{rpc_port}")
    result = _set_section_value(result, "p2p", "laddr", f"tcp://127.0.0.1:{p2p_port}")
    result = _set_section_value(result, "p2p", "persistent_peers", persistent_peers)
    # proxy_app is a top-level value in CometBFT config.toml.
    result, count = re.subn(
        r'^\s*proxy_app\s*=.*$',
        f'proxy_app = "tcp://127.0.0.1:{abci_port}"',
        result,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise ValueError("CometBFT config is missing proxy_app")
    return result


def build_consensus_genesis(
    template: dict[str, Any],
    validators: list[dict[str, Any]],
    *,
    chain_id: str,
) -> dict[str, Any]:
    if len(validators) < 1:
        raise ValueError("at least one CometBFT validator is required")
    result = json.loads(json.dumps(template))
    result["genesis_time"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    result["chain_id"] = chain_id
    result["initial_height"] = "1"
    result["validators"] = [
        {
            "address": str(item["address"]),
            "pub_key": dict(item["pub_key"]),
            "power": str(item.get("power", "10")),
            "name": str(item.get("name", f"validator-{index + 1}")),
        }
        for index, item in enumerate(validators)
    ]
    result["app_hash"] = ""
    return result


def generate_lab(
    *,
    output: str | Path,
    chain_id: str,
    nodes: int = 4,
    cometbft_binary: str = "cometbft",
    bridge_binary: str = "./cometbft-app/crakbit-cometbft-bridge",
    execution_script: str = "scripts/run_execution_service_v16.py",
    application_genesis: str = "runtime/genesis.json",
    base_rpc_port: int = 27657,
    base_p2p_port: int = 27656,
    base_abci_port: int = 27658,
    base_execution_port: int = 27659,
    force: bool = False,
) -> dict[str, Any]:
    if nodes < 1 or nodes > 16:
        raise ValueError("local lab supports between 1 and 16 nodes")
    binary = shutil.which(cometbft_binary) or (
        cometbft_binary if Path(cometbft_binary).is_file() else None
    )
    if not binary:
        raise FileNotFoundError(
            "CometBFT binary was not found; install the pinned v0.40.0 binary or pass --cometbft"
        )

    root = Path(output)
    if root.exists() and any(root.iterdir()):
        if not force:
            raise FileExistsError(f"lab output is not empty: {root}")
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    secrets_dir = root / ".secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)

    node_records: list[dict[str, Any]] = []
    validators: list[dict[str, Any]] = []
    for index in range(nodes):
        number = index + 1
        home = root / f"node{number}"
        _run([str(binary), "init", "validator", "--home", str(home)])
        validator_key = json.loads(
            (home / "config" / "priv_validator_key.json").read_text(encoding="utf-8")
        )
        node_id = _run([str(binary), "show-node-id", "--home", str(home)])
        rpc_port = base_rpc_port + index * 10
        p2p_port = base_p2p_port + index * 10
        abci_port = base_abci_port + index * 10
        execution_port = base_execution_port + index * 10
        token_path = secrets_dir / f"node{number}-execution-token.txt"
        token_path.write_text(secrets.token_hex(32) + "\n", encoding="utf-8")
        try:
            os.chmod(token_path, 0o600)
        except OSError:
            pass
        validators.append(
            {
                "address": validator_key["address"],
                "pub_key": validator_key["pub_key"],
                "power": "10",
                "name": f"validator-{number}",
            }
        )
        node_records.append(
            {
                "name": f"validator-{number}",
                "home": str(home),
                "node_id": node_id,
                "rpc_port": rpc_port,
                "p2p_port": p2p_port,
                "abci_port": abci_port,
                "execution_port": execution_port,
                "execution_data": str(root / f"app{number}"),
                "execution_token_file": str(token_path),
            }
        )

    template = json.loads(
        (Path(node_records[0]["home"]) / "config" / "genesis.json").read_text(
            encoding="utf-8"
        )
    )
    shared_genesis = build_consensus_genesis(template, validators, chain_id=chain_id)
    genesis_bytes = json.dumps(shared_genesis, indent=2) + "\n"

    for node in node_records:
        home = Path(node["home"])
        (home / "config" / "genesis.json").write_text(genesis_bytes, encoding="utf-8")
        peers = ",".join(
            f"{other['node_id']}@127.0.0.1:{other['p2p_port']}"
            for other in node_records
            if other["name"] != node["name"]
        )
        config_path = home / "config" / "config.toml"
        config_path.write_text(
            rewrite_config(
                config_path.read_text(encoding="utf-8"),
                rpc_port=int(node["rpc_port"]),
                p2p_port=int(node["p2p_port"]),
                abci_port=int(node["abci_port"]),
                persistent_peers=peers,
            ),
            encoding="utf-8",
        )

    manifest = {
        "format": LAB_FORMAT,
        "chain_id": chain_id,
        "cometbft_binary": str(binary),
        "expected_cometbft_version": "v0.40.0",
        "application_genesis": application_genesis,
        "bridge_binary": bridge_binary,
        "execution_script": execution_script,
        "nodes": node_records,
        "private_consensus_keys_generated": True,
        "private_keys_must_not_be_committed": True,
        "production_ready": False,
    }
    (root / "lab-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    commands: list[str] = []
    for node in node_records:
        commands.extend(
            [
                f"# {node['name']}",
                f"# token: {node['execution_token_file']}",
                (
                    f"python {execution_script} --genesis {application_genesis} "
                    f"--data {node['execution_data']} --token <TOKEN> "
                    f"--host 127.0.0.1 --port {node['execution_port']}"
                ),
                (
                    f"CRAKBIT_EXECUTION_URL=http://127.0.0.1:{node['execution_port']} "
                    f"CRAKBIT_EXECUTION_TOKEN=<TOKEN> CRAKBIT_ABCI_LISTEN=tcp://127.0.0.1:{node['abci_port']} "
                    f"{bridge_binary}"
                ),
                f"{binary} start --home {node['home']}",
                "",
            ]
        )
    (root / "commands.txt").write_text("\n".join(commands), encoding="utf-8")
    return manifest
