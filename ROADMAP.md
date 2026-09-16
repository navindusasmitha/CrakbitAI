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

### Foundation through v0.19

- [x] Native test-only CRKBIT accounting, Ed25519 wallets and signed transfers
- [x] Research consensus/network/recovery experiments
- [x] Integrity, backups, metrics and resource controls
- [x] Deterministic external application boundary
- [x] CometBFT `v0.40.0` ABCI integration PoC
- [x] Crash-safe external FinalizeBlock → Commit path
- [x] Browser wallet/public gateway/faucet/Mining Lab test tooling
- [x] Native ABCI state sync
- [x] Explorer reconciliation, soak/fault evidence tooling
- [x] Review freeze, remediation matrix, reproducible-build checks, SBOM and signed release provenance

### v0.20 — upgrade compatibility / lifecycle rehearsal

- [x] Explicit application schema versioning
- [x] v19 → v20 offline-copy migration
- [x] Logical state preservation and rollback verification
- [x] Package/schema/CometBFT compatibility checks
- [x] Signed migration/rollback evidence
- [x] Signed validator join/remove/replace drill plans
- [x] Explicit update emission/effective-height modeling

### v0.21 — deterministic validator governance / activation

- [x] Bump package/CLI to `0.21.0a1`
- [x] Add `crakbit-execution/3` governed application path
- [x] Add canonical validator join/remove/replace governance transaction format
- [x] Add strict `>2/3` current voting-power approval rule
- [x] Replicate active and pending validator lifecycle state
- [x] Include validator-governance state in the deterministic application hash
- [x] Derive live ABCI validator updates only from validated replicated input
- [x] Record deterministic validator-update emission for crash/replay recovery
- [x] Model application-side validator activation at `H+2`
- [x] Add schema 21 and v20 → v21 offline-copy migration/rollback rehearsal
- [x] Add governance-aware external snapshots and native ABCI state sync
- [x] Add multi-operator governance request build/sign/verify CLI
- [x] Add Python governance/migration/state-sync tests
- [x] Add Go bridge validator-update tests
- [ ] Execute independent multi-host join/remove/replace campaigns
- [ ] Independently review the update-height/activation semantics
- [ ] Drill protected remote/HSM governance signing

### v0.22 — governed multi-node campaigns / coordinated upgrades

- [ ] One-command four-node governed CometBFT campaign lab
- [ ] Controlled broadcast helper for quorum-approved governance transactions
- [ ] Automated join/remove/replace campaigns with convergence checks
- [ ] Restart/process-kill tests at `H`, `H+1`, and `H+2`
- [ ] Partition/latency tests across a pending validator activation
- [ ] Native state-sync bootstrap while governance state is pending
- [ ] Coordinated schema/protocol upgrade activation across all validators
- [ ] Explorer/index representation of governance transactions and validator history
- [ ] Signed campaign evidence + application/validator-set divergence detection
- [ ] Governance-key/consensus-key separation and remote-signer design
- [ ] Research timelock/emergency/cancel semantics before any production consideration

### External evidence still required

- [ ] Run validators continuously on independently managed VPS/providers
- [ ] Demonstrate live clean-host CometBFT state sync and app-hash/governance-state convergence
- [ ] Execute real partition, packet-loss, latency, process-kill and sustained-load campaigns
- [ ] Publish signed raw health/fault/recovery/soak/governance evidence tied to exact source/CometBFT version
- [ ] Deploy and drill a real remote-signer/HSM-compatible validator/governance flow
- [ ] Perform a multi-operator genesis ceremony with independently held validator keys
- [ ] Deploy/review multi-edge shared rate limiting, WAF/DDoS and TLS automation
- [ ] Freeze a candidate with real evidence and commission independent consensus/application/governance/network/wallet review

## Phase 7 — Long-Lived Public Testnet / Review Candidate

- [ ] Independent-host validator deployment
- [ ] Long-duration soak monitoring with published evidence
- [ ] Live state-sync/bootstrap recovery drills
- [ ] Fault/partition/load/governance campaigns
- [ ] Signed source/genesis/release/evidence publication
- [ ] Protected validator/governance signer drill
- [ ] Incident-response exercises
- [ ] Community test program
- [ ] Frozen independent-review candidate

Testnet CRKBIT units represent test units only and should not be represented as production-value assets.

## Phase 8 — Independent Security Review

- [ ] Independent consensus/application/governance review
- [ ] Independent network/RPC review
- [ ] Independent browser-wallet review
- [ ] Cryptography/key-management review
- [ ] Economic-security review
- [ ] Incident-response review
- [ ] Applicable legal/regulatory review
- [ ] Remediate or explicitly accept every high/critical finding

## Phase 9 — Release / Operations Hardening

- [ ] Independent reproducible build environment
- [ ] Complete transitive SBOM/supply-chain review
- [ ] Multi-edge DDoS/WAF/capacity testing
- [ ] Protected signing/recovery procedures
- [ ] Coordinated upgrade/rollback campaigns
- [ ] Governance emergency/recovery procedures

## Phase 10 — Mainnet Consideration

A production mainnet can only be considered after successful long-lived public testing, reviewed external consensus/application/governance behavior, independent security review and a clear operational/economic/legal model.

## CRKBIT Status

**Production CRKBIT is not launched. No official presale. No production token contract.**

The research/public-testnet code uses test-only CRKBIT accounting with 8 decimals and a proposed 21,000,000 maximum genesis supply. Those parameters remain subject to technical, security, economic and applicable legal review before any production implementation.
