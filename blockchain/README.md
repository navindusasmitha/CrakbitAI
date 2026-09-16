# Crakbit Chain — Development Network Prototype

**Status: research/devnet alpha (`0.12.0-alpha`)**

Crakbit Chain is the experimental blockchain component of the Crakbit AI ecosystem. The current development network includes native test-only `CRKBIT` accounting, Ed25519-signed transactions, certified view changes, prevote/precommit finality, authenticated validator requests, durable replay protection, quorum-certified snapshots, resumable recovery, integrity checks, verified backups, bounded RPC/mempool behavior, mTLS/pinning support, verified history archives and public-testnet operations tooling.

> This is **not a production mainnet**, has not completed independent consensus/network review, and must not be used to custody real value.

## Devnet parameters

- Symbol: `CRKBIT`
- Decimals: `8`
- Proposed development genesis cap: `21,000,000 CRKBIT`
- Default validators: `4`
- Default quorum: `3 of 4`
- Address format: `crk1...`
- Signatures: Ed25519
- State storage: SQLite
- RPC: FastAPI / JSON

The 21M value is a development-network configuration parameter, not a promise of future token value or final mainnet economics.

## Consensus direction

The current Python consensus remains a research implementation. `docs/ADR-0001-consensus-direction.md` records the decision that Crakbit will not keep extending this prototype as if it were production BFT. Before public-value mainnet planning, the project will evaluate migration of the execution/state layer to an established independently reviewed BFT core, with a Tendermint/CometBFT-style protocol as the primary architectural reference.

Current research flow:

```text
proposal
   ↓
>2/3 PREVOTE certificate
   ↓
>2/3 PRECOMMIT certificate
   ↓
finalized block
```

## v0.12 large update

v0.12 adds:

- fully verified genesis-anchored history archive export,
- archive replay verification of signatures, certificates, balances, nonces, state roots and hash continuity,
- verified pre-snapshot history backfill for snapshot-bootstrapped nodes without changing current state,
- `archive-export`, `archive-verify` and `archive-import` CLI commands,
- explicit consensus/execution boundary groundwork for future reviewed-BFT integration,
- optional bearer authentication for operator/monitoring endpoints,
- dual TLS certificate-pin overlap for safer certificate rotation,
- explicit duplicate/conflicting/forged validator-vote rejection fixtures,
- multi-node soak/divergence monitoring script,
- deny-by-default nftables public-testnet example,
- `/archive/status`, `/execution/status` and `/operator/security-status`.

See [`V0.12.md`](V0.12.md) for the full phase notes and limitations.

## Quick start

Requirements: Python 3.11+ and Docker Desktop / Docker Engine.

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
python scripts/bootstrap_devnet.py
docker compose up --build
```

Local RPC endpoints:

- Node 1: `http://127.0.0.1:9101`
- Node 2: `http://127.0.0.1:9102`
- Node 3: `http://127.0.0.1:9103`
- Node 4: `http://127.0.0.1:9104`
- API docs: `http://127.0.0.1:9101/docs`

## Wallet / test transfers

```bash
crakchain keygen --output runtime/alice.json
crakchain address --key runtime/alice.json
crakchain balance YOUR_ADDRESS --rpc http://127.0.0.1:9101
```

```bash
crakchain send \
  --key runtime/treasury.json \
  --genesis runtime/genesis.json \
  --to crk1RECIPIENT \
  --amount 25 \
  --rpc http://127.0.0.1:9101
```

Never commit or share validator/private wallet key files.

## Snapshot recovery

```bash
crakchain snapshot-fetch-chunked \
  --genesis runtime/genesis.json \
  --output runtime/snapshot-cert.json \
  --cache-dir runtime/snapshot-cache

crakchain snapshot-verify \
  --snapshot runtime/snapshot-cert.json \
  --genesis runtime/genesis.json

crakchain snapshot-import \
  --snapshot runtime/snapshot-cert.json \
  --genesis runtime/genesis.json \
  --data runtime/recovered-node
```

