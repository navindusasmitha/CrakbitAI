# Crakbit AI Roadmap

This roadmap describes intended development order. Dates are targets, not guarantees, and may change based on research, funding, testing and security findings.

## Guiding Principle

**Technology first. Security first. Tokens later.**

Crakbit AI remains primarily a defensive-security and secure-development project. Crakbit Chain is developed in parallel as a testable blockchain-security/infrastructure research platform. Production-mainnet consideration stays gated on long-running public testing, independently reviewed consensus/application behavior, wallet/network review, protected operations, economic-security review and applicable legal/regulatory review.

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
- [x] Native test-only CRKBIT accounting, Ed25519 wallets and signed transfers
- [x] CometBFT `v0.40.0` ABCI integration PoC
- [x] Crash-safe FinalizeBlock → Commit path
- [x] Native ABCI state sync
- [x] Browser wallet/public gateway/explorer/faucet/test-only Mining Lab
- [x] Validator join/remove/replace governance with strict `>2/3` approval
- [x] Versioned schema migration/rollback rehearsal
- [x] Reproducible-build/SBOM/release evidence tooling
- [x] v0.23 validator inventory/genesis/deployment/monitoring tooling

## Phase 7 — Review / Candidate Policy

### v0.24–v0.26
- [x] Operational preflight/fault/recovery/redundancy/signer evidence
- [x] 24h / 72h / 7-day readiness semantics
- [x] Signed operator evidence and exact review freezes
- [x] Findings/remediation/retest gates
- [x] Supply-chain/public-edge evidence hooks

### v0.27 — final mainnet-candidate policy
- [x] Package/CLI `0.27.0a1`
- [x] Coordinated upgrade + rollback policy
- [x] Strict `>2/3` validator readiness
- [x] Governance timelocks/cancellation/emergency policy
- [x] Economics/genesis freeze format
- [x] Economic-security + legal/regulatory review hooks
- [x] Deterministic candidate identity
- [x] Minimum three unique release approvers/signers
- [x] Final candidate evidence gate + signed report

## Phase 8 — Launch Rehearsal

### v0.28
- [x] Package/CLI `0.28.0a1`
- [x] Signed launch runbook
- [x] DNS/RPC/explorer cutover rehearsal
- [x] Public-edge SLO/capacity/failover evidence
- [x] Protected signer rotation/recovery drill
- [x] Coordinated upgrade/rollback rehearsal
- [x] Final risk register
- [x] Independent technical reviewer sign-off format
- [x] External reproducible-build/transitive-dependency attestation
- [x] Aggregate rehearsal gate + exact release freeze
- [x] Manual `hold` / `approve-launch-window` record with no automatic launch

## Phase 9 — Real Independent-Host Execution

### v0.29 — live host / cluster / genesis / soak / fault evidence
- [x] Package/CLI `0.29.0a1`
- [x] Live CometBFT `/status` + `/abci_info` probing
- [x] Signed per-validator live observations
- [x] Exact source/candidate/application-genesis/consensus-genesis binding
- [x] Reject RPC evidence URLs containing embedded credentials
- [x] 4+ unique validator/operator/evidence-signer cluster gate
- [x] Provider + region diversity gate
- [x] Height spread + observation-window bounds
- [x] Same-height application-hash divergence detection
- [x] Signed multi-operator genesis attestations + ceremony gate
- [x] Signed soak evidence with >=0.99 configured success ratio
- [x] Default seven-day candidate soak target
- [x] Signed raw-evidence-bound fault/recovery results
- [x] Require restart/process-kill/partition/latency/packet-loss/load/storage/state-sync/governance/upgrade coverage
- [x] Bind real-execution gate to exact v0.28 release freeze + rehearsal gate
- [x] Signed v0.29 real-evidence freeze
- [x] v0.29 regression tests + docs

### v0.29 real external execution still required
- [ ] Provision 4+ truly independent validator hosts
- [ ] Run live observations from real authorized operator infrastructure
- [ ] Perform genuine multi-operator genesis ceremony with separately held validator keys
- [ ] Complete continuous 24h → 72h → 7-day or longer campaign
- [ ] Execute authorized real fault/load/storage/state-sync/governance/upgrade campaigns
- [ ] Deploy and inspect protected HSM/remote-signer custody
- [ ] Operate redundant public RPC/explorer/gateway edges
- [ ] Complete genuine independent technical/security review and remediation/retest
- [ ] Import external reproducible-build/transitive dependency evidence
- [ ] Finalize production economics/incentives and applicable legal/regulatory position

### v0.30 — next target: operator automation / evidence retention / publication
- [ ] Non-secret multi-host deployment inventory/Ansible generation
- [ ] Continuous resumable signed cluster-observation collector
- [ ] Seven-day evidence rotation/checkpoint/resume support
- [ ] Raw log/archive bundle hashing + retention manifest
- [ ] Active redundant RPC/explorer health/failover collector
- [ ] Remote-signer connectivity/rotation status checks without private-key access
- [ ] Public release-candidate evidence bundle with hashes/SBOM/genesis/review summaries/runbooks
- [ ] Final operator launch checklist that still requires explicit human execution

## Phase 10 — Mainnet Consideration

A production mainnet can only be considered after successful long-lived real-host testing, reviewed external consensus/application/governance behavior, protected operations, independent security/economic/legal review, final economics and an explicit human launch decision.

A passing software evidence gate must never automatically launch the network.

## CRKBIT Status

**Production CRKBIT is not launched. No official presale. No production token contract.**

The research/public-testnet code uses test-only CRKBIT accounting. The 21,000,000 maximum-supply and 8-decimal values remain development proposals unless intentionally frozen and independently reviewed through the v0.27 economics process.
