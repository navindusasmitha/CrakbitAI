# Crakbit Chain Devnet Specification v0.2

**Status:** research/devnet specification. Not a production protocol commitment.

## Network Identity

- Network name: `Crakbit Chain Devnet`
- Chain ID: `crakbit-devnet-1`
- Native development unit: `CRKBIT`
- Decimal precision: `8`
- Atomic units per CRKBIT: `100,000,000`
- Proposed devnet max genesis supply: `21,000,000 CRKBIT`
- Default block interval: `5,000 ms`
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
amount        # integer atomic units
fee           # integer atomic units
nonce         # sender sequence number
public_key
memo
signature
```

The signature covers canonical JSON of every field except `signature`.

The transaction ID is SHA-256 over canonical JSON of the complete signed transaction.

### Transaction validity

A transaction is accepted only if:

1. `chain_id` matches genesis.
2. `amount` is positive.
3. `fee` is at least the configured minimum.
4. sender and recipient differ.
5. sender is derived from the supplied public key.
6. the Ed25519 signature verifies.
7. nonce equals current account nonce + 1.
8. sender balance covers `amount + fee`.

The early mempool accepts only one pending transaction per sender. This is a development simplification.

## Account State

Each account stores:

```text
address
balance
nonce
```

Balances and fees are stored only as integers; floating-point arithmetic is not used by the ledger.

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

The block proposer signs canonical JSON of the block fields excluding `signature`, `hash` and `commit_votes`.

The block hash is SHA-256 over the signed proposal payload. Commit votes do not change the block hash.

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

The signature covers all vote fields except `signature`.

A vote is valid only when:

1. the voter is present in the genesis validator set,
2. the supplied public key matches that configured validator,
3. the voter address is derived from the supplied public key,
4. the Ed25519 signature verifies,
5. `chain_id`, `height`, `round` and `block_hash` match the proposed block,
6. a validator is counted at most once in a commit certificate.

## Transaction Root

`tx_root` is a binary SHA-256 Merkle root constructed from transaction IDs. For an odd number of nodes in a Merkle layer, the final node is duplicated.

An empty block uses SHA-256 of the empty byte string as the transaction root.

## State Root

The current state root is a deterministic SHA-256 hash over sorted tuples of:

```text
(address, balance, nonce)
```

The root is calculated after simulating all block transactions and proposer fee credits.

This is a development commitment mechanism, not a Merkleized account trie and does not currently provide account proofs.

## Consensus — Round-Robin PoA + Signed Quorum Finality

The v0.2 devnet keeps deterministic round-robin proposal selection:

```text
validator_index = (height - 1) mod validator_count
```

Only the configured validator for a height may propose and sign the block proposal.

Before a proposal can be committed, validators independently validate the proposal and sign a commit vote for its block hash.

The commit threshold is:

```text
floor(2 * validator_count / 3) + 1
```

This is a strict greater-than-two-thirds validator threshold.

For the default three-validator devnet, all three validator signatures are therefore required to finalize a block.

### Proposal flow

1. The deterministic proposer constructs and signs a candidate block.
2. The proposer validates and signs its own commit vote.
3. The proposer submits the candidate to configured validator peers.
4. Each peer re-validates height, previous hash, proposer identity, block signature, transaction root, state root and transactions.
5. A peer that accepts the proposal signs a commit vote.
6. The proposer verifies returned votes.
7. Once quorum is reached, the block is finalized with the commit certificate attached.
8. Finalized blocks are broadcast to peers.
9. Receiving peers re-validate both the proposal and commit certificate before applying state changes.
10. Catch-up synchronization downloads only finalized blocks that include a valid quorum certificate.

### Double-vote guard

A running validator records the block hash it voted for at a given `(height, round)` and refuses to sign a conflicting proposal at that same height and round.

This protection is currently in-memory only. Validator restart safety, durable consensus state and evidence/slashing are later work.

### Important consensus limitations

v0.2 is **not a complete production BFT consensus protocol**.

It does not yet implement:

- view/round changes when a proposer is unavailable,
- a durable lock/precommit state machine,
- evidence and slashing,
- weighted stake voting,
- fork-choice recovery from arbitrary partitions,
- validator-set changes,
- durable double-vote prevention across restarts,
- formal safety/liveness proofs.

The chain may halt if the scheduled proposer or enough validators are unavailable. The v0.2 change improves finality safety over proposer-only PoA but is still a development step.

## Genesis

Genesis defines:

- chain identity
- native unit metadata
- max genesis supply
- block interval
- minimum fee
- validator set and peer URLs
- initial account allocations

Validator addresses must be unique.

The database stores a genesis fingerprint and refuses to open against a different genesis configuration.

## Fees

Transaction fees are credited to the block proposer in the current prototype. There is no inflation, mint transaction or post-genesis issuance path implemented in v0.2.

This fee model is experimental and not final token economics.

## Storage

The local implementation uses SQLite with tables for:

- metadata
- accounts
- blocks
- transactions

Finalized blocks are stored with their commit vote certificate.

SQLite is suitable for the current research prototype but the production storage architecture remains open.

## Peer Synchronization

Configured validator peers expose development HTTP endpoints. Nodes:

1. query peer status,
2. compare finalized chain heights,
3. request missing finalized blocks sequentially,
4. validate the proposal and quorum certificate locally before applying it.

New transactions and finalized blocks are also best-effort broadcast to configured peers.

The current transport is not authenticated or encrypted and must not be treated as production P2P networking.

## RPC

Public development endpoints:

- `GET /status`
- `GET /validators`
- `GET /balance/{address}`
- `GET /blocks/{height}`
- `GET /transactions/{txid}`
- `POST /transactions`

Development peer endpoints:

- `POST /internal/transaction`
- `POST /internal/proposal`
- `POST /internal/block`

The `/internal/*` API must not be directly exposed to the public internet in a production design.

## Upgrade Policy

There is currently no on-chain governance or protocol upgrade mechanism. Devnet changes are repository/code releases and may reset chain state.

## Mainnet Gate

This specification remains insufficient for mainnet. At minimum, a production candidate requires:

- mature/reviewed BFT or PoS consensus with proposer failover
- durable consensus state and equivocation handling
- authenticated/encrypted P2P transport
- peer discovery and eclipse/Sybil mitigations
- state snapshot and recovery design
- stronger mempool rules
- DoS/resource limits
- key-management standards
- upgrade/governance process
- economic-security analysis
- extensive fuzz/adversarial testing
- independent security review
- long-lived public testnet
