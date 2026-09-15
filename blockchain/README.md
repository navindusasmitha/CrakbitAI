# Crakbit Chain — Development Network Prototype

**Status: early devnet / research prototype (`0.4.0-alpha`)**

Crakbit Chain is the experimental blockchain component of the Crakbit AI ecosystem. The current devnet implements native test-only **CRKBIT** accounting, signed transactions, quorum-finalized blocks, quorum-certified view changes, round-based proposer failover, persistent consensus state, conservative cross-round vote locking, equivocation evidence, validator health telemetry, peer synchronization, an RPC API, CLI tooling and a simple explorer.

> This is **not a production mainnet**, has not been independently audited, and must not be used to custody real value.

## Devnet Parameters

- Native symbol: `CRKBIT`
- Decimals: `8`
- Proposed maximum genesis supply: `21,000,000 CRKBIT`
- Development consensus: rotating PoA proposals + signed >2/3 commit quorum + signed >2/3 view-change quorum
- Default local validator count: `4`
- Default local quorum: `3 of 4`
- Transaction/block/vote/view-change signatures: Ed25519
- Address format: `crk1...`
- Default block interval: 5 seconds
- Default view timeout: 10 seconds
- State/consensus storage: SQLite
- RPC: FastAPI / JSON over HTTP

The 21M cap is encoded only in generated devnet genesis configuration. It is **not a promise of future token value or final mainnet economics**.

## What Works

- Ed25519 wallet/key generation and `crk1...` addresses
- Signed CRKBIT transfers, nonces, replay protection and minimum fees
- Round-specific deterministic proposer selection
- Signed block proposals
- Signed validator commit votes
- Strict greater-than-two-thirds commit quorum before finalization
- Signed view-change messages for round advancement
- Strict greater-than-two-thirds view-change certificate for non-zero rounds
- View-change certificates embedded in later-round finalized blocks
- Persistent local consensus round across validator restarts
- Persistent same-round anti-double-vote state
- Conservative cross-round vote lock after a validator signs a block at a height
- Conflicting signed proposal/equivocation evidence persistence
- Previous-block hash linking
- Transaction Merkle roots and deterministic state roots
- SQLite-backed chain/account/consensus state
- Finalized block broadcast and catch-up sync
- REST endpoints for health, status, peers, validators, evidence, balances, blocks and transactions
- Validator health/height/round telemetry
- 4-validator Docker Compose devnet
- Browser development explorer
- Automated ledger/signature/quorum/view-change/evidence tests

## What v0.4 Changes

v0.3 allowed every validator to advance its local round after a timeout. v0.4 changes failover so a non-zero round must be justified by a **signed quorum view-change certificate**.

For height `H`, a validator first waits for the configured view timeout. It can then sign a `ViewChange` message from round `R` to `R+1`. A new round becomes usable only after at least:

```text
floor(2 * validator_count / 3) + 1
```

valid validator view-change signatures are collected.

For the default four-validator devnet this is **3 of 4** signatures. A later-round proposal carries the certificate, and every validator verifies it before signing a commit vote.

v0.4 also persists the local consensus round and view-change actions in SQLite. Restarting a validator therefore does not automatically return it to round zero for an unfinished height.

### Conservative cross-round lock

Once a validator signs a commit vote for a block at a height, v0.4 records that block as the validator's local lock. The validator refuses to sign a different block hash at that same height in a later round.

This is deliberately conservative: it improves safety against conflicting cross-round votes but does **not** yet implement a complete unlock/proof-of-lock rule. Under some partial-failure/network-partition scenarios this can halt progress rather than risk signing a conflicting block.

### Equivocation evidence

After a signed proposal passes normal proposal validation, the node records the proposal hash for `(height, round, proposer)`. If the same proposer later presents a second valid signed proposal with a different hash for that same height and round, the node stores evidence and refuses to vote for the conflicting proposal.

Evidence can be inspected with:

```bash
curl http://127.0.0.1:9101/evidence
```

No automatic slashing or punishment is implemented.

## Important Safety Limitation

v0.4 is **not a complete production BFT implementation**.

In particular, the current conservative lock does not yet include a mature proof-of-lock/unlock rule, multi-phase prevote/precommit state machine, formal safety/liveness proof, validator-set changes, staking/slashing, or authenticated encrypted P2P transport.

