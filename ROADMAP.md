# Crakbit AI Roadmap

This roadmap describes intended development order. Dates are targets, not guarantees, and may change based on research, funding, testing and security findings.

## Guiding Principle

**Technology first. Security first. Tokens later.**

Crakbit AI remains primarily a defensive-security and secure-development project. Crakbit Chain is developed in parallel as a testable blockchain-security/infrastructure research platform. Production-mainnet consideration stays gated on long-running public testing, independently reviewed consensus/application behavior, wallet/network review and operational readiness.

## Phase 1 — Foundation
**Target: Q3–Q4 2026**

- [x] Project identity, public website and GitHub repository
- [x] Initial roadmap/security documentation
- [x] Public Giveth project listing
- [ ] Consistent public development/update cadence
- [ ] Complete official community/social channels

## Phase 2 — Security MVP
**Target: Q4 2026**

- [x] Initial secure-code scanning pipeline alpha
- [x] Python + JavaScript/TypeScript rules and secret detection
- [x] Human-readable/JSON findings and severity/confidence model
- [ ] AI Security Assistant prototype
- [ ] Structured configuration checks
- [ ] Public web demo

## Phase 3 — Developer Tooling
**Target: Q1 2027**

- [x] `crak` CLI early alpha
- [x] JSON output
- [ ] Developer API alpha
- [ ] SARIF exploration
- [ ] Repository/CI integration prototypes
- [ ] Expanded documentation/examples

## Phase 4 — Blockchain Security
**Target: Q2 2027**

- [ ] Solidity analysis prototype
- [ ] Smart-contract security rules
- [ ] Contract permission/risk analysis
- [ ] Human-readable contract reports
- [ ] Public blockchain-data analysis experiments

## Phase 5 — Developer Ecosystem
**Target: Q2–Q3 2027**

- [ ] SDK design
- [ ] Git/CI/CD/IDE integration research
- [ ] Plugin architecture
- [ ] Open-source rule contribution framework

## Phase 6 — Crakbit Chain Research → Public-Testnet Candidate
**Prototype started September 2026**

A runnable research/devnet and external CometBFT application path exist. This does **not** mean a production blockchain or production-value CRKBIT asset has launched.

### Foundation through v0.14

- [x] Native test-only CRKBIT accounting, Ed25519 wallets and signed transfers
- [x] Research consensus/network/recovery experiments
- [x] Integrity, backups, metrics and resource controls
- [x] Deterministic external application boundary
- [x] Signed release/genesis tooling
- [x] CometBFT `v0.40.0` ABCI integration PoC
- [x] `crakbit-execution/2` crash-safe FinalizeBlock → Commit path
- [x] Combined Python + Go CI

### v0.15 — wallet/public gateway/Mining Lab

- [x] Browser wallet/explorer UI
- [x] Local encrypted Ed25519 vault + client-side signing
- [x] Public gateway with research + CometBFT modes
- [x] Persistent faucet controls
- [x] Test-only browser work-reward Mining Lab
- [x] Explicit mainnet release gates

### v0.16 — recovery/indexing/web hardening

- [x] Multi-node CometBFT lab generator
- [x] Deterministic external checkpoint export/verify/restore
- [x] Trusted height/application-hash verification
- [x] Dedicated external explorer index
- [x] Durable public-service limits
- [x] Same-origin gateway/CSP security profile
- [x] Multi-host health checker and crash/replay matrix
- [x] Wallet threat model + remote-signer/HSM guidance

### v0.17 — native state sync / operational evidence tooling

- [x] Native ABCI `ListSnapshots`, `OfferSnapshot`, `LoadSnapshotChunk`, `ApplySnapshotChunk`
- [x] Trusted app-hash binding and chunk/artifact verification
- [x] Pristine-state restore + snapshot-base semantics
- [x] Signed exact-commit public-testnet evidence bundles
- [x] Dry-run controlled fault-campaign runner
- [x] Single-edge TLS/rate-limit NGINX profile
- [x] Guarded remote-signer configuration helper
- [x] Expanded Python + Go tests

### v0.18 — review freeze / reconciliation / sustained evidence tooling

- [x] Signed review-candidate freeze manifest
- [x] Exact source/package/CometBFT/genesis identity binding
- [x] Review artifact hashing and conservative readiness claims
- [x] Clean explorer rebuild/reconciliation tooling
- [x] Deterministic explorer table fingerprints
- [x] Sustained health/soak evidence collector
- [x] v0.18 regression tests and documentation

