# Crakbit Chain Devnet Specification v0.6

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

## Cryptography

The devnet uses Ed25519 signatures through Python's `cryptography` package. Transactions, proposals, prevotes, precommits, view-change messages, validator peer requests, identity handshakes and state snapshots are signed.

Current address derivation:

```text
crk1 + first_40_hex_characters(SHA256(raw_public_key))
```

The address format is experimental.

## Transaction Model

Transactions contain:

```text
chain_id
sender
recipient
amount
fee
nonce
public_key
memo
signature
```

Validation requires the correct chain ID, positive amount, minimum fee, sender/public-key binding, valid Ed25519 signature, exact next nonce and sufficient balance.

## Block Model

A block contains proposal fields plus certificates:

```text
chain_id
height
previous_hash
timestamp
proposer
proposer_public_key
transactions
tx_root
state_root
round
signature
hash
view_changes[]
prevote_votes[]
precommit_votes[]
```

The block hash covers the signed proposal payload. Certificates do not alter the block hash.

## Consensus Phase Vote

A phase vote contains:

```text
chain_id
height
round
phase          # prevote | precommit
block_hash
voter
public_key
signature
```

A phase certificate is valid only when it contains at least:

```text
floor(2 * validator_count / 3) + 1
```

unique valid validator signatures for the exact block hash, height, round and phase.

## Finalization Flow

For height `H` and round `R`:

```text
validator_index = (H - 1 + R) mod validator_count
```

The expected proposer constructs and signs a candidate. Validators then execute:

1. Validate proposal identity, signature, roots, transactions and any required view-change certificate.
2. Record the signed proposal for equivocation detection.
3. Enforce any persistent local consensus lock.
4. Sign at most one `prevote` for `(height, round)`.
5. Once a >2/3 prevote certificate exists, validate that certificate.
6. Sign at most one `precommit` for `(height, round)`.
7. Persist a local per-height lock on the precommitted block hash.
8. Finalize only when both the prevote and precommit certificates reach quorum.
9. Broadcast the finalized block including both certificates.
10. Receiving/syncing nodes revalidate the proposal and both certificates before applying state.

## Persistent Safety State

SQLite persists:

- local phase votes by `(height, round, phase)`
- per-height consensus locks
- local consensus round
- local view-change actions
- first-seen signed proposals
- equivocation evidence
- append-only consensus events

A process restart therefore does not erase local prevote/precommit anti-double-vote state or the local lock.

## Lock Rule

The devnet still uses a deliberately conservative rule:

- a validator that precommits block hash `X` at height `H` becomes locked on `X`;
- while that height remains unfinished, it refuses to prevote or precommit a different block hash;
- the lock may advance to a later round only for the same block hash.

This is safety-biased but incomplete. v0.6 does **not** define a mature proof-based unlock rule. Some failures may therefore halt the devnet.

## View Changes

A non-zero proposal round requires a signed view-change certificate. Each message includes the validator's current local lock metadata, if any.

View changes do not override the local lock. A later-round proposal that conflicts with a validator's lock is rejected.

## Validator Peer Request Authentication

v0.6 signs internal validator HTTP requests.

Each signed request commits to:

```text
method
path
SHA-256(request body)
validator address
timestamp_ms
nonce
```

The sender attaches request metadata in headers. The receiver verifies the validator belongs to genesis, checks the Ed25519 signature, checks timestamp freshness and rejects a duplicate nonce in the active replay cache.

This authenticates validator requests and protects body integrity. It does not encrypt transport.

### Identity handshake

`POST /internal/hello` provides a challenge/response handshake. The response signs:

```text
chain_id
validator address
validator public key
challenge
timestamp_ms
```

A peer-health check may use this to verify that the remote process controls the configured validator key.

### HTTPS enforcement

A node may enable:

```text
CRAKBIT_REQUIRE_PEER_TLS=1
```

or `--require-peer-tls`.

When enabled, non-local remote validator URLs must use `https://`. Certificate provisioning, mTLS and rotation are not implemented by the chain process itself.

## Signed Snapshot Format

`GET /snapshot/latest` returns an envelope containing:

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

Accounts are sorted by address. `accounts_root` is SHA-256 over canonical JSON of the ordered account list. `snapshot_hash` is SHA-256 over canonical JSON of the snapshot object. A configured validator signs the envelope metadata.

`crakchain snapshot-verify` verifies the chain identity, genesis fingerprint, account root, snapshot hash, signer membership and signature.

v0.6 does not implement snapshot quorum certification or snapshot import / fast state sync.

## Equivocation Evidence

The node stores the first valid signed proposal seen for `(height, round, proposer)`. A different valid signed proposal from the same proposer for that tuple is stored as evidence and rejected for voting.

No automatic slashing or validator removal exists.

## State / Fees

`tx_root` is a SHA-256 Merkle root over transaction IDs. `state_root` is a deterministic SHA-256 commitment over sorted `(address, balance, nonce)` state after simulation.

Transaction fees are credited to the finalized proposer. There is no staking, inflation, slashing or on-chain governance in v0.6.

## RPC

Public development endpoints include:

- `GET /health`
- `GET /status`
- `GET /validators`
- `GET /peers`
- `GET /evidence`
- `GET /consensus/events`
- `GET /metrics`
- `GET /metrics/prometheus`
- `GET /snapshot/latest`
- `GET /balance/{address}`
- `GET /blocks/{height}`
- `GET /transactions/{txid}`
- `POST /transactions`

Authenticated development peer endpoints include:

- `POST /internal/hello`
- `POST /internal/transaction`
- `POST /internal/view-change-request`
- `POST /internal/prevote`
- `POST /internal/precommit`
- `POST /internal/proposal`
- `POST /internal/block`

## Known Mainnet Blockers

v0.6 still lacks:

- a reviewed proof-based cross-round unlock rule or mature BFT implementation
- formal safety/liveness proof
- mutually authenticated encrypted validator transport
- validator certificate/key rotation
- durable/session-grade peer replay protection across restarts
- production DoS/rate controls
- snapshot quorum certification and verified fast state sync import
- production key management
- dynamic validator-set changes / staking economics
- governance / upgrade process
- long-running public testnet evidence
- independent audit

## Mainnet Gate

A production candidate requires mature independently reviewed consensus, authenticated encrypted networking, state recovery, adversarial/partition/fuzz/load testing, key-management standards, economic-security review, incident response, a long-lived public testnet and external security audits.