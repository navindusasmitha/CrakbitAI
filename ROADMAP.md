# Crakbit AI Roadmap

This roadmap describes the intended development order for Crakbit AI. Dates are targets, not guarantees, and may change based on research, funding, testing and security findings.

## Guiding Principle

**Technology first. Security first. Tokens later.**

The immediate product focus remains a useful defensive-security MVP. In parallel, the Crakbit Chain local research network has progressed through signed quorum finality, certified view changes and a v0.5 two-phase prevote/precommit prototype. Public testnet/mainnet work still depends on safer cross-round unlock behavior or a mature BFT core, authenticated networking, state recovery, adversarial testing and independent security review.

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

### Completed through v0.5

- [x] Native devnet CRKBIT accounting unit
- [x] 8-decimal atomic-unit model
- [x] Proposed 21,000,000 maximum genesis supply encoded for devnet
- [x] Ed25519 wallet/key generation and `crk1...` addresses
- [x] Signed transfers, nonces/replay protection and minimum fees
- [x] Signed block proposals
- [x] Previous-block hash linking
- [x] Transaction Merkle roots and deterministic state roots
- [x] SQLite chain/account persistence
- [x] Round-specific deterministic proposer schedule
- [x] Signed quorum-certified view changes
- [x] Later-round proposals require a >2/3 view-change certificate
- [x] Signed prevote phase
- [x] Signed precommit phase
- [x] >2/3 prevote certificate required before precommit
- [x] >2/3 precommit certificate required before finalization
- [x] Persistent same-phase anti-double-vote records
- [x] Persistent per-height conservative consensus lock
- [x] Persistent local consensus-round/view-change state
- [x] Persistent consensus event journal
- [x] Conflicting signed proposal/equivocation evidence persistence
- [x] Finalized-block broadcast and catch-up synchronization
- [x] REST/RPC endpoints and CLI key/balance/send tooling
- [x] Validator health/height/round telemetry
- [x] Development metrics and consensus-event endpoints
- [x] 4-validator Docker Compose devnet with default 3-of-4 quorum
- [x] Simple development explorer
- [x] Automated multiphase consensus/persistence/evidence tests and CI
- [x] v0.5 protocol specification and security notes

### v0.6 consensus/network/recovery hardening — next

- [ ] Define/review a proof-based cross-round unlock rule or migrate to a mature BFT core
- [ ] Authenticated validator identity handshake
- [ ] Encrypted validator transport / deployment TLS requirements
- [ ] Validator certificate/key rotation plan
- [ ] Peer discovery / bootnode design
- [ ] Stronger mempool and multi-nonce handling
- [ ] Signed state snapshots and verified fast state sync
- [ ] Restart/recovery and database-corruption testing
- [ ] Adversarial multi-validator and network-partition tests
- [ ] Validator key-management specification
- [ ] Prometheus-style metrics, dashboard and alerts
- [ ] Public-testnet deployment configuration and operator runbooks
- [ ] Faucet policy and abuse controls
- [ ] Economic/incentive design review
- [ ] External consensus/network review

### Current consensus warning

v0.5 adds a genuine two-phase prevote/precommit research pipeline and durable local locks, but it is still **not** a complete production BFT protocol. The lock has no mature proof-based unlock rule, validator transport remains unauthenticated HTTP, and no formal safety/liveness proof or independent audit exists.

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