The internal HTTP peer API is development-only. Do not expose it directly to the public internet for a real-value network.

## Quick Start — Fresh Local 4-Validator Devnet

Requirements: Python 3.11+ and Docker Desktop / Docker Engine.

```bash
cd blockchain
python -m venv .venv
```

Activate the environment and install:

```bash
pip install -e ".[dev]"
```

Generate fresh devnet keys and genesis:

```bash
python scripts/bootstrap_devnet.py
```

Optional topology/timing settings:

```bash
python scripts/bootstrap_devnet.py --validators 4 --block-time-ms 5000 --view-timeout-ms 10000
```

Start the network:

```bash
docker compose up --build
```

RPC endpoints:

- Node 1: `http://127.0.0.1:9101`
- Node 2: `http://127.0.0.1:9102`
- Node 3: `http://127.0.0.1:9103`
- Node 4: `http://127.0.0.1:9104`
- API docs: `http://127.0.0.1:9101/docs`

### Upgrading an older disposable devnet

For a clean v0.4 test network:

```bash
docker compose down -v
```

Delete only the local disposable `runtime/` devnet directory, then regenerate it:

```bash
python scripts/bootstrap_devnet.py
docker compose up --build
```

Never delete/reset an environment containing real-value keys or data. The reset instruction above applies only to this disposable research devnet.

## Monitoring

```bash
curl http://127.0.0.1:9101/health
curl http://127.0.0.1:9101/status
curl http://127.0.0.1:9101/validators
curl http://127.0.0.1:9101/peers
curl http://127.0.0.1:9101/evidence
```

`/status` includes the current consensus round, view-certificate size, current proposer, local conservative lock, persistent vote/view state counts and equivocation-evidence count.

Peer-health telemetry remains unauthenticated operational data and is not a trust oracle.

## Test Certified Proposer Failover

The default topology has four validators and a quorum of three. Stop the current proposer, for example:

```bash
docker compose stop node1
```

After the view timeout, the remaining validators can sign a round-change certificate. The next proposer can then include that certificate in its proposal and attempt to collect the normal 3-of-4 commit quorum.

Inspect another node:

```bash
curl http://127.0.0.1:9102/status
```

Restart the stopped validator after testing:

```bash
docker compose start node1
```

This demonstrates the devnet mechanism only; it is not evidence of production Byzantine-fault tolerance.

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

## RPC Endpoints

Public development endpoints:

- `GET /health`
- `GET /status`
- `GET /validators`
- `GET /peers`
- `GET /evidence`
- `GET /balance/{address}`
- `GET /blocks/{height}`
- `GET /transactions/{txid}`
- `POST /transactions`

Development peer endpoints:

- `POST /internal/transaction`
- `POST /internal/view-change-request`
- `POST /internal/proposal`
- `POST /internal/block`

`/internal/*` endpoints are development-only.

## Run Tests

```bash
cd blockchain
pip install -e ".[dev]"
pytest -q
```

GitHub Actions also runs the blockchain test suite on repository changes.

## Security Rules for Development

- Never commit `runtime/`, private keys, seed phrases or production secrets.
- Never reuse bootstrap/devnet keys for a future testnet/mainnet.
- Do not market this prototype as audited or production-ready.
- Treat current HTTP peer transport and peer-health data as untrusted development infrastructure.
- Mainnet requires independent consensus, cryptography, networking, storage, economic and legal review.

Read [`SPEC.md`](SPEC.md) and [`SECURITY.md`](SECURITY.md) before extending consensus or networking.

## Next Engineering Milestones — v0.5

1. Replace the conservative no-unlock lock with a reviewed multi-phase lock/unlock rule.
2. Persist full proposal/view/commit event history and expand equivocation evidence.
3. Add authenticated encrypted validator transport and identity handshakes.
4. Add state snapshots, snapshot verification and fast state sync.
5. Add restart/recovery/database-corruption testing.
6. Add long-running partition/fault/load tests.
7. Add Prometheus-style metrics, dashboarding and alerts.
8. Add public-testnet deployment configuration and operational runbooks.
9. Add faucet abuse controls and improve the explorer/wallet experience.
10. Commission independent review before any production-value launch.
