# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent technology project building defensive-security tooling for developers, researchers, students and open-source communities. The repository contains an early secure-code scanner plus the Crakbit Chain research/public-testnet stack.

## Current status

- Security scanner: early alpha
- Security CLI: early alpha
- AI Security Assistant: in development
- Crakbit Chain: **v0.23.0a1 public-testnet / review-candidate alpha**
- External consensus candidate: CometBFT `v0.40.0`
- Governed execution protocol: `crakbit-execution/3`
- Browser wallet/public gateway: alpha
- Public-testnet deployment/monitoring tooling: implemented
- Production CRKBIT: **not launched**
- Official CRKBIT presale: **none**

Crakbit Chain is **not a production mainnet** and should not be used to custody real value.

## Crakbit Chain v0.23

The chain research path currently includes:

- Ed25519 wallets and `crk1...` addresses,
- signed test CRKBIT transfers,
- CometBFT ABCI integration,
- crash-safe staged FinalizeBlock → atomic Commit,
- deterministic application hashes and native ABCI state sync,
- validator `join` / `remove` / `replace` governance with strict `>2/3` current voting-power approval,
- governance state committed into the application hash and deterministic ABCI validator updates,
- schema migration/rollback rehearsal,
- browser wallet, public gateway, explorer, faucet and test-only Mining Lab,
- reproducible-build/SBOM/release-evidence tooling,
- governed multi-node campaign tooling from v0.22,
- **public validator identity export with secret-field rejection**,
- **4+ validator public-testnet inventory and operator/provider/region diversity gates**,
- **shared application + CometBFT genesis bundles without private material**,
- **per-operator deployment bundles and systemd service templates**,
- **independent-node height/app-hash monitoring and divergence detection**,
- **24h+ soak collection and readiness gates**,
- **signed public-testnet operations evidence tied to exact Git/artifact hashes**.

See [`blockchain/V0.23.md`](blockchain/V0.23.md) and [`blockchain/README.md`](blockchain/README.md).

## Quick test

```bash
git clone https://github.com/navindusasmitha/CrakbitAI.git
cd CrakbitAI/blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## v0.23 public-testnet workflow

Each independent validator operator first exports **public metadata only** from their own node. After collecting at least four identities, build the shared inventory/genesis/operator bundles and then collect live operational evidence.

```bash
crakchain public-testnet-inventory-build \
  --chain-id crakbit-public-testnet-1 \
  --network-name "Crakbit Public Testnet 1" \
  --identity validator-1-public.json \
  --identity validator-2-public.json \
  --identity validator-3-public.json \
  --identity validator-4-public.json \
  --output public-testnet-inventory.json
```

The repository provides deployment and evidence tooling, but **does not claim an independent-host public testnet has been operated merely because the tooling exists**.

## Mainnet path

Production launch remains gated by actual long-running independent-host evidence and independent review. Required work still includes real VPS validator operation, 24h → 72h → 7-day soak/fault/load/state-sync campaigns, protected remote/HSM signing, production RPC/TLS/WAF/DDoS/secret-management engineering, independent consensus/application/governance/network/cryptography/browser-wallet review, final validator/CRKBIT economics and applicable legal/regulatory review.

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
