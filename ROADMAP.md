# Crakbit AI Roadmap

This roadmap describes the intended development order for Crakbit AI. Dates are targets, not guarantees, and may change based on research, funding, testing and security findings.

## Guiding Principle

**Technology first. Security first. Tokens later.**

The immediate product focus remains a useful defensive-security MVP. In parallel, Crakbit Chain is being used as a research network to turn blockchain, validator-security, recovery and external-consensus integration ideas into testable code. Production mainnet planning remains gated on reviewed consensus, long-running public testing and independent security review.

## Phase 1 — Foundation
**Target: Q3–Q4 2026**

- [x] Establish Crakbit AI project identity
- [x] Launch public website
- [x] Create public GitHub repository
- [x] Publish initial roadmap and project documentation
- [x] Publish initial technical architecture
- [x] Publish initial security model
- [x] Establish public Giveth project listing
- [ ] Establish consistent public development/update cadence
- [ ] Launch/complete official project social and community channels
- [ ] Link final public fundraising URL throughout website/repository

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

### MVP success criteria

A developer should be able to submit or scan a small codebase and receive a clear, defensible report describing potential security issues and remediation guidance.

## Phase 3 — Developer Tooling
**Target: Q1 2027**

- [x] `crak` CLI early alpha
- [ ] Developer API alpha
- [x] JSON output
- [ ] SARIF-style output exploration
- [ ] Repository scan workflow
- [ ] CI/CD integration prototype
- [ ] Authentication and rate-limiting design
- [ ] Expanded documentation and examples

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
- [ ] Open-source rule contribution framework

## Phase 6 — Crakbit Chain Research & Devnet
**Prototype started September 2026**

A runnable research/devnet exists to turn network ideas into testable code. This does **not** mean a production blockchain or public-value CRKBIT asset has launched.

### Completed research/devnet foundation through v0.10

- [x] Native test-only CRKBIT accounting unit
- [x] Ed25519 wallet/key generation and `crk1...` addresses
- [x] Signed transfers, nonces/replay protection and minimum fees
- [x] Signed block proposals, previous-hash linking, Merkle roots and deterministic state roots
- [x] SQLite chain/account/consensus persistence
- [x] Round-specific deterministic proposer schedule
- [x] Signed quorum-certified view changes
- [x] Signed prevote + precommit phases with >2/3 certificates
- [x] Persistent anti-double-vote records and conservative per-height lock
- [x] Consensus event journal and equivocation evidence
- [x] Ed25519-authenticated validator internal requests
- [x] Signed validator challenge/response identity handshake
- [x] Durable validator request replay protection
- [x] Signed state snapshots and >2/3 quorum snapshot certificates
- [x] Resumable verified chunked snapshot transfer
- [x] Safe snapshot import/bootstrap for fresh node databases
- [x] Snapshot-base-aware history semantics
- [x] Local integrity verification and verified backups/restore drills
- [x] Prometheus/Grafana development observability and alerts
- [x] Bounded RPC, transaction, mempool and block resource controls
- [x] Public-testnet deployment/operator scaffold
- [x] Automated blockchain CI

### v0.11 — validator transport hardening

- [x] Record consensus architecture decision: do not treat the bespoke Python consensus as a production BFT path
- [x] Set reviewed/established BFT core migration evaluation as a release gate
- [x] Operator-managed outbound validator mTLS trust configuration
- [x] Dedicated inbound mutual-TLS validator launcher
- [x] Validator-address → TLS leaf certificate SHA-256 pin enforcement
- [x] `/transport/status`
- [x] Certificate fingerprint helper
- [x] Repeatable Toxiproxy latency/timeout/reachability fault harness
- [x] Validator TLS/consensus-key rotation and incident-response runbook
- [x] Public-testnet reverse-proxy hardening example

### v0.12 — archive, recovery and testnet hardening

- [x] Genesis-anchored full-history archive export
- [x] Full archive verification by replaying proposer signatures, quorum certificates, transactions, balances, nonces, state roots and hash continuity
- [x] Snapshot-node pre-snapshot history backfill without mutating current state
- [x] `archive-export`, `archive-verify` and `archive-import` CLI commands
- [x] `/archive/status` and history-status integration
- [x] Consensus/execution boundary groundwork for future reviewed-BFT integration
- [x] Dual certificate-pin overlap for coordinated TLS certificate rotation
- [x] Optional bearer authentication for monitoring/operator endpoints
- [x] Explicit duplicate/conflicting/forged validator-vote adversarial fixtures
- [x] Repeatable multi-node soak/divergence monitor
- [x] Deny-by-default nftables public-testnet example
- [x] Expanded public-testnet operator guidance

