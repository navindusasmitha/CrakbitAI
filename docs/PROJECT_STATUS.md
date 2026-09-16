# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.7 local devnet alpha**

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
| Crakbit Chain local devnet | **v0.7 alpha** | Runnable 4-validator research network under `blockchain/` |
| Certified view changes | **Implemented for devnet** | Later rounds require >2/3 signed view-change certificate |
| Prevote / precommit finality | **Implemented for devnet** | >2/3 prevote then >2/3 precommit required |
| Persistent consensus lock | **Research rule implemented** | Still lacks mature proof-based cross-round unlock |
| Validator request authentication | **Prototype implemented** | Ed25519 request signatures bind method/path/body/timestamp/nonce |
| Durable peer replay cache | **v0.7 implemented** | Recent validator request nonces persist in SQLite across restarts |
| Validator identity handshake | **Prototype implemented** | Signed challenge/response identity verification |
| HTTPS enforcement mode | **Optional** | Rejects non-HTTPS peer URLs; does not provision mTLS |
| Signed state snapshots | **Implemented for devnet** | Deterministic account state + validator signature |
| Quorum snapshot certificate | **v0.7 implemented** | >2/3 matching validator signatures required |
| Snapshot import/bootstrap | **v0.7 implemented** | Fresh height-zero database only; pre-snapshot history not reconstructed |
| Recovery status endpoint | **v0.7 implemented** | `/recovery/status` exposes local recovery metadata |
| Prometheus-style metrics | **Prototype implemented** | `/metrics/prometheus` available |
| Equivocation evidence | **Prototype implemented** | Conflicting valid signed proposals exposed through `/evidence` |
| CRKBIT devnet unit | Test-only | Native unit inside the local devnet; no represented production value |
| Crakbit Chain public testnet | Not launched | Mature BFT unlock, mTLS, adversarial testing and ops work still required |
| Production CRKBIT | Not launched | No presale or official production token contract |

## Completed Blockchain Work Through v0.7

- Ed25519 wallet/key generation and `crk1...` addresses
- Signed CRKBIT devnet transfers, nonces, replay protection and fees
- Signed block proposals, Merkle transaction roots and deterministic state roots
- SQLite blockchain/account/consensus persistence
- Round-specific proposer selection
- >2/3 certified view changes for later rounds
- Signed prevote and precommit phases
- >2/3 prevote certificate before precommit
- >2/3 precommit certificate before finalization
- Persistent same-phase anti-double-vote state
- Persistent per-height conservative consensus lock
- Persistent consensus event history and equivocation evidence
- Ed25519-authenticated internal validator requests
- Signed validator challenge/response handshake
- SQLite-persistent validator request replay cache
- Optional HTTPS peer-URL enforcement mode
- Signed state snapshot generation/verification
- >2/3 matching-state snapshot certificates
- Snapshot state/supply/hash/signature/quorum verification
- Fresh-database certified snapshot import
- Node startup bootstrap from certified snapshot
- Recovery metadata persistence and `/recovery/status`
- JSON and Prometheus-style metrics
- Finalized-block broadcast and catch-up sync after snapshot base height
- 4-validator Docker Compose topology with default 3-of-4 quorum
- Automated consensus, peer-authentication and recovery tests in CI

## Immediate Security-Platform Priorities

1. Expand scanner unit tests and rule coverage.
2. Improve Python and JavaScript/TypeScript rules.
3. Add structured configuration checks.
4. Reduce false positives and document rule behavior.
5. Build AI-assisted explanation/remediation on top of deterministic evidence.
6. Publish a simple public Security MVP interface/demo.
7. Begin security API work after scanner core becomes more stable.

## Immediate Blockchain Priorities — v0.8

1. Review/replace the conservative cross-round lock with a mature proof-based BFT lock/unlock design or migrate to a reviewed BFT core.
2. Add mutually authenticated TLS validator transport with certificate pinning/rotation.
3. Add snapshot chunking, size limits, resumable state transfer and retention policy.
4. Make historical block APIs explicitly snapshot-base aware.
5. Add database-corruption, crash and interrupted-import recovery testing.
6. Add long-running partition, latency, Byzantine-behavior and load tests.
7. Add Grafana dashboards and alert rules.
8. Add public-testnet deployment configuration and operator runbooks.
9. Add faucet abuse controls and improve wallet/explorer testnet UX.
10. Commission independent consensus/network review before public-value use.

## Important v0.7 Limitations

v0.7 materially improves replay durability and state recovery, but it is still not a production BFT/mainnet implementation. The consensus lock has no mature cross-round unlock rule, local Docker traffic is not encrypted by default, HTTPS enforcement is not mTLS lifecycle management, and snapshot bootstrap establishes certified state without reconstructing historical blocks before the snapshot base height.

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
