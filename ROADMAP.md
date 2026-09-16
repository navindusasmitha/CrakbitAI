# Crakbit AI Roadmap

This roadmap describes the intended development order for Crakbit AI. Dates are targets, not guarantees, and may change based on research, funding, testing and security findings.

## Guiding Principle

**Technology first. Security first. Tokens later.**

Crakbit AI remains primarily a defensive-security and secure-development project. Crakbit Chain is developed in parallel as a testable blockchain-security and infrastructure research platform. Production mainnet planning stays gated on long-running public testing, independently reviewed consensus/application behavior, wallet/network review and operational readiness.

## Phase 1 — Foundation
**Target: Q3–Q4 2026**

- [x] Establish Crakbit AI project identity
- [x] Launch public website
- [x] Create public GitHub repository
- [x] Publish initial roadmap and architecture/security documentation
- [x] Establish public Giveth project listing
- [ ] Establish consistent public development/update cadence
- [ ] Complete official community/social channels
- [ ] Link final fundraising URL consistently across public project surfaces

## Phase 2 — Security MVP
**Target: Q4 2026**

- [ ] AI Security Assistant prototype
- [x] Initial secure-code scanning pipeline alpha
- [x] Initial Python security rules
- [x] Initial JavaScript/TypeScript security rules
- [x] Initial secret detection
- [ ] Structured configuration checks
- [x] Human-readable findings and remediation fields
- [x] Severity/confidence model
- [ ] Public web demo

## Phase 3 — Developer Tooling
**Target: Q1 2027**

- [x] `crak` CLI early alpha
- [ ] Developer API alpha
- [x] JSON output
- [ ] SARIF-style output exploration
- [ ] Repository scan workflow
- [ ] CI/CD integration prototype
- [ ] Authentication and rate-limiting design
- [ ] Expanded documentation/examples

## Phase 4 — Blockchain Security
**Target: Q2 2027**

- [ ] Solidity analysis prototype
- [ ] Smart-contract security rules
- [ ] Contract permission/risk analysis
- [ ] Human-readable contract reports
- [ ] Public blockchain-data analysis experiments
- [ ] Developer guidance for common smart-contract risks

## Phase 5 — Developer Ecosystem
**Target: Q2–Q3 2027**

- [ ] SDK design
- [ ] Git integration
- [ ] CI/CD workflow templates
- [ ] IDE integration research
- [ ] Plugin/extension architecture
- [ ] Open-source rule-contribution framework

## Phase 6 — Crakbit Chain Research → Public-Testnet Candidate
**Prototype started September 2026**

A runnable research/devnet and external CometBFT application path exist. This does **not** mean a production blockchain or production-value CRKBIT asset has launched.

### Completed foundation through v0.14

- [x] Native test-only CRKBIT accounting, Ed25519 wallets and signed transfers
- [x] Research consensus experiments, authenticated validator networking, snapshots, recovery and archives
- [x] Integrity verification, backups, metrics and resource controls
- [x] Deterministic external application protocol boundary
- [x] Signed release/genesis tooling
- [x] CometBFT `v0.40.0` ABCI integration PoC
- [x] `crakbit-execution/2` crash-safe FinalizeBlock → Commit path
- [x] Strict >2/3 signed application-genesis ceremony tooling
- [x] Combined Python + Go CI

### v0.15 — wallet/public gateway/Mining Lab

- [x] Responsive browser wallet/explorer UI
- [x] Browser-generated Ed25519 wallet and encrypted local vault
- [x] Client-side canonical transaction signing
- [x] Public gateway with research + CometBFT modes
- [x] Persistent faucet controls
- [x] Test-only browser proof-of-work reward Mining Lab
- [x] Explicit production-mainnet release gates

### v0.16 — public-testnet recovery and web hardening

