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
- [x] v0.23 4+ validator inventory/genesis/deployment/monitoring tooling
- [ ] Real independent-host public testnet operation

## Phase 7 — Long-Lived Public Testnet / Independent Review Candidate

### v0.24 — operational hardening
- [x] Host preflight + exact package/CometBFT/genesis identity checks
- [x] Typed restart/process-kill/partition/latency/packet-loss/load/storage plans
- [x] Backup/restore + clean-host state-sync records
- [x] Redundant RPC/explorer consistency checks
- [x] Protected remote-signer/HSM-style evidence
- [x] 24h / 72h / 7-day readiness gates
- [ ] Execute modeled campaigns on real independent hosts

### v0.25 — independent-host evidence / initial review freeze
- [x] Signed operator host attestations and incident-response records
- [x] 4+ unique operators/validators/signers + provider/region diversity gates
- [x] Signed exact review candidate freeze
- [ ] Build freeze from real independent-host evidence

### v0.26 — independent-review remediation / re-freeze
- [x] Signed structured findings register + stable IDs
- [x] Remediation commit/config/regression-test binding
- [x] Signed independent retest records
- [x] Hard blocker for unresolved/un-retested high/critical findings
- [x] Supply-chain/reproducible-build attestation hook
- [x] Public-edge TLS/WAF/DDoS/load/failover evidence
- [x] Candidate supersession + signed post-remediation re-freeze
- [ ] Import real independent-review findings and retest final fixes

### v0.27 — final mainnet-candidate policy / economics / release approval
- [x] Package/CLI `0.27.0a1`
- [x] Signed coordinated upgrade proposal with activation + rollback evidence binding
- [x] Strict `>2/3` validator-readiness requirement
- [x] Conservative governance normal/emergency timelock policy
- [x] Pre-activation cancellation window + strict-supermajority emergency approval
- [x] Economics/genesis parameter-freeze format
- [x] Explicit no-return-promise / no-token-sale-authorization claims
- [x] Economic-security and legal/regulatory reviewer attestation hooks
- [x] Exact reviewer binding to candidate source + economics freeze
- [x] Deterministic final candidate identity hash
- [x] Minimum three unique release approvers/signers
- [x] Final candidate evidence gate + signed final report
- [ ] Build final gate from real independently corroborated evidence

## Phase 8 — Launch Rehearsal / Corroborated Evidence

### v0.28 — launch rehearsal and final release-candidate freeze tooling

- [x] Package/CLI `0.28.0a1`
- [x] Signed 4+ validator launch runbook with genesis ceremony/start order/rollback
- [x] Dry-run-only / no automatic DNS, network mutation or fund movement boundary
- [x] Signed DNS/RPC/explorer cutover rehearsal
- [x] Require redundant RPC/explorer failover + rollback verification
- [x] Configurable public-edge availability/latency/error/capacity/failover evidence
- [x] Protected HSM/remote-signer rotation + catastrophic recovery drill evidence
- [x] Coordinated upgrade + rollback rehearsal bound to v0.27 upgrade plan
- [x] Final signed unresolved-risk register
- [x] Unmitigated high/critical risk blocks the modeled release gate
- [x] Independent technical reviewer sign-offs bound to exact v0.27 final report
- [x] Required technical scopes: consensus/application, network/RPC, cryptography/key-management, browser-wallet
- [x] External reproducible-build/transitive-dependency attestation format
- [x] Aggregate v0.28 launch-rehearsal gate
- [x] Signed exact release-candidate freeze after the gate passes
- [x] Signed human `hold` / `approve-launch-window` record with no automatic execution
- [x] v0.28 regression tests and documentation

### v0.28 external execution still required

- [ ] Run 4+ independently managed validators continuously on real hosts
- [ ] Perform real multi-operator genesis ceremony with separately held keys
- [ ] Complete genuine 24h → 72h → 7-day or longer soak windows
- [ ] Execute real fault/load/storage/state-sync/governance campaigns
- [ ] Deploy and drill protected remote signer/HSM-equivalent custody
- [ ] Run real multi-edge SLO/capacity/outage/failover tests
- [ ] Execute coordinated upgrade + rollback rehearsal on independent hosts
- [ ] Execute DNS/RPC/explorer cutover rehearsal without production launch
- [ ] Complete genuine independent technical review and import real sign-offs/findings/retests
- [ ] Import external reproducible-build/transitive supply-chain evidence
- [ ] Freeze the final release candidate only from real corroborated evidence
- [ ] Keep actual production launch as an explicit human launch/no-launch decision

## Phase 9 — Real Independent-Host Execution (v0.29 target)

The next useful phase is operational rather than another self-attestation-only layer:

- [ ] Provision 4+ independent VPS validators
- [ ] Keep execution/ABCI/signer/operator surfaces private
- [ ] Generate and verify real genesis ceremony evidence
- [ ] Start continuous monitoring and 24h/72h/7d evidence collection
- [ ] Run authorized fault/recovery/state-sync/governance/upgrade campaigns
- [ ] Deploy protected key custody
- [ ] Deploy redundant public edges and collect real v0.28 SLO/cutover evidence
- [ ] Commission independent technical/security review
- [ ] Produce final release freeze from real evidence

## Phase 10 — Mainnet Consideration

A production mainnet can only be considered after successful long-lived public testing, reviewed external consensus/application/governance behavior, protected operations, independent security/economic/legal review, final economics and an explicit human launch decision.

A passing software evidence gate must never automatically launch the network.

## CRKBIT Status

**Production CRKBIT is not launched. No official presale. No production token contract.**

The research/public-testnet code uses test-only CRKBIT accounting. The 21,000,000 maximum-supply and 8-decimal values remain development proposals unless intentionally frozen and independently reviewed through the v0.27 economics process.
