# Crakbit Chain Devnet Specification v0.3

**Status:** research/devnet specification. Not a production protocol commitment.

## Network Identity

- Network name: `Crakbit Chain Devnet`
- Chain ID: `crakbit-devnet-1`
- Native development unit: `CRKBIT`
- Decimal precision: `8`
- Atomic units per CRKBIT: `100,000,000`
- Proposed devnet max genesis supply: `21,000,000 CRKBIT`
- Default block interval: `5,000 ms`
- Default view timeout: `10,000 ms`
- Default local validator set: `4`
- Default local quorum: `3`
- Address prefix: `crk1`

## Cryptography

The current prototype uses Ed25519 signatures through the Python `cryptography` library.

A public key is serialized as raw Ed25519 bytes and Base64 encoded for JSON transport. An account address is derived as:

```text
crk1 + first_40_hex_characters(SHA256(raw_public_key))
```

This address format is experimental and may change before public testnet/mainnet.

## Transaction Model

A transfer transaction contains:

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

The signature covers canonical JSON of every field except `signature`. The transaction ID is SHA-256 over canonical JSON of the complete signed transaction.

A transaction is valid only when chain ID, amount, fee, sender/public-key binding, Ed25519 signature, nonce and balance checks all pass.

The early mempool accepts only one pending transaction per sender.

## Block Model

A block contains:

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
commit_votes[]
```

The proposer signs canonical JSON of the proposal fields excluding `signature`, `hash` and `commit_votes`. Commit votes therefore do not alter the proposal hash.

## Commit Vote Model

Each validator commit vote contains:

```text
chain_id
height
round
block_hash
voter
public_key
signature
```

A vote is counted only when the validator is in genesis, the configured public key matches, the signature verifies, and the vote targets the exact block hash, height and round.

Duplicate validator votes inside a certificate are rejected.

## State Commitments

`tx_root` is a SHA-256 Merkle root over transaction IDs. `state_root` is currently a deterministic SHA-256 commitment over sorted `(address, balance, nonce)` tuples after simulating the proposed block.

This state-root design is a development commitment and is not a Merkleized account trie with account proofs.

## Consensus — Quorum Finality with Round-Based Proposer Failover

For height `H` and round `R`, the expected proposer is:

```text
validator_index = (H - 1 + R) mod validator_count
```

Every height starts at round `0`. If a node does not observe finalization before `view_timeout_ms`, it advances to the next round.

A proposal can be finalized only after it receives:

```text
floor(2 * validator_count / 3) + 1
```

valid signed commit votes.

For the default four-validator devnet, the commit threshold is `3 of 4`.

### Proposal/finalization flow

1. Nodes determine the expected proposer for the current height and round.
2. The expected proposer builds and signs a candidate block.
3. Each validator independently validates the proposal.
4. A validator signs at most one block hash for a specific `(height, round)`.
5. The proposer collects signed commit votes.
6. Once quorum is reached, the commit certificate is attached to the block.
7. The finalized block is broadcast.
8. Every receiving node re-validates the proposal and quorum certificate before state transition.
9. Catch-up synchronization downloads only finalized blocks and re-validates them locally.
10. If finalization does not occur before the view timeout, nodes advance to the next round and the next configured proposer.

## Persistent Same-Round Anti-Double-Vote State

v0.3 stores each local validator's voted block hash in SQLite keyed by:

```text
(height, round)
```

Before returning a signed vote, the node checks the persistent record. A conflicting hash at the same `(height, round)` is rejected. This means restarting a validator does not erase this same-round anti-double-vote protection.

Records for finalized heights may be pruned because the ledger will no longer accept proposals for those heights.

### Important limitation

This is **not** yet a full BFT locking/precommit protocol.

The current persistent record prevents conflicting votes only within the same round. It does not establish a cross-round lock or quorum-certified view-change proof. Therefore v0.3 must still be treated as a research/devnet consensus mechanism, not as a production Byzantine-fault-tolerant protocol.

## Round Advancement

A node tracks a local consensus round and a round start time. If the round remains unfinalized for at least `view_timeout_ms`, the local round increments.

A validator may accept a valid proposal for the next round and update its local round. Large arbitrary round jumps are rejected by the current node implementation.

Timeout coordination is intentionally simple and has not been formally analyzed for adversarial clock/network conditions.

## Genesis

Genesis defines:

- chain identity
- native unit metadata
- max genesis supply
- block interval
- view timeout
- minimum fee
- validator set and peer URLs
- initial allocations

Validator addresses must be unique. The database stores a genesis fingerprint and refuses to open against a different genesis configuration.

## Fees

Transaction fees are credited to the finalized block proposer. There is no post-genesis mint path, inflation system, staking, slashing or governance in v0.3.

This fee model is experimental and does not define final CRKBIT economics.

## Storage

The current SQLite state includes:

- metadata
- accounts
- blocks
- transactions
- persistent local same-round vote records

SQLite is suitable for the research devnet but is not a final production storage decision.

## Peer Synchronization and Monitoring

Configured validators communicate over development HTTP endpoints. Nodes perform finalized-block catch-up and best-effort transaction/block propagation.

Nodes also maintain cached peer telemetry including observed health, height and consensus round. This telemetry is operational only and must not be considered authenticated evidence because the transport is currently unauthenticated.

## RPC

Public development endpoints:

- `GET /health`
- `GET /status`
- `GET /validators`
- `GET /peers`
- `GET /balance/{address}`
- `GET /blocks/{height}`
- `GET /transactions/{txid}`
- `POST /transactions`

Development peer endpoints:

- `POST /internal/transaction`
- `POST /internal/proposal`
- `POST /internal/block`

The `/internal/*` endpoints must not be directly exposed as production peer networking.

## Known Consensus/Mainnet Gaps

v0.3 does not yet include:

- cross-round locking/precommit rules
- quorum-certified view-change messages
- formal safety/liveness proofs
- equivocation evidence or slashing
- authenticated/encrypted validator transport
- validator-set changes or stake weighting
- dynamic peer discovery
- state snapshots / fast state sync
- production DoS controls
- production key management
- production governance/upgrade process

## Mainnet Gate

A production candidate requires a mature and independently reviewed consensus implementation, authenticated networking, state recovery, adversarial testing, economic-security review, key-management standards, a long-lived public testnet and external security audits.
