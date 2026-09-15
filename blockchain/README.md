# Crakbit Chain — Development Network Prototype

**Status: early devnet / research prototype (`0.3.0-alpha`)**

Crakbit Chain is the experimental blockchain component of the Crakbit AI ecosystem. The current devnet implements native test-only **CRKBIT** accounting, signed transactions, quorum-finalized blocks, round-based proposer failover, persistent same-round anti-double-vote state, validator health telemetry, peer synchronization, an RPC API, CLI tooling and a simple explorer.

> This is **not a production mainnet**, has not been independently audited, and must not be used to custody real value.

## Devnet Parameters

- Native symbol: `CRKBIT`
- Decimals: `8`
- Proposed maximum genesis supply: `21,000,000 CRKBIT`
- Development consensus: round-robin PoA proposals + signed >2/3 validator commit quorum + timeout-based round failover
- Transaction/block/vote signatures: Ed25519
- Address format: `crk1...`
- Default block interval: 5 seconds
- Default view/round timeout: 10 seconds
- State storage: SQLite
- RPC: FastAPI / JSON over HTTP

The 21M cap is encoded in the generated genesis configuration for the devnet. It is **not a promise of future token value or final mainnet economics**.

## What Works

- Ed25519 wallet/key generation
- `crk1...` address derivation
- Signed CRKBIT transfers
- Nonces and replay protection
- Minimum transaction fee
- Fee payment to the finalized block proposer
- Genesis allocation
- Round-based deterministic proposer selection
- Timeout-based proposer failover
- Signed block proposals
- Signed validator commit votes
- Strict greater-than-two-thirds commit quorum before finalization
- Duplicate/unknown/invalid commit vote rejection
- Persistent same-height/same-round anti-double-vote records across validator restarts
- Previous-block hash linking
- Transaction Merkle root
- Deterministic state root
- SQLite persistence
- Basic peer block broadcast and catch-up sync
- REST endpoints for health, status, peers, validators, balances, blocks and transactions
- Validator health/height/round telemetry
- 3-validator Docker Compose devnet
- Simple browser explorer
- Automated ledger/signature/quorum/failover tests

## What v0.3 Changes

v0.2 could finalize only when the round-zero scheduled proposer was available. v0.3 adds a simple timeout-based consensus round mechanism.

For height `H` and round `R`, the proposer is selected as:

```text
validator_index = (H - 1 + R) mod validator_count
```

Nodes begin each height at round `0`. If the height is not finalized before `view_timeout_ms`, they move to the next round and therefore to the next validator. A valid proposal from the next round can then collect the normal >2/3 signed commit quorum.

v0.3 also persists the block hash a local validator voted for at each `(height, round)` in SQLite. Restarting the validator therefore does not erase the same-round anti-double-vote record.

### Important safety limitation

The persistent guard is **same-round only**. v0.3 does not yet implement a production BFT cross-round lock/precommit protocol or a quorum-certified view-change protocol. Validators can vote in a later round after timeout, so the current round-failover logic remains a research mechanism rather than a formally safe production consensus protocol.

## Quick Start — Fresh Local 3-Validator Devnet

Requirements: Python 3.11+ and Docker Desktop / Docker Engine.

```bash
cd blockchain
python -m venv .venv
```

Activate it and install:

```bash
pip install -e ".[dev]"
```

Generate validator keys and genesis:

```bash
python scripts/bootstrap_devnet.py
```

Optional timing parameters:

```bash
python scripts/bootstrap_devnet.py --block-time-ms 5000 --view-timeout-ms 10000
```

Start the nodes:

```bash
docker compose up --build
```

RPC endpoints:

- Node 1: `http://127.0.0.1:9101`
- Node 2: `http://127.0.0.1:9102`
- Node 3: `http://127.0.0.1:9103`
- API docs: `http://127.0.0.1:9101/docs`

### Upgrading an older local devnet

v0.3 changes the genesis fingerprint and consensus metadata. Treat old local devnet state as disposable and create a clean test network:

```bash
docker compose down -v
```

Delete the local `runtime/` directory, then run:

```bash
python scripts/bootstrap_devnet.py
docker compose up --build
```

Never delete or reset any environment containing real-value keys or data. This instruction applies only to the disposable Crakbit development network.

## Monitoring

Health:

```bash
curl http://127.0.0.1:9101/health
```

Consensus/network status:

```bash
curl http://127.0.0.1:9101/status
```

The status response includes:

- finalized height
- current consensus round
- current/next proposer
- view timeout
- persistent local vote count
- mempool size
- uptime
- cached validator health count

Peer/validator telemetry:

```bash
curl http://127.0.0.1:9101/peers
curl http://127.0.0.1:9101/validators
```

The peer-health data is operational telemetry only. Peer transport is not yet authenticated, so it must not be treated as trusted security evidence.

## Test Proposer Failover

With the three-node devnet running, stop whichever validator is the current proposer. After the configured view timeout, the remaining nodes should advance to the next round and select the next configured proposer.

For development testing only:

```bash
docker compose stop node1
```

Observe another node:

```bash
curl http://127.0.0.1:9102/status
```

Restart the validator afterward:

```bash
docker compose start node1
```

Whether the chain can continue depends on the configured quorum. The default 3-validator configuration uses a strict >2/3 threshold, which is **3 of 3**, so stopping any one validator prevents finalization even though proposer rotation continues. Use a larger validator set if you want to test quorum availability with one validator offline.

## Treasury / Wallet

The bootstrap script creates a **devnet-only** treasury key at `runtime/treasury.json` unless you pass an existing test address.

Generate another wallet:

```bash
crakchain keygen --output runtime/alice.json
crakchain address --key runtime/alice.json
```

Read balance:

```bash
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
- `GET /balance/{address}`
- `GET /blocks/{height}`
- `GET /transactions/{txid}`
- `POST /transactions`

Development peer endpoints:

- `POST /internal/transaction`
- `POST /internal/proposal`
- `POST /internal/block`

`/internal/*` endpoints are development-only and should **not** be directly exposed to the public internet.

## Run Tests

```bash
cd blockchain
pip install -e ".[dev]"
pytest -q
```

GitHub Actions also runs the blockchain test suite on repository changes.

## Security Rules for Development

- Never commit `runtime/` or real private keys.
- Never reuse bootstrap/devnet keys on a future testnet/mainnet.
- Do not expose validator key files through HTTP/static hosting.
- Do not market this prototype as audited or production-ready.
- Treat current peer transport and peer-health data as untrusted development infrastructure.
- Mainnet requires independent consensus, cryptography, networking, storage and economic review.

Read [`SPEC.md`](SPEC.md) and [`SECURITY.md`](SECURITY.md) before extending consensus or networking.

## Next Engineering Milestones

1. Add quorum-certified view changes and cross-round locking/precommit safety.
2. Add equivocation evidence and durable consensus event history.
3. Add authenticated encrypted validator transport and peer identity handshakes.
4. Add state snapshots, fast state sync and recovery testing.
5. Add robust mempool ordering and multi-pending nonce handling.
6. Build a dedicated validator dashboard and alerting pipeline.
7. Add public-testnet deployment configuration, faucet abuse controls and improved explorer.
8. Run long-lived partition/restart/load testing.
9. Commission independent security review before any production-value launch.
