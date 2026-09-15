# Crakbit Chain — Development Network Prototype

**Status: early devnet / research prototype (`0.1.0-alpha`)**

Crakbit Chain is the experimental blockchain component of the Crakbit AI ecosystem. This directory contains a runnable local development network with a native **CRKBIT** unit, signed transactions, deterministic validator rotation, blocks, account balances, fees, peer synchronization, an RPC API and a simple explorer.

> This is **not a production mainnet**, has not been independently audited, and should not be used to custody real value.

## Devnet Parameters

- Native symbol: `CRKBIT`
- Decimals: `8`
- Proposed maximum supply: `21,000,000 CRKBIT`
- Development consensus: round-robin Proof of Authority (PoA)
- Transaction signatures: Ed25519
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
- Deterministic round-robin validator selection
- Signed blocks
- Previous-block hash linking
- Transaction Merkle root
- Deterministic state root
- SQLite persistence
- Basic peer block broadcast and catch-up sync
- REST endpoints for status, balances, blocks and transactions
- 3-validator Docker Compose devnet
- Simple browser explorer
- Automated ledger/signature tests

## Important Consensus Limitation

The current PoA prototype verifies that the configured proposer signed each block, but it does **not** implement Byzantine-fault-tolerant quorum voting/finality. A production Crakbit network should replace this layer with a formally reviewed BFT/PoS consensus design or a mature audited consensus framework before mainnet consideration.

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

- `GET /status`
- `GET /balance/{address}`
- `GET /blocks/{height}`
- `GET /transactions/{txid}`
- `POST /transactions`

`/internal/*` endpoints are currently used for basic devnet gossip and should **not** be directly exposed to the public internet without authentication/firewalling in later network versions.

## Security Rules for Development

- Never commit `runtime/` or real private keys.
- Never reuse bootstrap/devnet keys on a future mainnet.
- Do not expose validator key files through a web server.
- Do not market this prototype as an audited or production-ready blockchain.
- Treat the current peer protocol as development-only.
- Mainnet requires independent consensus, cryptography, networking and economic review.

## Next Engineering Milestones

1. Replace simple proposer-only PoA with BFT finality/quorum consensus.
2. Add authenticated peer-to-peer transport and peer discovery.
3. Add snapshot/state-sync support.
4. Add robust mempool ordering and multi-pending nonce handling.
5. Add slashing/staking only after consensus design review.
6. Add smart-contract VM only after threat modeling and sandbox design.
7. Build wallet and production explorer separately.
8. Run long-lived public testnet.
9. Commission independent security audits before any mainnet/token launch.
