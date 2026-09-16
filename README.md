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
Planned security tooling includes smart-contract analysis, contract-risk assessment, blockchain transaction analysis, security-focused developer guidance and human-readable reports.

### Crakbit Chain — Devnet v0.7 Alpha
A runnable experimental blockchain prototype exists in [`blockchain/`](blockchain/).

The current research network includes:

- Native test-only `CRKBIT` unit
- Ed25519 wallets and signed transfers
- `crk1...` account addresses
- Nonces, replay protection and transaction fees
- Signed block proposals
- Strict >2/3 **prevote** quorum
- Strict >2/3 **precommit** quorum
- Finalization only after both phase certificates validate
- Round-specific proposer rotation
- >2/3 signed view-change certificates for non-zero rounds
- Persistent phase-vote anti-double-vote state
- Persistent per-height conservative consensus lock
- Consensus event journal and equivocation evidence
- Ed25519-authenticated validator-to-validator requests
- Signed validator challenge/response identity handshake
- **Persistent SQLite replay-nonce protection across process restarts**
- Optional HTTPS peer-URL enforcement mode
- Validator-signed state snapshots
- **>2/3 quorum-certified snapshot recovery**
- **Fresh-database snapshot import / node bootstrap**
- Recovery metadata endpoint
- Prometheus-style development metrics
- SQLite-backed chain/consensus state
- Finalized-block broadcast and catch-up sync
- REST/RPC API and CLI tooling
- 4-validator Docker Compose devnet with default 3-of-4 quorum
- Browser development explorer
- Automated blockchain/consensus/peer-auth/recovery tests and CI

The proposed devnet parameters use 8 decimals and a 21,000,000 CRKBIT maximum genesis supply. These parameters remain subject to technical, security, economic and legal review before any production network.

**Important:** v0.7 is still not a production BFT/mainnet protocol. The current cross-round lock lacks a mature proof-based unlock rule, default local networking is not encrypted, mTLS/certificate lifecycle management is not implemented, snapshot bootstrap does not recreate pre-snapshot history, and the network has not been independently audited.

Test CRKBIT units created by this devnet are not a production token, investment product or public presale.

See [`blockchain/README.md`](blockchain/README.md), [`blockchain/V0.7.md`](blockchain/V0.7.md), [`blockchain/SPEC.md`](blockchain/SPEC.md) and [`blockchain/SECURITY.md`](blockchain/SECURITY.md).

## Developer Platform

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

Consensus/recovery telemetry:

```bash
curl http://127.0.0.1:9101/status
curl http://127.0.0.1:9101/peers
curl http://127.0.0.1:9101/validators
curl http://127.0.0.1:9101/evidence
curl http://127.0.0.1:9101/consensus/events
curl http://127.0.0.1:9101/metrics/prometheus
curl http://127.0.0.1:9101/recovery/status
```

Quorum snapshot recovery:

```bash
crakchain snapshot-fetch --genesis runtime/genesis.json --output runtime/snapshot-cert.json
crakchain snapshot-verify --snapshot runtime/snapshot-cert.json --genesis runtime/genesis.json
crakchain snapshot-import --snapshot runtime/snapshot-cert.json --genesis runtime/genesis.json --data runtime/recovered-node
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
   |-- Dependency checks  |-- Certified view changes
   |-- Solidity analysis  |-- Prevote / precommit quorum
   `-- AI remediation     |-- Authenticated peer requests
                          |-- Quorum snapshot recovery
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
| Crakbit Chain local devnet | **v0.7 alpha available** |
| Quorum-certified view changes | **Devnet prototype implemented** |
| Prevote/precommit finality | **Devnet prototype implemented** |
| Persistent phase-vote state | **Prototype implemented** |
| Conservative per-height consensus lock | **Research rule implemented** |
| Validator request authentication | **Prototype implemented** |
| Durable peer replay cache | **v0.7 prototype implemented** |
| Validator identity handshake | **Prototype implemented** |
| Signed state snapshots | **Implemented for devnet** |
| Quorum snapshot certificate | **v0.7 prototype implemented** |
| Snapshot bootstrap/import | **v0.7 prototype implemented** |
| Prometheus-style metrics | **Prototype implemented** |
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
8. Proposer failover and persistent consensus state
9. Quorum-certified view changes and equivocation evidence
10. Multi-phase prevote/precommit finality + durable lock
11. Authenticated validator requests + signed snapshot foundation
12. Durable replay protection + quorum-certified snapshot recovery
13. Mature BFT unlock + mutually authenticated encrypted transport
14. Public testnet preparation
15. Long-lived public testnet and independent security review
16. Mainnet consideration only after technical, economic and legal validation

See [`ROADMAP.md`](ROADMAP.md) for milestones and target phases.

## Open Source

Crakbit AI intends to release useful developer-security and blockchain research components openly where practical, including selected scanners, rules, SDKs, documentation and testnet tooling.

## Public-Benefit Funding

Crakbit AI is raising funds to support development of the Security MVP, security research, infrastructure, developer tools, documentation, testing and carefully staged blockchain/testnet research.

The current fundraising target is **USD 150,000** with milestone-based allocation.

See [`docs/FUNDING.md`](docs/FUNDING.md) for the proposed allocation and transparency model.

**The current fundraising campaign is not a CRKBIT token sale and does not promise investment returns.**

## CRKBIT Notice

**Production CRKBIT has not been launched. There is currently no official CRKBIT presale or production token contract.**

The repository contains test-only CRKBIT units used inside the local development network. They have no represented production value and should not be marketed or sold as mainnet CRKBIT.

Any future production utility asset is subject to public testing, security review, economic design and applicable legal/regulatory consideration.

## Security and Responsible Use

Crakbit AI is being developed primarily for defensive security, secure software development, code review, research and educational use.

Please read [`SECURITY.md`](SECURITY.md) and [`blockchain/SECURITY.md`](blockchain/SECURITY.md) before reporting or evaluating security issues.

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) before participating.

## Official Links

- Website: https://crakbit.space
- Repository: https://github.com/navindusasmitha/CrakbitAI
- Funding / Giveth: Crakbit AI is publicly listed on Giveth

## Transparency

We intend to publish development milestones, major architecture decisions, releases, funding-allocation updates where practical, open-source components, security/testing progress and devnet/testnet limitations.

See [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for the current development snapshot.

## License

Unless otherwise noted, source code in this repository is released under the Apache License 2.0. See [`LICENSE`](LICENSE).

---

**Crakbit AI** — Secure Code. Secure Chains. Build the Future.
