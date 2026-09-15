# Crakbit Chain — Development Network Prototype

**Status: early devnet / research prototype (`0.5.0-alpha`)**

Crakbit Chain is the experimental blockchain component of the Crakbit AI ecosystem. The current devnet implements native test-only **CRKBIT** accounting, signed transactions, certified view changes, a two-phase **prevote → precommit** finality pipeline, durable local consensus locks, persistent consensus event history, validator telemetry, peer synchronization, RPC/CLI tooling and a development explorer.

> This is **not a production mainnet**, has not been independently audited, and must not be used to custody real value.

## Devnet Parameters

- Native symbol: `CRKBIT`
- Decimals: `8`
- Proposed maximum genesis supply: `21,000,000 CRKBIT`
- Default local validator count: `4`
- Default quorum: `3 of 4`
- Transaction/block/vote signatures: Ed25519
- Address format: `crk1...`
- Default block interval: 5 seconds
- Default view timeout: 10 seconds
- State storage: SQLite
- RPC: FastAPI / JSON over HTTP

The 21M cap is a **devnet configuration parameter**, not a promise of future token value or final mainnet economics.

## What v0.5 Adds

v0.4 finalized a proposal after one signed quorum vote phase. v0.5 introduces two explicit validator phases:

```text
proposal
   ↓
>2/3 PREVOTE certificate
   ↓
>2/3 PRECOMMIT certificate
   ↓
finalized block
```

A validator only signs a precommit after locally validating a quorum prevote certificate for the exact block hash, height and round.

The node also persists local prevotes, local precommits, a per-height consensus lock, round changes, local view-change actions, consensus event history and conflicting signed-proposal evidence in SQLite.

## Consensus Flow

For height `H` and round `R`, the expected proposer is:

```text
validator_index = (H - 1 + R) mod validator_count
```

The proposer builds and signs a block. Validators independently validate the proposal and sign a **prevote**. Once the proposer has a strict greater-than-two-thirds prevote certificate, validators may sign a **precommit** for that same block.

A validator persists its local lock when precommitting. A finalized block must contain both a valid prevote quorum certificate and a valid precommit quorum certificate.

If a round times out before finalization, validators can sign a certified view change for the next round, as introduced in v0.4.

## Conservative Lock Rule

v0.5 deliberately uses a conservative lock rule: once a validator has precommitted a block hash at a height, it refuses to vote for a different block hash at that height in a later round.

This improves safety compared with unrestricted cross-round voting, but it is **not a complete production BFT lock/unlock protocol**. If a quorum becomes locked and the block is not finalized/broadcast successfully, the devnet may halt rather than unlock unsafely.

A reviewed proof-of-lock/unlock rule or mature BFT implementation is still required before public-value use.

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
- Signed prevotes
- Signed precommits
- >2/3 prevote certificate validation
- >2/3 precommit certificate validation
- Durable same-phase anti-double-vote records
- Durable per-height consensus lock
- Conflicting signed-proposal evidence
- Persistent consensus event journal
- Finalized-block peer sync
- Validator health/height/round telemetry
- REST/RPC endpoints
- CLI key/balance/send tooling
- 4-validator Docker Compose devnet
- Browser development explorer
- Automated ledger/consensus tests in GitHub Actions

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

### Upgrading from v0.4 or earlier

The devnet schema and consensus certificate format changed. Treat previous local devnet data as disposable:

```bash
docker compose down -v
```

Delete local `runtime/`, regenerate it, then restart:

```bash
python scripts/bootstrap_devnet.py
docker compose up --build
```

Never use this reset procedure for an environment containing real-value keys or production data.

## Monitoring

```bash
curl http://127.0.0.1:9101/health
curl http://127.0.0.1:9101/status
curl http://127.0.0.1:9101/peers
curl http://127.0.0.1:9101/validators
curl http://127.0.0.1:9101/evidence
curl http://127.0.0.1:9101/consensus/events
curl http://127.0.0.1:9101/metrics
```

Useful v0.5 status fields include `candidate_prevotes`, `candidate_precommits`, `local_lock`, `persistent_phase_votes`, `consensus_events`, `view_certificate_votes` and `equivocation_evidence`.

## Wallet / Transfers

```bash
crakchain keygen --output runtime/alice.json
crakchain address --key runtime/alice.json
crakchain balance YOUR_ADDRESS --rpc http://127.0.0.1:9101
```

Send test CRKBIT:

```bash
crakchain send \
  --key runtime/treasury.json \
  --genesis runtime/genesis.json \
  --to crk1RECIPIENT \
  --amount 25 \
  --rpc http://127.0.0.1:9101
```

## RPC Endpoints

Public development endpoints:

- `GET /health`
- `GET /status`
- `GET /validators`
- `GET /peers`
- `GET /evidence`
- `GET /consensus/events`
- `GET /metrics`
- `GET /balance/{address}`
- `GET /blocks/{height}`
- `GET /transactions/{txid}`
- `POST /transactions`

Development peer endpoints:

- `POST /internal/transaction`
- `POST /internal/view-change-request`
- `POST /internal/prevote`
- `POST /internal/precommit`
- `POST /internal/block`

`/internal/*` is still development-only and **must not be exposed as production validator networking**.

## Tests

```bash
cd blockchain
pip install -e ".[dev]"
pytest -q
```

GitHub Actions runs the blockchain test suite on repository changes.

## Important Security Limitations

v0.5 is still a research network. Major remaining blockers include:

- no mature proof-based cross-round unlock rule
- no formal safety/liveness proof
- validator transport is still unauthenticated HTTP
- no encrypted/mutually authenticated P2P channel
- no production DoS/rate controls
- no signed state snapshots or fast state sync
- no production validator key-management standard
- no staking/slashing/governance system
- no independent audit
- no long-lived public testnet

## Next Phase — v0.6

1. Define/review a safer cross-round lock/unlock rule or migrate to a mature BFT core.
2. Add authenticated validator identity handshakes.
3. Add encrypted validator transport / deployment TLS requirements.
4. Add signed state snapshots and verified fast state sync.
5. Add crash/recovery, partition and long-running load tests.
6. Add Prometheus-style metrics, dashboard and alerts.
7. Add public-testnet deployment manifests and operator runbooks.
8. Improve faucet, explorer and testnet wallet UX.
9. Commission external consensus/network review before any production-value launch.

Read [`SPEC.md`](SPEC.md) and [`SECURITY.md`](SECURITY.md) before extending consensus or networking.
