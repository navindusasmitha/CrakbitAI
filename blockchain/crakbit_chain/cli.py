from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx
import uvicorn

from .crypto import KeyPair
from .genesis import Genesis
from .models import ATOMIC_UNITS, Transaction
from .snapshots import (
    build_snapshot_certificate,
    import_snapshot_certificate,
    verify_snapshot_artifact,
    verify_snapshot_certificate,
)
from .storage import Ledger


def cmd_keygen(args: argparse.Namespace) -> int:
    pair = KeyPair.generate()
    pair.save(args.output)
    print(pair.address)
    return 0


def cmd_address(args: argparse.Namespace) -> int:
    print(KeyPair.load(args.key).address)
    return 0


def cmd_balance(args: argparse.Namespace) -> int:
    response = httpx.get(f"{args.rpc.rstrip('/')}/balance/{args.address}", timeout=5.0)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))
    return 0


def cmd_send(args: argparse.Namespace) -> int:
    key = KeyPair.load(args.key)
    genesis = Genesis.load(args.genesis)
    account = httpx.get(f"{args.rpc.rstrip('/')}/balance/{key.address}", timeout=5.0)
    account.raise_for_status()
    nonce = int(account.json()["nonce"]) + 1
    amount = int(round(args.amount * ATOMIC_UNITS))
    fee = int(round(args.fee * ATOMIC_UNITS)) if args.fee is not None else genesis.min_fee
    tx = Transaction(
        chain_id=genesis.chain_id,
        sender=key.address,
        recipient=args.to,
        amount=amount,
        fee=fee,
        nonce=nonce,
        public_key=key.public_key_b64,
        memo=args.memo or "",
    )
    tx.signature = key.sign(tx.signing_bytes())
    response = httpx.post(
        f"{args.rpc.rstrip('/')}/transactions",
        json={"transaction": tx.to_dict()},
        timeout=5.0,
    )
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))
    return 0


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def cmd_snapshot_verify(args: argparse.Namespace) -> int:
    genesis = Genesis.load(args.genesis)
    artifact = _load_json(args.snapshot)
    snapshot = verify_snapshot_artifact(artifact, genesis)
    signatures = len(artifact.get("signatures", [])) if artifact.get("format") else 1
    print(
        json.dumps(
            {
                "valid": True,
                "height": snapshot["height"],
                "last_hash": snapshot["last_hash"],
                "accounts_root": snapshot["accounts_root"],
                "certificate_signatures": signatures,
                "required_quorum": genesis.quorum_size,
            },
            indent=2,
        )
    )
    return 0


def cmd_snapshot_fetch(args: argparse.Namespace) -> int:
    genesis = Genesis.load(args.genesis)
    envelopes: list[dict] = []
    failures: list[dict[str, str]] = []
    for peer in genesis.validators:
        url = f"{peer.peer_url.rstrip('/')}/snapshot/latest"
        try:
            response = httpx.get(url, timeout=args.timeout)
            response.raise_for_status()
            envelopes.append(response.json())
        except Exception as exc:
            failures.append({"validator": peer.address, "error": type(exc).__name__})
    certificate = build_snapshot_certificate(envelopes, genesis)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(certificate, indent=2) + "\n", encoding="utf-8")
    snapshot = verify_snapshot_certificate(certificate, genesis)
    print(
        json.dumps(
            {
                "saved": str(target),
                "height": snapshot["height"],
                "snapshot_hash": certificate["snapshot_hash"],
                "signatures": len(certificate["signatures"]),
                "required_quorum": genesis.quorum_size,
                "peer_failures": failures,
            },
            indent=2,
        )
    )
    return 0


def cmd_snapshot_import(args: argparse.Namespace) -> int:
    genesis = Genesis.load(args.genesis)
    certificate = _load_json(args.snapshot)
    data_dir = Path(args.data)
    data_dir.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(data_dir / "chain.sqlite3", genesis)
    snapshot = import_snapshot_certificate(ledger, certificate)
    print(
        json.dumps(
            {
                "imported": True,
                "database": str(data_dir / "chain.sqlite3"),
                "height": snapshot["height"],
                "last_hash": snapshot["last_hash"],
                "accounts_root": snapshot["accounts_root"],
                "history_before_snapshot_available": False,
            },
            indent=2,
        )
    )
    return 0


