# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent technology project building defensive-security tooling for developers, researchers, students and open-source communities. The repository contains an early secure-code scanner plus the Crakbit Chain research/public-testnet stack.

## Current status

- Security scanner: early alpha
- Security CLI: early alpha
- AI Security Assistant: in development
- Crakbit Chain: **v0.28.0a1 launch-rehearsal / independently-corroborated-evidence tooling alpha**
- External consensus candidate: CometBFT `v0.40.0`
- Governed execution protocol: `crakbit-execution/3`
- Browser wallet/public gateway: alpha
- Public-testnet, review/remediation, final-candidate and launch-rehearsal tooling: implemented
- Production CRKBIT: **not launched**
- Official CRKBIT presale: **none**

Crakbit Chain is **not a production mainnet** and should not be used to custody real value.

## Crakbit Chain v0.28

The research/public-testnet stack now includes:

- Ed25519 wallets and `crk1...` addresses,
- signed test CRKBIT transfers,
- CometBFT ABCI integration,
- crash-safe staged FinalizeBlock → atomic Commit,
- deterministic application hashes and native ABCI state sync,
- validator `join` / `remove` / `replace` governance with strict `>2/3` approval,
- browser wallet, hardened gateway, explorer, faucet and test-only Mining Lab,
- v0.23–v0.26 deployment/operations/review/remediation evidence tooling,
- v0.27 coordinated upgrade policy, governance timelocks, economics freeze, external economic/legal review hooks and multi-party release approval,
- **v0.28 signed genesis/start/rollback launch-rehearsal runbooks**,
- **DNS/RPC/explorer cutover rehearsal with no automatic production DNS changes**,
- **configurable public-edge availability/latency/error/capacity/failover evidence**,
- **protected HSM/remote-signer key-rotation and catastrophic-recovery drill records**,
- **coordinated upgrade + rollback rehearsal evidence bound to the v0.27 upgrade plan**,
- **final unresolved-risk register that blocks unmitigated high/critical risks**,
- **independent technical reviewer sign-offs bound to the exact v0.27 final report**,
- **external reproducible-build/transitive-dependency attestation**,
- **aggregate launch-rehearsal gate + signed release-candidate freeze for manual human review only**.

A passing v0.28 rehearsal gate does **not** automatically launch a network, change DNS, move funds or make CRKBIT a production-value asset. Every final v0.28 artifact keeps production readiness/launch claims false.

See [`blockchain/V0.28.md`](blockchain/V0.28.md) and [`blockchain/README.md`](blockchain/README.md).

## Quick test

```bash
git clone https://github.com/navindusasmitha/CrakbitAI.git
cd CrakbitAI/blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## v0.28 launch-rehearsal workflow

```bash
crakchain launch-runbook-v28-build --help
crakchain cutover-rehearsal-v28-build --help
crakchain edge-slo-v28-build --help
crakchain signer-drill-v28-build --help
crakchain upgrade-rehearsal-v28-build --help
crakchain risk-register-v28-build --help
crakchain review-signoff-v28-build --help
crakchain repro-attestation-v28-build --help
crakchain rehearsal-gate-v28-build --help
crakchain release-freeze-v28-build --help
crakchain launch-decision-v28-record --help
```

## Mainnet path

Production launch remains gated by actual independently managed validators, genuine long-running/fault/load/storage/state-sync evidence, protected remote/HSM signing, production RPC/TLS/WAF/DDoS/capacity/secret-management engineering, independently corroborated consensus/application/governance/network/cryptography/browser-wallet review, high/critical remediation/retest, finalized economics/incentives, applicable legal/regulatory review and an explicit human launch/no-launch decision.

See [`blockchain/docs/MAINNET_GATES.md`](blockchain/docs/MAINNET_GATES.md).

## Mining note

The current Mining Lab is a **test-only proof-of-work reward service**, not Crakbit consensus mining. It does not mint new supply or create CometBFT blocks.

## Funding

Crakbit AI is raising development funding for security tooling, infrastructure, testing, documentation and staged blockchain research. The fundraising campaign is **not a CRKBIT token sale and does not promise investment returns**.

## Links

- Website: https://crakbit.space
- Repository: https://github.com/navindusasmitha/CrakbitAI
- Giveth: Crakbit AI is publicly listed on Giveth

## License

Unless otherwise noted, source code in this repository is released under the Apache License 2.0. See [`LICENSE`](LICENSE).
