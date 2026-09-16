# Crakbit Chain — Development Network Prototype

**Status: research/devnet alpha (`0.14.0-alpha`)**

Crakbit Chain is the experimental blockchain component of the Crakbit AI ecosystem. The project now includes the earlier research Python consensus/devnet plus a separate v0.14 external-consensus integration path built around a pinned CometBFT ABCI bridge and a dedicated crash-safe Crakbit application-state service.

> This is **not a production mainnet**, has not completed independent consensus/network review, and must not be used to custody real value.

## Devnet parameters

- Symbol: `CRKBIT`
- Decimals: `8`
- Proposed development genesis cap: `21,000,000 CRKBIT`
- Default research validators: `4`
- Default research quorum: `3 of 4`
- Address format: `crk1...`
- Application signatures: Ed25519
- Application state: SQLite
- Research RPC: FastAPI / JSON

The 21M value is a development-network parameter, not a promise of future token value or final mainnet economics. Production CRKBIT has not launched, there is no official presale, and there is no production token contract.

## Consensus direction

The older Python prevote/precommit consensus remains a **research implementation only**. It is not the intended production BFT path.

v0.14 adds a concrete external-consensus proof-of-concept:

```text
CometBFT v0.40.0
      │ ABCI socket
      ▼
Crakbit Go ABCI bridge
      │ authenticated loopback HTTP
      ▼
crakbit-execution/2 service
      │ staged FinalizeBlock → atomic Commit
      ▼
Dedicated external application SQLite state
```

This topology is separate from the normal research `crakchain node` database. Do not point both consensus owners at the same data directory.

See [`docs/ADR-0001-consensus-direction.md`](docs/ADR-0001-consensus-direction.md), [`docs/EXTERNAL_CONSENSUS_V2.md`](docs/EXTERNAL_CONSENSUS_V2.md) and [`V0.14.md`](V0.14.md).

## v0.14 major update

v0.14 adds:

- versioned `crakbit-execution/2` mutating external-consensus protocol,
- deterministic application hash over height, consensus block hash and sorted account state,
- persisted non-mutating FinalizeBlock staging,
- atomic SQLite Commit with durable external commit records,
- pending-finalize recovery across process restart,
- dedicated external execution database isolation checks,
- authenticated v0.14 execution service,
- Go ABCI bridge pinned to `github.com/cometbft/cometbft v0.40.0`,
- ABCI `Info`, `CheckTx`, `PrepareProposal`, `ProcessProposal`, `FinalizeBlock`, `Commit` and minimal query support,
- signed >2/3 genesis ceremony/attestation tooling,
- external-consensus local CLI/debug commands,
- `/consensus/integration-status`,
- combined Python + Go blockchain CI.

All v0.13 signed release tooling, faucet/explorer experiments, v0.12 archive recovery, v0.11 mTLS/pinning and earlier backup/snapshot/resource-hardening work remain in the repository.

## Quick start — research local devnet

Requirements: Python 3.11+ and Docker Desktop / Docker Engine.

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
python scripts/bootstrap_devnet.py
docker compose up --build
```

Local research RPC endpoints:

- Node 1: `http://127.0.0.1:9101`
- Node 2: `http://127.0.0.1:9102`
- Node 3: `http://127.0.0.1:9103`
- Node 4: `http://127.0.0.1:9104`

## v0.14 external application service

Use a **fresh dedicated data directory**:

```bash
python scripts/run_execution_service_v14.py \
  --genesis runtime/genesis.json \
  --data runtime/comet-app \
  --token REPLACE_WITH_LONG_RANDOM_SECRET \
  --host 127.0.0.1 \
  --port 26659
```

Useful authenticated endpoints:

```text
GET  /v2/info
GET  /v2/pending
POST /v2/check-tx
POST /v2/preview-finalize
POST /v2/finalize
POST /v2/commit
```

Only `/health` is unauthenticated. Keep this service on loopback/private networking.

## CometBFT bridge

Requires Go 1.25+.

```bash
cd blockchain/cometbft-app
go mod download
go test -mod=mod ./...
go build -o crakbit-cometbft-bridge .
```

Run:

