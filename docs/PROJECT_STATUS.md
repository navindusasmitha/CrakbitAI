# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.5 local devnet alpha**

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
| Crakbit Chain local devnet | **v0.5 alpha** | Runnable 4-validator research network under `blockchain/` |
| Certified view changes | **Implemented for devnet** | Non-zero rounds require >2/3 signed view-change certificate |
| Prevote quorum | **Implemented for devnet** | >2/3 signed prevote certificate required before precommit |
| Precommit quorum | **Implemented for devnet** | >2/3 signed precommit certificate required before finalization |
| Persistent phase votes | **Implemented** | Local prevote/precommit choice survives restart |
| Persistent consensus lock | **Implemented as research safety rule** | Precommit creates per-height local lock |
| Consensus event journal | **Prototype implemented** | Round/vote/lock/finality events stored in SQLite |
| Equivocation evidence | **Prototype implemented** | Conflicting valid signed proposals exposed through `/evidence` |
| Validator telemetry | **Prototype implemented** | Health/status/peer/metrics/event endpoints available |
| CRKBIT devnet unit | Test-only | Native unit inside the local devnet; no represented production value |
| Crakbit Chain public testnet | Not launched | Lock/unlock, authenticated networking, recovery and external review still required |
| Production CRKBIT | Not launched | No presale or official production token contract |

## Completed Blockchain Work Through v0.5

- Ed25519 wallet/key generation and `crk1...` addresses
- Signed CRKBIT devnet transfers, nonces, replay protection and fees
- Signed block proposals, Merkle transaction roots and deterministic state roots
- SQLite blockchain/account persistence
- Round-specific proposer selection
- >2/3 signed certified view changes for later rounds
- Signed prevote phase
- Signed precommit phase
- >2/3 prevote certificate validation before precommit
- >2/3 precommit certificate validation before finalization
- Persistent same-phase anti-double-vote state
- Persistent per-height consensus lock
- Persistent consensus event history
- Conflicting signed-proposal/equivocation evidence
- Finalized-block broadcast and catch-up sync
- Validator health/height/round telemetry
- `/consensus/events` and `/metrics` development endpoints
- 4-validator Docker Compose topology with default 3-of-4 quorum
- CLI tooling and development explorer
- Automated multiphase consensus and persistence tests in CI
- v0.5 protocol specification and security notes

## Immediate Security-Platform Priorities

1. Expand scanner unit tests and rule coverage.
2. Improve Python and JavaScript/TypeScript rules.
3. Add structured configuration checks.
4. Reduce false positives and document rule behavior.
5. Build AI-assisted explanation/remediation on top of deterministic evidence.
6. Publish a simple public Security MVP interface/demo.
7. Begin security API work after scanner core becomes more stable.

## Immediate Blockchain Priorities — v0.6

1. Define and review a safe cross-round proof-based unlock rule, or migrate consensus to a mature BFT core.
2. Add authenticated validator identity handshakes.
3. Add encrypted validator transport / deployment TLS requirements.
4. Add validator key/certificate rotation design.
5. Add signed state snapshots and verified fast state sync.
6. Add restart/recovery/database-corruption tests.
7. Add long-running multi-node partition/fault/load tests.
8. Add Prometheus-style metrics, dashboarding and alerts.
9. Add public-testnet deployment configuration and operator runbooks.
10. Add faucet abuse controls and improve wallet/explorer testnet UX.
11. Commission independent consensus/network review before public-value use.

## Important v0.5 Limitation

v0.5 now has a real two-phase prevote/precommit research pipeline, but its per-height lock is deliberately conservative and does not yet have a mature proof-based unlock rule. Certain failures can therefore halt liveness rather than unlock. Validator transport is also still unauthenticated HTTP. The network remains a research devnet and is not suitable for real-value custody or mainnet claims.

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
