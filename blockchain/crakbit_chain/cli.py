from __future__ import annotations

import argparse
import json

import httpx
import uvicorn

from .crypto import KeyPair
from .genesis import Genesis
from .models import ATOMIC_UNITS, Transaction
from .snapshots import verify_snapshot


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


def cmd_snapshot_verify(args: argparse.Namespace) -> int:
    genesis = Genesis.load(args.genesis)
    with open(args.snapshot, "r", encoding="utf-8") as handle:
        envelope = json.load(handle)
    snapshot = verify_snapshot(envelope, genesis)
    print(
        json.dumps(
            {
                "valid": True,
                "height": snapshot["height"],
                "last_hash": snapshot["last_hash"],
                "accounts_root": snapshot["accounts_root"],
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
    from .secure_node import create_app

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

    snapshot = sub.add_parser("snapshot-verify", help="Verify a signed Crakbit state snapshot JSON file")
    snapshot.add_argument("--snapshot", required=True)
    snapshot.add_argument("--genesis", required=True)
    snapshot.set_defaults(func=cmd_snapshot_verify)

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
    node.set_defaults(func=cmd_node)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
