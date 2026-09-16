# Crakbit Chain — Research / Public-Testnet Infrastructure

**Status: alpha (`0.15.0a1`) — not a production mainnet.**

Crakbit Chain is the experimental blockchain component of Crakbit AI. v0.15 keeps the v0.14 CometBFT integration proof-of-concept and adds a browser wallet, unified public gateway, persistent test faucet and an optional proof-of-work reward lab so the system can be exercised more like a public testnet.

> Production CRKBIT has **not** launched. There is no official CRKBIT presale or production token contract. Do not use this software to custody real value.

## Development parameters

- Symbol: `CRKBIT`
- Decimals: `8`
- Proposed development genesis cap: `21,000,000 CRKBIT`
- Address format: `crk1...`
- Application signatures: Ed25519
- Research validator topology: 4 validators / strict 3-of-4 quorum by default
- External BFT integration candidate: CometBFT `v0.40.0`
- Application state: SQLite

The 21M figure is a development configuration parameter, not a promise of value or final production economics.

## Architecture

The repository currently has two clearly separated consensus paths.

### Research path

```text
Browser / CLI
    ↓
FastAPI research node
    ↓
Python prevote/precommit research consensus
    ↓
SQLite research-chain state
```

### External-BFT integration path

```text
Browser wallet
    ↓
Crakbit public gateway
    ├──────────────→ authenticated execution read APIs
    ↓
CometBFT JSON-RPC
    ↓
CometBFT v0.40.0
    ↓ ABCI
Crakbit Go bridge
    ↓ authenticated loopback HTTP
crakbit-execution/2 service
    ↓ staged FinalizeBlock → atomic Commit
Dedicated external application SQLite state
```

The Python consensus remains research-only. It is not presented as the intended production mainnet consensus.

## v0.15 large update

v0.15 adds:

- responsive Web UI for network status, wallet, explorer, validators, faucet and Mining Lab,
- browser-generated Ed25519 wallets and `crk1...` addresses,
- PBKDF2-SHA256 + AES-GCM encrypted local wallet vault,
- client-side canonical transaction signing,
- encrypted wallet backup/import support,
- standalone public gateway with `research` and `cometbft` modes,
- CometBFT `broadcast_tx_sync` support for signed Crakbit transactions,
- authenticated external-execution read APIs for accounts, transactions and commits,
- persistent SQLite test-faucet cooldown/distribution records,
- gateway-aware faucet broadcasting,
- opt-in browser proof-of-work Mining Lab with persistent server-side challenges,
- persistent mining cooldown and daily reward limits,
- dedicated non-validator mining-reward wallet model,
- v0.15 automated tests,
- explicit production mainnet release gates.

See [`V0.15.md`](V0.15.md) and [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md).

## Quick start — local research network + Web wallet

Requirements: Python 3.11+ and Docker.

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
python scripts/bootstrap_devnet.py
docker compose up --build
```

Open the browser wallet/explorer on node 1:

```text
http://127.0.0.1:9101/ui/
```

Research RPC nodes:

```text
http://127.0.0.1:9101
http://127.0.0.1:9102
http://127.0.0.1:9103
http://127.0.0.1:9104
```

## Browser wallet security model

The Web UI creates Ed25519 keys in the browser. The private key is stored only inside an encrypted local vault using PBKDF2-SHA256 and AES-GCM. Transactions are signed in the browser before broadcast.

The alpha browser vault is **not a hardware wallet and has not completed independent wallet review**. Browser compromise, malicious extensions, XSS or origin compromise can still put keys at risk. Keep an encrypted backup and never import validator/release/faucet/mining-reward keys into the browser wallet.

## Full local public-UX stack

Create dedicated test wallets for the faucet and mining rewards:

```bash
crakchain keygen --output runtime/faucet.json
crakchain keygen --output runtime/mining-reward.json
```

Fund these wallets with test CRKBIT from the development treasury. Do not use validator consensus keys.

Start the public gateway:

```bash
python scripts/run_public_gateway.py \
  --genesis runtime/genesis.json \
  --mode research \
  --research-rpc http://127.0.0.1:9101 \
  --faucet-url http://127.0.0.1:9400 \
  --mining-url http://127.0.0.1:9500 \
  --host 127.0.0.1 \
  --port 9600
