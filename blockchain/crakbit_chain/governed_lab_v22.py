from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

from .comet_lab import generate_lab
from .crypto import KeyPair, address_from_public_key, sha256_hex


LAB_FORMAT_V22 = "crakbit-governed-cometbft-lab/1"
DEFAULT_MAX_SUPPLY = 21_000_000 * 100_000_000


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_comet_validator_key(home: str | Path) -> dict[str, Any]:
    path = Path(home) / "config" / "priv_validator_key.json"
    body = json.loads(path.read_text(encoding="utf-8"))
    pub = body.get("pub_key") or {}
    key_type = str(pub.get("type", "")).lower()
    if "ed25519" not in key_type:
        raise ValueError(f"v0.22 governed lab requires Ed25519 CometBFT validators: {path}")
    raw_public = base64.b64decode(str(pub.get("value", "")).encode("ascii"), validate=True)
    if len(raw_public) != 32:
        raise ValueError(f"invalid CometBFT Ed25519 public key in {path}")
    return body


def _export_disposable_signing_key(comet_key: dict[str, Any], output: Path) -> KeyPair:
    """Export a lab-only Crakbit KeyPair view of a CometBFT private-validator key.

    This exists solely so a local v0.22 governance campaign can sign with the same
    validator identity that CometBFT is using. It is deliberately written under the
    generated lab's .secrets directory and must never be copied into a production design.
    """

    pub_b64 = str(comet_key["pub_key"]["value"])
    expected_public = base64.b64decode(pub_b64.encode("ascii"), validate=True)
    raw_private = base64.b64decode(str(comet_key["priv_key"]["value"]).encode("ascii"), validate=True)
    if len(raw_private) == 64:
        seed = raw_private[:32]
    elif len(raw_private) == 32:
        seed = raw_private
    else:
        raise ValueError("unsupported CometBFT Ed25519 private-key length")
    private = Ed25519PrivateKey.from_private_bytes(seed)
    derived_public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    if derived_public != expected_public:
        raise ValueError("CometBFT validator private/public key mismatch")
    private_b64 = base64.b64encode(
        private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    ).decode("ascii")
    key = KeyPair(private_b64, pub_b64, address_from_public_key(pub_b64))
    key.save(output)
    try:
        os.chmod(output, 0o600)
    except OSError:
        pass
    return key


def build_application_genesis(
    *,
    base_manifest: dict[str, Any],
    output: str | Path,
    treasury_key_path: str | Path,
    network_name: str = "Crakbit v0.22 Governed Lab",
    symbol: str = "CRKBIT",
    decimals: int = 8,
    max_supply: int = DEFAULT_MAX_SUPPLY,
    min_fee: int = 1_000,
    block_time_ms: int = 5_000,
    view_timeout_ms: int = 10_000,
    export_lab_signing_keys: bool = True,
) -> dict[str, Any]:
    nodes = list(base_manifest.get("nodes") or [])
    if len(nodes) < 4:
        raise ValueError("v0.22 governed lab requires at least four validators")
    if decimals != 8:
        raise ValueError("v0.22 development network currently requires 8 decimals")
    if max_supply <= 0:
        raise ValueError("max_supply must be positive")

    output_path = Path(output)
    secrets_dir = output_path.parent / ".secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)

    validators: list[dict[str, Any]] = []
    operator_records: list[dict[str, Any]] = []
    for index, node in enumerate(nodes):
        comet_key = _read_comet_validator_key(node["home"])
        public_key = str(comet_key["pub_key"]["value"])
        address = address_from_public_key(public_key)
        validator = {
            "address": address,
            "public_key": public_key,
            "name": str(node.get("name") or f"validator-{index + 1}"),
            "peer_url": f"http://127.0.0.1:{int(node['execution_port'])}",
        }
        validators.append(validator)
        operator_record: dict[str, Any] = {
            "name": validator["name"],
            "crakbit_validator_address": address,
            "cometbft_consensus_address": str(comet_key.get("address", "")),
            "public_key": public_key,
            "rpc_url": f"http://127.0.0.1:{int(node['rpc_port'])}",
            "execution_url": f"http://127.0.0.1:{int(node['execution_port'])}",
            "home": str(node["home"]),
        }
        if export_lab_signing_keys:
            signer_path = secrets_dir / f"{validator['name']}-DISPOSABLE-governance-key.json"
            signer = _export_disposable_signing_key(comet_key, signer_path)
            if signer.address != address:
                raise ValueError("lab governance signer address mismatch")
            operator_record["disposable_governance_key_file"] = str(signer_path)
        operator_records.append(operator_record)

    treasury_path = Path(treasury_key_path)
    if treasury_path.exists():
        raise FileExistsError(f"refusing to replace existing lab treasury key: {treasury_path}")
    treasury = KeyPair.generate()
    treasury.save(treasury_path)
    try:
        os.chmod(treasury_path, 0o600)
    except OSError:
        pass

    genesis = {
        "chain_id": str(base_manifest["chain_id"]),
        "network_name": network_name,
        "symbol": symbol,
        "decimals": int(decimals),
        "max_supply": int(max_supply),
        "block_time_ms": int(block_time_ms),
        "view_timeout_ms": int(view_timeout_ms),
        "min_fee": int(min_fee),
        "validators": validators,
        "allocations": {treasury.address: int(max_supply)},
    }
    _write_json(output_path, genesis)
    return {
        "genesis": genesis,
        "operator_records": operator_records,
        "treasury_address": treasury.address,
        "treasury_key_file": str(treasury_path),
        "genesis_sha256": sha256_hex(output_path.read_bytes()),
    }


