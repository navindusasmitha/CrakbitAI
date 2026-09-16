# Crakbit Chain — Public-Testnet / Review-Candidate Infrastructure

**Status: v0.20 alpha (`0.20.0a1`) — not a production mainnet.**

Crakbit Chain is the experimental blockchain/application-state component of Crakbit AI. The current external-consensus path uses CometBFT `v0.40.0`, a Go ABCI bridge, deterministic Crakbit execution, native ABCI state sync, browser wallet/public gateway tooling, indexed explorer support and signed review/release/upgrade evidence.

> Production CRKBIT has **not** launched. There is no official CRKBIT presale or production token contract. Do not use this software to custody real value.

## Development parameters

- Symbol: `CRKBIT`
- Decimals: `8`
- Proposed development genesis cap: `21,000,000 CRKBIT`
- Address format: `crk1...`
- Application signatures: Ed25519
- External BFT integration candidate: CometBFT `v0.40.0`
- Application state: SQLite
- Current package: `0.20.0a1`

The 21M figure is a development configuration parameter, not a promise of value or final production economics.

## Current external-consensus path

```text
Browser wallet / CLI
        │ signed transaction
        ▼
Public gateway
        │ CometBFT JSON-RPC
        ▼
CometBFT v0.40.0
        │ ABCI
        ▼
Crakbit Go bridge
        │ authenticated private HTTP
        ▼
crakbit-execution/2
        │
        ├── staged FinalizeBlock → atomic Commit
        ├── native ABCI snapshot lifecycle
        └── deterministic application state
                 │
                 ├── explorer index / reconciliation
                 ├── review + release provenance
                 ├── schema migration rehearsal
                 └── validator lifecycle drill plans
```

The older Python research consensus remains only for backwards-compatible experiments. It is not the intended production BFT path.

## v0.20 additions

v0.20 is an **upgrade compatibility and validator-lifecycle rehearsal phase**. It adds:

- explicit external-application schema version `20`,
- v19 → v20 offline-copy migration tooling,
- logical pre/post state fingerprint verification,
- disposable rollback verification,
- a package/schema/CometBFT compatibility matrix,
- full offline upgrade rehearsal with SQLite integrity checks,
- signed migration/rollback evidence,
- signed validator join/remove/replace drill plans,
- explicit CometBFT emission/effective-height modeling,
- v0.20 regression tests.

See [`V0.20.md`](V0.20.md).

## Install / test

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

Go bridge:

```bash
cd cometbft-app
go mod download
go test -mod=mod ./...
```

## Schema status and migration dry run

Check an external-application database:

```bash
crakchain schema-status \
  --data runtime/comet-app
```

Dry-run the v19 → v20 migration without modifying the source:

```bash
crakchain migration-dry-run \
  --source runtime/comet-app
```

Create a migrated copy:

```bash
crakchain migration-copy \
  --source runtime/comet-app \
  --output runtime/migrated-v20/chain.sqlite3
```

The migration command does **not** replace the source DB. It creates a copy, verifies logical state preservation and rehearses rollback on another disposable copy.

## Compatibility check

```bash
crakchain compatibility-check \
  --data runtime/migrated-v20 \
  --genesis runtime/genesis.json \
  --cometbft-version v0.40.0
```

Current v0.20 compatibility policy:

- execution protocol: `crakbit-execution/2`,
- supported schemas: `19`, `20`,
- recommended schema: `20`,
- declared CometBFT candidate: `v0.40.0`,
- live validator updates: disabled,
- production-mainnet readiness: false.

## Full offline upgrade rehearsal

```bash
crakchain upgrade-rehearse \
  --genesis runtime/genesis.json \
  --source-data runtime/comet-app \
  --output-data runtime/upgrade-rehearsal-v20 \
  --cometbft-version v0.40.0 \
  --report runtime/evidence/upgrade-v20.json
```

The rehearsal verifies migration, rollback, SQLite integrity, genesis identity and v0.20 compatibility. It explicitly reports that the source was not modified and no live node was upgraded.

