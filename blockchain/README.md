# Crakbit Chain — Development Network Prototype

**Status: early devnet / research prototype (`0.8.0-alpha`)**

Crakbit Chain is the experimental blockchain component of the Crakbit AI ecosystem. The current devnet implements native test-only **CRKBIT** accounting, signed transactions, certified view changes, a two-phase **prevote → precommit** finality pipeline, durable local consensus locks, authenticated validator requests, durable peer replay protection, quorum-certified state snapshots, resumable chunked snapshot transfer, recovery journaling, validator telemetry, peer synchronization, RPC/CLI tooling and a development explorer.

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

## v0.8 Recovery Upgrade

v0.8 keeps the existing research consensus flow unchanged and hardens snapshot transport and operational recovery.

New work includes:

- bounded chunked snapshot manifests,
- per-chunk SHA-256 validation,
- complete artifact hash validation,
- resumable verified chunk cache in the CLI,
- quorum certificate creation after chunk reassembly,
- crash-visible snapshot import journal,
- snapshot-base-aware history status/block endpoints,
- explicit distinction between certified current state and locally available historical blocks.

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

`--require-peer-tls` can enforce HTTPS peer URLs, but this is not yet a complete mTLS/certificate lifecycle.

## Quorum Snapshot Recovery

A quorum snapshot certificate requires strict `>2/3` signatures over the exact same snapshot hash. For the default four-validator devnet, at least three matching validator signatures are required.

Build a certificate using resumable verified chunks:

```bash
crakchain snapshot-fetch-chunked \
  --genesis runtime/genesis.json \
  --output runtime/snapshot-cert.json \
  --cache-dir runtime/snapshot-cache
```

The transfer manifest commits to every chunk and to the complete canonical JSON artifact. Re-running the command reuses valid cached chunks for the same artifact hash.

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

Or bootstrap a node before startup:

```bash
crakchain node \
  --genesis runtime/genesis.json \
  --key runtime/node4/validator.json \
  --data runtime/node4-recovered \
  --bootstrap-snapshot runtime/snapshot-cert.json \
  --port 9204
```

Snapshot bootstrap restores certified account balances/nonces and the finalized base hash. It does **not** reconstruct block bodies or transaction history before that snapshot base.

## Crash-Visible Import Journal

Before snapshot import mutates the database, v0.8 writes:

```text
snapshot-import.journal.json
```

next to the chain database. SQLite still provides the atomic database transaction; the sidecar records recovery intent and the target certificate hash/height/state root.

After success, the journal is removed. If a crash leaves it behind, re-running the same certificate can reconcile a completed commit or retry a rolled-back fresh database. A different certificate is refused until the unfinished journal is reviewed.

Status:

```bash
curl http://127.0.0.1:9101/recovery/import-journal
```

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
curl http://127.0.0.1:9101/metrics
curl http://127.0.0.1:9101/metrics/prometheus
curl http://127.0.0.1:9101/recovery/status
curl http://127.0.0.1:9101/history/status
```

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
- No validator-set changes, staking/slashing or production governance exists.
- Long-running Byzantine/partition/load testing remains incomplete.
- No independent consensus/network security audit has been completed.

See [`V0.8.md`](V0.8.md), [`SPEC.md`](SPEC.md) and [`SECURITY.md`](SECURITY.md) for protocol and security notes.

## Next Engineering Milestones — v0.9

1. Review/replace the conservative cross-round lock with a mature proof-based BFT design or reviewed BFT core.
2. Add mutually authenticated encrypted validator transport with certificate pinning/rotation.
3. Design archive/history synchronization for snapshot-bootstrapped nodes.
4. Add crash/corruption/abrupt-power-loss recovery harnesses.
5. Run long-lived partition, latency, Byzantine-behavior and load tests.
6. Add Grafana dashboards and alert rules.
7. Add public-testnet deployment manifests and operator runbooks.
8. Add faucet abuse controls and stronger wallet/explorer testnet UX.
9. Define validator key-management and incident-response procedures.
10. Commission independent consensus/network review before any public-value use.
