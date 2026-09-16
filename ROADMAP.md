# Crakbit AI Roadmap

This roadmap describes intended development order. Dates and architecture can change based on testing, security findings, economics and review.

## Guiding Principle

**Technology first. Security first. Tokens later.**

Production CRKBIT is not launched. There is no official presale or production token contract.

## Security Platform

### Foundation / Security MVP
- [x] Project identity, website and GitHub repository
- [x] Initial secure-code scanner alpha
- [x] Python + JavaScript/TypeScript rules and secret detection
- [x] `crak` CLI early alpha
- [ ] AI Security Assistant prototype
- [ ] Structured configuration checks
- [ ] Solidity/smart-contract security prototype
- [ ] Developer API / SDK / CI integration

## Legacy Blockchain Research — v0.1 through v0.30

The earlier chain path used CometBFT/BFT validator consensus. It produced useful work in:

- [x] signed transaction/accounting primitives,
- [x] browser wallet/gateway/explorer/faucet tooling,
- [x] ABCI/state-sync research,
- [x] validator governance research,
- [x] crash/replay/recovery testing,
- [x] deployment/monitoring tooling,
- [x] release/evidence signing,
- [x] audit/remediation/retest gates,
- [x] long-running evidence/archive/public-edge tooling.

This code remains available as legacy/research infrastructure. It is **not silently combined** with the new PoW consensus path.

## Native PoW Roadmap

### v0.31 — working CPU-mineable PoW devnet

- [x] Package/CLI `0.31.0a1`
- [x] Separate native PoW consensus path
- [x] Bitcoin-style UTXO ledger
- [x] Existing Ed25519 `crk1...` ownership keys
- [x] Signed UTXO transactions + fees
- [x] Mempool double-spend protection
- [x] Coinbase rewards + maturity
- [x] Merkle roots
- [x] Working memory-hard `crakpow-scrypt-v1`
- [x] 256-bit network target validation
- [x] Bounded automatic difficulty retargeting
- [x] Cumulative chainwork tracking
- [x] Actual CPU solo mining
- [x] SQLite chain/UTXO/mempool persistence
- [x] PoW node HTTP RPC
- [x] First-party `crakbit-pool/1` mining pool
- [x] Separate easier pool share target
- [x] PPLNS test accounting
- [x] Native CPU pool miner
- [x] PoW regression tests

### v0.31 limitations that remain explicit

- [ ] P2P peer network
- [ ] Block/transaction gossip
- [ ] Header-first sync
- [ ] Competing-fork storage
- [ ] Highest-cumulative-work reorganization
- [ ] UTXO undo/rollback records
- [ ] Orphan handling
- [ ] Production timestamp/mempool/fee policy
- [ ] Final PoW algorithm selection
- [ ] RandomX native integration/benchmark
- [ ] Standard Stratum/XMRig compatibility
- [ ] Automatic mature pool payouts
- [ ] Long-lived multi-node public PoW testnet

### v0.32 target — decentralized PoW networking / chain selection

- [ ] Define versioned P2P wire protocol
- [ ] Peer identity + handshake + network/chain ID checks
- [ ] Peer discovery / static seed nodes
- [ ] Headers/inventory/block/transaction messages
- [ ] Header-first synchronization
- [ ] Side-chain block storage
- [ ] Chainwork comparison across branches
- [ ] Safe canonical reorg engine
- [ ] UTXO undo journal
- [ ] Reorg mempool reconciliation
- [ ] Orphan block handling
- [ ] Median-time-past style timestamp rules
- [ ] Peer scoring / message-size / rate-limit protections

### v0.33 target — CPU mining algorithm / interoperability hardening

- [ ] Integrate a real RandomX native implementation as a candidate
- [ ] Benchmark scrypt vs RandomX on CPUs/GPUs
- [ ] Review validation CPU/memory DoS exposure
- [ ] Define deterministic RandomX seed/key schedule if selected
- [ ] Multi-core optimized native miner
- [ ] Standard Stratum compatibility for the selected algorithm
- [ ] XMRig interoperability if technically compatible
- [ ] Pool variable difficulty (vardiff)
- [ ] Stale/duplicate/share-replay defenses
- [ ] Pool TLS/auth/rate limits

### v0.34 target — wallet/pool/explorer production-testnet features

- [ ] Mature coinbase-aware pool payout transaction builder
- [ ] PPLNS payout batching / fee policy
- [ ] Pool hot/cold key separation
- [ ] PoW explorer difficulty/hashrate/coinbase/miner views
- [ ] Wallet confirmations / fee estimation / reorg awareness
- [ ] Watch-only addresses and safe backup/recovery flows
- [ ] Public node/RPC rate limiting and reverse proxy guidance

### v0.35 target — real multi-node PoW public testnet

- [ ] 4+ independently operated full nodes
- [ ] Multiple independent miners/pools
- [ ] Continuous 24h → 72h → 7-day+ operation
- [ ] Natural and forced competing forks/reorg testing
- [ ] Peer partition/reconnect tests
- [ ] Invalid block/tx/fuzz/DoS campaigns
- [ ] Snapshot/bootstrap/reindex/recovery testing
- [ ] Reproducible tagged releases + SBOM
- [ ] Independent consensus/network/wallet/pool review

## Mainnet Consideration

Production mainnet should only be considered after:

- a real decentralized P2P PoW network exists,
- highest-chainwork fork/reorg logic has been independently tested/reviewed,
- the final PoW algorithm and mining interoperability are frozen,
- long-lived independent public testing succeeds,
- wallet/node/pool security reviews are complete,
- high/critical findings are remediated/retested,
- production economics/rewards/fees/supply are finalized,
- economic attack incentives are reviewed,
- applicable legal/regulatory review is complete,
- an explicit human launch/no-launch decision is made.

## CRKBIT Status

**Production CRKBIT is not launched. No official presale. No production token contract.**

v0.31 subsidy, halving and target parameters are configurable devnet settings. The previously discussed 21,000,000 maximum-supply and 8-decimal design remain proposals until deliberately finalized and independently reviewed.