## Signed migration evidence

After a successful rehearsal:

```bash
SOURCE_COMMIT=$(git rev-parse HEAD)

crakchain migration-evidence-build \
  --key private/migration-evidence-key.json \
  --source-commit "$SOURCE_COMMIT" \
  --report runtime/evidence/upgrade-v20.json \
  --output runtime/evidence/upgrade-v20-signed.json
```

Verify:

```bash
crakchain migration-evidence-verify \
  --evidence runtime/evidence/upgrade-v20-signed.json \
  --report-dir runtime/evidence
```

Never commit migration/release/review/validator/wallet private keys.

## Validator lifecycle drill plans

v0.20 can create signed research plans for validator `join`, `remove` and `replace` drills.

Example join plan:

```bash
crakchain validator-plan-build \
  --genesis runtime/genesis.json \
  --key private/lifecycle-signing-key.json \
  --source-commit "$SOURCE_COMMIT" \
  --kind join \
  --effective-height 120 \
  --new-public-key BASE64_ED25519_PUBLIC_KEY \
  --new-name validator-5 \
  --output runtime/evidence/validator-join-plan.json
```

Verify:

```bash
crakchain validator-plan-verify \
  --genesis runtime/genesis.json \
  --plan runtime/evidence/validator-join-plan.json \
  --expected-source-commit "$SOURCE_COMMIT"
```

### Important validator-set boundary

These v0.20 plans **do not emit live ABCI validator updates**. They model the update and record the FinalizeBlock emission height and expected effective height, but they deliberately keep:

```text
consensus_change_applied = false
live_abci_validator_updates_emitted = false
```

A live validator-set change must come from deterministic replicated application state. Injecting an operator-local plan directly into one node could cause different ABCI responses across validators. A future phase must define and test a reviewed deterministic authorization/activation path before enabling live changes.

## v0.19 release engineering retained

The previous remediation/release tooling remains available:

```text
review-findings-build / review-findings-check
repro-compare
sbom-build
release-provenance-build / release-provenance-verify
ops-drill-build / ops-drill-verify
```

GitHub Actions also runs Python tests, Go bridge tests, reproducible Python/Go build checks and direct-dependency SBOM generation.

## State sync, explorer and soak tooling retained

The native ABCI snapshot lifecycle remains:

```text
ListSnapshots
OfferSnapshot
LoadSnapshotChunk
ApplySnapshotChunk
```

v0.18 explorer reconciliation and sustained health/soak collection also remain available. Snapshot acceptance is still bound to the CometBFT-supplied trusted application hash, with chunk/full-artifact verification and pristine-state restore requirements.

## Browser wallet / gateway

The alpha browser wallet provides local Ed25519 key generation, encrypted local vault storage, client-side transaction signing, balance/activity views, explorer access, test faucet access and an optional Mining Lab. The gateway should receive signed transactions, not wallet private keys.

The Mining Lab remains a **test-only work-reward service**. It does not mint supply, produce CometBFT blocks, select validators or change voting power.

## Security / release gates

Read:

- [`SECURITY.md`](SECURITY.md)
- [`V0.20.md`](V0.20.md)
- [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md)
- [`docs/WALLET_THREAT_MODEL.md`](docs/WALLET_THREAT_MODEL.md)
- [`docs/VALIDATOR_REMOTE_SIGNER.md`](docs/VALIDATOR_REMOTE_SIGNER.md)

Major external gates still open include long-lived independent-host validator operation, live clean-host state-sync evidence, executed partition/latency/load campaigns, protected remote-signer/HSM deployment, multi-operator genesis ceremony, independent wallet/consensus/application/network review, complete transitive supply-chain review, a reviewed deterministic live validator-update path, production multi-edge DDoS/capacity engineering, final validator economics and applicable legal review.

Until those gates are satisfied, describe this software as **research**, **public testnet**, **review candidate** or **mainnet-candidate infrastructure** — not production mainnet.
