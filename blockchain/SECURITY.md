# Crakbit Chain Devnet Security Notes

The current Crakbit Chain implementation is a **research/devnet prototype**. It is intentionally not presented as an audited production blockchain and must not be used to custody real value.

## Security Goals of v0.3

The current code attempts to provide useful integrity, quorum-finality and validator-restart protections for development:

- Ed25519 signatures for transactions, block proposals and commit votes,
- sender/public-key binding,
- nonce-based replay protection,
- integer balance accounting,
- deterministic transaction/state commitments,
- previous-block hash linking,
- round-specific proposer validation,
- signed greater-than-two-thirds commit quorum,
- duplicate/unknown/invalid vote rejection,
- persistent same-height/same-round anti-double-vote state,
- timeout-based proposer rotation,
- local re-validation of finalized blocks during sync,
- validator health/height/round telemetry.

These properties improve the devnet but are **not sufficient for a production-value network**.

## Private Keys

`runtime/` contains generated validator and treasury private keys and is intentionally git-ignored.

Rules:

1. Never commit private keys, seed phrases or production secrets.
2. Never reuse bootstrap/devnet keys for a future public testnet or mainnet.
3. Do not expose validator key files through HTTP/static hosting.
4. Production validator key backups require encrypted, access-controlled storage.
5. Hardware-backed signing/HSM/remote-signer options should be evaluated before production.

## Consensus Risk

v0.3 requires a signed validator commit certificate with threshold:

```text
floor(2N/3) + 1
```

for `N` configured validators. The default local topology uses four validators, giving a `3 of 4` quorum.

The expected proposer rotates by both height and round. If a height is not finalized before the configured view timeout, nodes advance rounds and select the next validator.

### Persistent anti-double-vote protection

Before a vote is returned, a node stores the selected block hash for that exact `(height, round)` in SQLite. A conflicting block hash for the same `(height, round)` is rejected after restart as well as during the original process lifetime.

### Remaining consensus weaknesses

This is still **not a complete production BFT protocol**.

The current design does not yet provide:

- cross-round lock/precommit safety,
- quorum-certified view-change messages,
- durable multi-phase consensus state,
- formal safety/liveness proofs,
- equivocation evidence and slashing,
- weighted stake or dynamic validator-set changes,
- adversarially reviewed timeout/clock assumptions,
- robust fork-choice recovery under arbitrary partitions.

Because validators may vote again in a later round, same-round persistence alone does not prove that two conflicting blocks can never receive certificates under all adversarial network schedules. A production network must use a mature reviewed BFT/PoS design or formally specified equivalent.

## Network Risk

The current peer protocol uses ordinary HTTP and static peer URLs. Cryptographic signatures protect transaction/block/vote integrity, but transport does not yet provide:

- encryption,
- mutual validator authentication,
- peer identity handshakes,
- certificate/key rotation,
- discovery protections,
- connection/rate limits,
- eclipse/Sybil defenses,
- authenticated peer-health telemetry.

The `/internal/*` endpoints are development-only and should be firewalled from the public internet.

## Monitoring Limitations

`/health`, `/status` and `/peers` provide operational visibility into validator uptime, height and round progress. This helps detect stalls during local testing, but the peer-health data is not authenticated and must not be treated as a trust or security oracle.

A public testnet should add metrics export, alerting, authenticated validator identity and independent network observers.

## Denial-of-Service Risk

The development RPC does not yet include production-grade request-size limits, per-IP limits, mempool quotas or resource accounting.

Before public testnet, add explicit limits for:

- request body size,
- transaction and memo size,
- block transaction count/byte size,
- commit-certificate size,
- concurrent connections,
- RPC rate,
- mempool size,
- peer synchronization bandwidth,
- consensus request frequency.

## State / Storage Risk

SQLite provides convenient local persistence. v0.3 now persists same-round local vote records, but it still does not include:

- state snapshots,
- snapshot signatures,
- fast state sync,
- pruning/archival policy,
- database integrity recovery procedures,
- crash-consistency stress testing,
- durable cross-round lock/precommit state.

Nodes should still be treated as disposable during early development.

## Transaction Risk

Current validation checks signatures, nonces, balances, fees and chain ID. Future work should also consider:

- strict field and memo size limits,
- canonical address parsing,
- integer overflow assumptions across implementations,
- mempool replacement policy,
- multiple pending nonces per account,
- transaction expiration/time bounds,
- malformed encoding fuzzing,
- duplicate/rebroadcast handling.

## Economic Security

The current prototype has no staking, slashing, inflation or on-chain governance. Fees are credited to the finalized block proposer.

No production token economics should be inferred from the implementation. A future public network requires separate analysis of validator incentives, attack cost, authority/stake concentration, fee-market behavior, spam resistance, issuance policy and governance risk.

## Smart Contracts

No smart-contract virtual machine is included in v0.3. Adding a VM would substantially increase the attack surface and should follow a separate threat model, deterministic execution specification, sandbox design and independent review.

## Required Testing Before Public Testnet

- accounting/property tests,
- fuzzing of transaction/block/vote parsers,
- malformed signature/public-key tests,
- quorum and duplicate-vote tests,
- cross-round conflicting proposal tests,
- proposer downtime/failover tests,
- validator restart/double-vote tests,
- network partition tests,
- long-running synchronization tests,
- database crash/restart tests,
- RPC/load abuse tests,
- reproducible build/container review,
- dependency/security scanning.

## Required Testing Before Mainnet

A production-value network should not launch without a long-lived public testnet and independent review of consensus, cryptography, P2P networking, storage, key management, RPC exposure, incident response and economic design.

Security findings should be reported through the repository-level [`SECURITY.md`](../SECURITY.md) process rather than disclosed publicly before maintainers have a reasonable opportunity to respond.
