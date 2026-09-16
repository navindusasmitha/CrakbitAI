# Crakbit Chain — Public-Testnet / Review-Candidate Infrastructure

**Status: v0.19 alpha (`0.19.0a1`) — not a production mainnet.**

Crakbit Chain is the experimental blockchain/application-state component of Crakbit AI. The current external-consensus path uses CometBFT `v0.40.0`, a Go ABCI bridge, deterministic Crakbit execution, native ABCI state sync, browser wallet/public gateway tooling, indexed explorer support and signed review/release evidence.

> Production CRKBIT has **not** launched. There is no official CRKBIT presale or production token contract. Do not use this software to custody real value.

## Development parameters

- Symbol: `CRKBIT`
- Decimals: `8`
- Proposed development genesis cap: `21,000,000 CRKBIT`
- Address format: `crk1...`
- Application signatures: Ed25519
- External BFT integration candidate: CometBFT `v0.40.0`
- Application state: SQLite
- Current package: `0.19.0a1`

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
                 ├── soak + fault evidence
                 ├── review finding matrix
                 └── signed release provenance
```

The older Python research consensus remains only for backwards-compatible experiments. It is not the intended production BFT path.

## v0.19 additions

v0.19 is a **review-remediation and release-engineering phase**. It adds:

- machine-readable security-review remediation matrices,
- conservative high/critical finding release gates,
- required regression-test references for remediated high/critical findings,
- reproducible artifact SHA-256 comparison tooling,
- CI checks for two Python wheel builds and two Go bridge builds,
- a direct-dependency CycloneDX 1.5 SBOM generator,
- signed release provenance bound to exact source/genesis/artifact hashes,
- signed upgrade/rollback/incident/disaster-recovery/validator-lifecycle drill evidence,
- v0.19 regression tests and documentation.

See [`V0.19.md`](V0.19.md).

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

## Review-finding remediation gate

Build a matrix from one or more review files:

```bash
SOURCE_COMMIT=$(git rev-parse HEAD)

crakchain review-findings-build \
  --source-commit "$SOURCE_COMMIT" \
  --finding private/review-findings.json \
  --output runtime/review/remediation-matrix.json

crakchain review-findings-check \
  --matrix runtime/review/remediation-matrix.json
```

The check returns non-zero while high/critical findings remain unresolved or a remediated high/critical finding lacks a recorded regression-test reference. Clearing this automated gate is not an audit certificate and does not make the network production-ready.

## Reproducible artifact comparison

```bash
crakchain repro-compare \
  --left runtime/build-a \
  --right runtime/build-b \
  --file crakbit-cometbft-bridge \
  --output runtime/release/reproducible-build.json
```

The report proves equality only for the supplied artifacts. It does not prove that two independent organizations or build environments reproduced the artifacts.

## Direct-dependency SBOM

```bash
crakchain sbom-build \
  --repo-root .. \
  --output runtime/release/sbom.cdx.json
```

The current CycloneDX document covers direct Python runtime dependencies and direct Go requirements, plus hashes of the dependency input files. It explicitly does not claim complete transitive dependency coverage.

## Signed release provenance

After real release artifacts, SBOM and reproducibility evidence exist:

```bash
crakchain release-provenance-build \
  --genesis runtime/genesis.json \
  --key private/release-signing-key.json \
  --source-commit "$SOURCE_COMMIT" \
  --package-version 0.19.0a1 \
  --cometbft-version v0.40.0 \
  --artifact bridge=runtime/release/crakbit-cometbft-bridge \
  --sbom runtime/release/sbom.cdx.json \
  --repro-report runtime/release/reproducible-build.json \
  --output runtime/release/provenance.json
```

Verify:

```bash
crakchain release-provenance-verify \
  --genesis runtime/genesis.json \
  --provenance runtime/release/provenance.json \
  --artifact-dir runtime/release \
  --expected-source-commit "$SOURCE_COMMIT"
```

Release-signing private keys must never be committed or sent through chat/support systems.

## Operations-drill evidence

v0.19 can sign evidence for upgrade, rollback, incident-response, disaster-recovery and validator-lifecycle drills. The format records operator-reported results and hashes supporting artifacts; it does not claim independent verification.

Example:

```bash
crakchain ops-drill-build \
  --key private/ops-evidence-key.json \
  --source-commit "$SOURCE_COMMIT" \
  --kind disaster-recovery \
  --started-at-ms 1000 \
  --completed-at-ms 2000 \
  --success \
  --summary "Recovered disposable test node and verified application state" \
  --evidence runtime/evidence/recovery.json \
  --output runtime/evidence/drill.json
```

## Native CometBFT state sync

v0.19 retains the v0.17+ ABCI snapshot lifecycle:

```text
ListSnapshots
OfferSnapshot
LoadSnapshotChunk
ApplySnapshotChunk
```

Snapshot acceptance remains bound to the application hash supplied through the CometBFT trust path, with chunk/full-artifact verification and pristine-state restore requirements.

## Explorer reconciliation and soak evidence

The v0.18 clean explorer reconciliation and sustained health collector remain available:

```bash
crakchain explorer-reconcile \
  --genesis runtime/genesis.json \
  --source-data runtime/comet-app \
  --index runtime/explorer-index.sqlite3 \
  --rebuilt-output runtime/reconcile/explorer-clean.sqlite3 \
  --output runtime/evidence/explorer-reconcile.json

python scripts/run_testnet_soak.py \
  --inventory private/testnet-inventory.json \
  --duration-seconds 21600 \
  --interval-seconds 30 \
  --output runtime/evidence/soak-6h.json
```

## Browser wallet / gateway

The alpha browser wallet still provides local Ed25519 key generation, encrypted local vault storage, client-side transaction signing, balance/activity views, explorer access, test faucet access and an optional Mining Lab. The gateway should receive signed transactions, not wallet private keys.

The Mining Lab remains a **test-only work-reward service**. It does not mint supply, produce CometBFT blocks, select validators or change voting power.

## Security / release gates

Read:

- [`SECURITY.md`](SECURITY.md)
- [`V0.19.md`](V0.19.md)
- [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md)
- [`docs/WALLET_THREAT_MODEL.md`](docs/WALLET_THREAT_MODEL.md)
- [`docs/VALIDATOR_REMOTE_SIGNER.md`](docs/VALIDATOR_REMOTE_SIGNER.md)

Major external gates still open include long-lived independent-host validator operation, live clean-host state-sync evidence, executed partition/latency/load campaigns, protected remote-signer/HSM deployment, multi-operator genesis ceremony, independent wallet/consensus/application/network review, complete transitive supply-chain review, production multi-edge DDoS/capacity engineering, final validator economics and applicable legal review.

Until those gates are satisfied, describe this software as **research**, **public testnet**, **review candidate** or **mainnet-candidate infrastructure** — not production mainnet.
