# Crakbit Chain — Development Network Prototype

**Status: early devnet / research prototype (`0.2.0-alpha`)**

Crakbit Chain is the experimental blockchain component of the Crakbit AI ecosystem. This directory contains a runnable local development network with a native **CRKBIT** unit, signed transactions, deterministic validator rotation, signed validator commit votes, quorum finality, blocks, account balances, fees, peer synchronization, an RPC API and a simple explorer.

> This is **not a production mainnet**, has not been independently audited, and must not be used to custody real value.

## Devnet Parameters

- Native symbol: `CRKBIT`
- Decimals: `8`
- Proposed maximum supply: `21,000,000 CRKBIT`
- Development consensus: round-robin PoA proposals + signed >2/3 validator commit quorum
- Transaction/block/vote signatures: Ed25519
- Address format: `crk1...`
- Default block interval: 5 seconds
- State storage: SQLite
- RPC: FastAPI / JSON over HTTP

The 21M cap is encoded in the generated genesis configuration for the devnet. It is **not a promise of future token value or final mainnet economics**.

## What Works

- Ed25519 wallet/key generation
- `crk1...` address derivation
- Signed CRKBIT transfers
- Nonces and replay protection
- Minimum transaction fee
- Fee payment to the current block proposer
- Genesis allocation
- Deterministic round-robin proposer selection
- Signed block proposals
- Signed validator commit votes
- Strict greater-than-two-thirds commit quorum before finalization
- Duplicate/unknown/invalid commit vote rejection
- Same-height/same-round in-memory double-vote guard
- Previous-block hash linking
- Transaction Merkle root
- Deterministic state root
- SQLite persistence
- Basic peer block broadcast and catch-up sync
- REST endpoints for status, validators, balances, blocks and transactions
- 3-validator Docker Compose devnet
- Simple browser explorer
- Automated ledger/signature/quorum tests

## What v0.2 Changes

v0.1 allowed the scheduled proposer to sign and finalize its own block. v0.2 separates **proposal** from **finalization**.

The scheduled proposer now constructs a signed block proposal. Every configured validator independently validates that proposal and signs a commit vote for its block hash. The proposer must collect:

```text
floor(2 * validator_count / 3) + 1
```

valid validator signatures before the block can be committed and broadcast as finalized.

For the default three-validator devnet, this means **3 of 3 validators** are required.

Nodes reject blocks with missing quorum, duplicate validator votes, votes from unknown validators, invalid signatures, or votes for a different block hash.

## Important Consensus Limitation

The v0.2 finality mechanism is **not yet a complete production BFT protocol**.

It does not yet implement proposer/view changes. If the scheduled proposer is unavailable, or quorum cannot be reached, the chain can halt. The anti-double-vote record is currently in memory and is not yet durable across validator restarts.

Before public-value mainnet consideration, this layer should be replaced or extended with a mature reviewed BFT/PoS design including durable consensus state, proposer failover, equivocation handling, authenticated P2P networking and extensive adversarial testing.

## Quick Start — Local 3-Validator Devnet

Requirements: Python 3.11+ and Docker Desktop / Docker Engine.

```bash
cd blockchain
python -m venv .venv
```

Activate it and install:

```bash
pip install -e ".[dev]"
```

Generate local validator keys and genesis:

```bash
python scripts/bootstrap_devnet.py
```

This creates `runtime/` locally. That directory is git-ignored because it contains **private devnet keys**.

Start the three nodes:

```bash
docker compose up --build
```

RPC endpoints:

- Node 1: http://127.0.0.1:9101
- Node 2: http://127.0.0.1:9102
- Node 3: http://127.0.0.1:9103
- API docs: http://127.0.0.1:9101/docs

Check status:

```bash
curl http://127.0.0.1:9101/status
```

The status response now includes `validator_count`, `commit_quorum`, `finalized_height`, consensus mode and any local pending proposal.

Validator information:

```bash
curl http://127.0.0.1:9101/validators
```

## Treasury / Wallet

The bootstrap script creates a **devnet-only** treasury key at `runtime/treasury.json` unless you pass an existing test address.

Generate another wallet:

```bash
crakchain keygen --output runtime/alice.json
crakchain address --key runtime/alice.json
```

Read treasury balance:

```bash
crakchain balance YOUR_TREASURY_ADDRESS --rpc http://127.0.0.1:9101
```

Send CRKBIT on the devnet:

```bash
crakchain send \
  --key runtime/treasury.json \
  --genesis runtime/genesis.json \
  --to crk1RECIPIENT \
  --amount 25 \
  --rpc http://127.0.0.1:9101
```

## Explorer

Serve `explorer/` with any static server, for example:

```bash
python -m http.server 8080 -d explorer
```

Then open `http://127.0.0.1:8080`.

## RPC Endpoints

Public development endpoints:

- `GET /status`
- `GET /validators`
- `GET /balance/{address}`
- `GET /blocks/{height}`
- `GET /transactions/{txid}`
- `POST /transactions`

Development peer endpoints:

- `POST /internal/transaction`
- `POST /internal/proposal`
- `POST /internal/block`

`/internal/*` endpoints are currently used for devnet coordination and should **not** be directly exposed to the public internet without later authentication/firewalling.

## Run Tests

```bash
cd blockchain
pip install -e ".[dev]"
pytest -q
```

GitHub Actions also runs the blockchain test suite on repository changes.

## Security Rules for Development

- Never commit `runtime/` or real private keys.
- Never reuse bootstrap/devnet keys on a future mainnet.
- Do not expose validator key files through a web server.
- Do not market this prototype as an audited or production-ready blockchain.
- Treat the current peer protocol as development-only.
- Mainnet requires independent consensus, cryptography, networking and economic review.

Read [`SPEC.md`](SPEC.md) and [`SECURITY.md`](SECURITY.md) before extending consensus or networking.

## Next Engineering Milestones

1. Add proposer/view changes and durable consensus lock/vote state.
2. Add authenticated encrypted peer-to-peer transport and peer discovery.
3. Add snapshot/state-sync support.
4. Add robust mempool ordering and multi-pending nonce handling.
5. Add validator health/monitoring and a public testnet deployment model.
6. Add slashing/staking only after consensus/economic review.
7. Add smart-contract execution only after a separate VM threat model and deterministic sandbox design.
8. Build a production-quality wallet, faucet and explorer separately.
9. Run a long-lived public testnet.
10. Commission independent security audits before any mainnet/token launch.
