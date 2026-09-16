# Crakbit Chain — Research / Public-Testnet Infrastructure

**Status: v0.16 alpha (`0.16.0a1`) — not a production mainnet.**

Crakbit Chain is the experimental blockchain/application-state component of Crakbit AI. The current codebase combines an older Python research devnet with a separate external-consensus path built around CometBFT `v0.40.0`, an authenticated Go ABCI bridge, deterministic Crakbit application execution, browser wallet/gateway tooling and public-testnet recovery/operations experiments.

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
- Current package: `0.16.0a1`

The 21M figure is a development configuration parameter, not a promise of value or final production economics.

## Current architecture

The intended external-BFT test path is:

```text
Browser wallet / CLI
        │ signed Crakbit transaction
        ▼
Public gateway
        │ CometBFT JSON-RPC
        ▼
CometBFT v0.40.0
        │ ABCI socket
        ▼
Crakbit Go ABCI bridge
        │ authenticated loopback/private HTTP
        ▼
crakbit-execution/2 service
        │ staged FinalizeBlock → atomic Commit
        ▼
Dedicated external application SQLite state
        │
        ├── deterministic checkpoint export/restore
        └── dedicated explorer index
```

The normal `crakchain node` command still exposes the older Python research consensus for backwards-compatible local experiments. It is **not** the intended production BFT path.

## v0.16 major additions

v0.16 adds:

- one-command local multi-node CometBFT lab generation,
- shared CometBFT consensus-genesis and persistent-peer generation from independent validator homes,
- explicit per-node execution-service secret separation,
- deterministic external-application checkpoint export/verification/restore,
- checkpoint verification against optional trusted consensus height + application hash,
- snapshot-base-aware external execution without invented historical commits,
- continued Commit operation after checkpoint restore,
- dedicated indexed external explorer database/service,
- restart-persistent SQLite public write-rate limiting,
- durable faucet and Mining Lab challenge limiting,
- same-origin gateway default instead of wildcard CORS,
- strict Content-Security-Policy and browser security headers,
- multi-host validator health/height-divergence checks,
- isolated FinalizeBlock/Commit crash/replay/checkpoint evidence matrix,
- browser-wallet threat model,
- remote-signer/HSM-equivalent validator custody guidance,
- v0.16 Python tests while retaining the Go bridge CI suite.

See [`V0.16.md`](V0.16.md) for the complete phase description.

## Browser wallet / Web UI

The package includes a responsive wallet interface under `crakbit_chain/webui/` with:

- locally generated Ed25519 wallets,
- `crk1...` addresses,
- PBKDF2-SHA256 + AES-GCM encrypted browser vault,
- encrypted import/export backup,
- client-side transaction signing,
- balance/nonce/activity,
- send flow,
- address/transaction explorer,
- validator view,
- test faucet integration,
- opt-in browser Mining Lab.

The private wallet key is intended to stay in the browser. The gateway receives the signed transaction, not the private key.

Run a v0.16 research-mode gateway:

```bash
python scripts/run_public_gateway_v16.py \
  --genesis runtime/genesis.json \
  --mode research \
  --research-rpc http://127.0.0.1:9101 \
  --host 127.0.0.1 \
  --port 9600
```

Open:

```text
http://127.0.0.1:9600/ui/
```

For a separate web origin, explicitly add approved origins with repeated `--allowed-origin` arguments. v0.16 otherwise defaults to same-origin access.

## External execution service — v0.16

Use a **fresh dedicated data directory** and a long random bearer token:

```bash
python scripts/run_execution_service_v16.py \
  --genesis runtime/genesis.json \
  --data runtime/comet-app \
  --token REPLACE_WITH_LONG_RANDOM_SECRET \
  --host 127.0.0.1 \
  --port 26659
```

Important authenticated endpoints include:

```text
GET  /v2/info
GET  /v2/pending
POST /v2/check-tx
POST /v2/finalize
POST /v2/commit
GET  /v2/state-sync/status
GET  /v2/state-snapshot/latest
```

Keep the execution service on loopback/private authorized networking. Its bearer token must never be exposed to browser JavaScript.

## CometBFT bridge

Build/test:

```bash
cd cometbft-app
go mod download
go test -mod=mod ./...
go build -o crakbit-cometbft-bridge .
```

Typical bridge environment:

```bash
export CRAKBIT_EXECUTION_URL=http://127.0.0.1:26659
export CRAKBIT_EXECUTION_TOKEN=REPLACE_WITH_LONG_RANDOM_SECRET
export CRAKBIT_ABCI_LISTEN=tcp://127.0.0.1:26658
./crakbit-cometbft-bridge
```

CometBFT consensus keys must remain separate from Crakbit wallet, research-validator, TLS, release, faucet and Mining Lab reward keys.

## Four-validator CometBFT lab

