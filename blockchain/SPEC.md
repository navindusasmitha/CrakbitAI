# Crakbit Chain Devnet Specification v0.4

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

The prototype uses Ed25519 signatures through Python's `cryptography` library. Transaction, block, commit-vote and view-change messages are signed.

Addresses are currently derived as:

```text
crk1 + first_40_hex_characters(SHA256(raw_public_key))
```

The address format remains experimental.

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

Transaction validity includes chain ID, positive amount, minimum fee, sender/public-key binding, signature, exact next nonce and sufficient balance.

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
view_changes[]
```

The proposal signature and block hash cover the proposal fields but not the later commit certificate or view-change certificate. A non-zero-round block must carry a valid view-change certificate for its round.

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

A commit certificate requires:

```text
floor(2 * validator_count / 3) + 1
```

unique valid validator signatures for the exact block hash, height and round.

## View-Change Model

A signed view-change message contains:

```text
chain_id
height
from_round
to_round
voter
public_key
locked_round
locked_block_hash
signature
```

The current protocol only permits a one-round transition:

```text
to_round = from_round + 1
```

A validator may sign a view change after its local view timeout. The message also publishes the validator's current conservative local lock, if one exists.

A view-change certificate requires the same strict greater-than-two-thirds validator threshold used for block finalization.

For a proposal at round `R > 0`, every attached view-change message must target:

```text
from_round = R - 1
to_round   = R
```

and the certificate must meet quorum.

## Consensus — Quorum Finality + Certified View Changes

For height `H` and round `R`, proposer selection is:

```text
validator_index = (H - 1 + R) mod validator_count
```

The v0.4 flow is:

1. Nodes begin an unfinished height at the persisted local round, normally round `0`.
2. The expected proposer builds and signs a proposal.
3. Validators validate proposer identity, proposal signature, roots, transactions and any required view-change certificate.
4. A validator records a valid signed proposal for equivocation detection.
5. The validator applies its local vote-lock rules and signs a commit vote if allowed.
6. The proposer collects a strict >2/3 commit quorum.
7. The finalized block is broadcast with its commit certificate.
8. Receiving nodes re-validate the proposal and certificate before applying state.
9. If the round does not finalize before timeout, validators may sign a view-change message to `R+1`.
10. A node may move to `R+1` only after collecting a strict >2/3 signed view-change certificate.
11. The next-round proposer includes that certificate in its proposal.

## Persistent Consensus State

SQLite stores:

- local commit-vote records by `(height, round)`,
- the highest local consensus round for unfinished heights,
- local signed view-change actions,
- first-seen valid proposal hashes,
- conflicting-proposal evidence.

This prevents a simple restart from erasing the local same-round vote record or local round advancement.

## Conservative Cross-Round Lock

After a validator signs a commit vote at a height, the node treats the most recent local voted block hash as a conservative lock.

The validator refuses to sign a different block hash at that height in a later round.

This is a deliberately safety-biased research rule. It does **not** yet implement a mature proof-of-lock/unlock mechanism. As a result, some network-failure patterns can stop liveness rather than permit a conflicting cross-round vote.

A future version should replace this with a reviewed multi-phase prevote/precommit or equivalent locking protocol with a formally specified unlock rule.

## Equivocation Evidence

After a proposal has passed normal validation, the node persists the first block hash seen for:

```text
(height, round, proposer)
```

If the same proposer supplies another valid signed proposal with a different block hash for that same tuple, the node stores evidence and refuses to vote for the conflicting proposal.

v0.4 does not implement automatic slashing or validator removal.

## State Commitments

`tx_root` is a SHA-256 Merkle root over transaction IDs. `state_root` is currently a deterministic SHA-256 commitment over sorted `(address, balance, nonce)` tuples after simulating the proposal.

This is not yet a proof-producing Merkleized account trie.

## Fees / Economics

Transaction fees are credited to the finalized block proposer. There is no post-genesis mint path, inflation system, staking, slashing or on-chain governance in v0.4.

No final CRKBIT economics should be inferred from this devnet.

## Peer Synchronization

Configured validator peers still communicate over ordinary development HTTP. Finalized-block catch-up re-validates blocks and certificates locally.

Peer transport is not authenticated or encrypted and must not be treated as production P2P networking.

## RPC

Public development endpoints:

- `GET /health`
- `GET /status`
- `GET /validators`
- `GET /peers`
- `GET /evidence`
- `GET /balance/{address}`
- `GET /blocks/{height}`
- `GET /transactions/{txid}`
- `POST /transactions`

Development peer endpoints:

- `POST /internal/transaction`
- `POST /internal/view-change-request`
- `POST /internal/proposal`
- `POST /internal/block`

The `/internal/*` API must not be exposed as production peer networking.

## Known Consensus/Mainnet Gaps

v0.4 still lacks:

- a mature multi-phase lock/unlock or equivalent reviewed BFT state machine,
- formal safety/liveness proofs,
- authenticated/encrypted validator transport,
- validator identity/certificate rotation,
- dynamic validator-set changes or stake weighting,
- automatic slashing/evidence processing,
- state snapshots and fast state sync,
- production DoS/rate controls,
- production key management,
- governance/upgrade mechanisms,
- long-running adversarial public testnet evidence,
- independent security audit.

## Mainnet Gate

A production candidate requires a mature independently reviewed consensus implementation, authenticated networking, state recovery, adversarial/fuzz/partition testing, economic-security review, production key-management standards, incident response, a long-lived public testnet and external security audits.
