# Crakbit Chain Devnet Specification v0.7

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

The devnet uses Ed25519 signatures through Python's `cryptography` package. Transactions, proposals, prevotes, precommits, view changes, validator peer requests, identity handshakes and state snapshots are signed.

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

## Block / Consensus Model

A block contains the signed proposal plus certified view-change, prevote and precommit data. The finalization pipeline is:

```text
proposal
  -> >2/3 prevote certificate
  -> >2/3 precommit certificate
  -> finalized block
```

For height `H` and round `R`, proposer selection remains:

```text
validator_index = (H - 1 + R) mod validator_count
```

Validators persist phase-vote decisions and a per-height local consensus lock. A non-zero proposal round requires the existing >2/3 signed view-change certificate.

## Current Lock Rule

The current research rule remains conservative:

- a validator that precommits block hash `X` at height `H` becomes locked on `X`;
- while `H` is unfinished, the validator refuses to prevote/precommit a different hash;
- the lock may advance to a later round only for the same hash.

v0.7 does **not** introduce a mature proof-based cross-round unlock rule. This remains a mainnet blocker and can sacrifice liveness during some partition/failure sequences.

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

The receiver verifies validator membership, Ed25519 signature, timestamp freshness and nonce uniqueness.

### Persistent replay cache

v0.7 persists accepted `(validator, nonce)` replay keys when `CRAKBIT_DATA_DIR` is configured. The cache is stored separately from chain state at:

```text
<CRAKBIT_DATA_DIR>/peer-replay.sqlite3
```

Old nonces are pruned after the bounded replay-retention window. This prevents a process restart from immediately resetting replay history.

This is still application-layer request authentication; it does not replace encrypted transport or mTLS.

## Validator Identity Handshake

`POST /internal/hello` remains a signed challenge/response handshake over chain ID, validator identity, challenge and timestamp. It demonstrates possession of the configured validator private key.

## HTTPS Enforcement

`CRAKBIT_REQUIRE_PEER_TLS=1` or `--require-peer-tls` rejects non-HTTPS configured peer URLs.

v0.7 does not provision certificates, pin certificates, require client certificates, or implement certificate rotation. Those remain future transport-hardening tasks.

## State Snapshot Format

A validator snapshot contains:

```text
format = crakbit-state-snapshot-v1
chain_id
genesis_fingerprint
height
last_hash
accounts_root
accounts[]
```

Accounts are strictly sorted by address. The root is SHA-256 over canonical JSON of the account list. The snapshot hash is SHA-256 over canonical JSON of the snapshot object.

A validator signs an envelope containing the snapshot, snapshot hash, signer address and signer public key.

Validation also checks conservation of the currently issued genesis supply because v0.7 has no mint/burn path.

## Quorum Snapshot Certificate

v0.7 adds:

```text
format = crakbit-snapshot-certificate-v1
snapshot
snapshot_hash
quorum
signatures[]
```

Each signature entry contains:

```text
signer
public_key
signature
```

A certificate is valid only if at least:

```text
floor(2 * validator_count / 3) + 1
```

unique configured validators signed the **same snapshot hash**.

When gathering snapshots, signatures are grouped by snapshot hash. Signatures from different state roots/heights cannot be combined to reach quorum.

## Snapshot Import / Fast-State Bootstrap

A quorum-certified snapshot may be imported only into a local ledger that is still at height `0` with the zero previous hash.

Import replaces the genesis account table with the certified account state, sets local metadata to the certified height/hash and records:

```text
snapshot_base_height
snapshot_base_hash
snapshot_accounts_root
snapshot_certificate_hash
```

Local consensus scratch state is cleared during the import.

The import does **not** reconstruct historical blocks or transactions before `snapshot_base_height`. The node can synchronize blocks newer than the snapshot base using normal finalized-block validation.

## Recovery Safety Rule

A snapshot import refuses to overwrite a non-empty local chain. Operators must intentionally bootstrap a fresh database. This prevents the recovery command from silently replacing locally finalized history.

## RPC / CLI Additions

Public development endpoints include the existing RPC plus:

- `GET /snapshot/latest`
- `GET /recovery/status`

CLI recovery commands include:

- `crakchain snapshot-fetch`
- `crakchain snapshot-verify`
- `crakchain snapshot-import`
- `crakchain node --bootstrap-snapshot ...`

## Equivocation Evidence

The node continues to persist conflicting signed proposals for the same `(height, round, proposer)` tuple. Automatic slashing/removal remains unimplemented.

## State / Fees

`tx_root` is a SHA-256 Merkle root over transaction IDs. `state_root` is currently a deterministic SHA-256 commitment over sorted account tuples after simulation.

Transaction fees are credited to the finalized proposer. There is no staking, inflation, slashing or on-chain governance in v0.7.

## Known Mainnet Blockers

v0.7 still lacks:

- a reviewed proof-based cross-round unlock rule or mature BFT implementation,
- formal safety/liveness proof,
- mutually authenticated TLS validator transport and certificate rotation,
- snapshot chunking/resume/size controls,
- full historical state reconstruction from snapshots,
- production RPC DoS/rate controls,
- production key management,
- dynamic validator-set changes / staking economics,
- governance / upgrade process,
- long-running Byzantine/partition/load test evidence,
- independent consensus/network audit.

## Mainnet Gate

A production candidate requires mature independently reviewed consensus, authenticated encrypted networking, robust recovery/state sync, adversarial/fuzz/partition/load testing, production key-management standards, economic-security review, incident response, a long-lived public testnet and external security audits.
