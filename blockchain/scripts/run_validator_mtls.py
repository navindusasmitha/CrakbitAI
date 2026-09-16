from __future__ import annotations

import argparse
import os
import ssl

import uvicorn


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a Crakbit validator with mutual TLS on the validator RPC listener"
    )
    parser.add_argument("--genesis", required=True)
    parser.add_argument("--key", required=True, help="Ed25519 validator key JSON")
    parser.add_argument("--data", required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9101)
    parser.add_argument("--tls-cert", required=True, help="Validator X.509 certificate PEM")
    parser.add_argument("--tls-key", required=True, help="Private key for --tls-cert")
    parser.add_argument("--client-ca", required=True, help="CA used to verify validator client certificates")
    parser.add_argument("--peer-pins", default=None, help="JSON map: validator address -> leaf cert SHA-256")
    parser.add_argument("--require-peer-pins", action="store_true")
    args = parser.parse_args()

    os.environ["CRAKBIT_GENESIS"] = args.genesis
    os.environ["CRAKBIT_VALIDATOR_KEY"] = args.key
    os.environ["CRAKBIT_DATA_DIR"] = args.data
    os.environ["CRAKBIT_REQUIRE_PEER_TLS"] = "1"
    os.environ["CRAKBIT_REQUIRE_MTLS"] = "1"
    os.environ["CRAKBIT_MTLS_CA"] = args.client_ca
    os.environ["CRAKBIT_MTLS_CERT"] = args.tls_cert
    os.environ["CRAKBIT_MTLS_KEY"] = args.tls_key
    if args.peer_pins:
        os.environ["CRAKBIT_PEER_CERT_PINS"] = args.peer_pins
    if args.require_peer_pins:
        os.environ["CRAKBIT_REQUIRE_PEER_PINS"] = "1"

    # Import only after the environment is complete; app construction validates transport config.
    from crakbit_chain.secure_node_v11 import create_app

    uvicorn.run(
        create_app(),
        host=args.host,
        port=args.port,
        reload=False,
        ssl_keyfile=args.tls_key,
        ssl_certfile=args.tls_cert,
        ssl_ca_certs=args.client_ca,
        ssl_cert_reqs=ssl.CERT_REQUIRED,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
