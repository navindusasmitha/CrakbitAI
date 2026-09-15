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
A first deterministic static-analysis prototype exists in [`scanner/`](scanner/).

Current alpha checks include:

- Possible hard-coded credentials with evidence redaction
- Python `subprocess` usage with `shell=True`
- Python `eval()`
- JavaScript/TypeScript `eval()`
- Potentially unsafe `innerHTML` assignment

The scanner performs static checks only and does not execute target code. It is an architecture proof and **not yet a production-grade security scanner**.

Initial language/file targets include Python, JavaScript/TypeScript, Go, Rust and Solidity.

### Blockchain Security
Planned tooling includes:

- Smart-contract analysis
- Contract-risk assessment
- Blockchain transaction analysis
- Security-focused developer guidance
- Human-readable security reports

### Crakbit Chain — Devnet Alpha
A runnable experimental blockchain prototype now exists in [`blockchain/`](blockchain/).

The current development network includes:

- Native devnet `CRKBIT` unit
- Ed25519 wallets and signed transfers
- `crk1...` account addresses
- Nonces and replay protection
- Transaction fees
- Signed blocks
- Transaction Merkle roots and deterministic state roots
- SQLite-backed chain state
- Round-robin development Proof of Authority validators
- Basic peer block broadcast and catch-up synchronization
- REST/RPC API
- CLI wallet/transfer commands
- 3-validator Docker Compose devnet
- Browser-based development explorer
- Automated ledger/signature tests and CI

The proposed devnet parameters use 8 decimals and a 21,000,000 CRKBIT maximum genesis supply. These parameters remain subject to security, economic and legal review before any production network.

**Important:** the current chain is an unaudited research/devnet implementation. Its simple PoA layer does not provide production-grade Byzantine-fault-tolerant finality. The test CRKBIT units created by this devnet are not a production token, investment product or public presale.

See [`blockchain/README.md`](blockchain/README.md) for setup and limitations.

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

See [`scanner/README.md`](scanner/README.md) for limitations and details.

## Run the Crakbit Chain Devnet

Requires Python 3.11+ and Docker.

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
python scripts/bootstrap_devnet.py
docker compose up --build
```

The default local RPC endpoints are `http://127.0.0.1:9101`, `:9102` and `:9103`.

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
   |-- Solidity analysis  `-- Validator/RPC layer
   `-- AI remediation
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the evolving platform design and [`blockchain/README.md`](blockchain/README.md) for the network prototype.

## Current Project Status

| Component | Status |
| --- | --- |
| Project architecture | In progress |
| Public website | Active |
| AI Security Assistant | In development |
| Secure Code Scanner | **Early alpha available** |
| Security CLI | Early alpha command included with scanner package |
| Developer API | Planned |
| Smart Contract Scanner | Planned |
| Crakbit Chain local devnet | **Early alpha available** |
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
6. Crakbit Chain research and local devnet prototyping
7. BFT consensus/network hardening and public testnet preparation
8. Public testnet and independent security review
9. Mainnet consideration only after technical, economic and legal validation

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

The repository now contains test-only CRKBIT units used inside the local Crakbit Chain development network. They have no represented production value and should not be marketed or sold as mainnet CRKBIT.

Any future production utility asset is subject to public testing, security review, economic design and applicable legal/regulatory consideration.

## Security and Responsible Use

Crakbit AI is being developed primarily for defensive security, secure software development, code review, research and educational use.

Please read [`SECURITY.md`](SECURITY.md) before reporting a vulnerability in this repository or project infrastructure. The blockchain devnet has additional limitations documented in [`blockchain/README.md`](blockchain/README.md).

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

Documentation and project materials may receive additional licensing notes as the repository grows.

---

**Crakbit AI** — Secure Code. Secure Chains. Build the Future.
