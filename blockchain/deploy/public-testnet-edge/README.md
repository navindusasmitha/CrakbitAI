# Crakbit v0.17 Public-Testnet Edge Profile

This directory is an **operator scaffold for a public testnet**, not a complete production WAF/DDoS architecture and not evidence that a production mainnet exists.

It puts one controlled NGINX edge in front of the Crakbit public gateway and provides:

- TLS 1.2/1.3 termination using operator-mounted certificates,
- HTTP-to-HTTPS redirect,
- request-body and connection bounds,
- separate rate-limit zones for transaction, faucet and Mining Lab writes,
- general API limits,
- upstream timeouts,
- controlled forwarding headers,
- basic security headers.

## Certificate layout

Set `CRAKBIT_TLS_DIR` to a directory outside the repository containing:

```text
fullchain.pem
privkey.pem
```

Never commit the private key or copy it into GitHub issues/chats.

Example PowerShell:

```powershell
$env:CRAKBIT_TLS_DIR="C:\crakbit-secrets\edge-tls"
docker compose up -d edge
```

Example Linux:

```bash
export CRAKBIT_TLS_DIR=/etc/crakbit/edge-tls
docker compose up -d edge
```

The NGINX upstream name is `gateway:9600`. Connect the real v0.16/v0.17 public gateway to the same private Docker network or adapt the upstream to an explicitly private service address.

## Trust boundary

Do not expose the execution-service bearer endpoint, ABCI socket, validator signer port, validator operator endpoints or raw database files through this edge.

The gateway should remain the only browser-facing application service behind the edge. CometBFT RPC exposure should be deliberately scoped and independently rate-limited if made public.

## Limits

The supplied rate limits are conservative starting values for testing, not universal production values. Measure actual traffic and failure behavior before changing them.

NGINX shared-memory zones coordinate limits across worker processes on **one edge host**. They do not form a globally distributed limiter across multiple edge hosts. A multi-edge deployment still needs a shared API gateway/rate-limit/WAF design.

## Remaining gate

Before any production-value launch, this profile still requires capacity testing, trusted-proxy review, certificate automation/rotation, upstream redundancy, logging/alerting, DDoS planning and independent web/API penetration testing.
