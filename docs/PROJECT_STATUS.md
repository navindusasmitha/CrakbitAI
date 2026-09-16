# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.31 native Proof-of-Work devnet alpha**

Crakbit AI now has two clearly separated blockchain research tracks in the repository:

1. the earlier CometBFT/BFT validator stack and its extensive operations/review/evidence tooling, retained as legacy/research infrastructure;
2. a new v0.31 native PoW path intended to evolve toward a Bitcoin-like miner-produced chain.

The new PoW path is now the primary chain research direction. It is **not production mainnet** and must not be used for real-value custody.

## Current Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| Public website | Active | Project/funding information |
| GitHub repository | Active | Security + blockchain research code |
| Secure Code Scanner | Early alpha | Deterministic static-analysis rules |
| AI Security Assistant | In development | Security MVP work ongoing |
| Crakbit Chain package | **v0.31.0a1** | Native PoW devnet alpha |
| New primary consensus research | **PoW** | Miner-produced blocks |
| Working v0.31 PoW | **`crakpow-scrypt-v1`** | CPU-mineable memory-hard scrypt bootstrap |
| Ledger | **UTXO** | Bitcoin-style unspent outputs |
| PoW block rewards | Implemented | Coinbase subsidy + fees + maturity |
| Difficulty | Implemented | 256-bit target + bounded retarget |
| Chainwork | Implemented | Cumulative work tracked |
| Solo CPU miner | Implemented | Mines actual block templates |
| PoW node RPC | Implemented | Template/block/tx/balance/UTXO endpoints |
| First-party mining pool | Implemented alpha | Native JSON-line pool protocol |
| Pool share accounting | Implemented alpha | Easier share target + PPLNS test balances |
| Native pool CPU miner | Implemented | Project-native miner script |
| Previous CometBFT stack | Retained | Legacy/research; not mixed into PoW consensus |
| P2P PoW networking | **Not yet implemented** | Required for decentralized multi-node chain |
| Fork/reorg engine | **Not yet implemented** | v0.31 accepts tip-extending blocks only |
| RandomX integration | **Not yet implemented** | Candidate for benchmark/review phase |
| XMRig/standard Stratum compatibility | **Not yet implemented** | Native pool protocol only |
| Production mainnet | **Not launched** | Alpha only |
| Production CRKBIT | **Not launched** | No official presale/token contract |

## v0.31 Completed Code Work

- package/CLI advanced to `0.31.0a1`,
- deterministic PoW genesis,
- persistent SQLite block/transaction/UTXO/mempool database,
- UTXO transactions using existing Ed25519 `crk1...` ownership keys,
- signed inputs and value-conservation checks,
- transaction fees and mempool double-spend prevention,
- coinbase rewards and configurable maturity,
- Merkle roots over transaction IDs,
- memory-hard scrypt PoW hashing,
- exact target verification,
- configurable/bounded difficulty retargeting,
- cumulative chainwork,
- actual CPU solo-mining loop,
- FastAPI PoW node RPC,
- first-party pool job/share verification,
- network target vs easier pool share target separation,
- PPLNS internal test accounting,
- native pool server and CPU pool miner,
- v0.31 regression tests and documentation.

## Important v0.31 Boundary

v0.31 is the first repository phase where `mine` means a miner actually hashes a block header and the node validates that proof against a network target.

However, one local PoW node is not yet a fully decentralized Bitcoin-like network. The following are still missing from the new PoW path:

- peer discovery and persistent P2P connections,
- block/transaction gossip,
- header-first synchronization,
- side-chain/fork storage,
- highest-cumulative-work fork selection across competing branches,
- safe UTXO rollback/reorganization data,
- orphan handling,
- stronger timestamp rules,
- production-grade fee/mempool policies,
- final PoW algorithm selection,
- interoperable mining protocol,
- hardened on-chain pool payout workflow,
- long-lived independent multi-node PoW testnet,
- independent PoW consensus/security/economic review.

## PoW Algorithm Status

The working alpha algorithm is `crakpow-scrypt-v1`. This is a real CPU-mineable memory-hard PoW path available through Python's standard cryptographic runtime.

RandomX remains a candidate for the production CPU-first design, but it must be integrated through a real native implementation, benchmarked against CPU/GPU behavior and independently reviewed. The project should not claim RandomX/XMRig compatibility until that work exists.

## Previous v0.23–v0.30 Work

The older CometBFT stack contains useful wallet, monitoring, release, audit/remediation, incident-response, evidence-retention and public-edge engineering. That work remains in the repository and can be reused where consensus-independent.

CometBFT validator voting power/governance is not the production-consensus model of the new PoW path unless the project later deliberately changes direction again.

## Immediate Blockchain Priorities — PoW v0.32 target

1. Implement a P2P peer protocol and node identity/handshake.
2. Add block + transaction inventory/gossip.
3. Add header-first synchronization and peer chainwork comparison.
4. Store side-chain blocks and implement highest-chainwork reorganization with UTXO undo records.
5. Add orphan/fork handling and stronger time rules.
6. Add multi-core/native mining improvements.
7. Implement/benchmark a real RandomX adapter before deciding the final PoW algorithm.
8. Add final-algorithm Stratum compatibility and pool vardiff/anti-abuse controls.
9. Add mature pool payout transaction building after coinbase maturity.
10. Run a real multi-node public PoW testnet and independent review.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

v0.31 subsidy/halving/difficulty values are configurable devnet parameters. The proposed 21,000,000 maximum supply and 8-decimal design remain proposals until intentionally frozen after technical, economic-security and applicable legal/regulatory review.

See `blockchain/V0.31.md`, `blockchain/README.md`, `ROADMAP.md` and GitHub Issue #1.
