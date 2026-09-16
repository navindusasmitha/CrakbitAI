# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.33 native Proof-of-Work mining-hardening devnet alpha**

Crakbit AI keeps two clearly separated blockchain research tracks:

1. the earlier CometBFT/BFT validator stack, retained as legacy/research infrastructure and a source of reusable operations/security tooling;
2. the primary v0.31+ native Proof-of-Work UTXO path, where miners produce blocks, v0.32 nodes exchange competing branches over a signed P2P network, and v0.33 hardens CPU mining/pool behavior while evaluating RandomX as an optional candidate.

The PoW path is **not production mainnet** and must not be used for real-value custody.

## Current Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| Public website | Active | Project/funding information |
| GitHub repository | Active | Security + blockchain research code |
| Secure Code Scanner | Early alpha | Deterministic static-analysis rules |
| AI Security Assistant | In development | Security MVP work ongoing |
| Crakbit Chain package | **v0.33.0a1** | Native PoW mining-hardening devnet alpha |
| Primary consensus research | **Proof of Work** | Miner-produced blocks |
| Active devnet PoW | **`crakpow-scrypt-v1`** | CPU-mineable bootstrap; not production-frozen |
| Ledger | **UTXO** | Bitcoin-style unspent outputs |
| PoW rewards/fees | Implemented | Coinbase + fees + maturity |
| Difficulty / chainwork | Implemented | 256-bit target, retarget, cumulative work |
| P2P protocol | **Implemented alpha** | `crakbit-p2p/1` with signed chain/genesis-bound hello |
| Fork choice / reorg | **Implemented alpha** | Highest valid work; replay-based state replacement |
| Multi-thread CPU solo miner | **v0.33 implemented** | RPC miner scans disjoint nonce sequences |
| Native pool protocol | **`crakbit-pool/2`** | v0.33 vardiff + stale/duplicate protections |
| Multi-thread pool miner | **v0.33 implemented** | Optional TLS client path |
| Pool vardiff | **v0.33 implemented alpha** | Per-worker target adaptation |
| Duplicate/share replay protection | **v0.33 implemented** | Job/extra-nonce/nonce + hash uniqueness |
| Pool TLS/auth | **v0.33 implemented alpha** | TLS 1.2+ + optional shared token |
| RandomX native adapter | **v0.33 implemented candidate** | Pinned upstream `v1.1.8`; optional local shared library |
| RandomX self-test/benchmark | **v0.33 implemented** | Light + fast modes; official API-example vector |
| RandomX key schedule candidate | **v0.33 implemented** | 2048-block interval / 64-block activation delay |
| XMRig candidate job verifier | **v0.33 implemented** | `rx/0` job fields/nonce layout + native submitted-hash verification |
| Stock XMRig live pool compatibility | **Not yet claimed** | Depends on final RandomX consensus/blob/target activation |
| On-chain pool payout automation | **Not implemented** | PPLNS balances remain test accounting |
| Production mainnet | **Not launched** | Alpha only |
| Production CRKBIT | **Not launched** | No official presale/token contract |

## v0.33 Completed Code Work

- package/CLI advanced to `0.33.0a1`,
- multi-thread CPU RPC miner for the active scrypt network,
- multi-thread first-party pool miner,
- hardened `crakbit-pool/2` path,
- per-worker vardiff,
- stale-job rejection,
- duplicate/replayed-share rejection,
- per-connection message-rate limits,
- optional TLS 1.2+ pool transport,
- optional pool authorization token,
- pool stats,
- optional ctypes integration with upstream RandomX `v1.1.8`,
- RandomX light and full-dataset/fast modes,
- official upstream API-example self-test vector,
- deterministic RandomX candidate key-height schedule,
- deterministic candidate hashing blob with XMRig common nonce offset,
- XMRig `rx/0` candidate job construction,
- native RandomX recomputation of captured XMRig-style submits,
- deterministic candidate vector generation,
- Windows pinned-source RandomX build helper,
- v0.33 regression tests that stay green even when RandomX is not installed in CI,
- v0.33 documentation and status updates.

## Important v0.33 Boundary

The active devnet consensus still uses `crakpow-scrypt-v1`. RandomX is a **real native candidate integration**, but it is deliberately not activated in block validation yet.

That separation prevents a silent consensus split. Before RandomX can become a network rule the project still needs to freeze the candidate blob/target semantics, publish cross-platform vectors, benchmark representative CPUs/GPUs, evaluate validation DoS cost, define an explicit versioned activation rule, run fork/reorg tests on the candidate algorithm and complete independent consensus review.

Likewise, v0.33's XMRig adapter proves candidate job/submit formatting and native hash recomputation. It does not yet prove an end-to-end public stock-XMRig pool against active Crakbit consensus.

## Mining-Pool Status

The first-party pool now includes vardiff, duplicate/stale/share-replay protection, TLS/auth options and stronger input/rate limits. PPLNS balances are still test accounting. Automatic coinbase-maturity-aware on-chain payouts remain disabled pending wallet/accounting review.

## Previous Work Reused

- v0.31: actual PoW blocks, UTXO ledger, rewards, fees, difficulty, chainwork and first pool.
- v0.32: P2P networking, side branches, orphan handling and higher-work reorganization.
- v0.23–v0.30: consensus-independent monitoring, release signing, evidence retention, incident-response and review/remediation tooling.

The old CometBFT validator voting-power path is not mixed into PoW consensus.

## Immediate Blockchain Priorities — v0.34 target

1. Benchmark the RandomX candidate on representative CPU/GPU systems and publish comparable evidence.
2. Decide whether RandomX should become the next consensus candidate; do not auto-activate it.
3. If selected, add explicit versioned RandomX activation + deterministic consensus vectors + multi-node fork/reorg tests.
4. Run stock XMRig end-to-end against the exact selected job/blob/target semantics before claiming compatibility.
5. Add mature coinbase-aware PPLNS payout transaction construction and reconciliation.
6. Separate pool hot wallet, cold funds and operator credentials; add payout caps/holds.
7. Persist peer/address reputation and add anti-eclipse/diversity controls.
8. Add deeper malformed-message/fork/reorg/fuzz/load/sync campaigns.
9. Add PoW explorer hashrate/difficulty/miner/coinbase/reorg views and wallet confirmation/reorg awareness.
10. Run a long-lived real multi-host PoW public testnet and complete independent node/network/wallet/pool/economic-security review.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

Subsidy/halving/difficulty values remain configurable devnet parameters. The proposed 21,000,000 maximum supply and 8-decimal design remain proposals until intentionally frozen after technical, economic-security and applicable legal/regulatory review.

See `blockchain/V0.33.md`, `blockchain/README.md`, `ROADMAP.md` and GitHub Issue #1.
