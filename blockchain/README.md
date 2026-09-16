# Crakbit Chain — v0.25 Independent-Review-Candidate Tooling Alpha

**Current package:** `0.25.0a1`  
**Consensus candidate:** CometBFT `v0.40.0`  
**Execution path:** `crakbit-execution/3`  
**Status:** research/public-testnet/independent-review-candidate tooling — **not production mainnet**.

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

## v0.25 scope

v0.25 builds on v0.24 operational hardening and adds the **evidence and freeze boundary before independent review**:

- incident-response records with acknowledgement/resolution ordering,
- escalation requirement for high/critical incidents,
- recovery-verification requirement before incident closure,
- signed per-operator host attestations using dedicated evidence-signing keys,
- exact source commit / package / CometBFT / application-genesis / consensus-genesis binding,
- required 7-day soak, backup/restore, clean-host state sync, validator-governance and protected-signer assertions,
- required restart/process-kill/partition/latency/packet-loss/load/storage coverage,
- at least four unique operator IDs, validator IDs and evidence signers,
- provider and region diversity gates,
- one exact source/package/CometBFT/application-genesis/consensus-genesis identity across the candidate,
- dependency on a successful v0.24 operational-readiness artifact,
- dependency on closed incident-response drill evidence,
- signed exact review-candidate freeze,
- explicit independent-review scope,
- hard-coded `independent_security_review_completed=false` and `production_mainnet_ready=false` claims,
- v0.25 regression tests.

See [`V0.25.md`](V0.25.md) and [`docs/INDEPENDENT_REVIEW_HANDOFF_V25.md`](docs/INDEPENDENT_REVIEW_HANDOFF_V25.md).

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

## v0.25 commands

```text
incident-v25-record
host-attestation-v25-build
host-attestation-v25-verify
review-gate-v25-build
review-freeze-v25-build
review-freeze-v25-verify
```

All v0.24 host-preflight/fault/recovery/signer/redundancy/readiness commands and earlier public-testnet/governance/release commands remain available through CLI delegation.

## Evidence key separation

Each operator should use a dedicated **evidence-signing key** for v0.25 host attestations. It should not be the validator consensus key, governance wallet key, user wallet key, TLS key or release key.

A valid cryptographic signature proves that the holder of the evidence key signed the record. It does **not** independently prove the operator/provider/region/soak/drill claims. Every v0.25 host attestation therefore records:

```text
operator_self_attested=true
independently_verified=false
production_mainnet_ready=false
```

## Review gate

The aggregate v0.25 review gate requires:

- v0.24 `operational_review_candidate=true`,
- at least four signed host attestations,
- unique operator / validator / evidence-signer identities,
- >=2 providers and >=2 regions,
- every per-host gate satisfied,
- single source commit and exact network identity,
- at least one incident-response drill,
- every incident closed with recovery verified.

Only then can `candidate_freeze_allowed=true` be produced.

## Freeze candidate for independent review

`review-freeze-v25-build` refuses to create a freeze if the supplied v0.25 review gate is unsatisfied. The freeze binds the exact source commit, package, CometBFT version, both genesis files, the review-gate hash and each review artifact SHA-256, then signs the manifest.

The freeze does **not** claim an audit has happened. It explicitly keeps independent review and production-mainnet readiness false.

## v0.24 operational layer retained

v0.24 remains the source of:

- validator host preflight,
- exact package/CometBFT/genesis identity checks,
- authorized typed fault/recovery records,
- backup/restore and clean-host state-sync convergence,
- protected remote-signer/HSM-style drill evidence,
- redundant RPC/explorer convergence checks,
- separate 24h/72h/7-day readiness gates,
- signed operational evidence.

## Mining note

The Mining Lab is a **test-only work-reward service**, not consensus mining. It does not mint new supply and does not create CometBFT blocks.

## Production boundary

Tooling, signatures and operator attestations are not substitutes for actual independent-host operation or independent review. Before production-value mainnet consideration the project still needs real independently managed validators, real multi-operator genesis, genuine long-running/fault/recovery evidence, protected signer deployment, production RPC/TLS/WAF/DDoS/secret-management engineering, independent consensus/application/governance/network/cryptography/browser-wallet review, remediation/retest of high/critical findings, finalized economics/incentives and applicable legal/regulatory review.

See [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md).
