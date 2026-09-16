# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent technology project building defensive-security tooling for developers, researchers, students and open-source communities. The repository contains an early secure-code scanner plus the Crakbit Chain research/public-testnet stack.

## Current status

- Security scanner: early alpha
- Security CLI: early alpha
- AI Security Assistant: in development
- Crakbit Chain: **v0.24.0a1 public-testnet / operational-review-candidate alpha**
- External consensus candidate: CometBFT `v0.40.0`
- Governed execution protocol: `crakbit-execution/3`
- Browser wallet/public gateway: alpha
- Public-testnet deployment + operational-hardening tooling: implemented
- Production CRKBIT: **not launched**
- Official CRKBIT presale: **none**

Crakbit Chain is **not a production mainnet** and should not be used to custody real value.

## Crakbit Chain v0.24

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
- **v0.24 host preflight for exact package/CometBFT/genesis identity, private binds, token presence and disk readiness**,
- **typed fault/recovery evidence for restart, process-kill, partition, latency, packet-loss, load and storage campaigns**,
- **backup-restore and clean-host state-sync convergence records**,
- **remote-signer/HSM-style drill evidence without private-key material**,
- **redundant RPC/explorer checks with same-height app-hash divergence detection**,
- **separate real-duration 24h, 72h and 7-day soak gates**,
- **signed operations evidence bound to exact source commit and artifact hashes**.

See [`blockchain/V0.24.md`](blockchain/V0.24.md) and [`blockchain/README.md`](blockchain/README.md).

## Quick test

```bash
git clone https://github.com/navindusasmitha/CrakbitAI.git
cd CrakbitAI/blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## Operational evidence workflow

The v0.24 commands are intended for a real authorized public-testnet environment. Start with host preflight, collect actual soak/fault/recovery/signer/redundancy artifacts, then build and sign a readiness evidence set.

```bash
crakchain host-preflight-v24 --help
crakchain fault-v24-plan-build --help
crakchain recovery-v24-record --help
crakchain redundancy-v24-check --help
crakchain readiness-v24-build --help
crakchain ops-v24-sign --help
```

Fault plans are dry-run by default and every planned fault requires an explicit recovery command. The repository does **not** treat generated files as proof that a real independent-host campaign occurred.

## Mainnet path

Production launch remains gated by actual independently managed validators, genuine 24h → 72h → 7-day operation, real fault/load/storage/state-sync campaigns, protected remote/HSM signing, production RPC/TLS/WAF/DDoS/secret-management engineering, independent consensus/application/governance/network/cryptography/browser-wallet review, final validator/CRKBIT economics and applicable legal/regulatory review.

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
