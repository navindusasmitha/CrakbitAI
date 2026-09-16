# Crakbit Chain — Development Network Prototype

**Status: early devnet / research prototype (`0.6.0-alpha`)**

Crakbit Chain is the experimental blockchain component of the Crakbit AI ecosystem. The current devnet implements native test-only **CRKBIT** accounting, signed transactions, certified view changes, a two-phase **prevote → precommit** finality pipeline, durable local consensus locks, persistent consensus event history, authenticated validator-to-validator requests, signed identity handshakes, signed state snapshots, validator telemetry, peer synchronization, RPC/CLI tooling and a development explorer.

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

## v0.6 Security Upgrade

v0.6 keeps the v0.5 consensus flow and hardens the validator-network boundary.

Internal validator requests now include an Ed25519 signature that commits to the HTTP method, request path, request-body hash, validator identity, timestamp and random nonce. Receivers verify the signer against the configured validator set, reject stale timestamps and reject duplicate nonces during the active replay window.

The node also exposes a signed challenge/response validator identity handshake and can require `https://` peer URLs in hardened deployments.

Enable HTTPS URL enforcement with:

```bash
crakchain node ... --require-peer-tls
```

or:

```bash
CRAKBIT_REQUIRE_PEER_TLS=1
```

This enforcement mode does **not** provision TLS certificates automatically. Local Docker development remains HTTP unless operators explicitly deploy HTTPS/TLS infrastructure.

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

Certified view changes remain required for later rounds. A validator persists its local lock when precommitting. The current lock remains deliberately conservative: a validator that precommits one block hash at a height refuses to vote for another hash at that height.

This is not yet a complete production BFT unlock protocol.

## What Works

- Ed25519 wallet/key generation
- `crk1...` address derivation
- Signed CRKBIT transfers
- Nonces and replay protection
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
- Timestamp + nonce replay-window checks for peer requests
- Signed validator challenge/response identity handshake
- Optional HTTPS peer-URL enforcement mode
- Signed state snapshot export and verification
- JSON and Prometheus-style development metrics
- Finalized-block peer sync
- Validator health/height/round telemetry
- REST/RPC endpoints
- CLI key/balance/send/snapshot verification tooling
- 4-validator Docker Compose devnet
- Browser development explorer
- Automated ledger/consensus/peer-auth/snapshot tests in GitHub Actions

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
```

## Signed Snapshot

Export the latest validator-signed state snapshot:

```bash
curl http://127.0.0.1:9101/snapshot/latest -o snapshot.json
```

Verify it locally:

```bash
crakchain snapshot-verify \
  --snapshot snapshot.json \
  --genesis runtime/genesis.json
```

v0.6 supports signed snapshot **generation and verification only**. Snapshot-based database import / fast state sync is not yet implemented.

## Peer Security Model

Application-level request authentication covers consensus/internal request identity and body integrity. It does not by itself encrypt network traffic.

The local devnet uses ordinary HTTP. A hardened remote validator deployment should use HTTPS/TLS and should eventually move to a reviewed mutually authenticated validator transport with certificate/key lifecycle management.

Replay-nonce memory is currently process-local. Timestamp validation limits the accepted replay window, but stronger session-level replay guarantees are still required before production use.

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
- Validator request replay state is process-local.
- Local Docker peer traffic is not encrypted by default.
- HTTPS enforcement does not provide certificate provisioning or mTLS automatically.
- Signed snapshots cannot yet be imported for fast state sync.
- No validator-set changes, staking/slashing or production governance exists.
- No independent consensus/network security audit has been completed.

See [`V0.6.md`](V0.6.md), [`SPEC.md`](SPEC.md) and [`SECURITY.md`](SECURITY.md) for protocol and security notes.

## Next Engineering Milestones — v0.7

1. Review/replace the conservative cross-round lock with a mature proof-based unlock/BFT design.
2. Add mutually authenticated encrypted validator transport with certificate/key rotation.
3. Harden replay/session handling across restarts.
4. Add snapshot quorum certification and verified snapshot import / fast state sync.
5. Add database-corruption and crash/restart recovery testing.
6. Run long-lived partition, latency, Byzantine-behavior and load tests.
7. Add Grafana/alerting deployment examples and public-testnet observability.
8. Add public-testnet infrastructure, faucet controls and operator runbooks.
9. Commission independent consensus/network review before any real-value launch.
