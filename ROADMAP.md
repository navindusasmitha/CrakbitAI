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

- [x] Bump package/CLI to `0.19.0a1`
- [x] Add machine-readable review-finding remediation matrix
- [x] Block automated gate on unresolved high/critical findings
- [x] Require regression-test references for remediated high/critical findings
- [x] Add reproducible artifact SHA-256 comparison tooling
- [x] Add CI double-build verification for Python wheel
- [x] Add CI double-build verification for Go bridge
- [x] Add direct-dependency CycloneDX 1.5 SBOM generation
- [x] Add signed release provenance tied to exact source/genesis/artifact hashes
- [x] Add signed upgrade/rollback/incident/DR/validator-lifecycle drill evidence format
- [x] Add v0.19 release-engineering tests and documentation
- [ ] Ingest real independent-review findings when received
- [ ] Produce a complete transitive release SBOM from the final release environment
- [ ] Reproduce release artifacts in a genuinely independent build environment

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

## Phase 9 — v0.20 Upgrade Compatibility / Validator Lifecycle

- [ ] Versioned application/database migration framework
- [ ] Offline migration dry-run and rollback verification
- [ ] Protocol/application compatibility matrix
- [ ] Validator-set lifecycle application boundary
- [ ] Safe join/remove/replace testnet drills
- [ ] Explorer/history migration verification
- [ ] Signed migration and rollback evidence
- [ ] Continue regression fixes for real review findings

## Phase 10 — Mainnet Consideration

A production mainnet can only be considered after successful long-lived public testing, reviewed external consensus/application behavior, independent security review and a clear operational/economic/legal model.

## CRKBIT Status

**Production CRKBIT is not launched. No official presale. No production token contract.**

The research/public-testnet code uses test-only CRKBIT accounting with 8 decimals and a proposed 21,000,000 maximum genesis supply. Those parameters remain subject to technical, security, economic and applicable legal review before any production implementation.
