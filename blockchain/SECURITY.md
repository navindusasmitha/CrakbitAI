# Crakbit Chain Devnet Security Notes

The current Crakbit Chain implementation is a **research/devnet prototype**. It is intentionally not presented as an audited production blockchain and must not be used to custody real value.

## Security Goals of v0.2

The current code attempts to provide basic integrity and quorum-finality properties for development:

- private-key signatures for transactions and block proposals,
- sender/public-key binding,
- nonce-based replay protection,
- integer balance accounting,
- deterministic transaction and state commitments,
- previous-block hash linking,
- configured proposer validation,
- genesis fingerprinting,
- local re-validation of proposals and finalized blocks,
- signed validator commit votes,
- strict greater-than-two-thirds validator quorum before commit,
- duplicate/unknown/invalid vote rejection,
- an in-memory same-height/same-round double-vote guard.

These properties are useful for development, but they are not sufficient for a public-value network.

## Private Keys

`runtime/` contains generated validator and treasury private keys and is intentionally git-ignored.

Rules:

1. Never commit private keys, seed phrases or production secrets.
2. Never reuse bootstrap/devnet keys for a future testnet or mainnet.
3. Do not expose key files through HTTP/static hosting.
4. Backups of any future production validator keys require encrypted, access-controlled key management.
5. Hardware-backed signing/HSM options should be evaluated before production.

## Consensus Risk

v0.2 improves on proposer-only PoA by requiring a signed validator commit certificate with a threshold of:

```text
floor(2N/3) + 1
```

for `N` configured validators.

Each validator re-validates a proposal before voting. Finalized blocks are re-validated, including the commit certificate, before ledger state is changed.

### Remaining consensus weaknesses

This is still **not a complete production BFT implementation**.

The current design does not yet provide:

- proposer/view changes when the scheduled proposer is offline,
- durable consensus locks across restarts,
- persistent anti-double-sign state,
- equivocation evidence and slashing,
- weighted stake or validator-set changes,
- formal fork-choice recovery,
- formal safety/liveness proofs,
- adversarially reviewed timeout/round logic.

A scheduled proposer failure can halt the chain. A validator restart can also lose its in-memory record of a previous vote. These are acceptable devnet limitations but mainnet blockers.

## Network Risk

The current peer protocol uses ordinary HTTP and static peer URLs. Proposal and block integrity is protected cryptographically, but the transport does not yet implement:

- encrypted validator channels,
- mutual peer authentication,
- peer identity handshakes,
- dynamic discovery protections,
- connection/rate limits,
- eclipse/Sybil defenses,
- signed peer metadata.

The `/internal/*` endpoints are development-only and should be firewalled from the public internet.

## Denial-of-Service Risk

The development RPC does not yet include production-grade request-size limits, per-IP limits, mempool quotas or resource accounting.

Before public testnet, add explicit limits for:

- request body size,
- transaction size,
- memo size,
- block transaction count/byte size,
- commit-certificate size,
- concurrent connections,
- RPC rate,
- mempool size,
- peer synchronization bandwidth.

## State / Storage Risk

SQLite provides convenient local persistence but v0.2 does not yet include:

- state snapshots,
- snapshot signatures,
- database integrity recovery procedures,
- pruning/archival policy,
- crash-consistency stress testing,
- fast state sync,
- persistent consensus vote/lock state.

Nodes should still be treated as disposable during early devnet work.

## Transaction Risk

Current validation checks signatures, nonces, balances, fees and chain ID. Future work should also consider:

- strict field and memo size limits,
- canonical address parsing,
- integer overflow assumptions across implementations,
- mempool replacement policy,
- multiple pending nonces per account,
- duplicate transaction handling,
- malformed encoding fuzzing,
- transaction expiration/time bounds if required.

## Economic Security

The current prototype has no staking, slashing, inflation or governance. Fees are credited to the block proposer.

No production token economics should be inferred from this implementation. A future public network requires separate analysis of:

- validator incentives,
- attack cost,
- stake/authority concentration,
- fee-market behavior,
- spam resistance,
- issuance/supply policy,
- governance and upgrade risk.

## Smart Contracts

No smart-contract virtual machine is included in v0.2. This is deliberate. Adding a VM dramatically increases attack surface and should follow a separate threat model, sandbox design, deterministic execution specification and audit plan.

## Required Testing Before Public Testnet

- property tests for accounting invariants,
- fuzzing of transaction/block/vote parsers,
- malformed signature/public-key tests,
- quorum and duplicate-vote tests,
- conflicting proposal tests,
- multi-node partition tests,
- validator downtime tests,
- validator restart/double-vote tests,
- long-running synchronization tests,
- database crash/restart tests,
- load and RPC abuse tests,
- dependency/security scanning,
- reproducible build/container review.

## Required Testing Before Mainnet

A production-value network should not launch without a long-lived public testnet and independent review of consensus, cryptography, P2P networking, storage, key management, RPC exposure and economic design.

Security findings for the project should be reported through the repository-level [`SECURITY.md`](../SECURITY.md) process rather than disclosed publicly before maintainers have a reasonable opportunity to respond.
