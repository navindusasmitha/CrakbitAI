# Crakbit Chain Devnet Specification v0.8

**Status:** research/devnet specification. Not a production protocol commitment.

## Network Identity

- Network: `Crakbit Chain Devnet`
- Chain ID: `crakbit-devnet-1`
- Native development unit: `CRKBIT`
- Decimals: `8`
- Atomic units per CRKBIT: `100,000,000`
- Proposed devnet max genesis supply: `21,000,000 CRKBIT`
- Default validator set: `4`
- Default quorum: `3`
- Default block interval: `5,000 ms`
- Default view timeout: `10,000 ms`
- Address prefix: `crk1`

## Consensus

The research consensus path remains:

```text
signed proposal
→ strict >2/3 signed prevotes
→ strict >2/3 signed precommits
→ finalized block
```

Later rounds require certified view changes. Local prevote/precommit decisions and per-height locks are persisted. The current lock remains deliberately conservative and does not yet define a mature proof-based cross-round unlock rule.

## Cryptography

Ed25519 signatures are used for transactions, proposals, phase votes, view changes, validator request authentication, identity handshakes and state snapshots.

Current experimental address derivation:

```text
crk1 + first_40_hex_characters(SHA256(raw_public_key))
```

## Validator Peer Authentication

Internal validator requests commit to:

```text
method
path
SHA-256(request body)
validator address
timestamp_ms
nonce
```

Receivers verify validator membership/signature, timestamp freshness and replay state. v0.7+ persists accepted replay nonces in SQLite when the node data directory is configured.

The signed challenge/response identity handshake remains available. HTTPS peer-URL enforcement is optional, but certificate provisioning, pinning and rotation are not yet protocol-managed.

## Quorum-Certified Snapshot Format

A single validator snapshot contains:

```text
snapshot:
  format
  chain_id
  genesis_fingerprint
  height
  last_hash
  accounts_root
  accounts[]
snapshot_hash
signer
public_key
signature
```

A quorum certificate contains the exact snapshot body/hash and at least the configured strict `>2/3` unique validator signatures over that identical snapshot.

Verification checks chain identity, genesis fingerprint, sorted accounts, account root, issued-supply conservation, snapshot hash, validator identities/public keys, signatures and quorum.

## v0.8 Snapshot Transfer Bundle

Large signed snapshot envelopes may be framed as:

```text
format = crakbit-snapshot-bundle-v1
artifact_sha256
total_bytes
chunk_size
total_chunks
chunks[]:
  index
  size
  sha256
```

The canonical JSON bytes of the signed validator envelope are split into bounded chunks. Each chunk is verified independently and the full byte stream must also match `artifact_sha256` before JSON parsing.

Development endpoints:

```text
GET /snapshot/bundle/manifest
GET /snapshot/bundle/chunk/{artifact_sha256}/{index}
```

The server keeps only a small in-memory cache of recently generated immutable bundles. A client must request a new manifest if that bundle has expired from cache.

The CLI command `snapshot-fetch-chunked` caches chunks under validator + artifact hash and reuses only chunks whose size and SHA-256 still match the manifest.

## Snapshot Import Semantics

A quorum-certified snapshot may be imported only into a fresh height-zero database.

The imported database receives:

```text
snapshot_base_height
snapshot_base_hash
snapshot_accounts_root
snapshot_certificate_hash
```

and the certified account balances/nonces. Pre-snapshot historical block bodies and transaction rows are **not** reconstructed.

### Import journal

Before database mutation, v0.8 writes a sidecar intent journal:

```text
snapshot-import.journal.json
```

The journal identifies the target certificate hash, state root and height/hash. SQLite transaction atomicity remains authoritative for database consistency. After successful commit the journal is removed.

If a matching journal remains after a crash, the same certificate may safely reconcile a completed commit or retry a fresh database whose transaction rolled back. A different certificate is rejected until operator review.

## Snapshot-Base-Aware History

Recovery-aware endpoints:

```text
GET /history/status
GET /history/block/{height}
```

A snapshot-bootstrapped node exposes the snapshot base height/hash and the start of locally available post-snapshot full block history. A missing block at or below the snapshot base is reported as unavailable local pre-snapshot history rather than as evidence that the block never existed.

## State / Fees

`tx_root` is a SHA-256 Merkle root over transaction IDs. `state_root` is a deterministic SHA-256 commitment over sorted `(address, balance, nonce)` state after simulation.

Transaction fees are credited to the finalized proposer. There is no production staking, inflation, slashing or on-chain governance in v0.8.

## RPC Additions in v0.8

In addition to existing development RPCs:

- `GET /snapshot/bundle/manifest`
- `GET /snapshot/bundle/chunk/{artifact_sha256}/{index}`
- `GET /recovery/import-journal`
- `GET /history/status`
- `GET /history/block/{height}`

## Known Mainnet Blockers

v0.8 still lacks:

- reviewed proof-based cross-round BFT lock/unlock or a mature BFT core
- formal safety/liveness proof
- mutually authenticated encrypted validator transport with certificate lifecycle
- production DoS/rate/bandwidth controls
- historical archive synchronization for snapshot-bootstrapped nodes
- production key management
- dynamic validator-set changes / staking economics
- governance / upgrade process
- long-running adversarial public-testnet evidence
- independent consensus/network audit

## Mainnet Gate

A production candidate requires mature independently reviewed consensus, authenticated encrypted networking, robust state/history recovery, adversarial/partition/fuzz/load testing, key-management standards, economic-security review, incident response, a long-lived public testnet and external security audits.