- [x] One-command multi-node CometBFT lab generator
- [x] Deterministic external-application checkpoint export/verify/restore
- [x] Trusted expected-height/application-hash verification
- [x] Snapshot-base-aware restore without invented historical commits
- [x] Dedicated indexed external explorer database/service
- [x] Durable SQLite public write/faucet/mining rate limits
- [x] Same-origin gateway defaults and production-style browser security headers
- [x] Multi-host health/divergence checker
- [x] FinalizeBlock/Commit crash/replay/checkpoint matrix
- [x] Browser-wallet threat model
- [x] Remote-signer/HSM-equivalent custody guidance

### v0.17 — native state sync and operational evidence tooling

- [x] Bump package/CLI to `0.17.0a1`
- [x] Implement deterministic CometBFT state-sync snapshots
- [x] Wire ABCI `ListSnapshots`, `OfferSnapshot`, `LoadSnapshotChunk`, `ApplySnapshotChunk`
- [x] Bind snapshot acceptance to CometBFT-supplied trusted application hash
- [x] Add per-chunk + complete artifact hash verification
- [x] Restrict restore to pristine application state and preserve snapshot-base semantics
- [x] Add authenticated v0.17 execution-service state-sync endpoints
- [x] Add signed exact-commit/CometBFT-version public-testnet evidence bundles
- [x] Add dry-run-by-default controlled fault-campaign evidence runner
- [x] Add single-edge TLS/rate-limit public-testnet NGINX profile
- [x] Add guarded CometBFT remote-signer configuration helper
- [x] Add Python + Go state-sync/evidence/operations tests
- [x] Publish `blockchain/V0.17.md`

### External evidence still required after v0.17

- [ ] Run four validators continuously on independently managed VPS/providers
- [ ] Demonstrate live clean-host state sync against that network
- [ ] Execute real partition, packet-loss, latency, process-kill and sustained-load campaigns
- [ ] Publish raw signed health/fault/recovery/soak evidence tied to exact source and CometBFT version
- [ ] Rebuild/reconcile explorer indexes from clean hosts
- [ ] Deploy and drill a real remote-signer/HSM-compatible validator flow
- [ ] Perform a multi-operator genesis ceremony with independently held validator keys
- [ ] Deploy/review multi-edge shared rate limiting, WAF/DDoS and TLS automation
- [ ] Freeze an independent-review candidate and commission consensus/application/network/wallet review

## Phase 7 — Long-Lived Public Testnet / v0.18 Evidence Freeze
**Only after operators provision independent infrastructure**

v0.18 should prioritize evidence over new features:

- [ ] Independent-host validator deployment
- [ ] Long-duration soak monitoring
- [ ] Live state-sync/bootstrap recovery drills
- [ ] Fault/partition/load campaigns using v0.17 tooling
- [ ] Signed source/genesis/release/evidence bundle publication
- [ ] Explorer reconciliation/rebuild evidence
- [ ] Protected validator signer drill
- [ ] Incident-response exercises
- [ ] Community test program
- [ ] Frozen security-review candidate

Testnet CRKBIT units represent test units only and should not be represented as production-value assets.

## Phase 8 — Independent Security Review

Before a production network launch:

- [ ] Independent consensus/application review
- [ ] Independent network/RPC security review
- [ ] Independent browser-wallet review
- [ ] Cryptography/key-management review
- [ ] Economic-security review
- [ ] Incident-response review
- [ ] Applicable legal/regulatory review
- [ ] Remediate or explicitly accept every high/critical finding

See `blockchain/docs/MAINNET_GATES.md` for the full release-gate checklist.

## Phase 9 — Mainnet Consideration

A production mainnet can only be considered after successful long-lived public testing, reviewed external consensus/application behavior, independent security review and a clear operational/economic/legal model.

Potential production items include final consensus configuration, reproducible signed releases, production genesis ceremony, hardened wallet ecosystem, production explorer/indexer, validator onboarding and remote signer strategy, CRKBIT production utility/economics, upgrade/governance process and incident-response operations.

## CRKBIT Status

**Production CRKBIT is not launched. No official presale. No production token contract.**

The research/public-testnet code uses test-only CRKBIT accounting with 8 decimals and a proposed 21,000,000 maximum genesis supply. Those parameters remain subject to technical, security, economic and legal review before any production implementation.
