# Crakbit Chain — v0.26 Independent-Review Remediation Alpha

**Current package:** `0.26.0a1`  
**Consensus candidate:** CometBFT `v0.40.0`  
**Execution path:** `crakbit-execution/3`  
**Status:** research/public-testnet/independent-review-remediation tooling — **not production mainnet**.

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

## v0.26 scope

v0.26 builds on the v0.25 exact review freeze and adds the **post-review remediation / re-freeze boundary**:

- signed review findings register,
- stable `CRK-REV-...` finding IDs,
- severity/component/title/affected-commit/reproduction metadata,
- remediation commit/config/regression-test binding,
- signed independent retest records,
- hard re-freeze gate for unresolved or un-retested high/critical findings,
- retests must pass against the **exact candidate source commit** being re-frozen,
- signed supply-chain/reproducible-build attestation hooks,
- dependency-lock and SBOM hash binding,
- signed public-edge TLS/WAF/DDoS/load/failover evidence without provider secrets,
- minimum two passing public-edge attestations,
- stale candidate supersession reasons when source/package/CometBFT/genesis/dependency/review evidence changes,
- signed post-remediation review re-freeze,
- explicit `independent_security_review_completed=false` and `production_mainnet_ready=false`,
- v0.26 regression tests.

See [`V0.26.md`](V0.26.md).

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

## v0.26 commands

```text
review-findings-v26-build
review-findings-v26-verify
review-retest-v26-build
review-retest-v26-verify
supply-attestation-v26-build
supply-attestation-v26-verify
edge-attestation-v26-build
edge-attestation-v26-verify
remediation-gate-v26-build
review-refreeze-v26-build
review-refreeze-v26-verify
```

All v0.25 and earlier commands remain available through CLI delegation.

## High/critical remediation rule

A high/critical finding cannot unlock a re-freeze merely because an operator marks it `remediated`. The finding must include remediation/regression metadata and the latest signed retest for that finding on the **exact candidate commit** must be `passed`.

A successful retest against an older commit does not satisfy the gate. A later failing retest on the candidate commit blocks the re-freeze.

## Supply-chain gate

The v0.26 supply-chain attestation binds:

- candidate Git commit,
- package version,
- dependency-lock SHA-256,
- SBOM SHA-256,
- Python reproducible-build result,
- Go bridge reproducible-build result,
- dependency-review completion assertion,
- transitive-SBOM completion assertion.

This remains an attestation format. A signature proves who signed the record; it does not independently prove the real-world build/review process.

## Public-edge gate

Each signed edge record captures public, non-secret operational facts such as minimum TLS version, TLS automation, WAF/DDoS controls, load-test/failover results and measured capacity. Provider API keys, certificate private keys and WAF secrets must never be embedded.

The v0.26 remediation gate requires at least two passing public-edge attestations tied to the candidate source commit.

## Candidate supersession

An old frozen candidate is never silently modified. If a previous freeze is supplied, v0.26 records supersession reasons such as source/package/CometBFT/genesis/dependency changes. New review/remediation evidence also results in a newly signed re-freeze.

## Existing v0.25/v0.24 layers retained

v0.25 remains responsible for independent-host operator evidence, incident-response drills and the initial exact review candidate freeze. v0.24 remains responsible for preflight, authorized fault/recovery records, clean-host state sync/backup recovery, protected signer evidence, redundant-edge convergence and separate 24h/72h/7-day operational gates.

## Mining note

The Mining Lab is a **test-only work-reward service**, not consensus mining. It does not mint new supply and does not create CometBFT blocks.

## Production boundary

A passing v0.26 re-freeze gate is not a completed audit and is not production-mainnet approval. Real independent-host operation, independently reviewed consensus/application/governance/network/cryptography/browser-wallet behavior, protected key custody, production public-edge engineering, economic-security review, finalized validator/CRKBIT economics and applicable legal/regulatory review remain mandatory.

See [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md).
