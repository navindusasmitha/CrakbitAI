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

### Crakbit Chain — v0.19 Public-Testnet / Review-Candidate Alpha

A runnable experimental blockchain/application stack exists in [`blockchain/`](blockchain/).

```text
Browser wallet / CLI
        │ signed transaction
        ▼
Public gateway / controlled edge
        │ CometBFT JSON-RPC
        ▼
CometBFT v0.40.0
        │ ABCI
        ▼
Crakbit Go bridge
        │ authenticated private HTTP
        ▼
crakbit-execution/2
        │
        ├── crash-safe FinalizeBlock → Commit
        ├── native ABCI snapshot state sync
        └── deterministic application state
                │
                ├── explorer index / reconciliation
                ├── health / soak / fault evidence
                ├── review remediation matrix
                └── signed release provenance
```

Implemented research/public-testnet components include:

- Ed25519 wallets and `crk1...` addresses,
- signed CRKBIT test transactions,
- browser wallet with encrypted local vault and client-side signing,
- public wallet/explorer gateway,
- CometBFT `v0.40.0` ABCI bridge,
- crash-safe staged FinalizeBlock → atomic Commit application flow,
- native ABCI `ListSnapshots`, `OfferSnapshot`, `LoadSnapshotChunk`, `ApplySnapshotChunk` state sync,
- deterministic application checkpoints and explorer reconciliation,
- multi-validator lab generation and health/soak/fault tooling,
- signed public-testnet evidence and review-freeze artifacts,
- review finding/remediation matrix with high/critical release gating,
- reproducible Python wheel and Go bridge checks in CI,
- direct-dependency CycloneDX SBOM generation,
- signed release provenance and signed operations-drill evidence,
- browser wallet security headers/threat model,
- test faucet and optional browser SHA-256 Mining Lab reward system,
- Python + Go automated blockchain CI.

The older Python prevote/precommit chain remains for research/backwards-compatible local experiments. It is not the intended production BFT path.

**Important:** v0.19 is not a production mainnet. Sustained independent-host operation, live recovery evidence, protected validator-key custody, real fault/load campaigns, complete supply-chain review and independent consensus/application/network/wallet security review are still required. It must not be used to custody real value.

See [`blockchain/V0.19.md`](blockchain/V0.19.md), [`blockchain/README.md`](blockchain/README.md) and [`blockchain/docs/MAINNET_GATES.md`](blockchain/docs/MAINNET_GATES.md).

## Browser Wallet / Web UI

The test wallet interface provides local Ed25519 wallet generation, PBKDF2-SHA256 + AES-GCM encrypted vaults, encrypted backup/import, local transaction signing, balances/activity, transfers, explorer views, validators, faucet requests and the opt-in Mining Lab.

The gateway is not intended to receive the wallet private key. The wallet is not an audited hardware-wallet replacement. See [`blockchain/docs/WALLET_THREAT_MODEL.md`](blockchain/docs/WALLET_THREAT_MODEL.md).

## Mining Lab

The Mining Lab is a **test-only work reward**, not blockchain consensus mining.

```text
browser solves SHA-256 challenge
        ↓
server verifies work
        ↓
dedicated funded reward wallet
        ↓
ordinary signed test CRKBIT transaction
```

It does not mint new supply, create CometBFT blocks, select validators or change voting power.

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

The normal `crakchain node` path still targets the older research node. The external-consensus candidate uses the CometBFT bridge and external execution service documented in [`blockchain/README.md`](blockchain/README.md).

## v0.19 Release Engineering

Build a direct-dependency SBOM:

```bash
cd blockchain
crakchain sbom-build \
  --repo-root .. \
  --output runtime/release/sbom.cdx.json
```

Build/check a security-review remediation matrix:

```bash
SOURCE_COMMIT=$(git rev-parse HEAD)

crakchain review-findings-build \
  --source-commit "$SOURCE_COMMIT" \
  --finding private/review-findings.json \
  --output runtime/review/remediation-matrix.json

crakchain review-findings-check \
  --matrix runtime/review/remediation-matrix.json
```

The automated gate stays blocked while high/critical findings are unresolved or remediated high/critical findings have no recorded regression-test reference.

Signed release provenance can bind exact source commit, package version, CometBFT version, genesis identity, SBOM, reproducibility report and selected artifact hashes. See [`blockchain/V0.19.md`](blockchain/V0.19.md).

## Current Project Status

| Component | Status |
| --- | --- |
| Public website | Active |
| Giveth project | Publicly listed |
| AI Security Assistant | In development |
| Secure Code Scanner | Early alpha available |
| Security CLI | Early alpha |
| Developer API | Planned |
| Smart-contract scanner | Planned |
| Crakbit Chain package | **v0.19.0a1 alpha** |
| Browser wallet/public gateway | **Alpha implemented** |
| CometBFT ABCI bridge | **Integration implemented** |
| Native ABCI application state sync | **Code implemented; live independent-host evidence pending** |
| Explorer reconciliation | **Implemented** |
| Review remediation matrix | **v0.19 implemented** |
| Reproducible build CI | **v0.19 Python wheel + Go bridge checks implemented** |
| Direct-dependency SBOM | **v0.19 implemented; full transitive inventory pending** |
| Signed release provenance | **v0.19 implemented** |
| Independent-host public testnet evidence | Not completed |
| Independent consensus/security audit | Not completed |
| Production CRKBIT | **Not launched** |

## Roadmap

The high-level path is:

1. Security MVP and developer tooling
2. Blockchain-security tooling
3. Research chain and recovery/security experiments
4. External reviewed-BFT integration
5. Browser wallet/public-testnet tooling
6. Native state sync and operational-evidence tooling
7. Review freeze, reproducible release engineering and remediation
8. Sustained independent-host public testnet and independent security review
9. Upgrade/validator-lifecycle hardening
10. Mainnet consideration only after technical, operational, economic and legal gates are satisfied

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
