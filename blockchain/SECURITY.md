# Crakbit Chain Devnet Security Notes

The current Crakbit Chain implementation is a **research/devnet prototype**. It is intentionally not presented as an audited production blockchain and must not be used to custody real value.

## Security Goals of v0.4

The current code provides development-stage protections including:

- Ed25519 signatures for transactions, block proposals, commit votes and view-change messages,
- sender/public-key binding,
- nonce-based replay protection,
- integer balance accounting,
- deterministic transaction/state commitments,
- previous-block hash linking,
- round-specific proposer validation,
- strict greater-than-two-thirds commit quorum,
- strict greater-than-two-thirds signed view-change quorum for non-zero rounds,
- persistent same-round anti-double-vote state,
- persistent local consensus-round advancement,
- conservative cross-round local vote locking,
- conflicting signed proposal/equivocation evidence,
- local re-validation of finalized blocks during sync,
- validator health/height/round telemetry.

These controls improve the devnet but remain **insufficient for a public-value production network**.

## Private Keys

`runtime/` contains generated validator and treasury private keys and is intentionally git-ignored.

Rules:

1. Never commit private keys, seed phrases or production secrets.
2. Never reuse bootstrap/devnet keys for a future public testnet or mainnet.
3. Do not expose validator key files through HTTP/static hosting.
4. Production validator key backups require encrypted, access-controlled storage.
5. Hardware-backed signing, HSMs or a reviewed remote-signer design should be evaluated before production.

## Consensus Risk

v0.4 uses a strict greater-than-two-thirds validator threshold for both commit certificates and view-change certificates.

The default four-validator topology therefore requires `3 of 4` signatures.

### Certified view changes

A validator may request movement from round `R` to `R+1` only after the local timeout. A later-round proposal must carry a quorum certificate of signed view-change messages for that exact transition.

This is safer than independent unilateral round advancement because every validator can verify why the later round exists.

### Persistent consensus state

The node persists local vote records, local round advancement and local view-change actions in SQLite. A restart therefore does not automatically erase the validator's prior same-round voting decision or return an unfinished height to round zero.

### Conservative cross-round lock

After a validator signs a commit vote at a height, v0.4 refuses to sign a different block hash at the same height in a later round.

This improves safety, but the rule is intentionally conservative and has **no mature unlock/proof-of-lock mechanism**. If enough validators become locked on a proposal that never finalizes, the chain can halt.

That liveness tradeoff is preferable for this research phase to silently allowing potentially conflicting cross-round signatures, but it is not a complete production BFT design.

### Equivocation evidence

A node stores the first valid signed proposal observed for `(height, round, proposer)`. A second different valid signed proposal from the same proposer for that same tuple is recorded as conflicting-proposal evidence and rejected for voting.

There is currently no automatic slashing, validator removal or evidence gossip protocol.

### Remaining consensus weaknesses

v0.4 still lacks:

- a mature prevote/precommit or equivalent multi-phase lock/unlock state machine,
- a formally reviewed cross-round unlock rule,
- formal safety/liveness proofs,
- weighted stake or validator-set changes,
- automatic evidence/slashing processing,
- adversarially reviewed timeout/clock assumptions,
- robust recovery under arbitrary partitions.

A production chain should use a mature reviewed BFT/PoS design or a formally specified equivalent before real value is placed at risk.

## Network Risk

Validator communication still uses ordinary HTTP and static peer URLs. Message signatures protect consensus-object integrity, but transport does not yet provide:

- encryption,
- mutual validator authentication,
- peer identity handshakes,
- certificate/key rotation,
- dynamic discovery protections,
- connection/rate limits,
- eclipse/Sybil defenses,
- authenticated peer-health telemetry.

The `/internal/*` endpoints are development-only and should be firewalled from the public internet.

## Monitoring Limitations

`/health`, `/status`, `/peers` and `/evidence` provide operational visibility. They are useful for development and testing, but current peer-health data is unauthenticated and must not be treated as a security oracle.

A public testnet should add authenticated validator identity, metrics export, alerting and independent observer nodes.

## Denial-of-Service Risk

The development RPC still lacks production-grade request-size limits, per-IP limits, connection quotas and resource accounting.

Before public testnet, explicitly limit:

- request body size,
- transaction and memo size,
- block transaction count/byte size,
- commit/view-change certificate size,
- concurrent connections,
- RPC request rate,
- mempool size,
- synchronization bandwidth,
- consensus request frequency.

## State / Storage Risk

SQLite is convenient for the devnet. v0.4 persists more consensus metadata, but the implementation still lacks:

- state snapshots,
- snapshot signatures,
- fast state sync,
- pruning/archival policy,
- database integrity recovery procedures,
- crash-consistency stress testing,
- complete multi-phase consensus event history.

Nodes should still be treated as disposable during early research.

## Transaction Risk

Current validation checks signatures, nonces, balances, fees and chain ID. Future work should add stronger bounds and fuzzing for:

- memo/field sizes,
- canonical address parsing,
- integer boundary assumptions across implementations,
- multiple pending nonces,
- transaction replacement policy,
- expiration/time bounds,
- malformed encodings,
- rebroadcast/duplicate handling.

## Economic Security

The prototype has no staking, slashing, inflation or on-chain governance. Fees are credited to the finalized block proposer.

No production token economics should be inferred from this implementation. A future public network requires separate analysis of validator incentives, attack cost, authority/stake concentration, fee-market behavior, spam resistance, issuance policy and governance risk.

## Smart Contracts

No smart-contract virtual machine is included in v0.4. Adding a VM would substantially increase attack surface and should follow a separate threat model, deterministic execution specification, sandbox design and independent review.

## Required Testing Before Public Testnet

- accounting/property tests,
- fuzzing of transaction/block/vote/view-change parsers,
- malformed signature/public-key tests,
- quorum and duplicate-vote tests,
- cross-round conflicting proposal tests,
- certified view-change tests,
- proposer downtime/failover tests,
- validator restart/consensus-state tests,
- network partition tests,
- long-running synchronization tests,
- database crash/restart tests,
- RPC/load abuse tests,
- reproducible build/container review,
- dependency/security scanning.

## Required Testing Before Mainnet

A production-value network should not launch without a long-lived public testnet and independent review of consensus, cryptography, P2P networking, storage, key management, RPC exposure, incident response and economic design.

Security findings should be reported through the repository-level [`SECURITY.md`](../SECURITY.md) process rather than disclosed publicly before maintainers have a reasonable opportunity to respond.
