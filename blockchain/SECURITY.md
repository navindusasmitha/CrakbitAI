# Crakbit Chain Devnet Security Notes

The current Crakbit Chain implementation is a **research/devnet prototype**. It is not an audited production blockchain and must not be used to custody real value.

## Security Goals of v0.8

v0.8 retains the existing research consensus and authenticated validator-request protections while hardening snapshot transfer and recovery operations.

Current development protections include:

- Ed25519 signatures for transactions, proposals, prevotes, precommits and view changes,
- strict greater-than-two-thirds prevote/precommit certificates,
- certified later-round view changes,
- persistent anti-double-vote records and per-height research locks,
- authenticated validator internal HTTP requests,
- durable SQLite replay-nonce storage across validator restarts,
- signed validator challenge/response identity handshakes,
- quorum-certified state snapshots,
- snapshot import restricted to fresh databases,
- bounded snapshot-transfer chunk sizes and total artifact size,
- per-chunk SHA-256 plus complete artifact SHA-256 validation,
- resumable reuse of already-verified chunks for the same immutable bundle,
- crash-visible snapshot import sidecar journaling,
- explicit snapshot-base/history availability reporting,
- finalized-block revalidation during normal sync,
- validator health and Prometheus-style development telemetry.

These controls improve the research network but remain **insufficient for a public-value production chain**.

## Consensus Safety Limitation

The finalization path remains:

```text
signed proposal
→ >2/3 signed prevotes
→ >2/3 signed precommits
→ finalized block
```

The local consensus lock is still conservative. A validator that precommits one block hash at a height refuses to vote for a conflicting hash at that height. There is no mature proof-based cross-round unlock rule.

This can preserve local safety bias at the cost of liveness under some failure/partition sequences. It is not a complete formally reviewed Tendermint/HotStuff-style BFT implementation.

## Validator Transport

Application-level validator request authentication proves configured validator-key possession and request-body integrity. Durable replay nonces now survive process restarts.

The default local Docker network still uses ordinary HTTP. `--require-peer-tls` / `CRAKBIT_REQUIRE_PEER_TLS=1` can reject non-HTTPS peer URLs, but this does **not** provide a complete reviewed validator transport stack.

Missing items include:

- mutual TLS provisioning,
- certificate pinning,
- certificate/key rotation lifecycle,
- secure peer discovery,
- connection/rate limits,
- eclipse/Sybil defenses,
- transport-level session semantics.

## Snapshot Transfer Security

v0.8 adds a transport bundle around a signed validator snapshot envelope.

The manifest commits to:

- total serialized byte count,
- bounded chunk size,
- bounded chunk count,
- each chunk size/hash,
- the complete canonical artifact SHA-256.

A client must validate the manifest, every chunk and the complete artifact before JSON parsing. After reassembly, normal snapshot signature verification still applies. Transport hashes provide corruption/substitution detection; they do **not** replace validator signatures or quorum trust.

The server caches only a small number of recent immutable bundle byte streams. A bundle that is no longer cached must be regenerated through a new manifest request.

## Resumable Cache Security

`snapshot-fetch-chunked` reuses a cached chunk only when its exact expected size and SHA-256 still match the current manifest for the same artifact hash.

A new snapshot/artifact hash uses a separate cache path, so stale chunks from a different state are not silently mixed into the new transfer.

This is still a development transfer mechanism and does not yet include production bandwidth/rate controls.

## Snapshot Import Journal

The snapshot database update is performed inside a SQLite transaction. v0.8 additionally writes a sidecar journal before the mutation so an interrupted import is visible after process restart.

If the database already committed the same certificate, a repeated import verifies the local height/hash and removes the stale journal. If the database is still fresh, the same certificate can be retried. A journal referencing a different certificate blocks automatic overwrite and requires operator review.

The journal is operational metadata, not a consensus proof.

## Snapshot History Limitation

A quorum snapshot certifies current account state and finalized base hash. It does not reconstruct pre-snapshot block bodies or transaction rows.

Snapshot-aware history endpoints therefore distinguish:

- locally available post-snapshot block history,
- unavailable pre-snapshot local history,
- genuinely unknown future/missing blocks.

A production design still needs an archive/history synchronization model if complete historical queries are required.

## Private Keys

`runtime/` contains generated devnet validator/treasury keys and is git-ignored.

Rules:

1. Never commit private keys, seed phrases or production secrets.
2. Never reuse bootstrap/devnet keys on future public testnet/mainnet networks.
3. Do not expose validator key files through HTTP/static hosting.
4. Production key backups require encrypted, access-controlled storage.
5. Evaluate HSM/remote-signer designs before production.

## Monitoring / DoS Limitations

Development diagnostics are not production observability/security infrastructure. Before public testnet, explicit controls are still required for request size, transaction/memo size, snapshot size, RPC rate, mempool size, concurrent connections, sync bandwidth and consensus-request frequency.

## Required Before Public Testnet

- reviewed cross-round BFT lock/unlock or mature BFT core,
- mutually authenticated encrypted validator transport,
- certificate/key rotation and validator key-management runbook,
- crash/corruption/abrupt-power-loss recovery testing,
- partition/latency/Byzantine/load testing,
- RPC and snapshot-transfer abuse controls,
- archive/history synchronization policy,
- reproducible build/container review,
- external consensus/network review.

## Required Before Mainnet

A production-value launch should require a long-lived public testnet and independent review of consensus, cryptography, P2P networking, storage, key management, RPC exposure, incident response and economic design.

Security findings should be reported through the repository-level [`SECURITY.md`](../SECURITY.md) process.
