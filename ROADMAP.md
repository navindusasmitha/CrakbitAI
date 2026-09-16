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

The earlier chain path used CometBFT/BFT validator consensus. It produced useful wallet, recovery, monitoring, release and review tooling. That code remains legacy/research infrastructure and is **not silently combined** with the PoW consensus path.

## Native PoW Roadmap

### v0.31 — working CPU-mineable PoW devnet

- [x] Package/CLI `0.31.0a1`
- [x] Separate native PoW consensus path
- [x] Bitcoin-style UTXO ledger
- [x] Ed25519 `crk1...` ownership keys
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

### v0.32 — decentralized PoW networking / chain selection

- [x] Package/CLI `0.32.0a1`
- [x] Versioned `crakbit-p2p/1` wire protocol
- [x] Ed25519 peer identity + signed handshake
- [x] Chain ID / genesis binding during handshake
- [x] Static seed peers + bounded peer discovery
- [x] Header locator/announcement synchronization path
- [x] Inventory/block/transaction gossip
- [x] Persistent side-chain block graph
- [x] Bounded orphan storage + parent-triggered retry
- [x] Cumulative-work comparison across branches
- [x] Full branch replay validation before activation
- [x] Strict higher-work canonical branch selection
- [x] Canonical block/transaction/UTXO replacement from replayed branch state
- [x] Reorg mempool/disconnected-transaction reconciliation
- [x] Median-time-past branch timestamp rule
- [x] Peer scoring + message/block/inventory/rate limits
- [x] Combined P2P + mining-compatible RPC node
- [x] Real two-node TCP synchronization regression test

### v0.32 limitations still explicit

- [ ] Durable UTXO undo journal for large reorg efficiency (v0.32 safely replays candidate state instead)
- [ ] Persisted peer reputation/address database
- [ ] Anti-eclipse/Sybil hardening
- [ ] Full independently validated header-chain sync before block download
- [ ] Compact block / bandwidth optimization
- [ ] Large-chain reorg/sync performance benchmarks
- [ ] Extensive malformed-message/fuzz/resource-exhaustion campaigns
- [ ] Production transport/privacy/NAT policy

### v0.33 target — CPU mining algorithm / interoperability hardening

- [ ] Integrate a real RandomX native implementation as a candidate
- [ ] Publish deterministic RandomX test vectors
- [ ] Benchmark scrypt vs RandomX on representative CPUs/GPUs
- [ ] Review validation CPU/memory DoS exposure
- [ ] Define deterministic RandomX seed/key schedule if selected
- [ ] Multi-core optimized native miner
- [ ] Standard Stratum compatibility for the selected algorithm
- [ ] XMRig interoperability if technically compatible
- [ ] Pool variable difficulty (vardiff)
- [ ] Stale/duplicate/share-replay defenses
- [ ] Pool TLS/auth/rate limits

### v0.34 target — wallet/pool/explorer + P2P hardening

- [ ] Mature coinbase-aware pool payout transaction builder
- [ ] PPLNS payout batching / fee policy
- [ ] Pool hot/cold key separation
- [ ] PoW explorer difficulty/hashrate/coinbase/miner views
- [ ] Wallet confirmations / fee estimation / reorg awareness
- [ ] Watch-only addresses and safe backup/recovery flows
- [ ] Persistent peer database + anti-eclipse controls
- [ ] Efficient UTXO undo/reorg journal
- [ ] Public node/RPC rate limiting and reverse-proxy guidance

### v0.35 target — real multi-node PoW public testnet

- [ ] 4+ independently operated full nodes
- [ ] Multiple independent miners/pools
- [ ] Continuous 24h → 72h → 7-day+ operation
- [ ] Natural and forced competing forks/reorg testing
- [ ] Peer partition/reconnect tests
- [ ] Invalid block/tx/fuzz/DoS campaigns
- [ ] Bootstrap/reindex/recovery testing
- [ ] Reproducible tagged releases + SBOM
- [ ] Independent consensus/network/wallet/pool review

## Mainnet Consideration

Production mainnet should only be considered after:

- the decentralized PoW P2P/fork-choice implementation has undergone long-lived independent testing,
- reorg/state-transition logic has been independently reviewed,
- the final PoW algorithm and mining interoperability are frozen,
- long-lived independent public testing succeeds,
- wallet/node/pool security reviews are complete,
- high/critical findings are remediated/retested,
- production economics/rewards/fees/supply are finalized,
- mining-centralization and economic attacks are reviewed,
- applicable legal/regulatory review is complete,
- an explicit human launch/no-launch decision is made.

## CRKBIT Status

**Production CRKBIT is not launched. No official presale. No production token contract.**

Current subsidy, halving and target parameters are configurable devnet settings. The previously discussed 21,000,000 maximum-supply and 8-decimal design remain proposals until deliberately finalized and independently reviewed.
