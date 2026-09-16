# Crakbit Chain — Production Mainnet Release Gates

This document defines conditions that must be satisfied before Crakbit Chain can responsibly be described as a production mainnet.

**Current status: gates are not satisfied.** The active research direction is the native PoW path introduced in v0.31. Production CRKBIT has not launched.

The earlier CometBFT/BFT validator stack remains in the repository as legacy/research infrastructure; its historical evidence/tooling can be reused where consensus-independent, but it does not satisfy PoW-specific launch gates by itself.

## 1. Native PoW consensus and chain selection

- [ ] Freeze the production PoW algorithm after benchmarking and independent review.
- [ ] Define deterministic PoW seed/key scheduling for the final algorithm.
- [ ] Validate proof-of-work target rules against independent implementations/test vectors.
- [ ] Implement P2P block/header/transaction propagation.
- [ ] Implement competing-fork storage and highest-cumulative-work fork choice.
- [ ] Implement safe canonical reorganization with UTXO undo/rollback records.
- [ ] Reconcile mempool state correctly across reorganizations.
- [ ] Implement orphan handling and peer synchronization.
- [ ] Add strong timestamp rules such as median-time-past or a reviewed alternative.
- [ ] Verify difficulty retarget behavior under fast/slow timestamp and hash-rate changes.
- [ ] Test long/deep reorg boundaries and malicious fork inputs.
- [ ] Publish deterministic consensus test vectors.

## 2. UTXO / transaction / monetary correctness

- [ ] Independently review transaction signing and ownership validation.
- [ ] Independently review UTXO conservation and integer-overflow boundaries.
- [ ] Review coinbase creation, maturity and fee accounting.
- [ ] Review subsidy/halving/issuance arithmetic over the complete intended schedule.
- [ ] Define dust/minimum-output policy.
- [ ] Define transaction size/weight limits.
- [ ] Define fee and mempool eviction policy.
- [ ] Add transaction malleability/replay/network-domain protections as needed.
- [ ] Test reorg effects on confirmed/unconfirmed wallet balances.
- [ ] Publish supply/issuance verification tooling.

## 3. Mining algorithm and miner interoperability

- [ ] Benchmark the final algorithm across representative CPUs and GPUs.
- [ ] Evaluate ASIC/FPGA risk and state the intended hardware-neutrality goals accurately.
- [ ] Review PoW validation cost for CPU/memory denial-of-service exposure.
- [ ] Build/verify a native optimized reference miner.
- [ ] Implement standard mining interoperability for the final algorithm (e.g. Stratum where appropriate).
- [ ] Verify third-party miner interoperability if supported.
- [ ] Publish block-header/job-format test vectors.
- [ ] Test stale work, duplicate shares and malformed mining submissions.
- [ ] Ensure pool/miner protocol never exposes wallet/private keys.

## 4. P2P network security

- [ ] Version and document the P2P wire protocol.
- [ ] Enforce chain/network ID during handshake.
- [ ] Add peer message-size, timeout and rate limits.
- [ ] Add peer scoring/ban policy for malformed or abusive behavior.
- [ ] Test eclipse/Sybil/peer-churn behavior.
- [ ] Test partition/reconnect and divergent-tip recovery.
- [ ] Test invalid-header/block/transaction flooding.
- [ ] Define seed-node/bootstrap discovery strategy without centralizing consensus.
- [ ] Review privacy implications of peer and transaction propagation.

## 5. Mining-pool security and accounting

- [ ] Freeze and document the production pool protocol.
- [ ] Add TLS/authentication/rate limits where exposed publicly.
- [ ] Implement variable difficulty or a reviewed share-difficulty design.
- [ ] Prevent duplicate/replayed/stale-share credit.
- [ ] Independently review PPLNS/PPS accounting if offered.
- [ ] Implement coinbase-maturity-aware payout construction.
- [ ] Separate pool hot wallet, cold funds and operator/admin keys.
- [ ] Add withdrawal/payout limits and reconciliation.
- [ ] Test pool outage without affecting chain consensus.
- [ ] Confirm miners can solo mine or use third-party pools; no official-pool dependency.

## 6. Wallet security

