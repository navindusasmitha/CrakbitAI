# Crakbit Chain — Development Network Prototype

**Status: early devnet / research prototype (`0.7.0-alpha`)**

Crakbit Chain is the experimental blockchain component of the Crakbit AI ecosystem. The current devnet includes native test-only **CRKBIT** accounting, signed transactions, certified view changes, a two-phase **prevote → precommit** finality pipeline, durable local consensus locks, authenticated validator requests, persistent replay protection, quorum-certified state snapshots, snapshot bootstrap/recovery tooling, metrics, CLI tooling and a development explorer.

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

## v0.7 Recovery + Replay Hardening

v0.7 keeps the v0.6 consensus semantics and hardens validator recovery.

### Persistent peer replay protection

Signed validator requests commit to the HTTP method, path, body hash, validator identity, timestamp and nonce. When `CRAKBIT_DATA_DIR` is configured, accepted replay nonces are now persisted in:

```text
<CRAKBIT_DATA_DIR>/peer-replay.sqlite3
```

This prevents a simple validator-process restart from immediately erasing the replay cache.

### Quorum-certified snapshots

A single validator snapshot is no longer sufficient for recovery bootstrap. v0.7 can combine signatures only when a strict `>2/3` validator quorum signed the **same snapshot hash**.

For the default four-validator devnet, this means **3 matching signatures**.

### Snapshot fetch / verify / import

Fetch matching snapshots from configured validators and build a certificate:

```bash
crakchain snapshot-fetch \
  --genesis runtime/genesis.json \
  --output runtime/snapshot-cert.json
```

Verify it:

```bash
crakchain snapshot-verify \
  --snapshot runtime/snapshot-cert.json \
  --genesis runtime/genesis.json
```

Import only into a fresh height-zero database:

```bash
crakchain snapshot-import \
  --snapshot runtime/snapshot-cert.json \
  --genesis runtime/genesis.json \
  --data runtime/recovered-node
```

Or bootstrap a validator directly:

```bash
crakchain node \
  --genesis runtime/genesis.json \
  --key runtime/node4/validator.json \
  --data runtime/node4-recovered \
  --bootstrap-snapshot runtime/snapshot-cert.json \
  --port 9104
```

Pre-snapshot historical blocks are **not reconstructed**. The imported state establishes a certified base height/hash; normal synchronization can continue from blocks newer than that height.

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

Certified view changes remain required for later rounds. A validator persists its local lock when precommitting. The current lock is deliberately conservative: a validator that precommits one block hash at a height refuses to vote for another hash at that height.

This is **not yet a mature production BFT unlock protocol**.

## What Works

- Ed25519 wallet/key generation
- `crk1...` address derivation
- Signed CRKBIT transfers
- Transaction nonces and replay protection
- Minimum transaction fees
- Genesis allocation
- Signed block proposals
- Transaction Merkle root and deterministic state root
- Round-specific proposer selection
- Quorum-certified view changes
- Signed prevotes and precommits
- >2/3 prevote and precommit certificate validation
- Durable same-phase anti-double-vote records
- Durable per-height consensus lock
- Conflicting signed-proposal evidence
- Persistent consensus event journal
- Ed25519-authenticated `/internal/*` validator requests
- Timestamp + nonce request validation
- **SQLite-persistent peer replay cache**
- Signed validator challenge/response identity handshake
- Optional HTTPS peer-URL enforcement mode
- Signed state snapshot export
- **>2/3 quorum snapshot certification**
- **Certified snapshot verification and fresh-database import**
- **Node bootstrap from a certified snapshot**
- Recovery metadata endpoint
- JSON and Prometheus-style development metrics
- Finalized-block peer sync
- Validator health/height/round telemetry
- REST/RPC endpoints
- CLI key/balance/send/snapshot tooling
- 4-validator Docker Compose devnet
- Browser development explorer
- Automated ledger/consensus/peer-auth/recovery tests in GitHub Actions

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
```

## Peer Security Model

Application-level request authentication protects validator request identity and body integrity. It does **not** by itself encrypt traffic.

Local Docker development remains HTTP. `--require-peer-tls` rejects non-HTTPS peer URLs, but v0.7 still does not provision certificates, implement mTLS certificate pinning, or automate certificate/key rotation.

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
- `GET /recovery/status`
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

- The conservative cross-round lock still has no mature proof-based unlock rule.
- Local Docker peer traffic is not encrypted by default.
- HTTPS enforcement is not the same as reviewed mTLS/certificate lifecycle management.
- Snapshot import reconstructs state, **not historical blocks before the snapshot base height**.
- Snapshot transfer is not chunked/resumable and does not yet include bandwidth/size controls.
- No validator-set changes, staking/slashing or production governance exists.
- No formal consensus proof or independent consensus/network audit has been completed.

See [`V0.7.md`](V0.7.md), [`SPEC.md`](SPEC.md) and [`SECURITY.md`](SECURITY.md) for protocol and security notes.

## Next Engineering Milestones — v0.8

1. Review/replace the conservative lock with a mature proof-based cross-round BFT lock/unlock design or migrate to a reviewed BFT core.
2. Add mutually authenticated TLS validator transport, certificate pinning and rotation.
3. Add snapshot chunking, transfer limits and resumable state sync.
4. Add explicit snapshot-base awareness to historical block APIs.
5. Add crash/corruption/interrupted-import recovery tests.
6. Run long-lived partition, latency, Byzantine-behavior and load tests.
7. Add Grafana dashboards and alert rules.
8. Add public-testnet deployment manifests, faucet controls and operator runbooks.
9. Commission independent consensus/network review before any real-value launch.
