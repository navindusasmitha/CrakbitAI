# Crakbit Chain — Research / Public-Testnet Infrastructure

**Status: v0.17 alpha (`0.17.0a1`) — not a production mainnet.**

Crakbit Chain is the experimental blockchain/application-state component of Crakbit AI. The current codebase combines an older Python research devnet with a separate external-consensus path built around CometBFT `v0.40.0`, an authenticated Go ABCI bridge, deterministic Crakbit application execution, browser wallet/gateway tooling, indexed explorer support and public-testnet recovery/operations tooling.

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
- Current package: `0.17.0a1`

The 21M figure is a development configuration parameter, not a promise of value or final production economics.

## Current external-consensus architecture

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
Crakbit Go ABCI bridge v0.17
        │ authenticated loopback/private HTTP
        ▼
crakbit-execution/2 service
        │
        ├── staged FinalizeBlock → atomic Commit
        ├── ABCI snapshot state-sync lifecycle
        └── deterministic application state
                │
                ├── dedicated explorer index
                └── signed public-testnet evidence tooling
```

The normal `crakchain node` command still exposes the older Python research consensus for backwards-compatible local experiments. It is **not** the intended production BFT path.

## v0.17 major additions

v0.17 adds:

- native CometBFT ABCI `ListSnapshots`, `OfferSnapshot`, `LoadSnapshotChunk` and `ApplySnapshotChunk` bridge support,
- deterministic state-sync snapshot materialization,
- per-chunk and whole-artifact SHA-256 validation,
- snapshot acceptance bound to the light-client-verified application hash supplied by CometBFT,
- restore restricted to pristine application state,
- no invented pre-snapshot external commit history,
- v0.17 authenticated execution-service state-sync endpoints,
- signed source/genesis/evidence bundles tied to an exact Git commit and declared CometBFT version,
- dry-run-by-default fault-campaign evidence runner with mandatory recovery commands,
- shared single-edge NGINX TLS/rate-limit profile for public-testnet gateway traffic,
- guarded CometBFT remote-signer configuration helper,
- expanded Python and Go state-sync tests.

See [`V0.17.md`](V0.17.md) for the complete phase description.

## Browser wallet / Web UI

The responsive wallet interface under `crakbit_chain/webui/` provides locally generated Ed25519 wallets, `crk1...` addresses, PBKDF2-SHA256 + AES-GCM encrypted browser vaults, encrypted backup/import, client-side transaction signing, account activity, explorer views, validators, test faucet integration and the opt-in Mining Lab.

The private wallet key is intended to stay in the browser. The gateway receives a signed transaction, not the private key.

Example hardened gateway:

```bash
python scripts/run_public_gateway_v16.py \
  --genesis runtime/genesis.json \
  --mode research \
  --research-rpc http://127.0.0.1:9101 \
  --host 127.0.0.1 \
  --port 9600
```

Open `http://127.0.0.1:9600/ui/` for local testing.

## v0.17 external execution service

Use a **fresh dedicated data directory** and a long random bearer token:

```bash
python scripts/run_execution_service_v17.py \
  --genesis runtime/genesis.json \
  --data runtime/comet-app \
  --token REPLACE_WITH_LONG_RANDOM_SECRET \
  --host 127.0.0.1 \
  --port 26659
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

CometBFT consensus keys must remain separate from Crakbit wallet, research-validator, TLS, release/evidence, faucet and Mining Lab reward keys.

## Native CometBFT state sync

After a committed application height, explicitly materialize a deterministic state-sync snapshot:

```bash
crakchain comet-snapshot-materialize \
  --genesis runtime/genesis.json \
  --data runtime/comet-app
```

Inspect available/local restore state:

```bash
crakchain comet-snapshot-status \
  --genesis runtime/genesis.json \
  --data runtime/comet-app
