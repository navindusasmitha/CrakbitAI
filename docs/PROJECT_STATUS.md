# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.8 local devnet alpha**

Crakbit AI currently has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and a runnable experimental blockchain development network. None of these alpha components should be described as production-ready.

## Current Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| Public website | Active | Project information and funding positioning available |
| GitHub repository | Active | Documentation, scanner alpha and blockchain devnet code published |
| Fundraising | Publicly listed on Giveth | GIVbacks verification/review is a separate process |
| AI Security Assistant | In development | MVP architecture and workflow definition |
| Secure Code Scanner | Early alpha | Initial deterministic rules and normalized findings implemented |
| Security CLI | Early alpha | `crak` command included with scanner package |
| Security API | Planned | To follow scanner core |
| Smart Contract Scanner | Planned | Blockchain-security phase |
| Crakbit Chain local devnet | **v0.8 alpha** | Runnable 4-validator research network under `blockchain/` |
| Certified view changes | **Implemented for devnet** | Later rounds require >2/3 signed view-change certificate |
| Prevote/precommit quorum | **Implemented for devnet** | >2/3 certificates required before finalization |
| Persistent consensus lock | **Research rule implemented** | Still lacks mature proof-based cross-round unlock |
| Validator request authentication | **Prototype implemented** | Ed25519 request signatures + identity handshake |
| Durable peer replay protection | **Prototype implemented** | SQLite replay-nonce store survives process restart |
| Quorum state snapshots | **Prototype implemented** | Matching >2/3 validator signatures required |
| Snapshot import/bootstrap | **Prototype implemented** | Fresh database can start from certified account state |
| Chunked snapshot transfer | **v0.8 prototype implemented** | Per-chunk + complete artifact hashes with bounded sizes |
| Resumable snapshot cache | **v0.8 CLI prototype implemented** | Verified chunks can be reused on retry for same bundle |
| Snapshot import journal | **v0.8 prototype implemented** | Crash-visible sidecar journal reconciles same certificate |
| Snapshot-aware history API | **v0.8 prototype implemented** | Distinguishes unavailable pre-snapshot local history |
| Prometheus-style metrics | **Prototype implemented** | `/metrics/prometheus` available |
| CRKBIT devnet unit | Test-only | Native unit inside the local devnet; no represented production value |
| Crakbit Chain public testnet | Not launched | Mature BFT/network transport/fault testing still required |
| Production CRKBIT | Not launched | No presale or official production token contract |

## Completed Blockchain Work Through v0.8

- Ed25519 wallet/key generation and `crk1...` addresses
- Signed CRKBIT devnet transfers, nonces, replay protection and fees
- Signed block proposals, Merkle transaction roots and deterministic state roots
- SQLite blockchain/account/consensus persistence
- Round-specific proposer selection
- >2/3 certified view changes for later rounds
- Signed prevote and precommit phases
- >2/3 prevote certificate before precommit
- >2/3 precommit certificate before finalization
- Persistent anti-double-vote state and conservative consensus lock
- Equivocation evidence and consensus event history
- Authenticated validator HTTP requests and signed identity handshake
- Durable SQLite-backed validator-request replay protection
- Quorum-certified state snapshots
- Verified snapshot import/bootstrap for fresh databases
- Snapshot-base recovery metadata
- Chunked snapshot manifest with per-chunk hashes and transfer limits
- Resumable verified chunk cache in `snapshot-fetch-chunked`
- Crash-visible snapshot import journal
- Snapshot-aware history status/block endpoints
- JSON and Prometheus-style metrics endpoints
- Finalized-block broadcast and catch-up sync
- Validator health/height/round telemetry
- 4-validator Docker Compose topology with default 3-of-4 quorum
- Automated consensus, peer-authentication, snapshot and recovery tests in CI

## Immediate Security-Platform Priorities

1. Expand scanner unit tests and rule coverage.
2. Improve Python and JavaScript/TypeScript rules.
3. Add structured configuration checks.
4. Reduce false positives and document rule behavior.
5. Build AI-assisted explanation/remediation on top of deterministic evidence.
6. Publish a simple public Security MVP interface/demo.
7. Begin security API work after scanner core becomes more stable.

## Immediate Blockchain Priorities — v0.9

1. Review/replace the conservative cross-round lock with a mature proof-based BFT design or migrate to a reviewed BFT core.
2. Add mutually authenticated encrypted validator transport with certificate pinning and rotation.
3. Design archive/history synchronization for snapshot-bootstrapped nodes.
4. Add database corruption, abrupt-power-loss and restart recovery tests.
5. Add long-running network partition, latency, Byzantine-behavior and load tests.
6. Add Grafana dashboards and alert rules.
7. Add public-testnet deployment configuration and operator runbooks.
8. Add faucet abuse controls and improve wallet/explorer testnet UX.
9. Define validator key-management and incident-response procedures.
10. Commission independent consensus/network review before public-value use.

## Important v0.8 Limitations

v0.8 improves state transfer and recovery operations, but it is still not a production BFT/mainnet implementation. The consensus lock lacks a mature proof-based unlock rule; HTTPS policy is not a reviewed mTLS/certificate lifecycle; snapshot bootstrap restores certified state but not pre-snapshot historical block bodies; and long-running adversarial/fault testing and independent review remain outstanding.

## What Is Not Yet Production-Ready

The following must not be described as completed production systems:

- Full AI security platform
- Production-grade scanner coverage
- Production security API/CLI
- Smart-contract security suite
- Production BFT Crakbit blockchain
- Public Crakbit testnet
- Production wallet/explorer
- Production CRKBIT token/coin

## Evidence and Transparency

Crakbit AI aims to distinguish clearly between completed work, active development, prototypes, planned features and long-term research. Devnet/testnet units and prototype features must not be presented as production assets or guaranteed future functionality.
