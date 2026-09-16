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
- [x] Round-specific proposer schedule and quorum-certified view changes
- [x] Signed prevote/precommit phases with >2/3 certificates
- [x] Persistent anti-double-vote records, locks, event journal and equivocation evidence
- [x] Authenticated validator requests, challenge/response and durable replay protection
- [x] Quorum snapshots, resumable state transfer and safe snapshot bootstrap
- [x] Local integrity verification and verified backup/restore drills
- [x] Prometheus/Grafana development observability and alerts
- [x] Bounded RPC, transaction, mempool and block resource controls
- [x] Public-testnet deployment/operator scaffold
- [x] Automated blockchain CI

### v0.11 — validator transport hardening

- [x] Record consensus architecture decision: do not treat the bespoke Python consensus as a production BFT path
- [x] Set reviewed external BFT migration/evaluation as a release gate
- [x] Operator-managed validator mTLS, CA/hostname validation and certificate pinning
- [x] Inbound mutual-TLS launcher
- [x] Certificate fingerprint helper and dual-key/transport incident runbook
- [x] Toxiproxy transport-fault harness
- [x] Public-testnet reverse-proxy hardening example

### v0.12 — archive, recovery and testnet hardening

- [x] Genesis-anchored full-history archive export/verify/import
- [x] Snapshot-node historical backfill without current-state mutation
- [x] Consensus/execution boundary groundwork
- [x] Dual TLS certificate-pin overlap during rotation
- [x] Optional bearer authentication for operator endpoints
- [x] Duplicate/conflicting/forged validator-vote fixtures
- [x] Multi-node soak/divergence tooling
- [x] Deny-by-default nftables public-testnet example

### v0.13 — external-consensus preparation and public-testnet tooling

- [x] Deterministic `crakbit-execution/1` preview/process boundary
- [x] Deterministic application hash independent from consensus-local metadata
- [x] Authenticated loopback execution-service PoC
- [x] Signed release/genesis manifest tooling
- [x] Non-secret independent-host provisioning scaffolds
- [x] Strictly test-only faucet foundation
- [x] Bounded read-only explorer APIs
- [x] Reproducible soak summary generation
- [x] External BFT evaluation criteria and external-review package checklist

### v0.14 — external BFT bridge + crash-safe application commit

- [x] Pin CometBFT `v0.40.0` for the integration PoC
- [x] Add Go ABCI bridge module
- [x] Implement ABCI `Info`, `CheckTx`, `PrepareProposal`, `ProcessProposal`, `FinalizeBlock`, `Commit` and minimal query support
- [x] Add versioned mutating `crakbit-execution/2` protocol
- [x] Add deterministic application hash bound to external consensus block hash
- [x] Add dedicated external application database isolation checks
- [x] Persist FinalizeBlock stage without mutating committed application state
- [x] Atomically apply staged Commit in SQLite
- [x] Persist external commit records and pending-finalize recovery state
- [x] Accept identical app-ahead FinalizeBlock replay and reject conflicting replay
- [x] Add authenticated v0.14 execution service
- [x] Add signed strict >2/3 genesis ceremony/validator attestations
- [x] Add external-consensus and ceremony CLI tooling
- [x] Add local CometBFT PoC runbook
- [x] Extend CI to test Python and Go bridge code

### v0.15 — repeatable external-BFT test network

- [ ] Add one-command local four-node CometBFT lab generation
- [ ] Generate/verify CometBFT consensus genesis and peer inventory separately from Crakbit application genesis
- [ ] Add exhaustive crash-point replay matrix around FinalizeBlock/Commit
- [ ] Add external-consensus snapshot/state-sync adapter work
- [ ] Add dedicated indexed explorer database for external-consensus history
- [ ] Make faucet cooldown/distribution accounting persistent across restart
- [ ] Add multi-host deployment inventory and automated health checks
- [ ] Automate partition, latency, restart and sustained-load campaigns against the CometBFT path
- [ ] Publish signed testnet release + application-genesis ceremony + soak/fault evidence bundle
- [ ] Add production-oriented validator key/remote-signer/HSM evaluation
- [ ] Prepare first independent consensus/network/application review handoff

### Current consensus/network warning

v0.14 provides a real ABCI bridge and crash-safe external application commit PoC, but it is still **not a production mainnet**. The older Python consensus remains research-only, the CometBFT path has not yet completed a sustained independent-host public testnet campaign, full state sync and production key operations are incomplete, and no independent consensus/network/security audit has been completed.

## Phase 7 — Public Testnet
**Only after Phase 6 security gates are met**

- [ ] Public external-BFT node software release
- [x] Signed application-genesis ceremony foundation
- [x] Signed release-manifest foundation
- [ ] CometBFT consensus-genesis ceremony/process
- [ ] Public indexed testnet explorer
- [ ] Testnet wallet support
- [x] Test-only faucet implementation foundation
- [x] Public node/operator documentation foundation
- [x] Network monitoring/soak tooling foundation
- [ ] Multi-host public deployment
- [ ] Stress/partition/restart testing with published evidence
- [ ] Community test program

Any CRKBIT units used on testnet are test-only and should have no represented production value.

## Phase 8 — Security Review

Before any production network launch:

- [ ] Internal security review
- [ ] Independent code/security audit
- [ ] External-consensus replay/failure testing
- [ ] Network partition/fault testing
- [ ] Economic-security review
- [ ] Cryptography/key-management review
- [ ] Incident-response planning
- [ ] Legal/regulatory review where applicable

## Phase 9 — Mainnet Consideration

A production mainnet should only be considered after successful long-lived public testing, independently reviewed consensus, external security review and a clear operational/economic model.

Potential items:

- Final consensus mechanism/version
- Genesis process
- Production explorer
- Production wallet ecosystem
- Validator onboarding and remote-signer/key-custody model
- CRKBIT utility implementation
- Developer/network services
- Upgrade/governance process

## CRKBIT Status

**Production CRKBIT is not launched. No official presale. No production token contract.**

The research/devnet implements test-only CRKBIT accounting with a proposed maximum genesis supply of 21,000,000 and 8 decimals. Those parameters remain subject to technical, security, economic and legal review before any production implementation.

## Roadmap Updates

Major roadmap changes should be documented in repository commits and project updates so supporters and contributors can distinguish completed prototypes, public testnets and production systems.
