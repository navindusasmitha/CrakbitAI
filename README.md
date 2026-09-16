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

### Crakbit Chain — v0.16 Public-Testnet/Mainnet-Candidate Infrastructure Alpha

A runnable experimental blockchain/application stack exists in [`blockchain/`](blockchain/).

The current external-consensus test path is:

```text
Browser wallet / CLI
        │
        ▼
Public gateway
        │
        ▼
CometBFT v0.40.0
        │ ABCI
        ▼
Crakbit Go bridge
        │
        ▼
crakbit-execution/2
        │
        ▼
Dedicated application state
```

Implemented research/public-testnet components include:

- Ed25519 wallets and `crk1...` addresses,
- signed CRKBIT test transactions,
- browser wallet with encrypted local vault,
- client-side transaction signing,
- public wallet/explorer gateway,
- CometBFT `v0.40.0` ABCI bridge PoC,
- crash-safe staged FinalizeBlock → atomic Commit application flow,
- deterministic application hashes,
- signed application-genesis ceremony tooling,
- deterministic external-application checkpoint export/verify/restore,
- checkpoint-base-aware recovery without fabricated history,
- dedicated external explorer index,
- one-command local multi-validator CometBFT lab generator,
- restart-persistent public write-rate limiting,
- persistent test faucet controls,
- optional browser SHA-256 Mining Lab reward system,
- wallet threat model and CSP/security-header profile,
- multi-host validator health/divergence checks,
- application crash/replay/checkpoint evidence matrix,
- validator remote-signer/HSM-equivalent guidance,
- Python + Go automated blockchain CI.

The older Python prevote/precommit chain remains in the repository for research/backwards-compatible local experiments. It is not the intended production BFT path.

**Important:** v0.16 is not a production mainnet. It has not completed sustained independent-host operation, native CometBFT state-sync integration, protected production validator-key custody or independent consensus/application/network/wallet security review. It must not be used to custody real value.

See [`blockchain/V0.16.md`](blockchain/V0.16.md), [`blockchain/README.md`](blockchain/README.md) and [`blockchain/docs/MAINNET_GATES.md`](blockchain/docs/MAINNET_GATES.md).

## Browser Wallet / Web UI

The test wallet interface provides:

- local Ed25519 wallet generation,
- PBKDF2-SHA256 + AES-GCM encrypted browser vault,
- encrypted wallet backup/import,
- local transaction signing,
- balance/nonce/activity,
- CRKBIT test transfer flow,
- address/transaction explorer,
- validator view,
- faucet requests,
- opt-in Mining Lab.

The gateway is not intended to receive the wallet private key. The v0.16 security profile defaults to same-origin access and adds restrictive CSP/browser security headers.

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

JSON output:

```bash
crak scan ../your-project --json
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

Open the local wallet UI:

```text
http://127.0.0.1:9101/ui/
```

This normal node path is the older research consensus path.

## v0.16 External-BFT Tooling

Build the Go bridge:

```bash
cd blockchain/cometbft-app
go mod download
go test -mod=mod ./...
go build -o crakbit-cometbft-bridge .
```

Generate a disposable 4-validator CometBFT lab with an operator-supplied CometBFT `v0.40.0` binary:

```bash
cd ..
python scripts/generate_cometbft_lab.py \
  --cometbft /path/to/cometbft \
  --chain-id crakbit-v16-local \
  --nodes 4 \
  --output runtime/cometbft-lab
```

See [`blockchain/deploy/cometbft-lab/README.md`](blockchain/deploy/cometbft-lab/README.md).

## External Application Checkpoints

v0.16 can export and verify deterministic application state:

```bash
crakchain external-snapshot-export \
  --genesis runtime/genesis.json \
  --data runtime/comet-app \
  --output runtime/external-checkpoint.json
```

A restore should be bound to a separately trusted CometBFT height/application hash. Native CometBFT state-sync lifecycle integration is still a future gate.

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
| Crakbit Chain package | **v0.16.0a1 alpha** |
| Browser wallet/public gateway | **Alpha implemented** |
| CometBFT ABCI bridge | **Integration PoC implemented** |
| Crash-safe external execution | **Prototype implemented** |
| External application checkpoint | **v0.16 adapter implemented** |
| Dedicated external explorer index | **v0.16 prototype implemented** |
| Local multi-validator CometBFT lab generator | **v0.16 implemented** |
| Independent-host public testnet evidence | Not completed |
| Independent consensus/security audit | Not completed |
| Production CRKBIT | **Not launched** |

## Roadmap

The high-level path is:

1. Security MVP and developer tooling
2. Blockchain-security tooling
3. Research chain and recovery/security experiments
4. External reviewed-BFT integration PoC
5. Browser wallet/public-testnet tooling
6. Repeatable multi-validator/state-recovery/indexing infrastructure
7. Sustained independent-host public testnet and published fault evidence
8. Independent security/consensus/wallet review
9. Mainnet consideration only after technical, operational, economic and legal gates are satisfied

See [`ROADMAP.md`](ROADMAP.md).

## Public-Benefit Funding

Crakbit AI is raising funds to support the Security MVP, security research, infrastructure, developer tools, documentation, testing and carefully staged blockchain/testnet research.

The current fundraising target is **USD 150,000** with milestone-based allocation.

See [`docs/FUNDING.md`](docs/FUNDING.md).

**The current fundraising campaign is not a CRKBIT token sale and does not promise investment returns.**

## CRKBIT Notice

**Production CRKBIT has not launched. There is currently no official CRKBIT presale or production token contract.**

The repository contains test-only CRKBIT accounting used in development/research/public-testnet work. These units have no represented production value and should not be marketed or sold as mainnet CRKBIT.

The proposed development parameters use 8 decimals and a 21,000,000 maximum genesis supply. Those are not final production economics and remain subject to technical, security, economic and applicable legal review.

## Security and Responsible Use

Crakbit AI is being developed primarily for defensive security, secure software development, code review, research and educational use.

Please read [`SECURITY.md`](SECURITY.md) for project vulnerability reporting and [`blockchain/SECURITY.md`](blockchain/SECURITY.md) for blockchain-specific limitations.

Mainnet release gates are documented in [`blockchain/docs/MAINNET_GATES.md`](blockchain/docs/MAINNET_GATES.md).

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