With an operator-supplied CometBFT `v0.40.0` binary:

```bash
python scripts/generate_cometbft_lab.py \
  --cometbft /path/to/cometbft \
  --chain-id crakbit-v16-local \
  --nodes 4 \
  --output runtime/cometbft-lab
```

This generates independent CometBFT homes, one shared consensus genesis, persistent peers, separate ABCI/execution ports and local execution-service tokens.

Generated validator private keys under `runtime/` are disposable lab secrets. Never commit or reuse them on a future production network.

See [`deploy/cometbft-lab/README.md`](deploy/cometbft-lab/README.md).

## External application checkpoint

Export:

```bash
crakchain external-snapshot-export \
  --genesis runtime/genesis.json \
  --data runtime/comet-app \
  --output runtime/external-checkpoint.json
```

Verify against a separately trusted CometBFT height/app hash:

```bash
crakchain external-snapshot-verify \
  --genesis runtime/genesis.json \
  --snapshot runtime/external-checkpoint.json \
  --expected-height EXPECTED_HEIGHT \
  --expected-app-hash EXPECTED_APPLICATION_HASH
```

Restore into a pristine external application directory:

```bash
crakchain external-snapshot-import \
  --genesis runtime/genesis.json \
  --snapshot runtime/external-checkpoint.json \
  --data runtime/recovered-comet-app \
  --expected-height EXPECTED_HEIGHT \
  --expected-app-hash EXPECTED_APPLICATION_HASH
```

The checkpoint restores account/application state and records a snapshot base. It does not manufacture pre-checkpoint external commit history.

**Limitation:** this is not yet complete native CometBFT state-sync lifecycle integration.

## Dedicated external explorer index

One-shot sync:

```bash
crakchain explorer-index-sync \
  --genesis runtime/genesis.json \
  --source-data runtime/comet-app \
  --index runtime/explorer-index.sqlite3
```

Continuous local service:

```bash
python scripts/run_explorer_indexer.py \
  --genesis runtime/genesis.json \
  --source-data runtime/comet-app \
  --index runtime/explorer-index.sqlite3 \
  --host 127.0.0.1 \
  --port 9700
```

The index separates public read workloads from the execution database and provides indexed commit, transaction, address activity and account-state queries.

## Faucet and Mining Lab

Faucet:

```bash
python scripts/run_faucet.py \
  --genesis runtime/genesis.json \
  --key runtime/faucet.json \
  --gateway http://127.0.0.1:9600 \
  --state runtime/faucet-state.sqlite3
```

Mining Lab:

```bash
python scripts/run_pow_mining.py \
  --genesis runtime/genesis.json \
  --key runtime/mining-reward.json \
  --gateway http://127.0.0.1:9600 \
  --state runtime/mining-state.sqlite3 \
  --reward 1 \
  --difficulty-bits 18
```

The Mining Lab is a **test-only work-reward service**, not consensus mining. A browser solves a SHA-256 challenge and a dedicated funded reward wallet sends an ordinary signed test CRKBIT transaction. It does not mint new units or produce CometBFT blocks.

## Multi-host health checks

Create a private inventory based on `deploy/cometbft-lab/inventory.example.json`, then:

```bash
python scripts/check_testnet_health.py \
  --inventory private/testnet-inventory.json \
  --max-height-spread 2 \
  --output runtime/evidence/health.json
```

Do not expose private signer/validator management interfaces publicly for monitoring convenience.

## Crash/replay matrix

For a disposable test genesis and funded test wallet:

```bash
python scripts/run_external_crash_matrix.py \
  --genesis runtime/genesis.json \
  --key runtime/treasury.json \
  --output runtime/evidence/crash-matrix.json
```

The matrix tests persisted finalize state, restart/commit behavior, replay rejection/idempotence and checkpoint restore/continue semantics.

## Tests

Python:

```bash
pip install -e ".[dev]"
pytest -q
```

Go bridge:

```bash
cd cometbft-app
go mod download
go test -mod=mod ./...
```

GitHub Actions runs both suites for blockchain changes.

## Security / production gates

Read:

- [`SECURITY.md`](SECURITY.md)
- [`docs/WALLET_THREAT_MODEL.md`](docs/WALLET_THREAT_MODEL.md)
- [`docs/VALIDATOR_REMOTE_SIGNER.md`](docs/VALIDATOR_REMOTE_SIGNER.md)
- [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md)
- [`V0.16.md`](V0.16.md)

Major gates still open include native CometBFT state-sync integration, sustained independent-host public-testnet evidence, real partition/packet-loss/load campaigns, shared upstream abuse controls, protected validator signer custody, independent wallet/consensus/application/network reviews, reproducible signed production releases, final economics and applicable legal review.

Until those gates are satisfied, describe this software as **research**, **public testnet**, or **mainnet-candidate infrastructure** — not production mainnet.
