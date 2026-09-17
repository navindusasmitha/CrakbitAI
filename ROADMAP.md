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
- [x] Two-node TCP sync regression test

### v0.33 — CPU mining / RandomX candidate / pool hardening
- [x] Package `0.33.0a1`
- [x] Multi-thread CPU solo/pool mining
- [x] `crakbit-pool/2` vardiff
- [x] Stale/duplicate/share-replay protection
- [x] Optional TLS/auth/rate limits
- [x] Native RandomX `v1.1.8` candidate adapter
- [x] RandomX self-test + benchmark tooling
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

### v0.35 — public PoW testnet evidence gate
- [x] Package `0.35.0a1`
- [x] Signed operator/host attestations
- [x] Exact source/package/chain/genesis binding
- [x] Live `/pow/v2` node probing
- [x] 4+ node convergence checks
- [x] Same-height tip conflict detection
- [x] Actual-duration 24h/72h/7d soak gates
- [x] Restart/partition/reconnect/invalid-block/invalid-tx/load fault records
- [x] Higher-work reorg + post-partition convergence evidence fields
- [x] Unique node/operator/evidence-signer gate
- [x] Provider/region diversity gate
- [x] Multiple miner-operator requirement
- [x] Signed public-testnet gate and review freeze

### v0.36 — controlled PoW integration / real-campaign tooling
- [x] Package/CLI advanced to `0.36.0a1`
- [x] Append-only signed campaign log for repeated real-node observations
- [x] Campaign-log signature/hash verification
- [x] 24h/72h/7d campaign summaries with minimum node count, sample success ratio and height-lag gates
- [x] Real RPC probe collection without fabricating elapsed time
- [x] Incremental UTXO-undo rehearsal on disposable chain copies
- [x] Undo rehearsal verifies state fingerprint rollback against expected historical state
- [x] Persistent peer-book seed selection wired into v0.36 node startup
- [x] Coarse per-network-bucket seed limits retained during node startup
- [x] v0.36 node launcher delegating to existing PoW P2P node with selected peer seeds
- [x] Signed PoW algorithm activation-proposal format
- [x] Activation proposal binds human algorithm decision, source commit, chain ID, genesis, notice window and optional consensus/vector/library hashes
- [x] Activation proposal explicitly does **not** activate consensus by itself
- [x] v0.36 regression tests for campaign logs, undo rehearsal, peer selection and activation proposal
- [x] CI pass for the v0.36 regression-code commit

### v0.36 real external work still open
- [ ] Provision 4+ independently managed public PoW nodes across multiple providers/regions
- [ ] Run the v0.36 campaign collector against those real nodes
- [ ] Complete real 24h → 72h → 7-day+ observation campaigns
- [ ] Run authorized restart/partition/reconnect/load/invalid-input drills on owned/authorized infrastructure
- [ ] Produce real competing forks and verify highest-work convergence
- [ ] Collect real scrypt vs RandomX benchmark evidence on independent hardware
- [ ] Make a human algorithm decision from real benchmark/security evidence
- [ ] If RandomX is selected, build and review an actual versioned consensus implementation; proposal tooling alone is insufficient
- [ ] Validate incremental undo mechanics under live competing-fork/reorg conditions before replacing replay-based reorgs
- [ ] Harden pool hot/cold payout-key operations, caps and reconciliation
- [ ] Complete independent consensus/network/wallet/pool review

### v0.37 target — public-testnet execution / review hardening
- [x] Package/CLI advanced to `0.37.0a1`
- [x] Signed multi-host deployment plans and operator runbooks for the PoW node/pool stack
- [x] Deployment evidence rejects secret-like fields and enforces node/operator/provider/region/network/miner diversity gates
- [ ] Persistent peer-health feedback from live sessions into the peer book
- [ ] Deeper anti-eclipse/diversity controls using externally reviewed network/operator metadata
- [ ] Controlled fork/reorg harness using incremental undo on disposable/live-testnet copies
- [ ] Public explorer/wallet reorg and confirmation UX
- [x] Pool payout policy evidence with hot/cold separation, operator approvals, caps and holds
- [x] Independent-review candidate bundle that cross-binds v0.36 handoff and v0.37 execution artifacts
- [x] Final PoW-algorithm review gate format requiring signed benchmark/decision evidence and external review assertions
- [x] v0.37 regression tests for signatures, secret rejection, cross-artifact binding and CLI round trip
- [ ] If justified, versioned candidate consensus activation on testnet only, never silent activation

## Mainnet Consideration

Production mainnet should only be considered after long-lived independent testing, final PoW algorithm freeze, reviewed reorg/state-transition logic, wallet/node/pool security reviews, high/critical remediation/retest, final economics, mining-centralization/attack-economics review, applicable legal/regulatory review and an explicit human launch/no-launch decision.

## CRKBIT Status

**Production CRKBIT is not launched. No official presale. No production token contract.**

Current subsidy, halving and target parameters remain devnet settings. The previously discussed 21,000,000 maximum-supply and 8-decimal design remain proposals until deliberately finalized and independently reviewed.