### v0.19 — review remediation / reproducible release engineering

- [x] Machine-readable review-finding remediation matrix
- [x] High/critical finding automated release gate
- [x] Regression-test references for remediated high/critical findings
- [x] Reproducible artifact SHA-256 comparison tooling
- [x] CI double-build verification for Python wheel + Go bridge
- [x] Direct-dependency CycloneDX 1.5 SBOM generation
- [x] Signed release provenance
- [x] Signed operations-drill evidence
- [ ] Ingest real independent-review findings when received
- [ ] Complete transitive release SBOM in final release environment
- [ ] Independent reproducible-build evidence

### v0.20 — upgrade compatibility / validator lifecycle rehearsal

- [x] Bump package/CLI to `0.20.0a1`
- [x] Add explicit external-application schema versioning
- [x] Add v19 → v20 offline-copy migration framework
- [x] Verify pre-existing logical application state across migration
- [x] Add disposable rollback verification
- [x] Add protocol/schema/CometBFT compatibility matrix
- [x] Add full offline upgrade rehearsal with SQLite/genesis checks
- [x] Add signed migration/rollback evidence
- [x] Add signed validator join/remove/replace drill plans
- [x] Model CometBFT validator-update emission/effective-height relationship
- [x] Prevent lifecycle plan from claiming a live consensus change
- [x] Add v0.20 regression tests/documentation
- [ ] Define a deterministic replicated authorization path for live validator-set updates
- [ ] Emit live ABCI validator updates from committed replicated application state
- [ ] Execute multi-node join/remove/replace drills after that deterministic path exists

### External evidence still required

- [ ] Run four validators continuously on independently managed VPS/providers
- [ ] Demonstrate live clean-host CometBFT state sync and app-hash convergence
- [ ] Execute real partition, packet-loss, latency, process-kill and sustained-load campaigns
- [ ] Publish signed raw health/fault/recovery/soak evidence tied to exact source/CometBFT version
- [ ] Rebuild/reconcile explorer indexes from clean independent hosts
- [ ] Deploy and drill a real remote-signer/HSM-compatible validator flow
- [ ] Perform a multi-operator genesis ceremony with independently held validator keys
- [ ] Deploy/review multi-edge shared rate limiting, WAF/DDoS and TLS automation
- [ ] Freeze a candidate with real evidence and commission independent consensus/application/network/wallet review

## Phase 7 — Long-Lived Public Testnet / Review Candidate

- [ ] Independent-host validator deployment
- [ ] Long-duration soak monitoring with published evidence
- [ ] Live state-sync/bootstrap recovery drills
- [ ] Fault/partition/load campaigns
- [ ] Signed source/genesis/release/evidence publication
- [ ] Protected validator signer drill
- [ ] Incident-response exercises
- [ ] Community test program
- [ ] Frozen independent-review candidate

Testnet CRKBIT units represent test units only and should not be represented as production-value assets.

## Phase 8 — Independent Security Review

- [ ] Independent consensus/application review
- [ ] Independent network/RPC review
- [ ] Independent browser-wallet review
- [ ] Cryptography/key-management review
- [ ] Economic-security review
- [ ] Incident-response review
- [ ] Applicable legal/regulatory review
- [ ] Remediate or explicitly accept every high/critical finding

## Phase 9 — v0.21 Deterministic Validator Governance / Upgrade Activation

- [ ] Replicated validator-change authorization object
- [ ] Pending validator lifecycle state committed in the application state machine
- [ ] Lifecycle state included in application hash
- [ ] Deterministic ABCI validator-update emission from committed state
- [ ] Activation-height replay/restart safety tests
- [ ] Multi-node join/remove/replace lab campaign
- [ ] Coordinated schema activation/rollback across a full testnet
- [ ] Explorer/history reconciliation after coordinated upgrades
- [ ] Continue regression fixes for real review findings

## Phase 10 — Mainnet Consideration

A production mainnet can only be considered after successful long-lived public testing, reviewed external consensus/application behavior, independent security review and a clear operational/economic/legal model.

## CRKBIT Status

**Production CRKBIT is not launched. No official presale. No production token contract.**

The research/public-testnet code uses test-only CRKBIT accounting with 8 decimals and a proposed 21,000,000 maximum genesis supply. Those parameters remain subject to technical, security, economic and applicable legal review before any production implementation.
