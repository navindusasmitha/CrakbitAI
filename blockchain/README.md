# Crakbit Chain — Development Network Prototype

**Status: early devnet / research prototype (`0.9.0-alpha`)**

Crakbit Chain is the experimental blockchain component of the Crakbit AI ecosystem. The current devnet implements native test-only **CRKBIT** accounting, signed transactions, certified view changes, a two-phase **prevote → precommit** finality pipeline, durable local consensus locks, authenticated validator requests, durable peer replay protection, quorum-certified state snapshots, resumable chunked snapshot transfer, recovery journaling, local integrity diagnostics, verified online backups, validator telemetry, peer synchronization, RPC/CLI tooling and a development explorer.

> This is **not a production mainnet**, has not been independently audited, and must not be used to custody real value.

## Devnet Parameters

- Native symbol: `CRKBIT`
- Decimals: `8`
- Proposed maximum genesis supply: `21,000,000 CRKBIT`
- Default local validator count: `4`
- Default quorum: `3 of 4`
- Transaction/block/vote/request signatures: Ed25519
- Address format: `crk1...`
- Default block interval: 5 seconds
- Default view timeout: 10 seconds
- State storage: SQLite
- RPC: FastAPI / JSON over HTTP

The 21M cap is a **devnet configuration parameter**, not a promise of future token value or final mainnet economics.

## v0.9 Operations / Integrity Upgrade

v0.9 keeps the existing research consensus behavior unchanged and adds operator-safety tooling around storage, recovery and monitoring.

New work includes:

- `crakchain doctor` quick/full ledger integrity checks,
- SQLite corruption checks,
- genesis/tip/supply/snapshot-base consistency verification,
- local block-chain continuity verification,
- proposer/certificate/transaction-index verification,
- online SQLite backup creation,
- SHA-256 backup manifests,
- backup verification against chain identity and integrity checks,
- `/integrity/status` and `/operations/status`,
- development Prometheus + Grafana configuration and validator dashboard.

This phase does **not** claim to solve the remaining mature-BFT or validator-mTLS blockers.

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

Certified view changes remain required for later rounds. A validator persists its local lock when precommitting. The current lock remains deliberately conservative and is **not yet a complete production BFT unlock protocol**.

## Validator Request Authentication

Internal validator requests are signed with Ed25519 and commit to the HTTP method, request path, request-body hash, validator identity, timestamp and random nonce.

Accepted replay nonces are persisted in SQLite under the node data directory so a process restart does not immediately erase replay state.

A signed challenge/response endpoint verifies possession of the configured validator key.

`--require-peer-tls` can enforce HTTPS peer URLs, but this is not yet a complete mutually authenticated TLS/certificate lifecycle.

## Quorum Snapshot Recovery

A quorum snapshot certificate requires strict `>2/3` signatures over the exact same snapshot hash. For the default four-validator devnet, at least three matching validator signatures are required.

Build a certificate using resumable verified chunks:

```bash
crakchain snapshot-fetch-chunked \
  --genesis runtime/genesis.json \
  --output runtime/snapshot-cert.json \
  --cache-dir runtime/snapshot-cache
```

Verify the resulting certificate:

```bash
crakchain snapshot-verify \
  --snapshot runtime/snapshot-cert.json \
  --genesis runtime/genesis.json
```

Import into a **fresh** database only:

```bash
crakchain snapshot-import \
  --snapshot runtime/snapshot-cert.json \
  --genesis runtime/genesis.json \
  --data runtime/recovered-node
```

Snapshot bootstrap restores certified account balances/nonces and the finalized base hash. It does **not** reconstruct block bodies or transaction history before that snapshot base.

## v0.9 Integrity Doctor

Quick local check:

```bash
crakchain doctor \
  --genesis runtime/genesis.json \
  --data runtime/node1-data
```

Full local-history check:

```bash
crakchain doctor \
  --genesis runtime/genesis.json \
  --data runtime/node1-data \
  --full
```

Full mode verifies locally stored block continuity, block hashes, proposer schedule/signatures, transaction Merkle roots, view-change/prevote/precommit certificates and the local transaction index.

Snapshot-bootstrapped nodes are checked starting from their certified snapshot base. Missing pre-snapshot block bodies are reported as an expected limitation, not silently treated as locally available history.

RPC diagnostics:

```bash
curl http://127.0.0.1:9101/integrity/status
curl "http://127.0.0.1:9101/integrity/status?full=true"
curl http://127.0.0.1:9101/operations/status
```

## Verified Online Backups

Create a consistent online SQLite backup and SHA-256 manifest:

```bash
crakchain backup-create \
  --genesis runtime/genesis.json \
  --data runtime/node1-data \
  --output runtime/backups/node1.sqlite3
```

