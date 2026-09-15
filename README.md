# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent, founder-led technology project building accessible security tooling for developers, security researchers, students and open-source communities.

The project is currently in **early development / Security MVP + blockchain devnet research** stage. Our priority remains useful defensive security technology and careful public testing before any production blockchain or production-value CRKBIT launch.

## Mission

Make practical cybersecurity, secure coding and blockchain-security tooling more accessible, understandable and easier to integrate into modern software-development workflows.

We believe AI should not only help developers write code faster — it should also help them understand risk and build safer systems.

## What We Are Building

### Crakbit AI Security Assistant
Security-focused AI guidance for secure coding, vulnerability understanding, remediation and defensive security workflows.

### Crakbit Scanner — Early Alpha
A deterministic static-analysis prototype exists in [`scanner/`](scanner/).

Current alpha checks include:

- Possible hard-coded credentials with evidence redaction
- Python `subprocess` usage with `shell=True`
- Python `eval()`
- JavaScript/TypeScript `eval()`
- Potentially unsafe `innerHTML` assignment

The scanner performs static checks only and does not execute target code. It is an early architecture proof and **not yet a production-grade security scanner**.

### Blockchain Security
Planned security tooling includes:

- Smart-contract analysis
- Contract-risk assessment
- Blockchain transaction analysis
- Security-focused developer guidance
- Human-readable security reports

### Crakbit Chain — Devnet v0.3 Alpha
A runnable experimental blockchain prototype exists in [`blockchain/`](blockchain/).

The current development network includes:

- Native devnet `CRKBIT` unit
- Ed25519 wallets and signed transfers
- `crk1...` account addresses
- Nonces and replay protection
- Transaction fees
- Signed block proposals and validator commit votes
- Strict greater-than-two-thirds commit quorum before finalization
- Round-based proposer rotation and timeout-based proposer failover
- Persistent same-height/same-round anti-double-vote records across restarts
- Transaction Merkle roots and deterministic state roots
- SQLite-backed chain state
- Peer block broadcast and finalized-block catch-up synchronization
- Validator health/height/round telemetry
- REST/RPC API
- CLI wallet/transfer commands
- 4-validator Docker Compose devnet with a default 3-of-4 quorum
- Browser-based development explorer
- Automated ledger/signature/quorum/failover tests and CI

The proposed devnet parameters use 8 decimals and a 21,000,000 CRKBIT maximum genesis supply. These parameters remain subject to technical, security, economic and legal review before any production network.

**Important:** v0.3 is still not a production BFT protocol. Same-round vote persistence is implemented, but cross-round locking/precommit safety, quorum-certified view changes, authenticated validator networking and independent audit are still missing.

Test CRKBIT units created by this devnet are not a production token, investment product or public presale.

See [`blockchain/README.md`](blockchain/README.md), [`blockchain/SPEC.md`](blockchain/SPEC.md) and [`blockchain/SECURITY.md`](blockchain/SECURITY.md).

### Developer Platform
Planned developer-facing components include:

- Web application
- `crak` security CLI
- Security API / SDK
- Git integrations
- CI/CD integrations
- Future IDE integrations
- Crakbit Chain node/RPC tooling

## Try the Security Scanner Alpha

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

## Run the Crakbit Chain Devnet

Requires Python 3.11+ and Docker.

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
python scripts/bootstrap_devnet.py
docker compose up --build
```

Default local RPC endpoints:

- `http://127.0.0.1:9101`
- `http://127.0.0.1:9102`
- `http://127.0.0.1:9103`
- `http://127.0.0.1:9104`

Node status:

```bash
curl http://127.0.0.1:9101/status
```

Peer/validator monitoring:

```bash
curl http://127.0.0.1:9101/peers
curl http://127.0.0.1:9101/validators
```

## Architecture Direction

