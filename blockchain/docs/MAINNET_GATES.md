# Crakbit Chain — Production Mainnet Release Gates

This document defines conditions that must be satisfied before Crakbit Chain can responsibly be described as a production mainnet.

**Current status: gates are not satisfied.** The active research direction is the native PoW path introduced in v0.31 and networked in v0.32. Production CRKBIT has not launched.

The earlier CometBFT/BFT validator stack remains legacy/research infrastructure and does not satisfy PoW-specific launch gates by itself.

## 1. Native PoW consensus and chain selection

- [ ] Freeze the production PoW algorithm after benchmarking and independent review.
- [ ] Define deterministic seed/key scheduling for the final algorithm if required.
- [ ] Validate final PoW target rules against independent implementations/test vectors.
- [x] Implement P2P block/header/transaction propagation path.
- [x] Implement competing-fork storage and highest-cumulative-work fork choice.
- [x] Implement replay-validated canonical reorganization.
- [x] Reconcile mempool/disconnected transactions across reorganizations.
- [x] Implement bounded orphan handling and peer synchronization path.
- [x] Add median-time-past branch timestamp rules.
- [ ] Add an efficient reviewed UTXO undo/reorg journal for long histories.
- [ ] Verify difficulty retarget behavior under adversarial timestamp/hash-rate changes.
- [ ] Test long/deep reorg boundaries, invalid work and malicious fork inputs.
- [ ] Publish deterministic consensus test vectors.

## 2. UTXO / transaction / monetary correctness

- [ ] Independently review transaction signing and ownership validation.
- [ ] Independently review UTXO conservation and integer-overflow boundaries.
- [ ] Review coinbase creation, maturity and fee accounting.
- [ ] Review subsidy/halving/issuance arithmetic over the complete intended schedule.
- [ ] Define dust/minimum-output policy.
- [ ] Define transaction size/weight limits.
- [ ] Define production fee and mempool eviction policy.
- [ ] Add transaction malleability/replay/network-domain protections as needed.
- [ ] Test reorg effects on confirmed/unconfirmed wallet balances.
- [ ] Publish supply/issuance verification tooling.

## 3. Mining algorithm and miner interoperability

- [ ] Benchmark the final algorithm across representative CPUs and GPUs.
- [ ] Evaluate ASIC/FPGA risk and state intended hardware-neutrality goals accurately.
- [ ] Review PoW validation cost for CPU/memory denial-of-service exposure.
- [ ] Build/verify a native optimized reference miner.
- [ ] Implement standard mining interoperability for the final algorithm (e.g. Stratum where appropriate).
- [ ] Verify third-party miner interoperability if supported.
- [ ] Publish block-header/job-format test vectors.
- [ ] Test stale work, duplicate shares and malformed mining submissions.
- [ ] Ensure pool/miner protocol never exposes wallet/private keys.

## 4. P2P network security

- [x] Version and document the research P2P wire protocol (`crakbit-p2p/1`).
- [x] Enforce chain/genesis identity during signed handshake.
- [x] Add basic peer message-size and rate limits.
- [x] Add basic peer scoring for malformed/abusive behavior.
- [x] Add static seed nodes plus bounded peer exchange.
- [x] Add locator/header announcement + block-fetch synchronization path.
- [ ] Persist peer reputation/address state.
- [ ] Add and review anti-eclipse/Sybil peer-diversity controls.
- [ ] Test peer churn, partition/reconnect and divergent-tip recovery at scale.
- [ ] Fuzz invalid-header/block/transaction/network-message flooding.
- [ ] Benchmark large-chain initial synchronization.
- [ ] Review NAT/privacy/onion/transport choices.

## 5. Mining-pool security and accounting