- [ ] Independent review of Ed25519 key generation/signing/address derivation.
- [ ] Review encrypted wallet backup/import/export flows.
- [ ] Add watch-only and confirmation/reorg-aware balance UX.
- [ ] Enforce production CSP, dependency integrity, secure headers and origin isolation for browser wallet components.
- [ ] Add hardware-wallet/external-signer support or document a reviewed alternative for high-value use.
- [ ] Test recovery across supported clients.
- [ ] Review transaction confirmation UX so users can verify recipient, amount, fee and network.

## 7. Node / RPC / explorer infrastructure

- [ ] Harden mutation RPC behind authentication/private networking.
- [ ] Put public read-only RPC behind production reverse proxy/load balancing.
- [ ] Add horizontally scalable abuse/rate limits.
- [ ] Add WAF/DDoS architecture and capacity testing.
- [ ] Adopt production TLS and certificate rotation.
- [ ] Use centralized secret management; no production secrets in source-controlled `.env` files.
- [ ] Deploy PoW-aware explorer/index storage.
- [ ] Reconcile explorer state against canonical chain after reorganizations.
- [ ] Define archive/pruning/history retention.
- [ ] Verify clean reindex/recovery/bootstrap paths.
- [ ] Run third-party web/API penetration testing.

## 8. Release and genesis integrity

- [ ] Build releases reproducibly from tagged source.
- [ ] Publish cryptographic hashes and dedicated release-signing signatures.
- [ ] Freeze final chain ID/genesis/PoW/economic parameters.
- [ ] Independently verify final genesis artifact.
- [ ] Maintain rollback/emergency patch/compromised-release procedures.
- [ ] Publish SBOM and dependency review.

## 9. Observability and incident response

- [ ] Monitor block production, tip height, cumulative work and difficulty.
- [ ] Monitor peer counts/connectivity and fork/reorg events.
- [ ] Monitor mempool, RPC health, storage and index integrity.
- [ ] Monitor pool share/block/payout health without exposing miner secrets.
- [ ] Define alert routing, escalation and on-call ownership.
- [ ] Conduct chain-stall, deep-reorg, corrupted-database, key-compromise, pool-outage and network-partition drills.
- [ ] Publish a responsible-disclosure process.

## 10. Independent review

- [ ] Independent PoW consensus/fork-choice review.
- [ ] Independent UTXO/state-transition review.
- [ ] Independent cryptography/key-management review.
- [ ] Independent P2P/network/RPC review.
- [ ] Independent wallet review.
- [ ] Independent mining-pool/accounting review.
- [ ] Fuzzing/property-based testing at block/transaction/network boundaries.
- [ ] Remediate and independently retest all high/critical findings before launch.

## 11. Economics, incentives and legal review

- [ ] Finalize production supply/issuance schedule.
- [ ] Finalize block subsidy/halving or alternative reward schedule.
- [ ] Finalize fee policy.
- [ ] Analyze miner/pool centralization incentives.
- [ ] Analyze selfish-mining, fee-sniping and chain-reorg economics.
- [ ] Analyze realistic hash-rate attack cost and confirmation policy.
- [ ] Review production CRKBIT utility/distribution for applicable legal/regulatory requirements.
- [ ] Publish clear user-facing terms and risk disclosures.

## 12. Real multi-node public testnet

- [ ] Operate 4+ independently managed full nodes.
- [ ] Operate multiple independent miners and preferably multiple pools/solo miners.
- [ ] Run 24h → 72h → 7-day+ sustained testnet campaigns.
- [ ] Produce real competing forks and verify highest-chainwork convergence.
- [ ] Run partition/reconnect/reorg campaigns.
- [ ] Run invalid block/transaction/P2P fuzz and load campaigns.
- [ ] Verify full clean-node bootstrap/reindex/recovery.
- [ ] Verify wallet balances and explorer indexes after reorgs.
- [ ] Publish representative evidence without secrets.

## Minimum production launch evidence package

Before a production-mainnet claim, publish at minimum:

1. exact source tag and reproducible release hashes,
2. final genesis + chain/PoW/economic parameters,
3. final PoW algorithm specification and test vectors,
4. P2P/fork-choice/reorg test evidence,
5. independent multi-node soak/partition/reorg/load evidence,
6. wallet/node/pool security-review reports or public summaries,
7. high/critical remediation + retest evidence,
8. incident-response / disaster-recovery runbooks,
9. final mining/pool interoperability documentation,
10. final production economics and legal/compliance position.

Until these gates are satisfied, project documentation should use terms such as **PoW devnet**, **public PoW testnet**, or **mainnet-candidate infrastructure**, not production mainnet.
