# Crakbit Chain — v0.22 Public-Testnet / Review-Candidate Alpha

**Current package:** `0.22.0a1`  
**Consensus candidate:** CometBFT `v0.40.0`  
**Execution path:** `crakbit-execution/3`  
**Status:** research/public-testnet/mainnet-candidate infrastructure — **not production mainnet**.

Production CRKBIT has **not** launched. There is no official presale or production token contract. Do not use this software to custody real value.

## Current architecture

```text
Browser wallet / CLI
        │ signed transaction
        ▼
Public gateway / CometBFT RPC
        │
        ▼
CometBFT v0.40.0
        │ ABCI
        ▼
Crakbit Go bridge
        │ authenticated private HTTP
        ▼
crakbit-execution/3
        │
        ├── transfer execution
        ├── deterministic validator governance
        ├── staged FinalizeBlock → atomic Commit
        ├── governance-aware application hash
        ├── ABCI validator updates
        └── governance-aware state sync
```

The older Python prevote/precommit implementation remains research-only and is not the intended production BFT path.

## What v0.22 adds

v0.22 is the **governed multi-node testnet campaign** phase. It adds:

- a one-command governed CometBFT lab generator,
- application-genesis validator identities aligned with the generated disposable CometBFT validators,
- lab-only governance signing views for local campaigns,
- cluster reachability/height/app-hash/governance divergence checks,
- validator-governance history/emission explorer output,
- explicit `H`, `H+1`, `H+2` campaign plans,
- signed campaign evidence bound to exact Git commit/genesis/artifact hashes,
- v0.22 regression tests.

See [`V0.22.md`](V0.22.md).

## Install / test

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

Go bridge tests:

```bash
cd cometbft-app
go mod download
go test -mod=mod ./...
```

## Create a governed four-node local lab

Install the pinned CometBFT candidate binary first, then:

```bash
crakchain governed-lab-create \
  --cometbft /path/to/cometbft \
  --output runtime/governed-v22-lab \
  --chain-id crakbit-v22-local \
  --nodes 4
```

The generator creates disposable local node homes, application genesis, operator inventory and `.secrets` material. **Never reuse the generated validator/treasury/governance keys on a public or production network.**

Use the generated `commands.txt` to start each node's v0.21 execution service, ABCI bridge and CometBFT process.

## Check cluster convergence

```bash
crakchain cluster-v22-check \
  --inventory runtime/governed-v22-lab/governed-lab-inventory.json \
  --max-height-spread 1 \
  --output runtime/evidence/cluster-check.json
```

The command checks execution height/application hash, governance state and CometBFT sync status. It rejects same-height app-hash/governance divergence.

## Validator governance

v0.21 commands remain available:

```text
validator-change-build
validator-change-sign
validator-change-verify
governance-status
snapshot-v21-export
snapshot-v21-verify
snapshot-v21-import
migration-v21-dry-run
migration-v21-copy
```

Validator change approvals require voting power **strictly greater than two-thirds** of the current application validator set. For four equal-power validators this means 3-of-4 approvals.

The modeled update lifecycle is:

```text
H    governance transaction is finalized and ABCI validator update is emitted
H+1  application change remains pending
H+2  target application validator set becomes active
```

## Campaign plan / evidence

Build a campaign plan after creating the quorum-approved governance request:

```bash
crakchain campaign-v22-plan-build \
  --genesis runtime/governed-v22-lab/application-genesis.json \
  --kind join \
  --emit-height 101 \
  --change-request runtime/governance/join-validator-5-signed.json \
  --output runtime/evidence/join-plan.json
```

Capture cluster observations around activation boundaries, then bind them into signed operator evidence:

```bash
SOURCE_COMMIT=$(git rev-parse HEAD)

crakchain campaign-v22-evidence-build \
  --genesis runtime/governed-v22-lab/application-genesis.json \
  --key private/campaign-evidence-key.json \
  --source-commit "$SOURCE_COMMIT" \
  --plan runtime/evidence/join-plan.json \
  --observation runtime/evidence/cluster-before.json \
  --observation runtime/evidence/cluster-after.json \
  --executed \
  --output runtime/evidence/join-evidence.json
```

A signature authenticates the operator evidence; it is not an independent audit certificate.

## Governance history

```bash
crakchain governance-history-v22 \
  --genesis runtime/governed-v22-lab/application-genesis.json \
  --data runtime/governed-v22-lab/app1 \
  --output runtime/evidence/governance-history.json
```

This exports active validators, pending changes, applied history and validator-update emissions for explorer/review use.

## Existing release/recovery tooling retained

Earlier phases remain available, including:

- native ABCI state sync,
- external snapshots/checkpoints,
- explorer indexing/reconciliation,
- soak/fault tooling,
- signed release/evidence/review artifacts,
- reproducible Python/Go build checks,
- CycloneDX direct-dependency SBOM generation,
- schema migration/rollback rehearsal,
- browser wallet/public gateway/faucet/Mining Lab test tooling.

The Mining Lab remains a **test-only work-reward mechanism**. It is not CometBFT consensus mining, does not mint new CRKBIT supply and must not be represented as guaranteed earnings.

## What still blocks production mainnet

Code implementation alone is not enough. The project still needs actual long-running independent-host validator operation, real join/remove/replace campaigns, activation-boundary restart/partition/state-sync evidence, protected remote/HSM signing, production RPC/TLS/WAF/DDoS/secret-management controls, independent consensus/application/network/cryptography/browser-wallet review, final validator/CRKBIT economics and applicable legal/regulatory review.

The canonical gate list is [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md).

Until those gates are actually satisfied, use **public testnet**, **review candidate**, or **mainnet-candidate infrastructure** — not production mainnet.