Snapshot bootstrap restores certified state but does not itself reconstruct older block bodies.

## v0.12 history archive / sync

Export a full genesis-anchored archive from a full-history node:

```bash
crakchain archive-export \
  --genesis runtime/genesis.json \
  --data runtime/node1-data \
  --output runtime/history.json
```

Verify it independently by replaying from genesis:

```bash
crakchain archive-verify \
  --genesis runtime/genesis.json \
  --archive runtime/history.json
```

Backfill verified history into a snapshot-bootstrapped node without changing balances/nonces/current state:

```bash
crakchain archive-import \
  --genesis runtime/genesis.json \
  --data runtime/recovered-node \
  --archive runtime/history.json
```

Useful status endpoints:

```text
GET /history/status
GET /archive/status
GET /history/block/{height}
```

## Validator transport security

v0.11+ supports operator-managed mTLS, CA/hostname verification and optional certificate SHA-256 pinning. v0.12 extends pin files to allow a bounded two-pin overlap during certificate rotation.

```json
{
  "crk1VALIDATOR": [
    "old_certificate_sha256",
    "new_certificate_sha256"
  ]
}
```

Remove the old fingerprint after all peers have confirmed the new certificate.

## Operator monitoring authentication

Optionally set a long random bearer token:

```text
CRAKBIT_MONITORING_BEARER_TOKEN=<secret-at-least-24-characters>
```

When enabled, monitoring/operations endpoints require an `Authorization: Bearer ...` header. This does not replace private networking, firewall policy or reverse-proxy access controls.

## Integrity & backups

```bash
crakchain doctor --genesis runtime/genesis.json --data runtime/node1-data --full

crakchain backup-create \
  --genesis runtime/genesis.json \
  --data runtime/node1-data \
  --output runtime/backups/node1.sqlite3

crakchain backup-verify \
  --genesis runtime/genesis.json \
  --backup runtime/backups/node1.sqlite3 \
  --manifest runtime/backups/node1.sqlite3.manifest.json \
  --full
```

## Multi-node soak monitoring

```bash
python scripts/soak_test.py \
  --node http://127.0.0.1:9101 \
  --node http://127.0.0.1:9102 \
  --node http://127.0.0.1:9103 \
  --node http://127.0.0.1:9104 \
  --duration-seconds 3600 \
  --interval-seconds 5 \
  --output runtime/soak-results.jsonl \
  --fail-on-divergence
```

The script records availability, latency, height spread and same-height hash divergence. It is evidence-gathering tooling, not a proof of consensus safety.

## Monitoring stack

```bash
cd ops
docker compose -f docker-compose.observability.yml up -d
```

- Prometheus: `http://127.0.0.1:9090`
- Grafana: `http://127.0.0.1:3000`

Development credentials/configuration must not be exposed unchanged to the Internet.

## Public-testnet deployment examples

See [`deploy/testnet/`](deploy/testnet/), including one-validator-per-host compose, mTLS environment configuration, reverse-proxy hardening and a deny-by-default nftables example.

These are reviewable starting points, not production deployment guarantees.

## Tests

```bash
cd blockchain
pip install -e ".[dev]"
pytest -q
```

GitHub Actions runs the blockchain test suite on blockchain changes.

## Main remaining blockers

- actual integration with an established independently reviewed BFT core,
- protocol-level consensus/execution integration and formal safety/liveness review,
- sustained independent-host partition/latency/Byzantine/load/soak testing,
- production validator key custody/HSM-equivalent strategy,
- production monitoring/alert routing and secret management,
- production firewall/reverse-proxy/DDoS architecture review,
- independent consensus/network/security audit,
- meaningful public-testnet operation before any mainnet planning.

See [`V0.12.md`](V0.12.md), [`V0.11.md`](V0.11.md), [`SPEC.md`](SPEC.md), [`SECURITY.md`](SECURITY.md) and [`docs/ADR-0001-consensus-direction.md`](docs/ADR-0001-consensus-direction.md).
