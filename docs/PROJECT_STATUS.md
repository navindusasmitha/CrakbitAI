# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.4 local devnet alpha**

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
| Crakbit Chain local devnet | **v0.4 alpha** | Runnable 4-validator research network under `blockchain/` |
| Signed quorum finality | **Implemented for devnet** | >2/3 validator commit certificate required before block commit |
| Certified view changes | **Implemented for devnet** | Non-zero rounds require >2/3 signed view-change certificate |
| Persistent consensus round | **Implemented** | Local unfinished-height round survives restart |
| Persistent same-round anti-double-vote | **Implemented** | Local vote hash stored in SQLite across restart |
| Conservative cross-round lock | **Implemented as research safety rule** | Conflicting later-round local vote is refused; no mature unlock rule yet |
| Equivocation evidence | **Prototype implemented** | Conflicting valid signed proposals are persisted and exposed by `/evidence` |
| Validator telemetry | **Prototype implemented** | `/health`, `/status`, `/peers`, `/validators`, `/evidence` |
| CRKBIT devnet unit | Test-only | Native unit inside the local devnet; no represented production value |
| Crakbit Chain public testnet | Not launched | Mature BFT lock/unlock, authenticated networking and recovery still required |
| Production CRKBIT | Not launched | No presale or official production token contract |

## Completed Blockchain Work Through v0.4

- Ed25519 wallet/key generation and `crk1...` addresses
- Signed CRKBIT devnet transfers
- Nonces, replay protection and transaction fees
- Signed block proposals, transaction Merkle roots and deterministic state roots
- SQLite blockchain/account persistence
- Signed validator commit votes and strict >2/3 quorum finality
- Duplicate/unknown/invalid commit-vote rejection
- Round-specific proposer selection
- Timeout-triggered signed view-change messages
- Strict >2/3 view-change certificates before entering a later proposal round
- Later-round proposals carry the verified view-change certificate
- Persistent local consensus round and view-change records
- Persistent same-height/same-round anti-double-vote records
- Conservative cross-round local vote locking
- Conflicting signed proposal/equivocation evidence persistence
- Basic finalized-block broadcast and catch-up sync
- Validator health/height/round telemetry
- 4-validator Docker Compose topology with default 3-of-4 quorum
- REST/RPC endpoints, CLI tooling and development explorer
- Automated ledger/signature/quorum/view-change/evidence tests and CI
- v0.4 protocol specification and security notes

## Immediate Security-Platform Priorities

1. Expand scanner unit tests and rule coverage.
2. Improve Python and JavaScript/TypeScript rules.
3. Add structured configuration checks.
4. Reduce false positives and document rule behavior.
5. Build AI-assisted explanation/remediation on top of deterministic evidence.
6. Publish a simple public Security MVP interface/demo.
7. Begin security API work after scanner core becomes more stable.

## Immediate Blockchain Priorities — v0.5

1. Replace the conservative no-unlock lock with a reviewed multi-phase prevote/precommit or equivalent lock/unlock protocol.
2. Persist richer consensus event history and extend equivocation evidence handling.
3. Add authenticated/encrypted validator transport and peer identity handshakes.
4. Add validator certificate/key rotation design.
5. Add state snapshots, snapshot verification and fast state sync.
6. Add restart/recovery/database-corruption tests.
7. Add long-running multi-node partition/fault/load tests.
8. Add metrics export, dashboarding and alerts.
9. Add public-testnet deployment configuration and operational runbooks.
10. Add faucet abuse controls and improve wallet/explorer testnet UX.
11. Commission independent consensus/network review before public-value use.

## Important v0.4 Limitation

v0.4 introduces quorum-certified view changes and a conservative cross-round local lock, but it is still not a complete production BFT protocol. The current lock has no mature proof-of-lock/unlock rule, so some fault/partition scenarios may halt the network. Validator transport is also still unauthenticated HTTP. The network remains a research devnet and is not suitable for real-value custody or mainnet claims.

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
