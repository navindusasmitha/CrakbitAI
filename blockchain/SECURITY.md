# Crakbit Chain Devnet Security Notes

The current Crakbit Chain implementation is a **research/devnet prototype**. It is not an audited production blockchain and must not be used to custody real value.

## Security Goals of v0.6

v0.6 retains the v0.5 multiphase consensus safeguards and adds application-level validator-network authentication plus signed state-snapshot verification.

Current development protections include:

- Ed25519 signatures for transactions, proposals, prevotes, precommits and view changes,
- sender/public-key binding,
- nonce-based transaction replay protection,
- deterministic transaction/state commitments,
- strict greater-than-two-thirds prevote quorum,
- strict greater-than-two-thirds precommit quorum,
- certified non-zero-round view changes,
- persistent same-phase anti-double-vote records,
- persistent per-height consensus locks,
- persistent consensus event history,
- conflicting signed-proposal evidence,
- Ed25519-authenticated `/internal/*` validator requests,
- peer request signatures bound to method, path and request-body hash,
- timestamp-window and nonce replay checks for validator HTTP requests,
- signed validator challenge/response identity handshake,
- optional HTTPS peer-URL enforcement,
- validator-signed state snapshot export and verification,
- finalized-block revalidation during sync,
- validator health/height/round telemetry.

These controls improve the research network but remain **insufficient for a public-value production chain**.

## Consensus Safety Model

The finalization path remains:

```text
signed proposal
→ >2/3 signed prevotes
→ >2/3 signed precommits
→ finalized block
```

A validator does not sign a precommit until it has locally validated the prevote certificate for the exact proposal hash, height and round.

Before/while precommitting, it persists a local lock on that block hash. A restart does not erase the lock or phase-vote record.

### Conservative lock limitation

The current lock has **no mature proof-based unlock rule**. Once locked on a block hash at a height, a validator refuses to vote for another block hash at that height.

This is intentionally safety-biased, but it can hurt liveness. Under some failure/partition sequences the devnet may halt rather than unlock.

This is not a complete Tendermint/HotStuff-style or otherwise formally reviewed BFT implementation.

### Certified view changes

Later proposal rounds require >2/3 signed view-change messages. View changes carry local lock metadata but do not override the current conservative lock.

### Equivocation evidence

The node records the first valid signed proposal for `(height, round, proposer)`. A conflicting valid signed proposal from the same proposer is stored as evidence and rejected for voting.

There is no automatic slashing, validator removal or evidence gossip/consensus processing.

## Validator Request Authentication

v0.6 signs validator-to-validator internal HTTP requests. The signed request commitment includes:

```text
HTTP method
request path
SHA-256(request body)
validator address
timestamp
random nonce
```

The receiver checks that the signer belongs to the configured validator set, verifies the Ed25519 signature, rejects timestamps outside the configured window and rejects a recently repeated nonce.

### Replay limitation

The nonce replay cache is currently process-local. Restarting a node clears that in-memory cache. Timestamp validation bounds the replay window, but this is not equivalent to a mature mutually authenticated session protocol with durable anti-replay state.

## Validator Identity Handshake

`POST /internal/hello` implements a signed challenge/response handshake. The signed response binds chain ID, validator address/public key, caller challenge and timestamp.

This proves possession of the configured validator private key at handshake time.

Peer status telemetry fetched afterward remains operational data and should not be treated as signed consensus evidence.

## Encryption / TLS Limitations

The default local Docker devnet still uses ordinary HTTP.

Operators can enable:

```text
CRAKBIT_REQUIRE_PEER_TLS=1
```

or the CLI flag:

```text
--require-peer-tls
```

which makes a node reject non-HTTPS validator peer URLs.

This is **URL-policy enforcement only**. It does not automatically provide:

- TLS certificate issuance,
- mutual TLS,
- certificate pinning,
- certificate/key rotation,
- secure discovery,
- session-level replay protection,
- eclipse/Sybil resistance.

A future public testnet requires a reviewed mutually authenticated encrypted validator transport.

## Signed Snapshot Security

`GET /snapshot/latest` exports a validator-signed snapshot envelope containing chain identity, genesis fingerprint, finalized height/hash, sorted account balances/nonces, a deterministic accounts root and a snapshot hash.

`crakchain snapshot-verify` verifies the snapshot contents and validator signature against genesis.

v0.6 does **not** implement snapshot quorum certification or snapshot import / fast state sync. A single validator signature is useful for integrity testing but is not enough to establish production trust in state recovery.

## Persistent Consensus State

SQLite persists:

- local prevotes,
- local precommits,
- local consensus locks,
- consensus round advancement,
- local view-change actions,
- proposal/equivocation records,
- consensus event journal entries.

SQLite remains a development storage choice and is not a production storage architecture decision.

## Private Keys

`runtime/` contains generated devnet validator/treasury keys and is git-ignored.

Rules:

1. Never commit private keys, seed phrases or production secrets.
2. Never reuse bootstrap/devnet keys on future public testnet/mainnet networks.
3. Do not expose validator key files through HTTP/static hosting.
4. Production key backups require encrypted, access-controlled storage.
5. Evaluate HSM/remote-signer designs before production.

## Monitoring / DoS Limitations

`/health`, `/status`, `/peers`, `/metrics`, `/metrics/prometheus`, `/consensus/events` and `/evidence` are development diagnostics, not production observability/security infrastructure.

Before public testnet, add explicit controls for request size, transaction/memo size, certificate size, RPC rate, mempool size, concurrent connections, sync bandwidth and consensus-request frequency.

## State / Recovery Risk

v0.6 now has signed snapshot export/verification but still lacks:

- snapshot quorum certification,
- verified snapshot import / fast state sync,
- pruning/archival policy,
- corruption recovery procedures,
- crash-consistency stress testing,
- long-running restart/partition tests.

## Economic Security

The devnet has no staking, slashing, inflation or on-chain governance. Fees are credited to the finalized block proposer.

No production economics or investment value should be inferred from the devnet implementation.

## Required Before Public Testnet

- reviewed cross-round unlock/mature BFT design,
- mutually authenticated encrypted validator transport,
- certificate/key rotation and key-management runbook,
- durable/session-grade replay protection,
- snapshot quorum and recovery/import design,
- parser fuzzing and malformed-message testing,
- partition/restart/load testing,
- RPC abuse controls,
- reproducible build/container review,
- external consensus/network review.

## Required Before Mainnet

A production-value launch should require a long-lived public testnet and independent review of consensus, cryptography, P2P networking, storage, key management, RPC exposure, incident response and economic design.

Security findings should be reported through the repository-level [`SECURITY.md`](../SECURITY.md) process.