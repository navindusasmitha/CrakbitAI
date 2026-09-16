# Crakbit Chain — v0.24 Operational-Hardening Alpha

**Current package:** `0.24.0a1`  
**Consensus candidate:** CometBFT `v0.40.0`  
**Execution path:** `crakbit-execution/3`  
**Status:** research/public-testnet/operational-review-candidate infrastructure — **not production mainnet**.

Production CRKBIT has **not** launched. There is no official presale or production token contract. Do not use this software to custody real value.

## Current architecture

```text
Browser wallet / CLI
        │ signed transaction / governed validator change
        ▼
Public gateway / redundant public RPC
        │
        ▼
CometBFT v0.40.0 validator network
        │ ABCI
        ▼
Crakbit Go bridge
        │ authenticated loopback/private HTTP
        ▼
crakbit-execution/3
        │
        ├── deterministic transfers
        ├── validator governance (>2/3 approval)
        ├── staged FinalizeBlock → atomic Commit
        ├── governance-aware application hash
        ├── validator updates
        └── governance-aware state sync
```

The older Python prevote/precommit implementation remains research-only and is not the intended production BFT path.

## v0.24 scope

v0.24 builds on the v0.23 public-testnet deployment layer and adds **operational fault/recovery hardening**:

- exact host preflight before a validator starts,
- package / CometBFT / application-genesis / consensus-genesis identity gates,
- loopback/private execution and ABCI bind checks,
- execution-token presence check without reading or exposing the token,
- data-directory writability and minimum free-space check,
- typed fault plans for restart, process-kill, partition, latency, packet-loss, load and storage,
- mandatory recovery command for every planned fault,
- explicit normalization of real executed fault-campaign results,
- backup/restore and clean-host state-sync convergence records,
- remote-signer/HSM-style drill records with key-export rejection,
- redundant RPC/explorer checks,
- same-height application-hash conflict detection across redundant RPC endpoints,
- separate 24h, 72h and 7-day soak gates,
- aggregate operational-review-candidate readiness,
- signed v0.24 operations evidence bound to exact source commit and artifact hashes,
- v0.24 regression tests.

See [`V0.24.md`](V0.24.md) for the full runbook and limitations.

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

## v0.24 commands

```text
host-preflight-v24
fault-v24-plan-build
fault-v24-result-build
recovery-v24-record
remote-signer-v24-record
redundancy-v24-check
readiness-v24-build
ops-v24-sign
ops-v24-verify
```

All v0.23 public-testnet commands and earlier validator-governance/release/recovery commands remain available through CLI delegation.

## Preflight each validator

```bash
crakchain host-preflight-v24 \
  --node-name validator-1 \
  --application-genesis /etc/crakbit/application-genesis.json \
  --application-genesis-sha256 EXPECTED_APP_GENESIS_SHA256 \
  --consensus-genesis /var/lib/crakbit/cometbft/config/genesis.json \
  --consensus-genesis-sha256 EXPECTED_COMET_GENESIS_SHA256 \
  --data /var/lib/crakbit/app \
  --token-file /etc/crakbit/node.env \
  --execution-bind 127.0.0.1:26659 \
  --abci-bind tcp://127.0.0.1:26658 \
  --cometbft /usr/local/bin/cometbft \
  --expected-cometbft-version v0.40.0 \
  --output runtime/evidence/validator-1-preflight.json
```

The evidence output contains only a token-presence boolean; it must never contain the token/private key itself.

## Fault campaigns are opt-in

`fault-v24-plan-build` creates a plan only. It requires a recovery command for every step. Existing `scripts/run_fault_campaign.py` remains dry-run unless the operator explicitly provides `--execute`.

Never run partition/storage/process-kill commands against infrastructure you do not own or administer. Real campaign evidence must preserve raw logs and recovery observations.

## Long-soak readiness

Use actual elapsed v0.23 soak summaries:

```bash
crakchain readiness-v24-build \
  --soak-24h runtime/evidence/soak-24h-summary.json \
  --soak-72h runtime/evidence/soak-72h-summary.json \
  --soak-7d runtime/evidence/soak-7d-summary.json \
  --fault-result runtime/evidence/fault-restart.json \
  --recovery runtime/evidence/backup-restore.json \
  --recovery runtime/evidence/clean-host-state-sync.json \
  --signer-record runtime/evidence/validator-1-signer.json \
  --redundancy runtime/evidence/redundancy.json \
  --output runtime/evidence/v24-readiness.json
```

The complete operational gate requires all seven modeled fault classes, both recovery classes, redundancy, protected-signer drill evidence and genuine 24h/72h/7d soak evidence. Even if those operator gates pass, the result still has `production_mainnet_ready=false` and `independent_security_review_completed=false`.

## Existing public-testnet layer retained

v0.23 remains the deployment foundation:

- public-only validator identities,
- >=4-validator inventory,
- operator/provider/region diversity checks,
- matching application + CometBFT genesis bundles,
- non-secret per-operator deployment bundles,
- public-testnet observations and JSONL soak collection,
- signed public-testnet operations evidence.

v0.22/v0.21 retain governed validator `join` / `remove` / `replace` flows with strict `>2/3` current voting-power approval and modeled `H → H+2` application activation.

## Mining note

The Mining Lab is a **test-only work-reward service**, not consensus mining. It does not mint new supply and does not create CometBFT blocks.

## Production boundary

Code and operator-generated evidence are not substitutes for independent review. Before any production-value mainnet consideration the project still needs real independently managed validators, genuine multi-operator genesis, sustained independent-host operation, real fault/load/storage/state-sync results, protected signer deployment, production RPC/TLS/WAF/DDoS/secret-management engineering, independent consensus/application/governance/network/cryptography/browser-wallet review, finalized economics/incentives and applicable legal/regulatory review.

See [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md).
