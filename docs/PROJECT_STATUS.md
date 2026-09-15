# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.2 local devnet alpha**

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
| Open-source rule packs | Started | Initial rules published with scanner alpha |
| Crakbit Chain local devnet | **v0.2 alpha** | Runnable 3-validator research network under `blockchain/` |
| Signed quorum finality | **Implemented for devnet** | >2/3 validator commit certificate required before block commit |
| Consensus proposer failover | Not implemented | Scheduled proposer failure can still halt the devnet |
| CRKBIT devnet unit | Test-only | Native unit inside the local devnet; no represented production value |
| Crakbit Chain public testnet | Not launched | Consensus/network hardening required first |
| Production CRKBIT | Not launched | No presale or official production token contract |

## Completed Foundation Work

- Public repository established
- Project README expanded
- Roadmap published
- Contribution guide and Code of Conduct published
- Vulnerability reporting policy published
- Architecture and security-model documentation published
- Funding/transparency documentation published
- GitHub issue and pull-request templates added
- Security scanner package architecture created
- Initial Python/JavaScript-oriented security rules created
- Secret evidence redaction added
- Scanner CLI alpha and tests added
- Crakbit Chain local devnet package created
- Ed25519 wallet/key generation implemented for the devnet
- Signed CRKBIT devnet transfers implemented
- Nonces, replay protection and transaction fees implemented
- Signed block proposals, transaction Merkle roots and state roots implemented
- SQLite blockchain/account persistence implemented
- Round-robin validator proposal schedule implemented
- Signed validator commit votes implemented
- Strict greater-than-two-thirds commit quorum required before finalization
- Duplicate/unknown/invalid commit vote rejection implemented
- In-memory same-height/same-round double-vote protection added
- Proposal validation includes transaction signature/field validation before voting
- Basic peer broadcast/catch-up synchronization implemented for finalized blocks
- REST/RPC status, validator, balance, block and transaction endpoints implemented
- 3-validator Docker Compose devnet added
- Simple devnet explorer added
- Blockchain ledger/signature/quorum tests added and passing in CI
- v0.2 protocol specification and security notes published

## Immediate Security-Platform Priorities

1. Expand scanner unit tests and rule coverage.
2. Improve Python and JavaScript/TypeScript rules.
3. Add structured configuration checks.
4. Reduce false positives and document rule behavior.
5. Build AI-assisted explanation/remediation on top of deterministic evidence.
6. Publish a simple public Security MVP interface/demo.
7. Begin security API work after scanner core becomes more stable.

## Immediate Blockchain Priorities — v0.3

1. Add proposer/view changes so validator downtime does not permanently halt progress.
2. Persist validator vote/lock state across restarts.
3. Add conflicting-proposal/equivocation evidence handling.
4. Add authenticated/encrypted validator peer transport and peer identity checks.
5. Add validator monitoring/health dashboard.
6. Add state snapshots, state sync and restart/recovery testing.
7. Expand adversarial multi-node and network-partition tests.
8. Add public-testnet deployment configuration, testnet faucet and improved explorer.
9. Define validator key-management requirements and operational runbooks.
10. Run a long-lived closed devnet before any public testnet.

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