Verify later:

```bash
crakchain backup-verify \
  --genesis runtime/genesis.json \
  --backup runtime/backups/node1.sqlite3 \
  --manifest runtime/backups/node1.sqlite3.manifest.json \
  --full
```

The copied database must pass integrity verification before backup creation succeeds. The manifest binds the chain ID, genesis fingerprint, height, tip hash, file size and complete-file SHA-256.

## Snapshot-Aware History

```bash
curl http://127.0.0.1:9101/history/status
curl http://127.0.0.1:9101/history/block/1
```

A snapshot-bootstrapped node reports its snapshot base height/hash and local history start. Requests for unavailable pre-snapshot local block bodies return an explicit `410 Gone` explanation through the history-aware endpoint.

## Quick Start — Fresh Local Devnet

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

## Monitoring

```bash
curl http://127.0.0.1:9101/health
curl http://127.0.0.1:9101/status
curl http://127.0.0.1:9101/peers
curl http://127.0.0.1:9101/validators
curl http://127.0.0.1:9101/evidence
curl http://127.0.0.1:9101/consensus/events
curl http://127.0.0.1:9101/metrics/prometheus
curl http://127.0.0.1:9101/recovery/status
curl http://127.0.0.1:9101/history/status
curl http://127.0.0.1:9101/integrity/status
```

A development Prometheus + Grafana stack is available under [`ops/`](ops/):

```bash
cd blockchain/ops
docker compose -f docker-compose.observability.yml up -d
```

See [`ops/README.md`](ops/README.md). The included Grafana credentials are development defaults and must not be exposed unchanged.

## Wallet / Test CRKBIT

Bootstrap creates a **devnet-only** treasury key at `runtime/treasury.json` unless an existing test address is supplied.

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

## Explorer

```bash
python -m http.server 8080 -d explorer
```

Open `http://127.0.0.1:8080`.

## Development RPC Endpoints

Public development endpoints include:

- `GET /health`
- `GET /status`
- `GET /validators`
- `GET /peers`
- `GET /evidence`
- `GET /consensus/events`
- `GET /metrics`
- `GET /metrics/prometheus`
- `GET /snapshot/latest`
- `GET /snapshot/bundle/manifest`
- `GET /snapshot/bundle/chunk/{artifact_sha256}/{index}`
- `GET /recovery/status`
- `GET /recovery/import-journal`
- `GET /history/status`
- `GET /history/block/{height}`
- `GET /integrity/status`
- `GET /operations/status`
- `GET /balance/{address}`
- `GET /blocks/{height}`
- `GET /transactions/{txid}`
- `POST /transactions`

Authenticated development peer endpoints include:

- `POST /internal/hello`
- `POST /internal/transaction`
- `POST /internal/view-change-request`
- `POST /internal/prevote`
- `POST /internal/precommit`
- `POST /internal/proposal`
- `POST /internal/block`

## Run Tests

```bash
cd blockchain
pip install -e ".[dev]"
pytest -q
```

GitHub Actions also runs the blockchain test suite on repository changes.

## Important Limitations

- The conservative cross-round lock has no mature proof-based unlock rule.
- HTTPS enforcement does not provide a reviewed mTLS/certificate pinning/rotation lifecycle.
- Snapshot bootstrap does not reconstruct historical blocks before the snapshot base.
- Chunk caching resumes the same immutable bundle; it is not a production streaming protocol.
- Verified backups improve operations but are not a disaster-recovery substitute until restore drills and external copies are tested.
- The development Grafana stack has local default credentials and is not production hardened.
- No validator-set changes, staking/slashing or production governance exists.
- Long-running Byzantine/partition/load testing remains incomplete.
- No independent consensus/network security audit has been completed.

See [`V0.9.md`](V0.9.md), [`V0.8.md`](V0.8.md), [`SPEC.md`](SPEC.md) and [`SECURITY.md`](SECURITY.md) for protocol and security notes.

## Next Engineering Milestones — v0.10

1. Resolve the conservative cross-round consensus lock through a reviewed BFT design or migration to an established BFT core.
2. Add mutually authenticated encrypted validator transport with certificate/key lifecycle management.
3. Add archive/history synchronization for snapshot-bootstrapped nodes.
4. Add bounded RPC/mempool/request abuse controls.
5. Build repeatable partition, latency, Byzantine and load-test harnesses.
6. Add abrupt-power-loss/database-corruption recovery automation and backup restore drills.
7. Add authenticated monitoring, alert rules and incident-response runbooks.
8. Add reproducible public-testnet deployment manifests.
9. Improve faucet, wallet and explorer testnet UX.
10. Commission independent consensus/network review before any public-value use.
