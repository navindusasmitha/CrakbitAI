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

### v0.33 — CPU mining algorithm / interoperability hardening

- [x] Package/CLI `0.33.0a1`
- [x] Optional native RandomX `v1.1.8` adapter candidate
- [x] Upstream official RandomX API-example self-test vector
- [x] RandomX light + full-dataset/fast modes
- [x] Deterministic RandomX candidate key schedule
- [x] Deterministic candidate blob with XMRig common RandomX nonce offset
- [x] Candidate XMRig `rx/0` job builder
- [x] Candidate XMRig native submitted-hash verifier
- [x] Deterministic v0.33 candidate vector output
- [x] Multi-thread CPU solo miner for active scrypt consensus
- [x] Multi-thread native pool miner
- [x] `crakbit-pool/2` variable difficulty (vardiff)
- [x] Stale/duplicate/share-replay defenses
- [x] Pool message-rate limits
- [x] Optional pool TLS 1.2+ transport
- [x] Optional pool authorization token
- [x] Pool stats
- [x] Windows pinned-source RandomX build helper
- [x] v0.33 regression coverage without requiring RandomX in CI

### v0.33 boundaries still open

- [ ] Benchmark scrypt vs RandomX on representative CPUs/GPUs
- [ ] Review RandomX validation CPU/memory DoS exposure
- [ ] Independently validate candidate vectors across Windows/Linux machines
- [ ] Decide whether RandomX is the production PoW candidate
- [ ] Define versioned network activation rules if RandomX is selected
- [ ] Run candidate-algorithm multi-node fork/reorg tests
- [ ] Prove end-to-end stock XMRig interoperability before advertising it
- [ ] Independently review the selected final PoW rules

### v0.34 target — wallet/pool/explorer + P2P hardening

- [ ] If RandomX is selected, add explicit versioned consensus activation and fork/reorg regression vectors
- [ ] Stock XMRig end-to-end compatibility for the exact selected algorithm/job semantics
- [ ] Mature coinbase-aware pool payout transaction builder
- [ ] PPLNS payout batching / fee policy / reconciliation
- [ ] Pool hot/cold key separation + payout caps/holds
- [ ] PoW explorer difficulty/hashrate/coinbase/miner/reorg views
- [ ] Wallet confirmations / fee estimation / reorg awareness
- [ ] Watch-only addresses and safe backup/recovery flows
- [ ] Persistent peer database + reputation / anti-eclipse diversity controls
- [ ] Efficient UTXO undo/reorg journal
- [ ] Public node/RPC rate limiting and reverse-proxy guidance
- [ ] Larger malformed-message/fuzz/resource-exhaustion campaigns

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