```text
Developer / Researcher
        |
        v
   Crakbit Web / CLI
        |
        v
   Crakbit API Layer
        |
        +----------------------+
        |                      |
        v                      v
   Security Engine        Crakbit Chain Devnet
   |-- Static analysis    |-- Wallet/signatures
   |-- Secret detection   |-- Transactions/fees
   |-- Dependency checks  |-- Blocks/state
   |-- Solidity analysis  |-- Commit votes/quorum
   `-- AI remediation     |-- Round failover
                          `-- Validator/RPC telemetry
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the evolving platform design.

## Current Project Status

| Component | Status |
| --- | --- |
| Project architecture | In progress |
| Public website | Active |
| Giveth project | **Publicly listed** |
| AI Security Assistant | In development |
| Secure Code Scanner | **Early alpha available** |
| Security CLI | Early alpha |
| Developer API | Planned |
| Smart Contract Scanner | Planned |
| Crakbit Chain local devnet | **v0.3 alpha available** |
| Signed quorum finality | **Devnet prototype implemented** |
| Proposer failover | **Devnet prototype implemented** |
| Persistent same-round vote guard | **Implemented** |
| Validator telemetry | **Prototype implemented** |
| Chain CLI / wallet key tooling | **Early alpha available** |
| Devnet explorer | **Prototype available** |
| Public blockchain testnet | Not launched |
| Production CRKBIT | **Not launched** |

The status of planned features is intentionally shown clearly. We do not present roadmap items as completed production systems.

## Roadmap

Our development sequence includes:

1. Foundation and public project infrastructure
2. Security MVP
3. Security CLI and API alpha
4. Blockchain-security tooling
5. Developer integrations
6. Crakbit Chain local devnet
7. Signed quorum finality
8. Round-based proposer failover and persistent same-round vote safety
9. Cross-round BFT safety + authenticated validator networking
10. Public testnet preparation
11. Long-lived public testnet and independent security review
12. Mainnet consideration only after technical, economic and legal validation

See [`ROADMAP.md`](ROADMAP.md) for milestones and target phases.

## Open Source

Crakbit AI intends to release useful developer-security and blockchain research components openly where practical, including selected scanners, rules, SDKs, documentation and testnet tooling.

Our goal is to make security knowledge and practical tooling useful to developers, students and researchers regardless of company size or budget.

## Public-Benefit Funding

Crakbit AI is raising funds to support development of the Security MVP, security research, infrastructure, developer tools, documentation, testing and carefully staged blockchain/testnet research.

The current fundraising target is **USD 150,000** with milestone-based allocation.

See [`docs/FUNDING.md`](docs/FUNDING.md) for the proposed allocation and transparency model.

**The current fundraising campaign is not a CRKBIT token sale and does not promise investment returns.**

## CRKBIT Notice

**Production CRKBIT has not been launched. There is currently no official CRKBIT presale or production token contract.**

The repository contains test-only CRKBIT units used inside the local Crakbit Chain development network. They have no represented production value and should not be marketed or sold as mainnet CRKBIT.

Any future production utility asset is subject to public testing, security review, economic design and applicable legal/regulatory consideration.

## Security and Responsible Use

Crakbit AI is being developed primarily for defensive security, secure software development, code review, research and educational use.

Please read [`SECURITY.md`](SECURITY.md) before reporting a vulnerability in this repository or project infrastructure. The blockchain devnet has additional limitations documented in [`blockchain/SECURITY.md`](blockchain/SECURITY.md).

## Contributing

Contributions, research, documentation improvements and security-focused ideas are welcome as the project opens more components.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) before participating.

## Official Links

- Website: https://crakbit.space
- Repository: https://github.com/navindusasmitha/CrakbitAI
- Funding / Giveth: Crakbit AI is publicly listed on Giveth

Additional official community links will be added here as they are launched.

## Transparency

We intend to publish:

- Development milestones
- Major architecture decisions
- Public releases
- Funding allocation updates where practical
- Open-source components
- Security and testing progress
- Devnet/testnet limitations and audit status

See [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for the current development snapshot.

## License

Unless otherwise noted, source code in this repository is released under the Apache License 2.0. See [`LICENSE`](LICENSE).

---

**Crakbit AI** — Secure Code. Secure Chains. Build the Future.
