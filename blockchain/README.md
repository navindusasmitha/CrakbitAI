# Crakbit Chain — v0.23 Public-Testnet / Review-Candidate Alpha

**Current package:** `0.23.0a1`  
**Consensus candidate:** CometBFT `v0.40.0`  
**Execution path:** `crakbit-execution/3`  
**Status:** research/public-testnet/mainnet-candidate infrastructure — **not production mainnet**.

Production CRKBIT has **not** launched. There is no official presale or production token contract. Do not use this software to custody real value.

## Current architecture

```text
Browser wallet / CLI
        │ signed transaction / governed validator change
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

v0.23 adds an operational layer around this path for independent public-testnet operators. The older Python prevote/precommit implementation remains research-only and is not the intended production BFT path.

## What v0.23 adds

v0.23 is the **public-testnet deployment / operations** phase. It adds:

- public-only validator identity export from each operator's own CometBFT host,
- explicit secret-field rejection for shared operator metadata,
- 4+ validator public-testnet inventory generation,
- operator/provider/region diversity gates,
- shared application + CometBFT genesis bundles with SHA-256 manifests,
- per-validator non-secret deployment bundles,
- systemd templates for execution service, ABCI bridge and CometBFT,
- persistent-peer configuration artifacts,
- independent-node `/status` + `/abci_info` monitoring,
- same-height application-hash divergence detection,
- long-running JSONL soak collection,
- 24-hour minimum operational evidence gate,
- readiness reports that separate public-testnet readiness from production-mainnet readiness,
- signed operations evidence tied to exact source commit and artifact hashes,
- v0.23 regression tests.

See [`V0.23.md`](V0.23.md).

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

## Public-testnet operator workflow

Each operator should initialize and control their own validator key. Export public metadata only:

```bash
crakchain validator-identity-v23-export \
  --home /var/lib/crakbit/cometbft \
  --cometbft /usr/local/bin/cometbft \
  --name validator-1 \
  --operator-id operator-a \
  --provider provider-a \
  --region region-a \
  --p2p-host validator1.example.org \
  --monitor-rpc-url https://validator1-monitor.example.org \
  --output validator-1-public.json
```

Collect at least four operator identities and build the shared inventory:

```bash
crakchain public-testnet-inventory-build \
  --chain-id crakbit-public-testnet-1 \
  --network-name "Crakbit Public Testnet 1" \
  --identity validator-1-public.json \
  --identity validator-2-public.json \
  --identity validator-3-public.json \
  --identity validator-4-public.json \
  --output public-testnet-inventory.json
```

The inventory never needs private validator keys. Do not collect operator private keys on a central machine.

## Shared genesis / deployment bundles

Use a reviewed CometBFT genesis template and a **public** treasury address:

```bash
crakchain public-testnet-genesis-build \
  --inventory public-testnet-inventory.json \
  --cometbft-template cometbft-template-genesis.json \
  --treasury-address crk1PUBLIC_ADDRESS_ONLY \
  --output runtime/public-testnet/genesis
```

Build non-secret operator bundles:

```bash
crakchain public-testnet-bundles-build \
  --inventory public-testnet-inventory.json \
  --genesis-bundle runtime/public-testnet/genesis \
  --output runtime/public-testnet/operators
```

The generated bundle manifest keeps `deployment_executed=false`; generation does not mean the VPS deployment happened.

## Monitoring and soak evidence

One health observation:

```bash
crakchain public-testnet-observe \
  --inventory public-testnet-inventory.json \
  --output runtime/evidence/observation.json
```

24-hour collection:

```bash
crakchain public-testnet-soak \
  --inventory public-testnet-inventory.json \
  --output runtime/evidence/soak-24h.jsonl \
  --duration-seconds 86400 \
  --interval-seconds 30
```

Summarize:

```bash
crakchain public-testnet-soak-summary \
  --input runtime/evidence/soak-24h.jsonl \
  --output runtime/evidence/soak-24h-summary.json
```

The v0.23 minimum soak gate requires actual observed duration of at least 24 hours, zero same-height app-hash divergence, full reachability and at least 99% healthy observations.

## Readiness / signed evidence

```bash
crakchain public-testnet-readiness \
  --inventory public-testnet-inventory.json \
  --genesis-manifest runtime/public-testnet/genesis/genesis-bundle.json \
  --deployment-manifest runtime/public-testnet/operators/deployment-manifest.json \
  --soak-summary runtime/evidence/soak-24h-summary.json \
  --output runtime/evidence/public-testnet-readiness.json
```

A dedicated evidence signer can bind the exact source commit and artifact hashes:

```bash
SOURCE_COMMIT=$(git rev-parse HEAD)
crakchain public-testnet-evidence-build \
  --key private/public-testnet-evidence-key.json \
  --source-commit "$SOURCE_COMMIT" \
  --inventory public-testnet-inventory.json \
  --readiness runtime/evidence/public-testnet-readiness.json \
  --artifact runtime/evidence/soak-24h-summary.json \
  --output runtime/evidence/public-testnet-operations-evidence.json
```

A signature authenticates operator-produced evidence; it is not an independent audit certificate.

## Validator governance retained

v0.21/v0.22 commands remain available for governed `join` / `remove` / `replace` campaigns. Approvals require voting power **strictly greater than two-thirds** of the current application validator set; for four equal-power validators that means 3-of-4 approvals.

The modeled lifecycle remains:

```text
H    governance transaction finalizes and validator update is emitted
H+1  application change remains pending
H+2  target application validator set becomes active
```

Those semantics still need independent-host campaign evidence and review before production consideration.

## Existing release/recovery tooling retained

Earlier phases remain available, including native ABCI state sync, external snapshots/checkpoints, explorer indexing/reconciliation, fault tooling, signed release/evidence/review artifacts, reproducible Python/Go build checks, CycloneDX direct-dependency SBOM generation, schema migration/rollback rehearsal and browser wallet/public gateway/faucet/Mining Lab test tooling.

The Mining Lab remains a **test-only work-reward mechanism**. It is not CometBFT consensus mining, does not mint new CRKBIT supply and must not be represented as guaranteed earnings.

## What still blocks production mainnet

The repository now has public-testnet deployment/evidence tooling, but production launch still requires **actual** independent-host operation, multi-operator genesis, 24h → 72h → 7-day soak/fault/load/state-sync campaigns, protected remote/HSM signing, production RPC/TLS/WAF/DDoS/secret-management/capacity controls, independent consensus/application/governance/network/cryptography/browser-wallet review, final validator/CRKBIT economics and applicable legal/regulatory review.

The canonical gate list is [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md).

Until those gates are actually satisfied, use **public testnet**, **review candidate**, or **mainnet-candidate infrastructure** — not production mainnet.
