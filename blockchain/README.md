# Crakbit Chain — Public-Testnet / Review-Candidate Infrastructure

**Status: v0.18 alpha (`0.18.0a1`) — not a production mainnet.**

Crakbit Chain is the experimental blockchain/application-state component of Crakbit AI. The current external-consensus path uses CometBFT `v0.40.0`, a Go ABCI bridge, deterministic Crakbit execution, native ABCI state sync, a browser wallet/public gateway, indexed explorer tooling and signed evidence/review artifacts.

> Production CRKBIT has **not** launched. There is no official CRKBIT presale or production token contract. Do not use this software to custody real value.

## Development parameters

- Symbol: `CRKBIT`
- Decimals: `8`
- Proposed development genesis cap: `21,000,000 CRKBIT`
- Address format: `crk1...`
- Application signatures: Ed25519
- External BFT integration candidate: CometBFT `v0.40.0`
- Application state: SQLite
- Current package: `0.18.0a1`

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
                 ├── explorer index
                 ├── soak/fault evidence
                 └── signed review freeze
```

The older Python research consensus remains in the repository only for backwards-compatible experiments. It is not the intended production BFT path.

## v0.18 additions

v0.18 is intentionally a **review/evidence phase**, not another mainnet marketing step. It adds:

- signed review-candidate freeze manifests,
- exact Git commit + package + CometBFT version binding,
- genesis fingerprint/file-hash binding,
- cryptographic hashing of selected review artifacts,
- clean explorer rebuild/reconciliation with per-table SHA-256 fingerprints,
- sustained multi-host health/soak evidence collection,
- conservative review claims that remain `false` until independent work is actually completed,
- v0.18 tests while retaining v0.17 native CometBFT state-sync and Go bridge tests.

See [`V0.18.md`](V0.18.md).

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

## Native CometBFT state sync

After a committed external-application height:

```bash
crakchain comet-snapshot-materialize \
  --genesis runtime/genesis.json \
  --data runtime/comet-app

crakchain comet-snapshot-status \
  --genesis runtime/genesis.json \
  --data runtime/comet-app
```

The bridge supports `ListSnapshots`, `OfferSnapshot`, `LoadSnapshotChunk` and `ApplySnapshotChunk`. Offered snapshot state is accepted only when it matches the application hash supplied through the CometBFT state-sync trust path, and chunk/full-artifact hashes are verified before import.

## Explorer reconciliation

Build a fresh explorer index from the external application DB and compare it with the current index:

```bash
crakchain explorer-reconcile \
  --genesis runtime/genesis.json \
  --source-data runtime/comet-app \
  --index runtime/explorer-index.sqlite3 \
  --rebuilt-output runtime/reconcile/explorer-clean.sqlite3 \
  --output runtime/evidence/explorer-reconcile.json
```

A mismatch returns a non-zero exit code. The current index is not silently repaired or overwritten.

## Sustained testnet soak evidence

```bash
python scripts/run_testnet_soak.py \
  --inventory private/testnet-inventory.json \
  --duration-seconds 21600 \
  --interval-seconds 30 \
  --max-height-spread 2 \
  --output runtime/evidence/soak-6h.json
```

The collector records only the endpoints actually sampled. It does not infer independent ownership/provider diversity from hostnames.

## Controlled fault campaigns

Fault campaigns remain dry-run by default:

```bash
python scripts/run_fault_campaign.py \
  --inventory private/testnet-inventory.json \
  --campaign private/fault-campaign.json \
  --output runtime/evidence/fault-campaign.json
```

Only add `--execute` after reviewing every fault/recovery command on an authorized test network.

## Signed public-testnet evidence

```bash
crakchain evidence-build \
  --genesis runtime/genesis.json \
  --key private/evidence-signing-key.json \
  --source-commit EXACT_GIT_COMMIT \
  --cometbft-version v0.40.0 \
  --evidence runtime/evidence/soak-6h.json \
  --evidence runtime/evidence/fault-campaign.json \
  --output runtime/evidence/public-testnet-evidence.json
```

Evidence-signing keys must never be committed.

## Signed review freeze

After generating **real** evidence and any release/genesis artifacts:

```bash
crakchain review-freeze-build \
  --genesis runtime/genesis.json \
  --key private/review-signing-key.json \
  --source-commit EXACT_GIT_COMMIT \
  --package-version 0.18.0a1 \
  --cometbft-version v0.40.0 \
  --artifact evidence=runtime/evidence/public-testnet-evidence.json \
  --artifact reconcile=runtime/evidence/explorer-reconcile.json \
  --artifact soak=runtime/evidence/soak-6h.json \
  --output runtime/review/crakbit-v0.18-review-freeze.json
```

Verify:

```bash
crakchain review-freeze-verify \
  --genesis runtime/genesis.json \
  --freeze runtime/review/crakbit-v0.18-review-freeze.json \
  --artifact-dir runtime/evidence
```

If the frozen source changes, create a new review candidate rather than claiming the old review manifest covers new code.

## Browser wallet / gateway

The alpha browser wallet still provides local Ed25519 key generation, encrypted local vault storage, local transaction signing, balance/activity views, explorer access, test faucet access and an optional Mining Lab. The gateway should receive signed transactions, not wallet private keys.

The Mining Lab remains a **test-only work-reward service**. It does not mint supply, produce CometBFT blocks, select validators or change voting power.

## Security / release gates

Read:

- [`SECURITY.md`](SECURITY.md)
- [`V0.18.md`](V0.18.md)
- [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md)
- [`docs/WALLET_THREAT_MODEL.md`](docs/WALLET_THREAT_MODEL.md)
- [`docs/VALIDATOR_REMOTE_SIGNER.md`](docs/VALIDATOR_REMOTE_SIGNER.md)

Major external gates still open include long-lived independent-host validator operation, live clean-host state-sync evidence, executed partition/latency/load campaigns, protected remote-signer/HSM deployment, multi-operator genesis ceremony, independent wallet/consensus/application/network review, production multi-edge DDoS/capacity engineering, final validator economics and applicable legal review.

Until those gates are satisfied, describe this software as **research**, **public testnet**, **review candidate** or **mainnet-candidate infrastructure** — not production mainnet.
