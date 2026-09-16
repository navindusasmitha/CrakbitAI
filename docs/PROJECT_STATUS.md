# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.6 local devnet alpha**

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
| Crakbit Chain local devnet | **v0.6 alpha** | Runnable 4-validator research network under `blockchain/` |
| Certified view changes | **Implemented for devnet** | Later rounds require >2/3 signed view-change certificate |
| Prevote quorum | **Implemented for devnet** | >2/3 signed prevote certificate required before precommit |
| Precommit quorum | **Implemented for devnet** | >2/3 signed precommit certificate required before finalization |
| Persistent consensus lock | **Implemented as research rule** | Precommit creates a per-height local lock |
| Validator request authentication | **v0.6 prototype implemented** | Ed25519 signatures bind method/path/body hash/timestamp/nonce |
| Validator identity handshake | **v0.6 prototype implemented** | Signed challenge/response identity verification |
| HTTPS enforcement mode | **Optional** | Rejects non-HTTPS peer URLs when explicitly enabled; does not provision TLS |
| Signed state snapshots | **Export + verification implemented** | Fast-sync import is not implemented yet |
| Prometheus-style metrics | **Prototype implemented** | `/metrics/prometheus` available |
| Equivocation evidence | **Prototype implemented** | Conflicting valid signed proposals exposed through `/evidence` |
| CRKBIT devnet unit | Test-only | Native unit inside the local devnet; no represented production value |
| Crakbit Chain public testnet | Not launched | Stronger BFT unlock/network recovery/testnet infrastructure still required |
| Production CRKBIT | Not launched | No presale or official production token contract |

## Completed Blockchain Work Through v0.6

- Ed25519 wallet/key generation and `crk1...` addresses
- Signed CRKBIT devnet transfers, nonces, replay protection and fees
- Signed block proposals, Merkle transaction roots and deterministic state roots
- SQLite blockchain/account/consensus persistence
- Round-specific proposer selection
- >2/3 signed certified view changes for later rounds
- Signed prevote and precommit phases
- >2/3 prevote certificate before precommit
- >2/3 precommit certificate before finalization
- Persistent same-phase anti-double-vote state
- Persistent per-height conservative consensus lock
- Persistent consensus event history
- Conflicting signed-proposal/equivocation evidence
- Ed25519-authenticated internal validator requests
- Timestamp-window and nonce replay checks for peer requests
- Signed validator challenge/response handshake
- Optional HTTPS peer-URL enforcement mode
- Signed state snapshot export and local verification
- `crakchain snapshot-verify`
- `/snapshot/latest`
- JSON and Prometheus-style metrics endpoints
- Finalized-block broadcast and catch-up sync
- Validator health/height/round telemetry
- 4-validator Docker Compose topology with default 3-of-4 quorum
- Automated consensus, peer-authentication and snapshot tests in CI

## Immediate Security-Platform Priorities

1. Expand scanner unit tests and rule coverage.
2. Improve Python and JavaScript/TypeScript rules.
3. Add structured configuration checks.
4. Reduce false positives and document rule behavior.
5. Build AI-assisted explanation/remediation on top of deterministic evidence.
6. Publish a simple public Security MVP interface/demo.
7. Begin security API work after scanner core becomes more stable.

## Immediate Blockchain Priorities — v0.7

1. Review/replace the conservative cross-round lock with a mature proof-based unlock/BFT design.
2. Add mutually authenticated encrypted validator transport with certificate/key rotation.
3. Harden peer replay/session handling across restarts.
4. Add snapshot quorum certification and verified snapshot import / fast state sync.
5. Add restart/recovery/database-corruption testing.
6. Add long-running network partition, latency, Byzantine-behavior and load tests.
7. Add Grafana dashboards and alert rules.
8. Add public-testnet deployment configuration and operator runbooks.
9. Add faucet abuse controls and improve wallet/explorer testnet UX.
10. Commission independent consensus/network review before public-value use.

## Important v0.6 Limitations

v0.6 improves validator request authentication and adds signed snapshot verification, but it is still not a production BFT/mainnet implementation. The consensus lock lacks a mature proof-based unlock rule, replay-nonce memory is process-local, local Docker traffic is not encrypted by default, HTTPS enforcement does not configure certificates/mTLS, and signed snapshots cannot yet be imported for fast state sync.

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