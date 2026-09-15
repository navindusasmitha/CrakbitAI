# Crakbit Chain Devnet Specification v0.1

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
signature
hash
```

The block proposer signs canonical JSON of the block fields excluding `signature` and `hash`.

The block hash is SHA-256 over the canonical signed block payload.

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

## Consensus — Development PoA

The local devnet uses deterministic round-robin Proof of Authority:

```text
validator_index = (height - 1) mod validator_count
```

Only the configured validator for that height may sign the next block.

Nodes validate proposer identity, proposer public key, signature, height, previous hash, transaction root, state root and all transactions before committing a block.

### Consensus limitation

This mechanism does **not** provide BFT quorum voting/finality. It is intended for local development only. A public Crakbit network requires a reviewed BFT/PoS consensus design and adversarial testing.

## Genesis

Genesis defines:

- chain identity
- native unit metadata
- max genesis supply
- block interval
- minimum fee
- validator set and peer URLs
- initial account allocations

The database stores a genesis fingerprint and refuses to open against a different genesis configuration.

## Fees

Transaction fees are credited to the block proposer in the current prototype. There is no inflation, mint transaction or post-genesis issuance path implemented in v0.1.

This fee model is experimental and not final token economics.

## Storage

The local implementation uses SQLite with tables for:

- metadata
- accounts
- blocks
- transactions

SQLite is suitable for the current research prototype but the production storage architecture remains open.

## Peer Synchronization

Configured validator peers expose development HTTP endpoints. Nodes:

1. query peer status,
2. compare chain heights,
3. request missing blocks sequentially,
4. validate each block locally before applying it.

New blocks and transactions are also best-effort broadcast to configured peers.

The current transport is not authenticated and must not be treated as production P2P networking.

## RPC

Public development endpoints:

- `GET /status`
- `GET /balance/{address}`
- `GET /blocks/{height}`
- `GET /transactions/{txid}`
- `POST /transactions`

Development peer endpoints:

- `POST /internal/transaction`
- `POST /internal/block`

The `/internal/*` API must not be publicly exposed in a production design.

## Upgrade Policy

There is currently no on-chain governance or protocol upgrade mechanism. Devnet changes are repository/code releases and may reset chain state.

## Mainnet Gate

This specification is insufficient for mainnet. At minimum, a production candidate requires:

- BFT/quorum finality
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
