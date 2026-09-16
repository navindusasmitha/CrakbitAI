# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent, founder-led technology project building accessible security tooling for developers, security researchers, students and open-source communities.

The project is currently in **early development / Security MVP alpha + blockchain public-testnet research**. The priority remains useful defensive-security technology and careful public testing before any production blockchain or production-value CRKBIT launch.

## Mission

Make practical cybersecurity, secure coding and blockchain-security tooling more accessible, understandable and easier to integrate into modern software-development workflows.

## What We Are Building

### Crakbit AI Security Assistant

Security-focused AI guidance for secure coding, vulnerability understanding, remediation and defensive-security workflows.

### Crakbit Scanner — Early Alpha

A deterministic static-analysis prototype exists in [`scanner/`](scanner/). Current alpha checks include credential indicators with safe redaction and selected Python/JavaScript/TypeScript insecure coding patterns.

The scanner performs static checks only and does not execute target code. It is an early architecture prototype, not a production-grade security scanner.

### Blockchain Security

Planned defensive tooling includes smart-contract analysis, contract-risk assessment, public blockchain-data analysis, developer guidance and human-readable security reports.

### Crakbit Chain — v0.17 Public-Testnet/Mainnet-Candidate Infrastructure Alpha

A runnable experimental blockchain/application stack exists in [`blockchain/`](blockchain/).

The current external-consensus test path is:

```text
Browser wallet / CLI
        │
        ▼
Public gateway / controlled testnet edge
        │
        ▼
CometBFT v0.40.0
        │ ABCI
        ▼
Crakbit Go bridge v0.17
        │
        ▼
crakbit-execution/2
        │
        ├── crash-safe FinalizeBlock → Commit
        ├── native ABCI snapshot state-sync lifecycle
        └── deterministic application state
                │
                ├── dedicated explorer index
                └── signed testnet evidence tooling
```

Implemented research/public-testnet components now include:

- Ed25519 wallets and `crk1...` addresses,
- signed CRKBIT test transactions,
- browser wallet with encrypted local vault and client-side signing,
- public wallet/explorer gateway,
- CometBFT `v0.40.0` ABCI bridge,
- crash-safe staged FinalizeBlock → atomic Commit application flow,
- deterministic application hashes,
- signed application-genesis/release tooling,
- native ABCI `ListSnapshots`, `OfferSnapshot`, `LoadSnapshotChunk`, `ApplySnapshotChunk` state-sync code,
- chunk/transport/application-hash verification for state restore,
- dedicated external explorer index,
- one-command local multi-validator CometBFT lab generator,
- durable public write/faucet/mining limits,
- optional browser SHA-256 Mining Lab reward system,
- wallet threat model and CSP/security-header profile,
- multi-host validator health/divergence checks,
- controlled dry-run-by-default fault campaign tooling,
- signed exact-source public-testnet evidence bundles,
- single-edge TLS/rate-limit deployment profile,
- validator remote-signer configuration helper/guidance,
- Python + Go automated blockchain CI.

The older Python prevote/precommit chain remains in the repository for research/backwards-compatible local experiments. It is not the intended production BFT path.

**Important:** v0.17 is not a production mainnet. Sustained independent-host operation, live recovery evidence, protected validator-key custody, real fault/load campaigns and independent consensus/application/network/wallet security review are still required. It must not be used to custody real value.

See [`blockchain/V0.17.md`](blockchain/V0.17.md), [`blockchain/README.md`](blockchain/README.md) and [`blockchain/docs/MAINNET_GATES.md`](blockchain/docs/MAINNET_GATES.md).

## Browser Wallet / Web UI

The test wallet interface provides local Ed25519 wallet generation, PBKDF2-SHA256 + AES-GCM encrypted vaults, encrypted backup/import, local transaction signing, balances/activity, transfers, explorer views, validators, faucet requests and the opt-in Mining Lab.

The gateway is not intended to receive the wallet private key. The security profile defaults to same-origin access and restrictive CSP/browser security headers.

The wallet is not an audited hardware-wallet replacement. See [`blockchain/docs/WALLET_THREAT_MODEL.md`](blockchain/docs/WALLET_THREAT_MODEL.md).

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

## Quick Start — Crakbit Chain Research Node

Requires Python 3.11+ and Docker.

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
python scripts/bootstrap_devnet.py
docker compose up --build
```

Open the local wallet UI at `http://127.0.0.1:9101/ui/`. This normal node path is the older research-consensus path.

## v0.17 External-BFT / State-Sync Tooling

Build the Go bridge:

```bash
cd blockchain/cometbft-app
go mod download
go test -mod=mod ./...
go build -o crakbit-cometbft-bridge .
```

Run the v0.17 external execution service with a secret kept local:

```bash
python ../scripts/run_execution_service_v17.py \
  --genesis ../runtime/genesis.json \
  --data ../runtime/comet-app \
  --token REPLACE_WITH_LONG_RANDOM_SECRET
```

Materialize a CometBFT state-sync snapshot after a committed height:

```bash
cd ..
crakchain comet-snapshot-materialize \
  --genesis runtime/genesis.json \
  --data runtime/comet-app
```

The state-sync snapshot is accepted on restore only when its application hash matches the trusted hash supplied by CometBFT and the complete reconstructed state verifies.

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
| Crakbit Chain package | **v0.17.0a1 alpha** |
| Browser wallet/public gateway | **Alpha implemented** |
| CometBFT ABCI bridge | **v0.17 integration implemented** |
| Crash-safe external execution | **Prototype implemented** |
| Native ABCI application state sync | **v0.17 code implemented; live independent-host evidence pending** |
| Dedicated external explorer index | **Prototype implemented** |
| Local multi-validator CometBFT lab generator | **Implemented** |
| Signed public-testnet evidence tooling | **v0.17 implemented** |
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
6. Native state-sync and operational-evidence tooling
7. Sustained independent-host public testnet and published fault/recovery evidence
8. Independent security/consensus/wallet review
9. Mainnet consideration only after technical, operational, economic and legal gates are satisfied

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

Please read [`SECURITY.md`](SECURITY.md) for project vulnerability reporting and [`blockchain/SECURITY.md`](blockchain/SECURITY.md) for blockchain-specific limitations. Mainnet release gates are documented in [`blockchain/docs/MAINNET_GATES.md`](blockchain/docs/MAINNET_GATES.md).

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) before contributing.

## Official Links

- Website: https://crakbit.space
- Repository: https://github.com/navindusasmitha/CrakbitAI
- Funding / Giveth: Crakbit AI is publicly listed on Giveth

## Transparency

Project documentation aims to distinguish implemented code, test evidence, public-testnet operation and production readiness. A feature being present in source code is not the same as that feature being independently audited or ready for real-value use.

See [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for the current development snapshot.

## License

Unless otherwise noted, source code in this repository is released under the Apache License 2.0. See [`LICENSE`](LICENSE).

---

**Crakbit AI** — Secure Code. Secure Chains. Build the Future.
