# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.3 local devnet alpha**

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
| Crakbit Chain local devnet | **v0.3 alpha** | Runnable 4-validator research network under `blockchain/` |
| Signed quorum finality | **Implemented for devnet** | >2/3 validator commit certificate required before block commit |
| Round-based proposer failover | **Implemented for devnet** | Timeout advances consensus round and proposer |
| Persistent same-round anti-double-vote | **Implemented** | Local vote hash stored in SQLite across restart |
| Validator telemetry | **Prototype implemented** | `/health`, `/status`, `/peers`, `/validators` |
| CRKBIT devnet unit | Test-only | Native unit inside the local devnet; no represented production value |
| Crakbit Chain public testnet | Not launched | Cross-round BFT safety and network hardening still required |
| Production CRKBIT | Not launched | No presale or official production token contract |

## Completed Blockchain Work Through v0.3

- Ed25519 wallet/key generation and `crk1...` addresses
- Signed CRKBIT devnet transfers
- Nonces, replay protection and transaction fees
- Signed block proposals, transaction Merkle roots and deterministic state roots
- SQLite blockchain/account persistence
- Signed validator commit votes and strict >2/3 quorum finality
- Duplicate/unknown/invalid vote rejection
- Transaction validation before validator voting
- Round-specific proposer selection
- Timeout-based consensus-round advancement
- Proposer failover to the next validator
- Persistent same-height/same-round anti-double-vote records
- Basic finalized-block broadcast and catch-up sync
- Validator health/height/round telemetry
- 4-validator Docker Compose topology with default 3-of-4 quorum
- REST/RPC endpoints, CLI tooling and development explorer
- Automated ledger/signature/quorum/failover tests and CI
- v0.3 protocol specification and security notes

## Immediate Security-Platform Priorities

1. Expand scanner unit tests and rule coverage.
2. Improve Python and JavaScript/TypeScript rules.
3. Add structured configuration checks.
4. Reduce false positives and document rule behavior.
5. Build AI-assisted explanation/remediation on top of deterministic evidence.
6. Publish a simple public Security MVP interface/demo.
7. Begin security API work after scanner core becomes more stable.

## Immediate Blockchain Priorities — v0.4

1. Add quorum-certified view-change messages rather than local timeout-only round movement.
2. Add cross-round lock/precommit rules to prevent unsafe conflicting finalization paths.
3. Persist richer consensus state and equivocation evidence.
4. Add authenticated/encrypted validator transport and peer identity checks.
5. Add state snapshots, fast state sync and recovery testing.
6. Add a dedicated validator dashboard/metrics pipeline and alerts.
7. Add public-testnet deployment configuration and operational runbooks.
8. Add faucet abuse controls and improve the explorer for testnet users.
9. Run long-lived multi-node, partition, restart and load tests.
10. Commission independent consensus/network review before public-value use.

## Important v0.3 Limitation

v0.3 persistent vote protection is same-round only. It does not yet provide a formally reviewed cross-round BFT lock/precommit protocol. The network therefore remains a research devnet and is not suitable for real-value custody or mainnet claims.

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
