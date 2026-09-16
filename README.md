# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent technology project building defensive-security tooling for developers, researchers, students and open-source communities. The repository currently contains an early secure-code scanner plus the Crakbit Chain research/public-testnet stack.

## Current status

- Security scanner: early alpha
- Security CLI: early alpha
- AI Security Assistant: in development
- Crakbit Chain: **v0.22.0a1 public-testnet / review-candidate alpha**
- External consensus candidate: CometBFT `v0.40.0`
- Governed execution protocol: `crakbit-execution/3`
- Browser wallet/public gateway: alpha
- Production CRKBIT: **not launched**
- Official CRKBIT presale: **none**

Crakbit Chain is **not a production mainnet** and should not be used to custody real value.

## Crakbit Chain v0.22

The chain research path currently includes:

- Ed25519 wallets and `crk1...` addresses,
- signed test CRKBIT transfers,
- CometBFT ABCI integration,
- crash-safe staged FinalizeBlock → atomic Commit,
- deterministic application hashes,
- native ABCI state sync,
- validator `join` / `remove` / `replace` governance with strict `>2/3` current voting-power approval,
- governance state committed into the application hash,
- deterministic ABCI validator updates,
- schema migration/rollback rehearsal,
- browser wallet, public gateway, explorer, faucet and test-only Mining Lab,
- reproducible-build/SBOM/release-evidence tooling,
- v0.22 governed four-node lab generation,
- cluster app-hash/governance divergence monitoring,
- governance history export,
- signed validator-governance campaign evidence.

See [`blockchain/V0.22.md`](blockchain/V0.22.md) and [`blockchain/README.md`](blockchain/README.md).

## Quick test

```bash
git clone https://github.com/navindusasmitha/CrakbitAI.git
cd CrakbitAI/blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## Governed local testnet lab

With the pinned CometBFT candidate binary installed:

```bash
crakchain governed-lab-create \
  --cometbft /path/to/cometbft \
  --output runtime/governed-v22-lab \
  --chain-id crakbit-v22-local \
  --nodes 4
```

The generated validator/treasury/governance keys are disposable local-lab keys only and must never be reused for a public or production network.

## Mainnet path

The codebase has moved beyond a basic blockchain demo, but production launch remains gated by real operational evidence and independent review. Required work still includes independent-host validators, long-duration soak/fault/load/state-sync campaigns, protected remote/HSM signing, production RPC/TLS/WAF/DDoS/secret-management engineering, independent consensus/application/network/cryptography/browser-wallet review, final validator/CRKBIT economics and applicable legal/regulatory review.

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
