# Crakbit Chain Devnet Security Notes

The current Crakbit Chain implementation is a **research/devnet prototype**. It is not an audited production blockchain and must not be used to custody real value.

## Security Goals of v0.5

v0.5 adds development-stage protections including:

- Ed25519 signatures for transactions, proposals, prevotes, precommits and view changes,
- sender/public-key binding,
- nonce-based replay protection,
- deterministic transaction/state commitments,
- strict greater-than-two-thirds prevote quorum,
- strict greater-than-two-thirds precommit quorum,
- certified non-zero-round view changes,
- persistent same-phase anti-double-vote records,
- persistent per-height consensus locks,
- persistent consensus event history,
- conflicting signed-proposal evidence,
- finalized-block revalidation during sync,
- validator health/height/round telemetry.

These controls improve the research network but remain **insufficient for a public-value production chain**.

## Consensus Safety Model

The v0.5 finalization path is:

```text
signed proposal
→ >2/3 signed prevotes
→ >2/3 signed precommits
→ finalized block
```

A validator does not sign a precommit until it has locally validated the prevote certificate for the exact proposal hash, height and round.

Before/while precommitting, it persists a local lock on that block hash. A restart does not erase the lock or phase-vote record.

### Conservative lock limitation

The current lock has **no proof-based unlock rule**. Once locked on a block hash at a height, a validator refuses to vote for another block hash at that height.

This is intentionally safety-biased, but it can hurt liveness. Under some failure/partition sequences the devnet may halt rather than unlock.

This is not a complete Tendermint/HotStuff-style or otherwise formally reviewed BFT implementation.

### Certified view changes

Later proposal rounds still require >2/3 signed view-change messages. View changes carry local lock metadata but do not override a local v0.5 lock.

### Equivocation evidence

The node records the first valid signed proposal for `(height, round, proposer)`. A conflicting valid signed proposal from the same proposer is stored as evidence and rejected for voting.

There is no automatic slashing, validator removal or evidence gossip/consensus processing.

## Persistent Consensus State

SQLite persists:

- local prevotes,
- local precommits,
- local consensus locks,
- consensus round advancement,
- local view-change actions,
- proposal/equivocation records,
- consensus event journal entries.

This improves restart safety, but SQLite remains a development storage choice and is not a production storage architecture decision.

## Network Risk

Validator communication still uses ordinary HTTP and static peer URLs. Consensus objects are signed, but the transport does **not** yet provide:

- encryption,
- mutual validator authentication,
- peer identity handshakes,
- certificate/key rotation,
- connection/rate limits,
- eclipse/Sybil defenses,
- authenticated peer telemetry.

The `/internal/*` endpoints are development-only and should not be publicly exposed.

## Private Keys

`runtime/` contains generated devnet validator/treasury keys and is git-ignored.

Rules:

1. Never commit private keys, seed phrases or production secrets.
2. Never reuse bootstrap/devnet keys on future public testnet/mainnet networks.
3. Do not expose validator key files through HTTP/static hosting.
4. Production key backups require encrypted, access-controlled storage.
5. Evaluate HSM/remote-signer designs before production.

## Monitoring / DoS Limitations

`/health`, `/status`, `/peers`, `/metrics`, `/consensus/events` and `/evidence` are useful development diagnostics, but they are not production observability/security infrastructure.

Before public testnet, add explicit controls for request size, transaction/memo size, certificate size, RPC rate, mempool size, concurrent connections, sync bandwidth and consensus-request frequency.

## State / Recovery Risk

v0.5 still lacks:

- signed state snapshots,
- verified fast state sync,
- pruning/archival policy,
- corruption recovery procedures,
- crash-consistency stress testing,
- long-running restart/partition tests.

## Economic Security

The devnet has no staking, slashing, inflation or on-chain governance. Fees are credited to the finalized block proposer.

No production economics or investment value should be inferred from the devnet implementation.

## Smart Contracts

No smart-contract VM is included. Adding one should require a separate threat model, deterministic execution specification, sandbox design, resource/gas model and independent review.

## Required Before Public Testnet

- reviewed cross-round unlock/mature BFT design,
- authenticated validator identity,
- encrypted validator transport,
- state snapshot/recovery design,
- parser fuzzing and malformed-message testing,
- partition/restart/load testing,
- RPC abuse controls,
- key-management runbook,
- reproducible build/container review,
- external consensus/network review.

## Required Before Mainnet

A production-value launch should require a long-lived public testnet and independent review of consensus, cryptography, P2P networking, storage, key management, RPC exposure, incident response and economic design.

Security findings should be reported through the repository-level [`SECURITY.md`](../SECURITY.md) process.
