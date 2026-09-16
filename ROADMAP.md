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

- [x] Package/CLI `0.21.0a1`
- [x] `crakbit-execution/3` governed application path
- [x] Canonical validator join/remove/replace governance transaction format
- [x] Strict `>2/3` current voting-power approval rule
- [x] Replicated active and pending validator lifecycle state
- [x] Validator-governance state in deterministic application hash
- [x] ABCI validator updates derived from validated replicated input
- [x] Crash/replay-safe validator-update emission records
- [x] Modeled application-side validator activation at `H+2`
- [x] Schema 21 and v20 → v21 offline-copy migration/rollback rehearsal
- [x] Governance-aware external snapshots and native ABCI state sync
- [x] Multi-operator governance request build/sign/verify CLI
- [x] Python + Go governance/migration/state-sync tests
- [ ] Independent multi-host join/remove/replace execution evidence
- [ ] Independent review of update-height/activation semantics
- [ ] Protected remote/HSM governance-signing drill

### v0.22 — governed multi-node campaigns / evidence tooling

- [x] Package/CLI `0.22.0a1`
- [x] One-command governed CometBFT local lab generator
- [x] Align generated application-genesis validator identities with disposable CometBFT lab validator identities
- [x] Generate explicit disposable local-lab treasury/governance signing material under `.secrets`
- [x] Generate governed operator inventory with RPC/execution endpoints
- [x] Cluster reachability/height/application-hash/governance convergence monitor
- [x] Detect same-height application-hash divergence
- [x] Detect same-height validator-set/pending-governance divergence
- [x] Governance history + validator-update emission export for explorer/review use
- [x] Explicit `H`, `H+1`, `H+2` validator-governance campaign plan format
- [x] Signed campaign evidence tied to exact source commit, genesis and artifact hashes
- [x] Guarded normal-CometBFT governance broadcast helper
- [x] v0.22 regression tests
- [ ] Actually execute join/remove/replace campaigns on the generated four-node lab
- [ ] Execute restart/process-kill tests at `H`, `H+1`, and `H+2`
- [ ] Execute partition/latency tests across a pending validator activation
- [ ] Execute clean-node native state sync while governance state is pending
- [ ] Execute coordinated schema/protocol upgrade activation across all validators
- [ ] Repeat the campaign across independently managed VPS/providers
- [ ] Review governance-key/consensus-key separation and remote-signer design
- [ ] Research timelock/emergency/cancel semantics before any production consideration

### v0.23 — public-testnet deployment / operations tooling

- [x] Package/CLI `0.23.0a1`
- [x] Public-only validator identity export from each operator host
- [x] Reject secret/private fields from shared validator metadata
- [x] 4+ validator public-testnet inventory format
- [x] Independent-operator/provider/region diversity gates
- [x] Shared application + CometBFT genesis bundle generation
- [x] SHA-256 genesis manifest without private material
- [x] Per-validator non-secret deployment bundles
- [x] systemd service templates and persistent-peer artifacts
- [x] Independent-node `/status` + `/abci_info` monitoring
- [x] Same-height application-hash divergence detection
- [x] JSONL long-running soak collection + summary
- [x] Minimum 24-hour soak gate semantics
- [x] Public-testnet readiness report distinct from production-mainnet readiness
- [x] Signed operations evidence tied to exact Git commit and artifact hashes
- [x] v0.23 regression tests/documentation
- [ ] Provision four or more independently managed VPS validators
- [ ] Perform real multi-operator genesis ceremony
- [ ] Run actual 24-hour soak on independent hosts
- [ ] Extend actual soak to 72 hours and then 7 days
- [ ] Execute real independent-host validator governance campaigns
- [ ] Execute real clean-host state-sync/disaster-recovery drills
- [ ] Execute partition/latency/packet-loss/process-kill/storage/load campaigns

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

### v0.24 — operational fault / recovery hardening

- [ ] Add operator-safe host/deployment preflight validation
- [ ] Add automated backup/restore and clean-host state-sync drill runner
- [ ] Add signed restart/partition/latency/packet-loss/load/storage-fault campaign records
- [ ] Run validator-governance campaigns across real independent hosts
- [ ] Add public RPC/explorer redundancy and recovery verification
- [ ] Add alert/incident evidence and operator escalation records
- [ ] Enforce 72-hour and 7-day readiness gates
- [ ] Deploy/drill protected validator remote signer/HSM-equivalent custody
- [ ] Produce frozen independent-review package only after real evidence exists

### Operational launch tasks

- [ ] Provision four or more independently managed VPS validators
- [ ] Deploy governed execution/ABCI path with private execution/validator surfaces
- [ ] Deploy separate public RPC/gateway/explorer/faucet edge
- [ ] Configure DNS/TLS/firewall/monitoring/alerts/backups
- [ ] Run 24-hour soak and publish evidence
- [ ] Extend to 72-hour soak
- [ ] Extend to 7-day soak
- [ ] Execute validator-governance activation campaigns
- [ ] Execute clean-host state-sync/bootstrap recovery drills
- [ ] Execute partition/load/restart campaigns
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
- [ ] Remediate or explicitly accept every high/critical finding before launch

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
