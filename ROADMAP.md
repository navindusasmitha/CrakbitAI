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

A runnable research/devnet exists. It does **not** mean a production blockchain or production-value CRKBIT asset has launched.

### Completed foundation through v0.10

- [x] Native test-only CRKBIT accounting
- [x] Ed25519 wallets and `crk1...` addresses
- [x] Signed transfers, nonce/replay protection and fees
- [x] Signed block proposals, Merkle/state roots and SQLite persistence
- [x] Research prevote/precommit + certified view changes
- [x] Persistent anti-double-vote/lock/event/evidence state
- [x] Authenticated validator requests and durable replay protection
- [x] Quorum snapshots, resumable transfer and state bootstrap
- [x] Integrity verification, backups and restore drills
- [x] RPC/mempool/block resource bounds
- [x] Prometheus/Grafana development observability
- [x] Public-testnet operator scaffold

### v0.11 — validator transport hardening

- [x] Record architecture decision not to market bespoke Python consensus as production BFT
- [x] Make independently reviewed external BFT evaluation a release gate
- [x] Operator-managed mTLS trust configuration
- [x] Inbound mutual-TLS launcher
- [x] TLS certificate pinning and rotation runbook
- [x] Toxiproxy fault harness
- [x] Public-testnet reverse-proxy example

### v0.12 — archive/recovery/testnet hardening

- [x] Genesis-anchored full-history archive export/verify/import
- [x] Snapshot-node history backfill without mutating current state
- [x] Consensus/execution boundary groundwork
- [x] Dual TLS pin overlap
- [x] Authenticated operator monitoring option
- [x] Byzantine vote fixtures
- [x] Multi-node soak/divergence monitor
- [x] Deny-by-default firewall example

### v0.13 — external-consensus protocol/tooling

- [x] Deterministic `crakbit-execution/1` preview boundary
- [x] Deterministic application hash
- [x] Authenticated loopback execution-service PoC
- [x] Signed release/genesis artifact manifests
- [x] Multi-host validator provisioning scaffold
- [x] Test faucet foundation
- [x] Read-only explorer APIs
- [x] Soak evidence summarizer
- [x] External BFT evaluation/review package

### v0.14 — CometBFT bridge + crash-safe application commit

- [x] Select/pin CometBFT `v0.40.0` for integration PoC
- [x] Add `crakbit-execution/2` mutating application protocol
- [x] Persist deterministic application hashes at commit boundaries
- [x] Persist non-mutating FinalizeBlock staging
- [x] Atomic crash-safe SQLite Commit
- [x] Finalize replay/idempotency handling
- [x] Separate external application DB ownership
- [x] Go ABCI bridge: Info/CheckTx/PrepareProposal/ProcessProposal/FinalizeBlock/Commit
- [x] Signed strict >2/3 genesis ceremony tooling
- [x] Combined Python + Go CI
- [x] Local CometBFT integration runbook

### v0.15 — wallet/public gateway/mining-lab large phase

- [x] Bump chain package to `0.15.0a1`
- [x] Responsive Web UI for overview, wallet, explorer, validators and services
- [x] Browser-generated Ed25519 wallet compatible with Crakbit addresses
- [x] PBKDF2-SHA256 + AES-GCM encrypted local wallet vault
- [x] Client-side canonical transaction signing and broadcast
- [x] Encrypted wallet backup/import flow
- [x] Embedded same-origin wallet API/UI on research nodes
- [x] Standalone public gateway with `research` and `cometbft` modes
- [x] CometBFT `broadcast_tx_sync` transaction path
- [x] Authenticated external-state read APIs for accounts/transactions/commits
- [x] Persistent SQLite faucet distribution/cooldown records
- [x] Faucet broadcasting through research or CometBFT gateway path
- [x] Opt-in browser proof-of-work Mining Lab
- [x] Persistent mining challenge/solution/cooldown/daily-limit state
- [x] Dedicated non-validator mining-reward wallet model
- [x] Explicitly document that Mining Lab is **not** consensus block mining
- [x] Publish explicit production mainnet release gates
- [x] Add automated v0.15 wallet/mining/read-API tests

### v0.16 — public-testnet evidence, checkpoint recovery and web hardening