def cmd_node(args: argparse.Namespace) -> int:
    import os

    os.environ["CRAKBIT_GENESIS"] = args.genesis
    os.environ["CRAKBIT_VALIDATOR_KEY"] = args.key
    os.environ["CRAKBIT_DATA_DIR"] = args.data
    if args.require_peer_tls:
        os.environ["CRAKBIT_REQUIRE_PEER_TLS"] = "1"

    if args.bootstrap_snapshot:
        genesis = Genesis.load(args.genesis)
        ledger = Ledger(Path(args.data) / "chain.sqlite3", genesis)
        certificate = _load_json(args.bootstrap_snapshot)
        import_snapshot_certificate(ledger, certificate)

    from .secure_node_v07 import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port, reload=False)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="crakchain", description="Crakbit Chain devnet CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    keygen = sub.add_parser("keygen", help="Generate an Ed25519 wallet/validator key")
    keygen.add_argument("--output", required=True)
    keygen.set_defaults(func=cmd_keygen)

    address = sub.add_parser("address", help="Print the address for a key file")
    address.add_argument("--key", required=True)
    address.set_defaults(func=cmd_address)

    balance = sub.add_parser("balance", help="Read an account balance")
    balance.add_argument("address")
    balance.add_argument("--rpc", default="http://127.0.0.1:9101")
    balance.set_defaults(func=cmd_balance)

    send = sub.add_parser("send", help="Sign and submit a CRKBIT transfer")
    send.add_argument("--key", required=True)
    send.add_argument("--genesis", required=True)
    send.add_argument("--to", required=True)
    send.add_argument("--amount", type=float, required=True, help="Amount in CRKBIT")
    send.add_argument("--fee", type=float, default=None, help="Fee in CRKBIT; defaults to genesis minimum")
    send.add_argument("--memo", default="")
    send.add_argument("--rpc", default="http://127.0.0.1:9101")
    send.set_defaults(func=cmd_send)

    snapshot = sub.add_parser("snapshot-verify", help="Verify a signed or quorum-certified snapshot JSON file")
    snapshot.add_argument("--snapshot", required=True)
    snapshot.add_argument("--genesis", required=True)
    snapshot.set_defaults(func=cmd_snapshot_verify)

    snapshot_fetch = sub.add_parser(
        "snapshot-fetch",
        help="Fetch validator snapshots and save the newest state hash that reaches quorum",
    )
    snapshot_fetch.add_argument("--genesis", required=True)
    snapshot_fetch.add_argument("--output", required=True)
    snapshot_fetch.add_argument("--timeout", type=float, default=5.0)
    snapshot_fetch.set_defaults(func=cmd_snapshot_fetch)

    snapshot_import = sub.add_parser(
        "snapshot-import",
        help="Bootstrap a fresh node database from a quorum-certified snapshot",
    )
    snapshot_import.add_argument("--snapshot", required=True)
    snapshot_import.add_argument("--genesis", required=True)
    snapshot_import.add_argument("--data", required=True)
    snapshot_import.set_defaults(func=cmd_snapshot_import)

    node = sub.add_parser("node", help="Run a validator node")
    node.add_argument("--genesis", required=True)
    node.add_argument("--key", required=True)
    node.add_argument("--data", required=True)
    node.add_argument("--host", default="0.0.0.0")
    node.add_argument("--port", type=int, default=9101)
    node.add_argument(
        "--require-peer-tls",
        action="store_true",
        help="Refuse non-HTTPS validator peer URLs (intended for hardened deployments)",
    )
    node.add_argument(
        "--bootstrap-snapshot",
        default=None,
        help="Import a quorum-certified snapshot into a fresh node database before startup",
    )
    node.set_defaults(func=cmd_node)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
