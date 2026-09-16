# Crakbit Chain — Production Mainnet Release Gates

This document defines conditions that must be satisfied before the project can responsibly describe a Crakbit Chain release as a production mainnet candidate or production mainnet.

**Current status: gates are not satisfied.** The repository contains research/devnet and public-testnet-candidate infrastructure only. Production CRKBIT has not launched.

## Consensus and deterministic execution

- [ ] Operate the selected external BFT implementation across multiple independent hosts for an extended test period.
- [ ] Complete and review the full consensus/application interface, including FinalizeBlock, Commit, replay and crash recovery.
- [ ] Verify deterministic application hashes across independent nodes under sustained workloads.
- [ ] Complete external-consensus snapshot/state-sync integration and recovery testing.
- [ ] Define validator-set lifecycle, onboarding, removal, rotation and emergency procedures.
- [ ] Define protocol upgrade and chain-halt/restart procedures.
- [ ] Publish reproducible partition, latency, packet-loss, restart and sustained-load evidence.
- [ ] Test Byzantine/malformed input behavior at consensus and application boundaries.

## Validator and key security

- [ ] Keep CometBFT node/validator keys separate from Crakbit wallet, research-validator, TLS, release, faucet and mining-reward keys.
- [ ] Adopt remote-signer, HSM or equivalent protected validator-key custody for production operators.
- [ ] Define validator backup, rotation, compromise and revocation procedures.
- [ ] Use authenticated/encrypted private validator networking where appropriate.
- [ ] Complete certificate lifecycle, pinning/rotation and secret-management design.
- [ ] Run validator disaster-recovery drills without copying private keys into unsafe locations.

## Wallet security

- [ ] Complete an independent review of the browser wallet's key generation, canonical signing, encryption and backup formats.
- [ ] Publish a wallet threat model covering XSS, malicious extensions, compromised origins, local-storage theft and phishing.
- [ ] Enforce strict production CSP, dependency integrity, secure headers and origin isolation.
- [ ] Add hardware-wallet / external-signer support or document a reviewed alternative for high-value use.
- [ ] Test import/export compatibility and recovery across supported clients.
- [ ] Complete transaction confirmation UX review so users can clearly verify recipient, amount, fee and network.

## Public RPC and Web infrastructure

- [ ] Put public RPC/gateway services behind production reverse-proxy/load-balancer controls.
- [ ] Add upstream connection, request, transaction and abuse limits that survive process restarts and scale horizontally.
- [ ] Complete WAF/DDoS architecture and capacity testing.
- [ ] Restrict execution service, ABCI sockets, validator services and operator endpoints to private/authorized networks.
- [ ] Adopt production TLS configuration and automated certificate rotation.
- [ ] Add centralized secret management; do not deploy secrets in source-controlled `.env` files.
- [ ] Run third-party web/API penetration testing.

## Explorer, indexing and data availability

- [ ] Deploy a dedicated indexed explorer database for external-consensus history.
- [ ] Reconcile explorer indexes against consensus/application state and publish recovery procedures.
- [ ] Define archive-node and history-retention requirements.
- [ ] Verify snapshot/archive/replay paths from clean hosts.
- [ ] Provide independently verifiable block, transaction and application-state commitments.

## Faucet and mining-lab separation

- [ ] Keep faucet and proof-of-work reward services explicitly testnet-only unless a separately reviewed production design is approved.
- [ ] Keep faucet/mining reward keys separate from validator and release keys.
- [ ] Apply persistent distribution limits and upstream abuse controls.
- [ ] Do not represent Mining Lab work as consensus block mining. The current external consensus path is BFT/CometBFT-based.

## Release and genesis integrity

- [ ] Build releases reproducibly from tagged source.
- [ ] Publish cryptographic hashes and dedicated release-signing signatures.
- [ ] Run a documented genesis ceremony with independently held validator keys.
- [ ] Verify the final genesis artifact, validator set and release artifacts before launch.
- [ ] Maintain rollback, emergency patch and compromised-release procedures.

## Observability and incident response

- [ ] Run production metrics, logs and alerts without leaking secrets or sensitive request data.
- [ ] Monitor validator availability, consensus progress, app hashes, peer connectivity, RPC health and storage integrity.
- [ ] Define alert routing, escalation and on-call ownership.
- [ ] Conduct chain-halt, validator-loss, key-compromise, corrupted-database and network-partition incident drills.
- [ ] Publish a responsible disclosure process for chain/wallet/network vulnerabilities.

## Independent review

- [ ] Independent consensus review.
- [ ] Independent application/state-transition review.
- [ ] Independent cryptography/key-management review.
- [ ] Independent network/RPC/validator security review.
- [ ] Independent browser-wallet review.
- [ ] Remediate or explicitly accept every high/critical finding before launch.

## Economics, policy and legal review

- [ ] Finalize production supply, issuance/reward/fee and validator-incentive rules separately from devnet assumptions.
- [ ] Evaluate economic attacks and validator incentives.
- [ ] Review any production CRKBIT utility and distribution plan for applicable legal/regulatory requirements.
- [ ] Publish clear user-facing terms and risk disclosures appropriate to the final deployment.

## Minimum launch evidence package

Before a production mainnet claim, publish at minimum:

1. exact source commit/tag and reproducible release hashes,
2. final genesis artifact and ceremony attestations,
3. external-consensus version and configuration,
4. independent-host soak/partition/restart/load results,
5. state-sync and disaster-recovery evidence,
6. independent security-review reports or public summaries,
7. validator/key operational runbook,
8. incident-response plan,
9. wallet security/recovery documentation,
10. final production economics and legal/compliance position.

Until these gates are satisfied, project documentation should use terms such as **research devnet**, **public testnet**, or **mainnet-candidate infrastructure**, not production mainnet.