- [x] First-party native pool prototype with separate share/network targets.
- [x] Test PPLNS accounting.
- [ ] Freeze/document a production pool protocol.
- [ ] Add TLS/authentication/rate limits where exposed publicly.
- [ ] Implement variable difficulty or a reviewed share-difficulty design.
- [ ] Prevent duplicate/replayed/stale-share credit.
- [ ] Independently review pool accounting.
- [ ] Implement coinbase-maturity-aware payout construction.
- [ ] Separate pool hot wallet, cold funds and operator/admin keys.
- [ ] Add withdrawal/payout limits and reconciliation.
- [ ] Test pool outage without affecting consensus.
- [ ] Preserve solo mining and third-party pool support.

## 6. Wallet security

- [ ] Independent review of Ed25519 key generation/signing/address derivation.
- [ ] Review encrypted wallet backup/import/export flows.
- [ ] Add watch-only and confirmation/reorg-aware balance UX.
- [ ] Enforce production CSP, dependency integrity, secure headers and origin isolation.
- [ ] Add hardware-wallet/external-signer support or a reviewed alternative for high-value use.
- [ ] Test recovery across supported clients.
- [ ] Review transaction confirmation UX for recipient, amount, fee and network verification.

## 7. Node / RPC / explorer infrastructure

- [ ] Harden mutation RPC behind authentication/private networking.
- [ ] Put public read-only/mining RPC behind production reverse proxy/load balancing.
- [ ] Add horizontally scalable abuse/rate limits.
- [ ] Add WAF/DDoS architecture and capacity testing.
- [ ] Adopt production TLS and certificate rotation.
- [ ] Use centralized secret management; no production secrets in source-controlled files.
- [ ] Deploy PoW-aware explorer/index storage.
- [ ] Reconcile explorer state after reorganizations.
- [ ] Define archive/pruning/history retention.
- [ ] Verify clean reindex/recovery/bootstrap paths.
- [ ] Run third-party web/API penetration testing.

## 8. Release and genesis integrity

- [ ] Build releases reproducibly from tagged source.
- [ ] Publish cryptographic hashes and dedicated release signatures.
- [ ] Freeze final chain ID/genesis/PoW/economic parameters.
- [ ] Independently verify final genesis artifact.
- [ ] Maintain rollback/emergency patch/compromised-release procedures.
- [ ] Publish SBOM and dependency review.

## 9. Observability and incident response

- [ ] Monitor block production, tip height/hash, cumulative work and difficulty.
- [ ] Monitor peer diversity/connectivity and fork/reorg events.
- [ ] Monitor mempool, RPC health, storage and index integrity.
- [ ] Monitor pool share/block/payout health without exposing miner secrets.
- [ ] Define alert routing, escalation and on-call ownership.
- [ ] Conduct chain-stall, deep-reorg, corrupted-database, key-compromise, pool-outage and partition drills.
- [ ] Publish a responsible-disclosure process.

## 10. Independent review

- [ ] Independent PoW consensus/fork-choice/reorg review.
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
- [ ] Analyze 51%/selfish-mining/fee-sniping/reorg economics.
- [ ] Analyze realistic hash-rate attack cost and confirmation policy.
- [ ] Review production CRKBIT utility/distribution for applicable legal/regulatory requirements.
- [ ] Publish clear user-facing terms and risk disclosures.

## 12. Real multi-node public testnet

- [ ] Operate 4+ independently managed full nodes.
- [ ] Operate multiple independent miners and preferably multiple pools/solo miners.
- [ ] Run 24h → 72h → 7-day+ sustained campaigns.
- [ ] Produce real competing forks and verify highest-work convergence.
- [ ] Run partition/reconnect/reorg campaigns.
- [ ] Run invalid block/transaction/P2P fuzz and load campaigns.
- [ ] Verify clean-node bootstrap/reindex/recovery.
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
8. incident-response/disaster-recovery runbooks,
9. final mining/pool interoperability documentation,
10. final production economics and legal/compliance position.

Until these gates are satisfied, project documentation should use terms such as **PoW devnet**, **public PoW testnet**, or **mainnet-candidate infrastructure**, not production mainnet.
