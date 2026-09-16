# Crakbit AI Roadmap

This roadmap describes the intended development order for Crakbit AI. Dates are targets, not guarantees, and may change based on research, funding, testing and security findings.

## Guiding Principle

**Technology first. Security first. Tokens later.**

The immediate product focus remains a useful defensive-security MVP. In parallel, the Crakbit Chain local research network has progressed through signed quorum finality, certified view changes, a two-phase prevote/precommit pipeline, authenticated validator requests, durable replay protection, quorum-certified snapshots and v0.8 chunked/resumable snapshot recovery. Public testnet/mainnet work still depends on a mature BFT lock/unlock design, mutually authenticated encrypted validator transport, adversarial testing and independent security review.

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

## Phase 6 — Crakbit Chain Research & Local Devnet
**Prototype started September 2026**

A runnable local devnet exists to turn network research into testable code. This does **not** mean a production blockchain or public-value CRKBIT asset has launched.

### Completed through v0.8

- [x] Native devnet CRKBIT accounting unit
- [x] 8-decimal atomic-unit model
- [x] Proposed 21,000,000 maximum genesis supply encoded for devnet
- [x] Ed25519 wallet/key generation and `crk1...` addresses
- [x] Signed transfers, nonces/replay protection and minimum fees
- [x] Signed block proposals
- [x] Previous-block hash linking
- [x] Transaction Merkle roots and deterministic state roots
- [x] SQLite chain/account/consensus persistence
- [x] Round-specific deterministic proposer schedule
- [x] Signed quorum-certified view changes
- [x] Signed prevote + precommit phases
- [x] >2/3 prevote and precommit certificates before finalization
- [x] Persistent anti-double-vote records and conservative per-height lock
- [x] Persistent consensus event journal and equivocation evidence
- [x] Ed25519-authenticated validator internal requests
- [x] Signed validator challenge/response identity handshake
- [x] Durable SQLite-backed validator request replay protection
- [x] Optional HTTPS peer-URL enforcement mode
- [x] Signed state snapshot generation and verification
- [x] >2/3 quorum snapshot certificates over identical state
- [x] Safe snapshot import/bootstrap for fresh node databases
- [x] Snapshot recovery metadata and recovery-status endpoint
- [x] Bounded chunked snapshot transfer manifest
- [x] Per-chunk + complete artifact hash validation
- [x] Resumable verified chunk cache in `snapshot-fetch-chunked`
- [x] Crash-visible snapshot import sidecar journal
- [x] Snapshot-base-aware history status/block API
- [x] Prometheus-style development metrics endpoint
- [x] Finalized-block broadcast and catch-up synchronization
- [x] REST/RPC endpoints and CLI key/balance/send/recovery tooling
- [x] Validator health/height/round telemetry
- [x] 4-validator Docker Compose devnet with default 3-of-4 quorum
- [x] Simple development explorer
- [x] Automated consensus/peer-authentication/snapshot/recovery tests and CI
- [x] v0.8 recovery-hardening documentation

### v0.9 consensus/network/public-testnet hardening — next

- [ ] Review/replace the conservative cross-round lock with mature proof-based BFT lock/unlock, or migrate to a reviewed BFT core
- [ ] Add mutually authenticated encrypted validator transport
- [ ] Add certificate pinning and validator certificate/key rotation lifecycle
- [ ] Add archive/history synchronization design for snapshot-bootstrapped nodes
- [ ] Add database corruption, abrupt-power-loss and crash/restart recovery testing
- [ ] Add long-running partition, latency, Byzantine-behavior and load tests
- [ ] Add validator key-management and incident-response specification
- [ ] Add Grafana dashboards and alert rules
- [ ] Add public-testnet deployment configuration and operator runbooks
- [ ] Add faucet policy and abuse controls
- [ ] Add stronger explorer/wallet testnet UX
- [ ] Add economic/incentive design review
- [ ] Commission external consensus/network review

### Current consensus/network warning

v0.8 materially improves authenticated recovery and state-transfer operations, but it is still **not** a production BFT or production P2P implementation. The consensus lock has no mature proof-based unlock rule, HTTPS enforcement is not a reviewed mTLS/certificate lifecycle, snapshot bootstrap does not reconstruct pre-snapshot historical block bodies, and no formal safety/liveness proof or independent audit exists.

## Phase 7 — Public Testnet
**Only after Phase 6 security gates are met**

- [ ] Public node software release
- [ ] Testnet genesis ceremony/process
- [ ] Public testnet explorer
- [ ] Testnet wallet support
- [ ] Faucet
- [ ] Public node/operator documentation
- [ ] Network monitoring
- [ ] Stress testing
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

A production mainnet should only be considered after successful long-lived public testing, independent security review and a clear operational/economic model.

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

The local development network implements test-only CRKBIT accounting with a proposed maximum genesis supply of 21,000,000 and 8 decimals. Those devnet parameters remain subject to technical, security, economic and legal review before any production implementation.

## Roadmap Updates

Major roadmap changes should be documented in repository commits and project updates so supporters and contributors can distinguish completed work from prototypes, public testnets and production systems.
