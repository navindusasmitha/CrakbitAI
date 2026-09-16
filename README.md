# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent technology project building defensive-security tooling for developers, researchers, students and open-source communities. The repository contains an early secure-code scanner plus the Crakbit Chain research/public-testnet stack.

## Current status

- Security scanner: early alpha
- Security CLI: early alpha
- AI Security Assistant: in development
- Crakbit Chain: **v0.26.0a1 public-testnet / independent-review-remediation alpha**
- External consensus candidate: CometBFT `v0.40.0`
- Governed execution protocol: `crakbit-execution/3`
- Browser wallet/public gateway: alpha
- Public-testnet deployment, operational-hardening, review-freeze and remediation tooling: implemented
- Production CRKBIT: **not launched**
- Official CRKBIT presale: **none**

Crakbit Chain is **not a production mainnet** and should not be used to custody real value.

## Crakbit Chain v0.26

The research/public-testnet stack now includes:

- Ed25519 wallets and `crk1...` addresses,
- signed test CRKBIT transfers,
- CometBFT ABCI integration,
- crash-safe staged FinalizeBlock → atomic Commit,
- deterministic application hashes and native ABCI state sync,
- validator `join` / `remove` / `replace` governance with strict `>2/3` current voting-power approval,
- governance-aware snapshots/migrations and deterministic validator updates,
- browser wallet, hardened gateway, explorer, faucet and test-only Mining Lab,
- reproducible-build/SBOM/release/review evidence tooling,
- v0.23 independent-operator inventory, genesis/deployment bundles and public-testnet monitoring,
- v0.24 host preflight, authorized fault/recovery records, redundant-edge checks, protected-signer evidence and 24h/72h/7-day readiness gates,
- v0.25 signed operator evidence, incident-response records and exact independent-review candidate freeze,
- **v0.26 signed review-finding register with stable IDs**,
- **hard blocker for high/critical findings until fixes are independently retested on the exact candidate commit**,
- **signed supply-chain/reproducible-build attestations tied to dependency-lock and SBOM hashes**,
- **signed public-edge TLS/WAF/DDoS/load/failover attestations without provider secrets**,
- **candidate supersession rules and signed post-remediation re-freeze**.

A passing v0.26 remediation gate is not an audit verdict or mainnet approval. It only verifies consistency of the supplied signed review/remediation evidence.

See [`blockchain/V0.26.md`](blockchain/V0.26.md) and [`blockchain/README.md`](blockchain/README.md).

## Quick test

```bash
git clone https://github.com/navindusasmitha/CrakbitAI.git
cd CrakbitAI/blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## v0.26 review remediation workflow

```bash
crakchain review-findings-v26-build --help
crakchain review-retest-v26-build --help
crakchain supply-attestation-v26-build --help
crakchain edge-attestation-v26-build --help
crakchain remediation-gate-v26-build --help
crakchain review-refreeze-v26-build --help
crakchain review-refreeze-v26-verify --help
```

The repository does **not** claim that real independent VPS validators, seven-day soak campaigns, protected-signer deployment or independent security review have completed merely because the tooling exists.

## Mainnet path

Production launch remains gated by actual independently managed validators, genuine long-running/fault/load/storage/state-sync evidence, protected remote/HSM signing, production RPC/TLS/WAF/DDoS/secret-management engineering, independent consensus/application/governance/network/cryptography/browser-wallet review, remediation and independent retest of high/critical findings, final validator/CRKBIT economics and applicable legal/regulatory review.

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
