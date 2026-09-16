# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent, founder-led technology project building accessible security tooling for developers, security researchers, students and open-source communities.

The project is currently in **early development / Security MVP alpha + blockchain public-testnet review-candidate research**. The priority remains useful defensive-security technology and careful public testing before any production blockchain or production-value CRKBIT launch.

## Mission

Make practical cybersecurity, secure coding and blockchain-security tooling more accessible, understandable and easier to integrate into modern software-development workflows.

## What We Are Building

### Crakbit AI Security Assistant

Security-focused AI guidance for secure coding, vulnerability understanding, remediation and defensive-security workflows.

### Crakbit Scanner — Early Alpha

A deterministic static-analysis prototype exists in [`scanner/`](scanner/). Current alpha checks include credential indicators with safe redaction and selected Python/JavaScript/TypeScript insecure coding patterns. The scanner performs static checks only and does not execute target code.

### Blockchain Security

Planned defensive tooling includes smart-contract analysis, contract-risk assessment, public blockchain-data analysis, developer guidance and human-readable security reports.

### Crakbit Chain — v0.21 Public-Testnet / Review-Candidate Alpha

A runnable experimental blockchain/application stack exists in [`blockchain/`](blockchain/).

```text
Browser wallet / CLI / governance tx
        │ signed input
        ▼
Public gateway / CometBFT RPC
        ▼
CometBFT v0.40.0
        │ ABCI
        ▼
Crakbit Go bridge 0.21
        │ authenticated private HTTP
        ▼
crakbit-execution/3
        │
        ├── crash-safe FinalizeBlock → Commit
        ├── replicated validator-governance state
        ├── deterministic ABCI validator updates
        ├── governance-aware app hash
        └── native governance-aware state sync
```

Implemented research/public-testnet components include Ed25519 wallets and `crk1...` addresses, signed CRKBIT test transactions, browser wallet/public gateway, CometBFT ABCI integration, native state sync, indexed explorer tooling, signed review/release evidence, schema migration/rollback rehearsal and v0.21 deterministic validator-governance research.

v0.21 can validate quorum-approved `join`, `remove` and `replace` validator-change transactions. Approval power must be strictly greater than two-thirds of the committed current validator power; the default four-validator/equal-power lab therefore requires 3 of 4 approvals. Governance state is included in the deterministic application hash, and the Go bridge can return the validated update through `ResponseFinalizeBlock.ValidatorUpdates`.

**Important:** v0.21 is not a production mainnet. Independent multi-host validator-change campaigns, activation-boundary fault/recovery tests, protected governance/validator signing, sustained public-testnet operation and independent security review remain required. It must not be used to custody real value.

See [`blockchain/V0.21.md`](blockchain/V0.21.md), [`blockchain/README.md`](blockchain/README.md) and [`blockchain/docs/MAINNET_GATES.md`](blockchain/docs/MAINNET_GATES.md).

## Browser Wallet / Web UI

The test wallet interface provides local Ed25519 wallet generation, PBKDF2-SHA256 + AES-GCM encrypted vaults, encrypted backup/import, local transaction signing, balances/activity, transfers, explorer views, validators, faucet requests and the opt-in Mining Lab.

The gateway is not intended to receive the wallet private key. The wallet is not an audited hardware-wallet replacement. See [`blockchain/docs/WALLET_THREAT_MODEL.md`](blockchain/docs/WALLET_THREAT_MODEL.md).

## Mining Lab

The Mining Lab is a **test-only work reward, not blockchain consensus mining**. It does not mint new supply, create CometBFT blocks, select validators or change voting power.

## Quick Start — Security Scanner

Requires Python 3.10+.

```bash
git clone https://github.com/navindusasmitha/CrakbitAI.git
cd CrakbitAI/scanner
python -m venv .venv
pip install -e ".[dev]"
crak scan ../your-project
```

## Quick Start — Crakbit Chain

Requires Python 3.11+.

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

Go bridge:

```bash
cd cometbft-app
go mod download
go test -mod=mod ./...
```

The external-consensus candidate uses the CometBFT bridge and v0.21 governed execution service documented in [`blockchain/README.md`](blockchain/README.md).

## v0.21 Validator Governance

Existing application state should be migrated using the offline-copy v0.21 migration before enabling governance on a non-pristine node. Multi-operator validator-change requests can then be built, signed independently by current validator operators and verified for strict `>2/3` quorum before controlled testnet broadcast.

Never collect validator private keys onto one machine simply to assemble approvals. Keep validator, governance/release/evidence, wallet, TLS, faucet/mining and service credentials separated.

## Current Project Status

| Component | Status |
| --- | --- |
| Public website | Active |
| Giveth project | Publicly listed |
| AI Security Assistant | In development |
| Secure Code Scanner | Early alpha available |
| Security CLI | Early alpha |
| Crakbit Chain package | **v0.21.0a1 alpha** |
| Browser wallet/public gateway | Alpha implemented |
| CometBFT ABCI bridge | **v0.21 governed integration implemented** |
| External execution | **`crakbit-execution/3` implemented** |
| Validator governance | **Deterministic testnet path implemented; real multi-host campaigns pending** |
| Native ABCI application state sync | **Governance-aware code implemented; live independent-host evidence pending** |
| Upgrade migration/rollback | **Offline-copy rehearsal implemented** |
| Review/release evidence | Implemented |
| Independent-host public testnet evidence | Not completed |
| Independent consensus/security audit | Not completed |
| Production CRKBIT | **Not launched** |

## Roadmap

The high-level path is security MVP → developer tooling → blockchain-security tooling → public-testnet research → governed multi-node campaigns → long-lived independent-host testnet → independent review → operations/economic/legal readiness → mainnet consideration.

See [`ROADMAP.md`](ROADMAP.md).

## Public-Benefit Funding

Crakbit AI is raising funds to support the Security MVP, security research, infrastructure, developer tools, documentation, testing and carefully staged blockchain/testnet research.

The current fundraising target is **USD 150,000** with milestone-based allocation. See [`docs/FUNDING.md`](docs/FUNDING.md).

**The current fundraising campaign is not a CRKBIT token sale and does not promise investment returns.**

## CRKBIT Notice

**Production CRKBIT has not launched. There is currently no official CRKBIT presale or production token contract.**

The repository contains test-only CRKBIT accounting used in development/research/public-testnet work. These units have no represented production value and should not be marketed or sold as mainnet CRKBIT.

The proposed development parameters use 8 decimals and a 21,000,000 maximum genesis supply. Those are not final production economics and remain subject to technical, security, economic and applicable legal review.

## Security and Responsible Use

Crakbit AI is being developed primarily for defensive security, secure software development, code review, research and educational use.

Please read [`SECURITY.md`](SECURITY.md), [`blockchain/SECURITY.md`](blockchain/SECURITY.md) and [`blockchain/docs/MAINNET_GATES.md`](blockchain/docs/MAINNET_GATES.md).

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) before contributing.

## Official Links

- Website: https://crakbit.space
- Repository: https://github.com/navindusasmitha/CrakbitAI
- Funding / Giveth: Crakbit AI is publicly listed on Giveth

## Transparency

Project documentation distinguishes implemented code, test evidence, public-testnet operation and production readiness. A feature being present in source code is not the same as that feature being independently audited or ready for real-value use.

See [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md).

## License

Unless otherwise noted, source code in this repository is released under the Apache License 2.0. See [`LICENSE`](LICENSE).

---

**Crakbit AI** — Secure Code. Secure Chains. Build the Future.
