# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.32 native Proof-of-Work P2P devnet alpha**

Crakbit AI now keeps two clearly separated blockchain research tracks:

1. the earlier CometBFT/BFT validator stack, retained as legacy/research infrastructure and a source of reusable operations/security tooling;
2. the primary v0.31+ native Proof-of-Work UTXO path, where miners produce blocks and v0.32 nodes exchange competing branches over a signed P2P network.

The PoW path is **not production mainnet** and must not be used for real-value custody.

## Current Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| Public website | Active | Project/funding information |
| GitHub repository | Active | Security + blockchain research code |
| Secure Code Scanner | Early alpha | Deterministic static-analysis rules |
| AI Security Assistant | In development | Security MVP work ongoing |
| Crakbit Chain package | **v0.32.0a1** | Native PoW P2P devnet alpha |
| Primary consensus research | **Proof of Work** | Miner-produced blocks |
| Current PoW | **`crakpow-scrypt-v1`** | CPU-mineable bootstrap; not production-frozen |
| Ledger | **UTXO** | Bitcoin-style unspent outputs |
| PoW rewards/fees | Implemented | Coinbase + fees + maturity |
| Difficulty / chainwork | Implemented | 256-bit target, retarget, cumulative work |
| Solo CPU miner | Implemented | Mines real block templates |
| Mining pool | Implemented alpha | `crakbit-pool/1` + PPLNS test accounting |
| P2P protocol | **v0.32 implemented** | `crakbit-p2p/1`, signed chain/genesis-bound hello |
| Peer discovery | **v0.32 implemented alpha** | Static seeds + bounded peer exchange |
| Block/tx gossip | **v0.32 implemented** | inventory/getblock/gettx propagation |
| Header sync path | **v0.32 implemented alpha** | locator + headers + block fetch |
| Side-chain storage | **v0.32 implemented** | Persistent all-branch block graph |
| Fork choice | **v0.32 implemented** | Highest cumulative valid work |
| Reorganization | **v0.32 implemented** | Replay-validated canonical state replacement |
| Orphan handling | **v0.32 implemented** | Bounded orphan queue + parent-triggered processing |
| Timestamp hardening | **v0.32 implemented alpha** | Median-time-past branch rule |
| Two-node real TCP sync test | **Implemented** | Regression test mines/syncs a block across nodes |
| RandomX integration | Not yet implemented | Candidate for v0.33 benchmark/review |
| Standard Stratum/XMRig | Not yet implemented | Current pool protocol is project-native |
| Production mainnet | **Not launched** | Alpha only |
| Production CRKBIT | **Not launched** | No official presale/token contract |

## v0.32 Completed Code Work

- package/CLI advanced to `0.32.0a1`,
- persistent block graph for canonical + side branches,
- bounded orphan-block storage,
- complete candidate-branch replay before activation,
- strict higher-cumulative-work fork selection,
- canonical block/transaction/UTXO state replacement from fully replayed candidate state,
- reorg mempool + disconnected transaction reconciliation,
- median-time-past timestamp rule for v0.32 branch validation,
- Bitcoin-style exponential block locator,
- Ed25519 P2P node identity,
- signed protocol/chain/genesis/tip/chainwork handshake,
- static seeds + bounded peer discovery,
- headers/inventory/block/transaction exchange,
- ping/pong + peer scoring + basic rate/size limits,
- combined v1-compatible mining RPC and v2 P2P-aware RPC node,
- peer/graph inspection endpoints,
- two-node TCP synchronization regression coverage,
- v0.32 documentation and updated release boundary.

## Important v0.32 Boundary

v0.32 is materially closer to a Bitcoin-like architecture than v0.31 because nodes can now disagree temporarily, keep competing branches and converge when one branch gains strictly more valid work.

It is still a devnet alpha. The implementation needs deeper adversarial review around reorg correctness, eclipse/Sybil resistance, peer persistence, sync efficiency, malformed-message fuzzing, resource-exhaustion behavior, large-chain replay/reorg cost and long-lived multi-host operation.

The current P2P transport is newline-delimited JSON/TCP for research simplicity. Production framing/transport decisions remain open.

## PoW Algorithm Status

`crakpow-scrypt-v1` is a working CPU-verifiable bootstrap algorithm. It is **not frozen for production**.

RandomX remains a candidate for the CPU-first goal, but the project must integrate a real native implementation, publish deterministic test vectors, benchmark validation/mining cost across CPUs/GPUs and complete independent review before selecting it.

## Mining-Pool Status

The first-party pool can issue jobs, validate easier shares, submit full-difficulty blocks and account PPLNS balances. It is still `crakbit-pool/1`, not standard Stratum/XMRig. Automatic on-chain payouts remain disabled.

## Previous v0.23–v0.30 Work

Consensus-independent work such as monitoring, release signing, evidence retention, incident-response, review/remediation and public-edge hardening remains reusable. CometBFT validator voting power is not mixed into the PoW consensus path.

## Immediate Blockchain Priorities — v0.33 target

1. Integrate a real native RandomX candidate and publish deterministic vectors.
2. Benchmark scrypt vs RandomX on representative CPUs/GPUs and measure validation DoS cost.
3. Add optimized multi-core CPU mining.
4. Add standard Stratum compatibility for the selected algorithm and test XMRig interoperability where technically valid.
5. Add pool vardiff, duplicate/stale/share-replay protection, TLS/auth and stronger rate limits.
6. Add hardened on-chain PPLNS payout transaction construction after coinbase maturity.
7. Persist peer/address reputation and add anti-eclipse controls.
8. Add adversarial fork/reorg/fuzz/load tests and larger-chain sync benchmarks.
9. Run a real multi-host public PoW testnet for an extended period.
10. Complete independent node/network/wallet/pool/economic-security review before mainnet consideration.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

Subsidy/halving/difficulty values remain configurable devnet parameters. The proposed 21,000,000 maximum supply and 8-decimal design remain proposals until intentionally frozen after technical, economic-security and applicable legal/regulatory review.

See `blockchain/V0.32.md`, `blockchain/README.md`, `ROADMAP.md` and GitHub Issue #1.