def generate_governed_lab(
    *,
    output: str | Path,
    chain_id: str = "crakbit-v22-local",
    nodes: int = 4,
    cometbft_binary: str = "cometbft",
    bridge_binary: str = "./cometbft-app/crakbit-cometbft-bridge",
    base_rpc_port: int = 28657,
    base_p2p_port: int = 28656,
    base_abci_port: int = 28658,
    base_execution_port: int = 28659,
    force: bool = False,
) -> dict[str, Any]:
    if nodes < 4 or nodes > 16:
        raise ValueError("v0.22 governed lab supports 4 to 16 validators")
    root = Path(output)
    app_genesis = root / "application-genesis.json"
    base = generate_lab(
        output=root,
        chain_id=chain_id,
        nodes=nodes,
        cometbft_binary=cometbft_binary,
        bridge_binary=bridge_binary,
        execution_script="scripts/run_execution_service_v21.py",
        application_genesis=str(app_genesis),
        base_rpc_port=base_rpc_port,
        base_p2p_port=base_p2p_port,
        base_abci_port=base_abci_port,
        base_execution_port=base_execution_port,
        force=force,
    )
    built = build_application_genesis(
        base_manifest=base,
        output=app_genesis,
        treasury_key_path=root / ".secrets" / "DISPOSABLE-lab-treasury.json",
        export_lab_signing_keys=True,
    )
    inventory = {
        "format": LAB_FORMAT_V22,
        "chain_id": chain_id,
        "application_genesis": str(app_genesis),
        "application_genesis_sha256": built["genesis_sha256"],
        "treasury_address": built["treasury_address"],
        "nodes": built["operator_records"],
        "governance_quorum_rule": "strictly-greater-than-two-thirds-active-voting-power",
        "expected_cometbft_version": "v0.40.0",
        "execution_protocol": "crakbit-execution/3",
        "disposable_local_lab_keys_present": True,
        "production_mainnet_ready": False,
    }
    _write_json(root / "governed-lab-inventory.json", inventory)

    instructions = f"""# Crakbit v0.22 governed local lab\n\nThis directory contains disposable local validator keys. Never reuse them on a public or production network.\n\nApplication genesis: {app_genesis}\nTreasury key: {built['treasury_key_file']}\n\nStart each execution service, bridge and CometBFT process using commands.txt.\nAfter all nodes converge, use `crakchain cluster-v22-check --inventory {root / 'governed-lab-inventory.json'}`.\n\nThe generated DISPOSABLE governance key views mirror the local CometBFT validator identities solely for lab campaigns. A production design still requires reviewed protected signer/key-separation policy.\n"""
    (root / "README-V22.md").write_text(instructions, encoding="utf-8")
    return inventory
