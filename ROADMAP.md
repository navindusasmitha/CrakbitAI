# Crakbit AI Roadmap

This roadmap describes intended development order. Dates are targets, not guarantees, and may change based on research, funding, testing and security findings.

## Guiding Principle

**Technology first. Security first. Tokens later.**

Crakbit AI remains primarily a defensive-security and secure-development project. Crakbit Chain is developed in parallel as a testable blockchain-security/infrastructure research platform. Production-mainnet consideration stays gated on long-running public testing, independently reviewed consensus/application behavior, wallet/network review, operational readiness, economic-security review and applicable legal/regulatory review.

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

### Foundation through v0.20

- [x] Native test-only CRKBIT accounting, Ed25519 wallets and signed transfers
- [x] Research consensus/network/recovery experiments
- [x] Deterministic external application boundary
- [x] CometBFT `v0.40.0` ABCI integration PoC
- [x] Crash-safe FinalizeBlock → Commit path
- [x] Browser wallet/public gateway/faucet/Mining Lab test tooling
- [x] Native ABCI state sync
- [x] Explorer reconciliation, soak/fault evidence tooling
- [x] Review freeze/remediation/reproducible-build/SBOM/provenance tooling
- [x] Versioned schema migration/rollback rehearsal

### v0.21 — deterministic validator governance

- [x] `crakbit-execution/3`
- [x] Validator join/remove/replace governance transactions
- [x] Strict `>2/3` current voting-power approval
- [x] Active/pending validator state committed into application hash
- [x] Deterministic ABCI validator updates
- [x] Governance-aware state sync and migration tests
- [ ] Independent multi-host activation evidence
- [ ] Independent review of activation-height semantics

### v0.22 — governed multi-node campaigns

- [x] Governed CometBFT local-lab generator
- [x] Cluster convergence/divergence monitoring
- [x] Governance history/update-emission export
- [x] H/H+1/H+2 campaign plans and signed evidence tooling
- [ ] Repeat equivalent campaigns across independently managed hosts

### v0.23 — public-testnet deployment / operations tooling

- [x] Public-only validator identity export
- [x] 4+ validator inventory + operator/provider/region diversity gates
- [x] Matching application + CometBFT genesis bundles
- [x] Non-secret per-validator deployment/systemd/persistent-peer bundles
- [x] Independent-node height/app-hash monitoring
- [x] JSONL soak collection + 24h readiness semantics
- [x] Signed public-testnet operations evidence
- [ ] Real independent-host deployment/evidence

## Phase 7 — Long-Lived Public Testnet / Independent Review Candidate

### v0.24 — operational fault / recovery hardening

- [x] Host preflight with package/CometBFT/genesis identity checks
- [x] Private bind/token-presence/disk checks
- [x] Typed restart/process-kill/partition/latency/packet-loss/load/storage fault plans
- [x] Mandatory recovery actions + dry-run default
- [x] Backup/restore and clean-host state-sync records
- [x] Redundant RPC/explorer consistency checks
- [x] Protected remote-signer/HSM-style evidence
- [x] Separate 24h / 72h / 7-day readiness gates
- [x] Signed operational evidence
- [ ] Execute modeled campaigns on real independent hosts

### v0.25 — independent-host evidence / initial review freeze

- [x] Package/CLI `0.25.0a1`
- [x] Incident-response records with high/critical escalation requirements
- [x] Signed per-operator host attestations
- [x] Exact source/package/CometBFT/genesis identity binding
- [x] 4+ unique operators/validators/evidence signers + provider/region diversity gates
- [x] v0.24 readiness + incident-drill dependency
- [x] Signed exact independent-review candidate freeze
- [x] Explicit independent-review scope
- [ ] Build freeze from real independent-host evidence

### v0.26 — independent-review remediation / re-freeze

- [x] Package/CLI `0.26.0a1`
- [x] Signed structured independent-review findings register
- [x] Stable `CRK-REV-...` finding IDs
- [x] Severity/component/title/affected-commit/reproduction metadata
- [x] Remediation commit/config/regression-test binding
- [x] Signed independent retest records
- [x] Require latest high/critical retest to pass on exact candidate commit
- [x] Hard re-freeze blocker for unresolved/un-retested high/critical findings
- [x] Signed supply-chain/reproducible-build attestation hook
- [x] Dependency-lock + SBOM hash binding
- [x] Signed public-edge TLS/WAF/DDoS/load/failover evidence without provider secrets
- [x] Require 2+ passing public-edge attestations
- [x] Candidate supersession rules for source/package/CometBFT/genesis/dependency/review-evidence changes
- [x] Signed post-remediation review re-freeze
- [x] v0.26 regression tests and documentation
- [ ] Import real independent-review findings
- [ ] Independently retest every real high/critical remediation on final candidate
- [ ] Produce re-freeze from real review/supply-chain/public-edge evidence

### v0.27 — final release policy / coordinated upgrade / economics freeze

- [ ] Add final mainnet-candidate gate consuming only real operational + review evidence
- [ ] Add coordinated multi-host protocol/schema upgrade proposal, activation and rollback evidence
- [ ] Add governance timelock/emergency/cancel research artifacts with conservative defaults
- [ ] Add final genesis/economics parameter-freeze format
- [ ] Add economic-security reviewer attestation hook
- [ ] Add multi-party/threshold release-approval evidence instead of a single release signer
- [ ] Add complete transitive dependency inventory + external reproducible-build attestation import
- [ ] Add final launch-readiness report that remains false unless operations, security review, economics and legal gates are explicitly satisfied

## Phase 8 — Independent Security Review

- [ ] Independent consensus/application/governance review
- [ ] Independent network/RPC review
- [ ] Independent browser-wallet review
- [ ] Cryptography/key-management review
- [ ] Economic-security review
- [ ] Incident-response review
- [ ] Applicable legal/regulatory review
- [ ] Remediate/retest every high/critical finding before production-value launch consideration

## Phase 9 — Release / Operations Hardening

- [ ] Independent reproducible build environment
- [ ] Complete transitive SBOM/supply-chain review
- [ ] Multi-edge DDoS/WAF/capacity testing
- [ ] Protected signing/recovery procedures
- [ ] Coordinated upgrade/rollback campaigns
- [ ] Governance emergency/recovery procedures

## Phase 10 — Mainnet Consideration

A production mainnet can only be considered after successful long-lived public testing, reviewed external consensus/application/governance behavior, independent security review, protected operations, and a clear economic/legal model.

## CRKBIT Status

**Production CRKBIT is not launched. No official presale. No production token contract.**

The research/public-testnet code uses test-only CRKBIT accounting with 8 decimals and a proposed 21,000,000 maximum genesis supply. Those parameters remain subject to technical, security, economic and applicable legal review before any production implementation.