- [x] Bump package/CLI to `0.16.0a1`
- [x] Add one-command local multi-node CometBFT lab generation
- [x] Generate shared CometBFT consensus genesis + persistent-peer inventory from independent validator homes
- [x] Generate separate per-node external application state locations and execution-service tokens
- [x] Add deterministic external-application checkpoint export/verification/import
- [x] Bind checkpoint to chain ID, genesis fingerprint, state root, fixed supply and deterministic application hash
- [x] Support trusted expected consensus height/application hash checks before restore
- [x] Track checkpoint base explicitly and continue committing after restore
- [x] Add dedicated indexed explorer database/service for external-consensus state
- [x] Add restart-persistent SQLite write-rate limiting for public gateway paths
- [x] Add durable faucet and Mining Lab request limiting
- [x] Replace wildcard CORS default with same-origin + explicit allow-list
- [x] Add production-style CSP and browser security headers
- [x] Add browser-wallet threat model
- [x] Add validator remote-signer/HSM-equivalent custody guidance
- [x] Add multi-host health/divergence inventory checker
- [x] Add isolated FinalizeBlock/Commit restart/replay/checkpoint matrix
- [x] Add v0.16 automated tests and keep Python + Go bridge CI green
- [ ] Complete native CometBFT state-sync protocol wiring for the application checkpoint format
- [ ] Operate validators continuously across independently managed hosts/providers
- [ ] Execute and publish real partition/latency/packet-loss/restart/load campaign results
- [ ] Deploy shared/horizontally consistent upstream abuse controls
- [ ] Deploy/test protected remote-signer or HSM-equivalent validator custody
- [ ] Complete independent browser-wallet/consensus/application/network review

### v0.17 — next major phase: independent-host public-testnet evidence

- [ ] Integrate application checkpoints into reviewed CometBFT snapshot/state-sync lifecycle
- [ ] Run generated 4-validator topology across independent VPS/providers for an extended period
- [ ] Automate and execute packet-loss, partition, latency, process-kill and sustained-load campaigns
- [ ] Publish raw fault/soak/recovery evidence tied to exact source commit and CometBFT version
- [ ] Add explorer reconciliation and clean-host rebuild drills
- [ ] Deploy shared upstream rate limiting, reverse-proxy/load-balancer and TLS profiles
- [ ] Integrate a remote-signer/HSM-compatible validator path and run recovery/double-sign drills
- [ ] Produce a reproducible signed public-testnet release bundle
- [ ] Run documented multi-operator genesis ceremony with independently held keys
- [ ] Freeze and hand off an independent consensus/application/network/wallet review candidate

### Current warning

v0.16 materially improves repeatability, recovery, indexing and browser/public-service hardening, but it is still not production mainnet software. Source-code features are not substitutes for sustained independent-host operation, published fault evidence, protected production key custody, DDoS architecture or independent review.

The Mining Lab remains a test-reward service only; external block consensus remains CometBFT-based and no new CRKBIT supply is minted by the Mining Lab.

## Phase 7 — Public Testnet
**Only after Phase 6 technical gates are met**

- [ ] Signed public node software release
- [ ] Signed testnet genesis ceremony
- [x] Browser wallet/explorer UI foundation
- [x] Test-faucet implementation foundation
- [x] Public gateway foundation
- [x] Network monitoring/health tooling foundation
- [x] Dedicated external explorer index prototype
- [x] Application checkpoint export/restore prototype
- [ ] Independent multi-host sustained deployment
- [ ] Native external-consensus state sync
- [ ] Stress/partition testing with published evidence
- [ ] Community test program

Testnet CRKBIT units represent test units only and should not be represented as production-value assets.

## Phase 8 — Security Review

Before a production network launch:

- [ ] Internal security review
- [ ] Independent consensus/application audit
- [ ] Independent network/RPC security review
- [ ] Browser-wallet security review
- [ ] Consensus-failure and partition testing
- [ ] Economic-security review
- [ ] Cryptography/key-management review
- [ ] Incident-response drills
- [ ] Legal/regulatory review where applicable

See `blockchain/docs/MAINNET_GATES.md` for the full release-gate checklist.

## Phase 9 — Mainnet Consideration

A production mainnet can only be considered after successful long-lived public testing, reviewed external consensus/application behavior, independent security review and a clear operational/economic/legal model.

Potential production items include:

- final consensus configuration,
- reproducible signed releases,
- production genesis ceremony,
- hardened wallet ecosystem,
- production explorer/indexer,
- validator onboarding and protected signer strategy,
- CRKBIT production utility/economics,
- upgrade/governance process,
- incident-response operations.

## CRKBIT Status

**Production CRKBIT is not launched. No official presale. No production token contract.**

The research/public-testnet code uses test-only CRKBIT accounting with 8 decimals and a proposed 21,000,000 maximum genesis supply. Those parameters remain subject to technical, security, economic and legal review before any production implementation.