```bash
export CRAKBIT_EXECUTION_URL=http://127.0.0.1:26659
export CRAKBIT_EXECUTION_TOKEN=REPLACE_WITH_LONG_RANDOM_SECRET
export CRAKBIT_ABCI_LISTEN=tcp://127.0.0.1:26658
./crakbit-cometbft-bridge
```

Configure the CometBFT node's `proxy_app` to the bridge socket. CometBFT node/validator keys are separate from Crakbit application keys.

See [`cometbft-app/README.md`](cometbft-app/README.md).

## External execution CLI

```bash
crakchain external-status \
  --genesis runtime/genesis.json \
  --data runtime/comet-app
```

Preview a block transition without mutating state:

```bash
crakchain external-preview \
  --genesis runtime/genesis.json \
  --data runtime/comet-app \
  --height 1 \
  --block-hash 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef \
  --transactions runtime/transactions.json
```

The `external-finalize` and `external-commit` commands expose the same staged lifecycle for local/debug testing.

## Signed genesis ceremony

Create the ceremony statement:

```bash
crakchain ceremony-create \
  --genesis runtime/genesis.json \
  --output runtime/genesis-ceremony.json
```

Each configured validator signs independently with its own local validator key:

```bash
crakchain ceremony-sign \
  --ceremony runtime/genesis-ceremony.json \
  --key runtime/node1/validator.json
```

After enough independent validator attestations, verify strict >2/3 quorum:

```bash
crakchain ceremony-verify \
  --ceremony runtime/genesis-ceremony.json \
  --genesis runtime/genesis.json
```

Never send validator private keys to another operator just to create a ceremony file. Only exchange the signed public ceremony artifact.

## Signed release manifests

Use a **dedicated release-signing key**, not a validator key:

```bash
crakchain keygen --output runtime/release-signing-key.json

crakchain release-build \
  --genesis runtime/genesis.json \
  --key runtime/release-signing-key.json \
  --version 0.14.0a1 \
  --artifact dist/crakbit-chain.whl \
  --output runtime/release-0.14.json
```

Verify with `crakchain release-verify` and an expected release-signer address.

## Snapshot, archive, integrity and recovery

Earlier recovery tooling remains available:

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

The genesis-anchored archive tooling verifies proposer signatures, view-change certificates, prevote/precommit quorum certificates, transaction signatures/nonces/balances, state roots and hash continuity for the research chain history.

## Research explorer / faucet / operations

The research node continues to provide bounded explorer APIs and test-only faucet tooling. Public deployment still requires upstream reverse-proxy/firewall/DDoS controls and persistent abuse limits.

Useful research-node endpoints include:

```text
GET /consensus/integration-status
GET /protocol/status
GET /explorer/summary
GET /explorer/blocks
GET /explorer/address/{address}
GET /transport/status
GET /archive/status
GET /execution/status
GET /operator/security-status
GET /metrics/prometheus
```

## Tests

Python suite:

```bash
cd blockchain
pip install -e ".[dev]"
pytest -q
```

Go bridge suite:

```bash
cd blockchain/cometbft-app
go mod download
go test -mod=mod ./...
```

GitHub Actions runs both suites on blockchain changes.

## Main remaining blockers

- sustained live multi-process CometBFT replay/restart testing,
- multi-host CometBFT validator deployment with published partition/latency/load evidence,
- exhaustive app-ahead/consensus-ahead crash recovery testing,
- CometBFT state-sync integration with Crakbit snapshots,
- reviewed validator-set lifecycle/governance design,
- production validator/release-key custody or HSM/remote-signer strategy,
- indexed external-consensus explorer storage,
- persistent/upstream faucet abuse protection,
- production monitoring/firewall/reverse-proxy/DDoS architecture,
- independent consensus/network/application security review,
- meaningful public-testnet operation before any mainnet planning.

See [`V0.14.md`](V0.14.md), [`docs/EXTERNAL_CONSENSUS_V2.md`](docs/EXTERNAL_CONSENSUS_V2.md), [`cometbft-app/README.md`](cometbft-app/README.md), [`V0.13.md`](V0.13.md), [`SPEC.md`](SPEC.md) and [`SECURITY.md`](SECURITY.md).
