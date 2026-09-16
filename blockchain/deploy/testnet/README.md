# Crakbit Chain v0.10 — Public Testnet Operator Template

This directory is an **operator scaffold for a future public testnet**. It is not a mainnet deployment recipe and must not be used for real-value custody.

## Required local files

Create these locally and do not commit private validator material:

```text
genesis.json
validator-key.json
.env
```

`validator-key.json` must be generated and transferred securely for the specific validator host. Never reuse the devnet treasury key as a validator key.

## Important transport requirement

The compose template starts the node with `--require-peer-tls`. Therefore every validator `peer_url` in `genesis.json` must use `https://`.

The current Crakbit node only enforces HTTPS peer URLs; it does **not** yet provision certificates, perform reviewed mutual-TLS client authentication, pin certificates, or rotate them. A reverse proxy/service mesh may terminate TLS for testnet experiments, but this is not a substitute for the planned native validator mTLS lifecycle.

## RPC exposure

Do not publish port `9101` directly to the Internet. Put a hardened reverse proxy or load balancer in front of the RPC and enforce at least:

- TLS,
- connection limits,
- request/body limits,
- per-IP rate limits,
- timeouts,
- logging with secret/header redaction,
- firewall rules that keep `/internal/*` validator traffic private.

v0.10 adds node-local transaction rate limiting, request-size checks and bounded mempool/block selection, but those are defense-in-depth controls rather than DDoS protection.

## Start

After placing a reviewed genesis file and validator key on the host:

```bash
cp .env.example .env
docker compose up -d --build
```

Check locally from the host or trusted management network:

```bash
curl http://127.0.0.1:9101/health
curl http://127.0.0.1:9101/limits/status
curl http://127.0.0.1:9101/operations/status
```

If the reverse proxy is the only component publishing a public port, keep the validator container network private.

## Before a real public testnet

Still required:

1. reviewed cross-round BFT lock/unlock semantics or migration to an established BFT core,
2. mutual validator TLS with identity binding, pinning and rotation,
3. repeated partition/latency/Byzantine/load tests,
4. backup restore drills and corruption/power-loss tests,
5. alert routing and incident runbooks,
6. independent consensus/network security review.