```

Start the persistent test faucet:

```bash
python scripts/run_faucet.py \
  --genesis runtime/genesis.json \
  --key runtime/faucet.json \
  --gateway http://127.0.0.1:9600 \
  --state runtime/faucet-state.sqlite3 \
  --amount 10
```

Start the test Mining Lab reward service:

```bash
python scripts/run_pow_mining.py \
  --genesis runtime/genesis.json \
  --key runtime/mining-reward.json \
  --gateway http://127.0.0.1:9600 \
  --state runtime/mining-state.sqlite3 \
  --reward 1 \
  --difficulty-bits 18
```

Open:

```text
http://127.0.0.1:9600/ui/
```

## What “Mining Lab” means

The current Mining Lab is **not consensus block mining**.

It works like this:

```text
browser gets random challenge
        ↓
visible SHA-256 proof-of-work
        ↓
server verifies target
        ↓
dedicated reward wallet sends a test CRKBIT transaction
```

CometBFT remains the external BFT consensus integration path. Converting Crakbit itself to proof-of-work block production would require a different consensus protocol and is not silently mixed into this design.

## CometBFT integration

Run the external application service on a private/loopback interface with a long random bearer token:

```bash
python scripts/run_execution_service_v14.py \
  --genesis runtime/genesis.json \
  --data runtime/comet-app \
  --token REPLACE_WITH_LONG_RANDOM_SECRET \
  --host 127.0.0.1 \
  --port 26659
```

Build/test the ABCI bridge:

```bash
cd blockchain/cometbft-app
go mod download
go test -mod=mod ./...
go build -o crakbit-cometbft-bridge .
```

The execution service and ABCI socket should remain private. Never expose the execution bearer token in browser JavaScript.

Public gateway in CometBFT mode:

```bash
python scripts/run_public_gateway.py \
  --genesis runtime/genesis.json \
  --mode cometbft \
  --comet-rpc http://127.0.0.1:26657 \
  --execution-url http://127.0.0.1:26659 \
  --execution-token REPLACE_WITH_LOCAL_SECRET \
  --host 127.0.0.1 \
  --port 9600
```

## Key-role separation

Use different keys for different jobs:

```text
CometBFT consensus/node key
Crakbit research-validator key
user wallet key
TLS key
release-signing key
faucet key
mining-reward key
```

Never commit private keys or seed material to GitHub.

## Signed genesis and release artifacts

The v0.14+ tooling remains available:

```text
crakchain ceremony-create
crakchain ceremony-sign
crakchain ceremony-verify
crakchain release-build
crakchain release-verify
```

A proper production launch would require independently held validator keys, reproducible artifacts and a verified final genesis ceremony.

## Recovery and integrity tooling

Existing tooling remains available:

```text
snapshot-fetch-chunked
snapshot-verify
snapshot-import
archive-export
archive-verify
archive-import
doctor
backup-create
backup-verify
```

## Tests

Python:

```bash
cd blockchain
pip install -e ".[dev]"
pytest -q
```

CometBFT Go bridge:

```bash
cd blockchain/cometbft-app
go mod download
go test -mod=mod ./...
```

GitHub Actions runs both suites for blockchain changes.

## Before a real mainnet

A Web UI, wallets and a mining-looking feature do **not** make a blockchain production-ready. Before any production mainnet claim, the project still needs a sustained independent-host testnet, external-consensus state sync, exhaustive fault/load testing, production validator key custody, hardened public infrastructure, indexed explorer, independent consensus/network/application/wallet review, incident-response operations and final economic/legal review.

The complete checklist is in [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md).

Further documentation:

- [`V0.15.md`](V0.15.md)
- [`V0.14.md`](V0.14.md)
- [`docs/EXTERNAL_CONSENSUS_V2.md`](docs/EXTERNAL_CONSENSUS_V2.md)
- [`docs/ADR-0001-consensus-direction.md`](docs/ADR-0001-consensus-direction.md)
- [`SPEC.md`](SPEC.md)
- [`SECURITY.md`](SECURITY.md)
