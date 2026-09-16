# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent technology project building defensive-security tooling for developers, researchers, students and open-source communities. The repository contains an early secure-code scanner plus the Crakbit Chain research/public-testnet stack.

## Current status

- Security scanner: early alpha
- Security CLI: early alpha
- AI Security Assistant: in development
- Crakbit Chain: **v0.27.0a1 final mainnet-candidate policy/evidence alpha**
- External consensus candidate: CometBFT `v0.40.0`
- Governed execution protocol: `crakbit-execution/3`
- Browser wallet/public gateway: alpha
- Public-testnet deployment, operational-hardening, review/remediation and final-candidate policy tooling: implemented
- Production CRKBIT: **not launched**
- Official CRKBIT presale: **none**

Crakbit Chain is **not a production mainnet** and should not be used to custody real value.

## Crakbit Chain v0.27

The research/public-testnet stack now includes:

- Ed25519 wallets and `crk1...` addresses,
- signed test CRKBIT transfers,
- CometBFT ABCI integration,
- crash-safe staged FinalizeBlock → atomic Commit,
- deterministic application hashes and native ABCI state sync,
- validator `join` / `remove` / `replace` governance with strict `>2/3` current voting-power approval,
- browser wallet, hardened gateway, explorer, faucet and test-only Mining Lab,
- v0.23–v0.25 independent-operator/public-testnet/operations/review-freeze evidence tooling,
- v0.26 signed independent-review findings, remediation, retest, supply-chain and public-edge gates,
- **v0.27 signed coordinated upgrade/rollback plans with strict `>2/3` validator readiness**,
- **conservative governance timelock/emergency/cancellation policy artifacts**,
- **signed CRKBIT economics/genesis parameter freeze with no token-sale or return promise**,
- **signed independent economic-security and legal/regulatory attestations bound to the exact candidate**,
- **deterministic candidate identity + minimum three unique release approvals**,
- **final mainnet-candidate evidence gate and signed final report**.

A passing v0.27 gate means only that the modeled final candidate evidence is internally consistent. It does **not** launch mainnet, create production-value CRKBIT, approve real-value custody or replace independent human/security/economic/legal judgment.

See [`blockchain/V0.27.md`](blockchain/V0.27.md) and [`blockchain/README.md`](blockchain/README.md).

## Quick test

```bash
git clone https://github.com/navindusasmitha/CrakbitAI.git
cd CrakbitAI/blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## v0.27 final-candidate workflow

```bash
crakchain upgrade-plan-v27-build --help
crakchain governance-policy-v27-build --help
crakchain economics-freeze-v27-build --help
crakchain external-review-v27-build --help
crakchain candidate-identity-v27-build --help
crakchain release-approval-v27-build --help
crakchain final-gate-v27-build --help
crakchain final-report-v27-build --help
```

## Mainnet path

Production launch remains gated by actual independently managed validators, genuine long-running/fault/load/storage/state-sync evidence, protected remote/HSM signing, production RPC/TLS/WAF/DDoS/capacity/secret-management engineering, independently corroborated consensus/application/governance/network/cryptography/browser-wallet review, high/critical remediation/retest, finalized economics/incentives, applicable legal/regulatory review and an explicit human launch decision.

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
