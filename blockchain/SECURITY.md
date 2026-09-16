# Crakbit Chain Devnet Security Notes

The current Crakbit Chain implementation is a **research/devnet prototype**. It is not an audited production blockchain and must not be used to custody real value.

## Security Goals of v0.7

v0.7 keeps the v0.6 multiphase consensus and signed validator-network controls while improving replay durability and state-recovery trust.

Current development protections include:

- Ed25519 signatures for transactions, proposals, prevotes, precommits and view changes,
- strict greater-than-two-thirds prevote and precommit certificates,
- certified later-round view changes,
- persistent same-phase anti-double-vote records,
- persistent per-height consensus locks,
- persistent consensus event history,
- conflicting signed-proposal evidence,
- Ed25519-authenticated `/internal/*` validator requests,
- request signatures bound to method, path, body hash, validator, timestamp and nonce,
- **SQLite-persistent replay-nonce tracking across process restarts**,
- signed validator challenge/response identity handshake,
- optional HTTPS peer-URL enforcement,
- validator-signed state snapshots,
- **strict >2/3 quorum snapshot certificates**, 
- **fresh-database snapshot bootstrap/import**, 
- issued-supply conservation checks during snapshot verification,
- finalized-block revalidation during normal sync,
- validator metrics and recovery metadata.

These controls improve the research network but remain **insufficient for a public-value production chain**.

## Consensus Safety Model

The finalization path remains:

```text
signed proposal
→ >2/3 signed prevotes
→ >2/3 signed precommits
→ finalized block
```

### Conservative lock limitation

The current lock still has **no mature proof-based cross-round unlock rule**. Once locked on a block hash at a height, a validator refuses to vote for another block hash at that height.

This is safety-biased and may halt liveness during some partition/failure sequences. v0.7 must not be described as a complete Tendermint/HotStuff-style or formally reviewed BFT protocol.

## Validator Request Authentication

Internal requests are authenticated at the application layer. The receiver verifies validator membership, Ed25519 signature, body binding, timestamp freshness and nonce uniqueness.

### Durable replay cache

When `CRAKBIT_DATA_DIR` is configured, accepted replay keys are persisted in `peer-replay.sqlite3`. A simple process restart therefore does not erase recent nonce history.

This is still not equivalent to a reviewed mutually authenticated transport/session protocol. Replay protection depends on clock-window assumptions and the integrity of the local replay database.

## Encryption / TLS Limitations

The default Docker devnet still uses ordinary HTTP. `--require-peer-tls` / `CRAKBIT_REQUIRE_PEER_TLS=1` rejects non-HTTPS configured peers, but it does **not** automatically provide:

- mutual TLS,
- certificate pinning,
- certificate issuance,
- certificate/key rotation,
- secure peer discovery,
- eclipse/Sybil defenses.

A public testnet should use a reviewed mutually authenticated encrypted validator transport.

## Quorum Snapshot Security

A single validator-signed snapshot is no longer sufficient for v0.7 recovery bootstrap.

`build_snapshot_certificate` groups signatures by exact snapshot hash and requires the configured strict `>2/3` validator quorum. Signatures over different state roots/heights cannot be combined.

Snapshot verification checks:

- chain ID,
- genesis fingerprint,
- sorted account encoding,
- account root,
- total issued supply conservation,
- snapshot hash,
- configured validator identity/public key,
- signature validity,
- unique signer count,
- validator quorum.

## Snapshot Import Safety

Snapshot import is restricted to a fresh height-zero database. The command refuses to overwrite a node that already has local finalized height.

The imported certificate establishes an account-state base height and block hash. It does **not** recreate historical blocks/transactions before that height. Operators and API users must understand that pre-snapshot historical queries may be unavailable locally.

Snapshot transfer is not yet chunked/resumable and has no production bandwidth/size policy.

## Private Keys

`runtime/` contains generated devnet validator/treasury keys and is git-ignored.

Rules:

1. Never commit private keys, seed phrases or production secrets.
2. Never reuse bootstrap/devnet keys on future public testnet/mainnet networks.
3. Do not expose validator key files through HTTP/static hosting.
4. Production key backups require encrypted, access-controlled storage.
5. Evaluate HSM/remote-signer designs before production.

## Monitoring / DoS Limitations

Current health, metrics, evidence and recovery endpoints are development diagnostics. Before public testnet, add explicit controls for request body size, transaction/memo size, snapshot/certificate size, RPC rate, mempool size, concurrent connections, sync bandwidth and consensus-request frequency.

## State / Recovery Risks Still Open

v0.7 still lacks:

- chunked/resumable snapshot transfer,
- snapshot retention/pruning policy,
- explicit historical API behavior below snapshot base height,
- corruption-repair tooling,
- interrupted-import recovery journal,
- long-running crash/restart testing,
- adversarial partition/latency/Byzantine testing.

## Economic Security

The devnet has no staking, slashing, inflation or on-chain governance. Fees are credited to the finalized block proposer.

No production economics or investment value should be inferred from the devnet implementation.

## Required Before Public Testnet

- reviewed cross-round unlock or mature BFT core,
- mutually authenticated encrypted validator transport,
- certificate/key rotation and production key-management runbook,
- snapshot transfer/retention hardening,
- parser fuzzing and malformed-message testing,
- partition/restart/corruption/load testing,
- RPC abuse controls,
- reproducible build/container review,
- external consensus/network review.

## Required Before Mainnet

A production-value launch should require a long-lived public testnet and independent review of consensus, cryptography, P2P networking, storage, key management, RPC exposure, incident response and economic design.

Security findings should be reported through the repository-level [`SECURITY.md`](../SECURITY.md) process.
