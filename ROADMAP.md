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

Earlier CometBFT/BFT work remains legacy/research infrastructure and is not mixed into the PoW consensus path.

## Native PoW Roadmap

### v0.31 — working CPU-mineable PoW devnet
- [x] Native PoW + UTXO ledger
- [x] Ed25519 `crk1...` ownership/signatures
- [x] Coinbase rewards, maturity, fees, mempool
- [x] `crakpow-scrypt-v1`, target/retarget/chainwork
- [x] CPU solo mining + node RPC
- [x] First-party pool + PPLNS test accounting

### v0.32 — decentralized PoW networking / chain selection
- [x] `crakbit-p2p/1`
- [x] Signed chain/genesis-bound peer hello
- [x] Seed peers + bounded discovery
- [x] Header/inventory/block/transaction propagation
- [x] Persistent side branches/orphans
- [x] Highest cumulative valid work fork choice
- [x] Replay-validated canonical reorganization
- [x] Mempool/disconnected-transaction reconciliation
- [x] Median-time-past branch rule
- [x] Basic peer scoring/rate/size limits
- [x] Two-node real TCP sync regression test

### v0.33 — CPU mining / RandomX candidate / pool hardening
- [x] Package `0.33.0a1`
- [x] Multi-thread CPU solo/pool mining
- [x] `crakbit-pool/2` vardiff
- [x] Stale/duplicate/share-replay protection
- [x] Optional TLS/auth/rate limits
- [x] Native RandomX `v1.1.8` candidate adapter
- [x] RandomX self-test + light/fast benchmark tooling
- [x] Deterministic candidate key schedule/blob
- [x] XMRig `rx/0` candidate job/submit verifier
- [ ] Real cross-machine CPU/GPU benchmark evidence
- [ ] Human final PoW algorithm decision
- [ ] End-to-end stock XMRig compatibility if RandomX is selected

### v0.34 — PoW operations / payout / reorg preparation
- [x] Package `0.34.0a1`
- [x] Signed scrypt/RandomX benchmark evidence
- [x] Multi-machine benchmark gate
- [x] Explicit human algorithm decision record; no auto-activation
- [x] UTXO undo-journal backfill + verification
- [x] Persistent peer reputation/address book
- [x] Coarse peer-diversity selection
- [x] PoW difficulty/hashrate/miner stats
- [x] Transaction confirmations + fee-estimate helper
- [x] Watch-only address record
- [x] Mature coinbase-aware PPLNS payout plan
- [x] Payout reservation / confirmation-depth reconciliation
- [ ] Live incremental undo-based reorg engine
- [ ] Production pool hot/cold operational key policy

### v0.35 — public PoW testnet evidence gate
- [x] Package `0.35.0a1`
- [x] Signed operator/host attestations
- [x] Exact source/package/chain/genesis binding
- [x] Live `/pow/v2` node probing
- [x] 4+ node convergence checks
- [x] Same-height tip conflict detection
- [x] Actual-duration 24h/72h/7d soak gates
- [x] Restart/partition/reconnect/invalid-block/invalid-tx/load fault record
- [x] Higher-work reorg + post-partition convergence evidence fields
- [x] Unique node/operator/evidence-signer gate
- [x] Provider/region diversity gate
- [x] Multiple miner-operator requirement
- [x] Signed public-testnet gate
- [x] Signed public-testnet review freeze
- [x] Regression tests including signer-reuse rejection

### v0.35 real external work still open
- [ ] 4+ independently operated public full nodes
- [ ] Multiple independent miners and preferably multiple pools/solo miners
- [ ] Real 24h → 72h → 7-day+ sustained operation
- [ ] Real authorized competing-fork/reorg campaign
- [ ] Real partition/reconnect campaign
- [ ] Real invalid block/tx/fuzz/load campaigns
- [ ] Real backup/reindex/recovery evidence
- [ ] Real cross-machine algorithm benchmarks
- [ ] Independent consensus/network/wallet/pool review

### v0.36 target — real campaign + controlled integration
- [ ] Provision independently managed public PoW nodes across multiple providers/regions
- [ ] Collect v0.35 host attestations and convergence samples from real operators
- [ ] Automate periodic observation collection without fabricating elapsed time
- [ ] Complete 24h/72h/7d campaign evidence
- [ ] Produce controlled natural/forced forks and verify highest-work convergence
- [ ] Run authorized partition/reconnect/restart/load/invalid-input drills
- [ ] Collect real scrypt vs RandomX benchmark evidence and make a human algorithm decision
- [ ] If RandomX is selected, implement an explicit versioned activation rule and deterministic consensus vectors
- [ ] Integrate peer-book selection into live node startup with anti-eclipse diversity limits
- [ ] Move from undo metadata to reviewed incremental disconnect/connect reorg mechanics
- [ ] Harden pool payout hot/cold separation, caps, holds and operator reconciliation
- [ ] Expand PoW explorer/wallet reorg UX
- [ ] Prepare independent review handoff from real evidence

## Mainnet Consideration

Production mainnet should only be considered after long-lived independent testing, final PoW algorithm freeze, reviewed reorg/state transition logic, wallet/node/pool security reviews, high/critical remediation/retest, final economics, mining-centralization/attack-economics review, applicable legal/regulatory review and an explicit human launch/no-launch decision.

## CRKBIT Status

**Production CRKBIT is not launched. No official presale. No production token contract.**

Current subsidy, halving and target parameters remain devnet settings. The previously discussed 21,000,000 maximum-supply and 8-decimal design remain proposals until deliberately finalized and independently reviewed.
