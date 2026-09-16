# Crakbit Chain — Public-Testnet / Review-Candidate Infrastructure

**Status: v0.21 alpha (`0.21.0a1`) — not a production mainnet.**

Crakbit Chain is the experimental blockchain/application-state component of Crakbit AI. The current external-consensus path uses CometBFT `v0.40.0`, a Go ABCI bridge, deterministic Crakbit execution, native ABCI state sync, browser wallet/public gateway tooling, indexed explorer support, signed release/review evidence and a testnet validator-governance state machine.

> Production CRKBIT has **not** launched. There is no official CRKBIT presale or production token contract. Do not use this software to custody real value.

## Development parameters

- Symbol: `CRKBIT`
- Decimals: `8`
- Proposed development genesis cap: `21,000,000 CRKBIT`
- Address format: `crk1...`
- Application signatures: Ed25519
- External BFT integration candidate: CometBFT `v0.40.0`
- Application state: SQLite
- Current package: `0.21.0a1`
- Governed execution protocol: `crakbit-execution/3`
- Current application schema: `21`

The 21M figure is a development configuration parameter, not a promise of value or final production economics.

## Current external-consensus path

```text
Browser wallet / CLI
        │ signed tx / quorum-approved governance tx
        ▼
Public gateway / CometBFT RPC
        ▼
CometBFT v0.40.0
        │ ABCI
        ▼
Crakbit Go bridge 0.21
        │ authenticated private HTTP
        ▼
crakbit-execution/3
        │
        ├── staged FinalizeBlock → atomic Commit
        ├── replicated validator-governance state
        ├── deterministic ABCI validator updates
        ├── governance-aware application hash
        └── governance-aware ABCI state sync
```

The older Python research consensus remains only for backwards-compatible experiments. It is not the intended production BFT path.

## v0.21 additions

v0.21 moves validator changes from v0.20 operator-only rehearsal artifacts into deterministic replicated **testnet application state**. It adds:

- canonical validator `join`, `remove`, and `replace` governance transactions,
- validator approvals with strict `>2/3` current voting-power quorum,
- replicated active/pending validator state,
- governance state committed into the application hash,
- CometBFT ABCI validator updates returned only from validated replicated input,
- modeled update emission at height `H` and effective validator-set change at `H+2`,
- crash/replay-safe validator update emission,
- schema `21` with offline v20 → v21 migration and rollback rehearsal,
- governance-aware native ABCI state-sync snapshots,
- multi-operator request build/sign/verify CLI tooling,
- Python governance/migration/state-sync tests and Go bridge validator-update tests.

See [`V0.21.md`](V0.21.md).

## Install / test

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q

cd cometbft-app
go mod download
go test -mod=mod ./...
```

## Upgrade an existing v0.20 application copy

Do a dry run first:

```bash
crakchain migration-v21-dry-run \
  --genesis runtime/genesis.json \
  --source runtime/comet-app
```

Create a v0.21 copy:

```bash
crakchain migration-v21-copy \
  --genesis runtime/genesis.json \
  --source runtime/comet-app \
  --output runtime/comet-app-v21/chain.sqlite3
```

The source database is not modified. Existing non-pristine schema-19/20 application data is not silently upgraded when the v0.21 execution service starts.

## Run the governed execution service

```bash
python scripts/run_execution_service_v21.py \
  --genesis runtime/genesis.json \
  --data runtime/comet-app-v21 \
  --token "$CRAKBIT_EXECUTION_TOKEN" \
  --host 127.0.0.1 \
  --port 26659
```

Keep the execution token private and keep this service off the public Internet.

The v0.21 bridge uses:

```text
GET  /v4/info
POST /v4/check-tx
POST /v4/finalize
POST /v4/commit
```

The existing `/v3/state-sync/*` routes use the governance-aware state-sync manager under the v0.21 service.

## Validator-governance flow

Build a join request using the currently committed validator-set hash:

```bash
crakchain validator-change-build \
  --genesis runtime/genesis.json \
  --data runtime/comet-app-v21 \
  --kind join \
  --emit-height 101 \
  --new-public-key BASE64_ED25519_PUBLIC_KEY \
  --new-name validator-5 \
  --output runtime/governance/join-validator-5.json
```

Each current validator operator should verify and sign the same request **locally** with their own validator governance key:

```bash
crakchain validator-change-sign \
  --genesis runtime/genesis.json \
  --data runtime/comet-app-v21 \
  --request runtime/governance/join-validator-5.json \
  --key private/my-validator-key.json \
  --output runtime/governance/join-validator-5-signed.json
```

Verify quorum:

```bash
crakchain validator-change-verify \
  --genesis runtime/genesis.json \
  --data runtime/comet-app-v21 \
  --request runtime/governance/join-validator-5-signed.json
```

For the default four-validator/equal-power lab, strict `>2/3` means **3 of 4 approvals**. Do not gather validator private keys onto one machine merely to produce the signatures.

The quorum-approved JSON is a transaction artifact intended for controlled CometBFT testnet broadcast. `CheckTx` and `FinalizeBlock` revalidate it against committed application state before an update can be returned.

## Governance status

```bash
crakchain governance-status \
  --genesis runtime/genesis.json \
  --data runtime/comet-app-v21
```

Status includes the active validator set, active-set hash, pending activation, governance hash and history/emission counts.

## Governance-aware snapshots

```bash
crakchain snapshot-v21-export \
  --genesis runtime/genesis.json \
  --data runtime/comet-app-v21 \
  --output runtime/snapshot-v21.json

crakchain snapshot-v21-verify \
  --genesis runtime/genesis.json \
  --snapshot runtime/snapshot-v21.json
```

v0.21 snapshots include account state plus the active/pending validator governance state. Native CometBFT state sync remains bound to the light-client-trusted application hash and requires pristine restore state.

## Retained release/security tooling

v0.19/v0.20 tools remain available for review findings, reproducible builds, SBOM, signed release provenance, operations evidence, schema compatibility, migration rehearsal and signed lifecycle-plan review.

The browser wallet, explorer, public gateway, faucet and optional Mining Lab also remain alpha/test-only components. The Mining Lab is **not consensus mining**: it does not mint supply, create CometBFT blocks, select validators or change voting power.

## Security / release gates

Read:

- [`SECURITY.md`](SECURITY.md)
- [`V0.21.md`](V0.21.md)
- [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md)
- [`docs/WALLET_THREAT_MODEL.md`](docs/WALLET_THREAT_MODEL.md)
- [`docs/VALIDATOR_REMOTE_SIGNER.md`](docs/VALIDATOR_REMOTE_SIGNER.md)

v0.21 implements a testnet validator-governance path, but it has **not** completed independent multi-host join/remove/replace campaigns, activation-boundary fault tests, protected remote/HSM governance signing, independent consensus/application/network/wallet review, long-duration public-testnet evidence, complete supply-chain review, production DDoS/capacity engineering, final validator economics or applicable legal review.

Until those gates are actually satisfied, describe this software as **research**, **public testnet**, **review candidate** or **mainnet-candidate infrastructure** — not production mainnet.