```

`ListSnapshots` serves materialized local snapshots. `OfferSnapshot` accepts a candidate only if its declared application hash matches the trusted application hash supplied by CometBFT. Every received chunk and the reconstructed snapshot are verified again before import.

Snapshot import remains restricted to pristine application state and does not manufacture pre-checkpoint commit rows.

**Operational gate:** code-level ABCI state-sync wiring now exists, but long-running live recovery across independently managed validators still has to be executed and published as evidence.

## Four-validator CometBFT lab

With an operator-supplied CometBFT `v0.40.0` binary:

```bash
python scripts/generate_cometbft_lab.py \
  --cometbft /path/to/cometbft \
  --chain-id crakbit-v17-local \
  --nodes 4 \
  --output runtime/cometbft-lab
```

This generates independent CometBFT homes, one shared consensus genesis, persistent peers, separate ABCI/execution ports and local execution-service tokens. Generated validator private keys under `runtime/` are disposable lab secrets; never commit or reuse them on a future production network.

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

## Controlled fault campaigns

Campaign execution is **dry-run by default**:

```bash
python scripts/run_fault_campaign.py \
  --inventory private/testnet-inventory.json \
  --campaign private/fault-campaign.json \
  --output runtime/evidence/fault-campaign.json
```

Only add `--execute` after reviewing every operator-supplied fault and recovery command. Each campaign step must define a recovery command. The runner records health before, during and after the scenario.

This tool does not claim that independent-host failures have already been tested.

## Signed public-testnet evidence bundles

Create a bundle after generating real health/fault/recovery evidence:

```bash
crakchain evidence-build \
  --genesis runtime/genesis.json \
  --key private/evidence-signing-key.json \
  --source-commit EXACT_GIT_COMMIT \
  --cometbft-version v0.40.0 \
  --evidence runtime/evidence/health.json \
  --evidence runtime/evidence/fault-campaign.json \
  --output runtime/evidence/public-testnet-evidence.json
```

Verify it:

```bash
crakchain evidence-verify \
  --genesis runtime/genesis.json \
  --bundle runtime/evidence/public-testnet-evidence.json \
  --evidence-dir runtime/evidence
```

The evidence signer must be a dedicated key. Do not commit that private key. Evidence bundles explicitly do **not** claim production-mainnet readiness or independent review completion.

## Public-testnet edge and remote signer

A testnet edge scaffold is under [`deploy/public-testnet-edge/`](deploy/public-testnet-edge/). It provides TLS termination, per-path request limits, connection/body bounds and controlled proxy headers for a single shared edge host. It is not a complete distributed WAF/DDoS system.

A guarded helper can update CometBFT's remote-signer address:

```bash
python scripts/configure_comet_remote_signer.py \
  --config /path/to/config.toml \
  --signer tcp://127.0.0.1:1234
```

The helper never reads or migrates validator private keys. A real remote signer/HSM-equivalent service remains an external component requiring independent review and operational testing.

## Faucet and Mining Lab

The faucet and Mining Lab remain test-only services. The Mining Lab performs opt-in browser SHA-256 work and pays an ordinary transaction from a dedicated funded reward wallet. It **does not mint supply, choose validators or produce CometBFT blocks**.

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
- [`V0.17.md`](V0.17.md)
- [`docs/WALLET_THREAT_MODEL.md`](docs/WALLET_THREAT_MODEL.md)
- [`docs/VALIDATOR_REMOTE_SIGNER.md`](docs/VALIDATOR_REMOTE_SIGNER.md)
- [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md)

Major gates still open include sustained independent-host validator operation, live state-sync/recovery evidence, real partition/packet-loss/load campaigns, protected remote-signer/HSM deployment, distributed public-edge abuse controls, independent wallet/consensus/application/network reviews, reproducible release/genesis ceremony evidence, final economics and applicable legal review.

Until those gates are satisfied, describe this software as **research**, **public testnet**, or **mainnet-candidate infrastructure** — not production mainnet.