### v0.13 — large external-consensus and public-testnet tooling phase

- [x] Versioned deterministic `crakbit-execution/1` process/application boundary
- [x] Deterministic application hash independent from consensus-local state
- [x] Transaction validation and ordered batch preview without state mutation
- [x] Authenticated loopback external execution-service PoC
- [x] Protocol compatibility/non-mutation tests
- [x] Signed genesis/release artifact generation and verification
- [x] Release manifest binding to genesis fingerprint, exact genesis hash and artifact hashes
- [x] Dedicated release-signer identity verification
- [x] Non-secret validator provisioning automation for multiple independent hosts
- [x] Strictly test-only faucet with amount, cooldown and global request limits
- [x] Validator-consensus-key rejection in faucet configuration
- [x] Bounded read-only explorer summary/block/address APIs
- [x] Reproducible soak JSONL summary generation
- [x] External BFT integration evaluation criteria
- [x] External consensus/network/security review package checklist
- [x] `release-build`, `release-verify`, `protocol-status`, `protocol-preview` CLI tooling
- [x] v0.13 automated tests and GitHub Actions pass
- [ ] Run sustained independent-host partition/latency/load/soak campaigns
- [ ] Publish real multi-host test results and incident logs
- [ ] Integrate an independently reviewed external BFT core

### v0.14 — real external-BFT integration test network

- [ ] Select and pin an established independently reviewed BFT implementation/version
- [ ] Define authenticated versioned finalize/commit protocol
- [ ] Persist deterministic application hashes at commit boundaries
- [ ] Make duplicate finalize/commit requests idempotent and crash-safe
- [ ] Add external-consensus replay/recovery and process-crash tests
- [ ] Add signed testnet release-bundle and genesis-ceremony workflow
- [ ] Deploy validators on multiple independent hosts using generated operator bundles
- [ ] Automate partition, latency, restart and sustained-load campaigns
- [ ] Publish soak/fault summaries and incident logs
- [ ] Add dedicated indexed explorer backend
- [ ] Harden faucet with upstream abuse controls and persistent distribution limits
- [ ] Prepare first external consensus/network/security review candidate

### Current consensus/network warning

v0.13 improves deterministic execution boundaries, release verification and testnet operations, but it is still **not** a production BFT or production P2P implementation. The current Python consensus is research-only and is not the intended production mainnet path. No independently reviewed external BFT engine has been integrated and no independent security audit has been completed.

## Phase 7 — Public Testnet
**Only after Phase 6 security gates are met**

- [ ] Public node software release
- [ ] Signed testnet genesis/release process
- [ ] Public testnet explorer
- [ ] Testnet wallet support
- [x] Test-only faucet implementation foundation
- [x] Public node/operator documentation foundation
- [x] Network monitoring/soak tooling foundation
- [ ] Multi-host public deployment
- [ ] Stress/partition testing with published evidence
- [ ] Community test program

Any CRKBIT units used on testnet are test-only and should have no represented production value.

## Phase 8 — Security Review

Before any production network launch:

- [ ] Internal security review
- [ ] Independent code/security audit
- [ ] Consensus-failure testing
- [ ] Network partition/fault testing
- [ ] Economic-security review
- [ ] Cryptography/key-management review
- [ ] Incident-response planning
- [ ] Legal/regulatory review where applicable

## Phase 9 — Mainnet Consideration

A production mainnet should only be considered after successful long-lived public testing, independently reviewed consensus, external security review and a clear operational/economic model.

Potential items:

- Final consensus mechanism
- Genesis process
- Production explorer
- Production wallet ecosystem
- Validator onboarding
- CRKBIT utility implementation
- Developer/network services
- Upgrade/governance process

## CRKBIT Status

**Production CRKBIT is not launched. No official presale. No production token contract.**

The research/devnet implements test-only CRKBIT accounting with a proposed maximum genesis supply of 21,000,000 and 8 decimals. Those parameters remain subject to technical, security, economic and legal review before any production implementation.

## Roadmap Updates

Major roadmap changes should be documented in repository commits and project updates so supporters and contributors can distinguish completed prototypes, public testnets and production systems.
