# Crakbit Chain — Development Network Prototype

**Status: research/devnet alpha (`0.10.0-alpha`)**

Crakbit Chain is the experimental blockchain component of the Crakbit AI ecosystem. The current development network includes native test-only `CRKBIT` accounting, Ed25519-signed transactions, certified view changes, prevote/precommit finality, authenticated validator requests, durable replay protection, quorum-certified state snapshots, resumable snapshot transfer, integrity checks, verified backups, Prometheus/Grafana monitoring and v0.10 resource-bounding controls.

> This is **not a production mainnet**, has not completed independent consensus/network review, and must not be used to custody real value.

## Devnet Parameters

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

## Consensus Flow

```text
proposal
   ↓
>2/3 PREVOTE certificate
   ↓
>2/3 PRECOMMIT certificate
   ↓
finalized block
```

Later rounds require certified view changes. Local phase votes and locks survive restart. The current cross-round lock remains conservative and is **not yet a reviewed production BFT lock/unlock protocol**.

## v0.10 Hardening

v0.10 adds:

- bounded public/internal request sizes,
- public `POST /transactions` rate limiting,
- maximum serialized transaction size,
- bounded mempool capacity,
- bounded block transaction selection,
- `/limits/status`,
- verified backup restore-drill tooling,
- Prometheus alert rules,
- a future public-testnet validator deployment scaffold.

Default development limits:

```text
CRAKBIT_MAX_PUBLIC_BODY_BYTES=262144
CRAKBIT_MAX_INTERNAL_BODY_BYTES=2097152
CRAKBIT_PUBLIC_TX_RPM=60
CRAKBIT_MAX_MEMPOOL_TXS=5000
CRAKBIT_MAX_BLOCK_TXS=1000
CRAKBIT_MAX_TX_BYTES=65536
```

These node-local limits are defense-in-depth. A public testnet still requires a hardened reverse proxy/load balancer, firewall policy and network-level abuse controls.

## Quick Start

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

## Wallet / Test Transfers

```bash
crakchain keygen --output runtime/alice.json
crakchain address --key runtime/alice.json
crakchain balance YOUR_ADDRESS --rpc http://127.0.0.1:9101
```

Send test units:

```bash
crakchain send \
  --key runtime/treasury.json \
  --genesis runtime/genesis.json \
  --to crk1RECIPIENT \
  --amount 25 \
  --rpc http://127.0.0.1:9101
```

Never commit or share validator/private wallet key files.

## Snapshot Recovery

Build a quorum certificate using resumable verified chunks:

```bash
crakchain snapshot-fetch-chunked \
  --genesis runtime/genesis.json \
  --output runtime/snapshot-cert.json \
  --cache-dir runtime/snapshot-cache
```

Verify:

```bash
crakchain snapshot-verify \
  --snapshot runtime/snapshot-cert.json \
  --genesis runtime/genesis.json
```

Import into a fresh node database:

```bash
crakchain snapshot-import \
  --snapshot runtime/snapshot-cert.json \
  --genesis runtime/genesis.json \
  --data runtime/recovered-node
```

Snapshot bootstrap restores certified state but does not reconstruct historical block bodies before the snapshot base.

## Integrity & Backups

Quick local integrity check:

```bash
crakchain doctor --genesis runtime/genesis.json --data runtime/node1-data
```

Full locally stored history/certificate check:

```bash
crakchain doctor --genesis runtime/genesis.json --data runtime/node1-data --full
```

Create a verified online SQLite backup:

```bash
crakchain backup-create \
  --genesis runtime/genesis.json \
  --data runtime/node1-data \
  --output runtime/backups/node1.sqlite3
```

Verify the backup:

```bash
crakchain backup-verify \
  --genesis runtime/genesis.json \
  --backup runtime/backups/node1.sqlite3 \
  --manifest runtime/backups/node1.sqlite3.manifest.json \
  --full
```

Restore drill into a fresh directory:

```bash
python scripts/backup_restore_drill.py \
  --genesis runtime/genesis.json \
  --backup runtime/backups/node1.sqlite3 \
  --manifest runtime/backups/node1.sqlite3.manifest.json \
  --output-data runtime/restore-drill/node1
```

The restore drill never replaces a live database automatically.

## Monitoring

Start the development Prometheus/Grafana stack after the local validators are running:

```bash
cd ops
docker compose -f docker-compose.observability.yml up -d
```

- Prometheus: `http://127.0.0.1:9090`
- Grafana: `http://127.0.0.1:3000`

The included credentials/configuration are development defaults and must not be exposed unchanged to the Internet.

Useful node endpoints:

```text
GET /health
GET /status
GET /limits/status
GET /operations/status
GET /integrity/status
GET /validators
GET /peers
GET /evidence
GET /consensus/events
GET /metrics
GET /metrics/prometheus
GET /snapshot/latest
GET /recovery/status
GET /history/status
```

## Future Public Testnet Scaffold

See [`deploy/testnet/`](deploy/testnet/).

The scaffold intentionally requires HTTPS validator peer URLs and keeps the validator service un-published by default. It still needs a real reverse proxy/network policy and does not provide native reviewed mTLS certificate provisioning or rotation.

## Tests

```bash
cd blockchain
pip install -e ".[dev]"
pytest -q
```

GitHub Actions runs the blockchain test suite on blockchain changes.

## Main Remaining Blockers

- mature proof-based cross-round BFT lock/unlock semantics or migration to an established reviewed BFT core,
- formal safety/liveness review,
- mutually authenticated validator TLS with certificate pinning and rotation,
- archive/history synchronization for snapshot-bootstrapped nodes,
- long-running partition/latency/Byzantine/load testing,
- production key-management and incident-response procedures,
- production firewall/reverse-proxy/DDoS controls,
- independent consensus/network/security audit.

See [`V0.10.md`](V0.10.md), [`V0.9.md`](V0.9.md), [`SPEC.md`](SPEC.md) and [`SECURITY.md`](SECURITY.md).
