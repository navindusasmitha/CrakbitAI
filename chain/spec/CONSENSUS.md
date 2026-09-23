# Crakbit Chain Consensus Specification v0.1

Status: pre-mainnet, production engineering specification.

## Units
- 1 CBIT = 100,000,000 base units.
- All consensus monetary arithmetic uses signed/unsigned integer base units only. Floating-point arithmetic is forbidden in consensus code.

## Block timing
- Target block spacing: 120 seconds.
- Difficulty is adjusted by the production PoW implementation using deterministic chain data only.

## Block subsidy
- Initial subsidy: 1,000,000,000 base units (10 CBIT).
- Halving interval: 1,051,200 blocks.
- Subsidy at height `h`: `INITIAL_SUBSIDY >> floor(h / HALVING_INTERVAL)` until the shifted value is zero.
- With integer base-unit rounding, the scheduled subsidy emission is 2,102,399,986,334,400 base units = 21,023,999.86334400 CBIT.
- There is no premine.

## Treasury
- Treasury window: heights 1 through 400,000 inclusive.
- Treasury share during that window: `floor(subsidy / 20)` (5%).
- Miner share: `subsidy - treasury`.
- The treasury output is mandatory during the treasury window when the computed treasury amount is nonzero.
- Treasury is never minted in addition to the block subsidy.
- Maximum treasury issuance under the initial era is 200,000 CBIT across the 400,000-block window.
- Treasury destination is a consensus constant fixed before genesis and must use a custody design documented before mainnet.

## Proof of Work
- Algorithm family: RandomX.
- Reference library lineage: tevador/RandomX, pinned to an audited/reviewed release commit before code freeze.
- Crakbit uses a project-unique RandomX configuration identifier/salt and a deterministic blockchain-derived key schedule.
- RandomX seed/key selection is a pure function of prior accepted block data; local wall-clock time, filesystem state, hostname and implementation cache state never affect validity.
- Header PoW hash must be <= the target encoded by `nBits`.
- Difficulty/target encoding must reject invalid, negative, overflow or out-of-range targets.

## RandomX key schedule
The final production implementation must define constants for:
- epoch length
- seed/key-block lag
- genesis/early-chain seed behavior

The values become consensus constants at code freeze. Every transition boundary must have cross-platform test vectors.

## Chain selection
- Select the valid chain with greatest cumulative proof of work.
- No administrator key can override valid chainwork.
- Historical checkpoints, if present, are compile-time constants for historical synchronization/DoS hardening only; they are not an online centralized finality mechanism.

## Coinbase validity
A non-genesis block is invalid if any of the following is true:
1. total coinbase value exceeds `subsidy(height) + allowed_fees`;
2. the required treasury output is missing, underpaid, redirected, or malformed during the active treasury window;
3. treasury payment is added on top of the subsidy instead of carved from it;
4. coinbase maturity rules are violated by a spending transaction.

## Genesis
Genesis is generated once after consensus code freeze. The following are fixed and published with the release:
- timestamp text
- nTime
- nBits
- nNonce
- merkle root
- genesis block hash
- genesis coinbase script

Genesis must contain no spendable premine.

## 51% / deep reorganization model
Crakbit does not claim that a new PoW network is immune to majority-hash attacks. Consensus remains proof-of-work based. Operational safety requires:
- distributed independent miners/pools;
- reorg-depth monitoring;
- conservative exchange confirmation guidance;
- public network-concentration metrics;
- no false claim of absolute finality.

## Consensus freeze rule
After mainnet genesis, any change that alters block validity, monetary issuance, PoW, difficulty, transaction validity, address interpretation or chain selection requires an explicitly versioned network upgrade and cannot be silently deployed as a normal software update.
