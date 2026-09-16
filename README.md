# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent, founder-led technology project building accessible security tooling for developers, security researchers, students and open-source communities.

The project is currently in **early development / Security MVP + blockchain devnet research** stage. The priority remains useful defensive-security technology and careful public testing before any production blockchain or production-value CRKBIT launch.

## Mission

Make practical cybersecurity, secure coding and blockchain-security tooling more accessible, understandable and easier to integrate into modern software-development workflows.

## What We Are Building

### Crakbit AI Security Assistant

Security-focused AI guidance for secure coding, vulnerability understanding, remediation and defensive-security workflows.

### Crakbit Scanner — Early Alpha

A deterministic static-analysis prototype exists in [`scanner/`](scanner/). Current alpha checks include hard-coded credential indicators with redaction, Python `subprocess(..., shell=True)`, Python/JavaScript `eval()` and potentially unsafe DOM `innerHTML` assignment.

The scanner performs static checks only and does not execute target code. It is an early architecture prototype, not a production-grade security scanner.

### Blockchain Security

Planned defensive tooling includes smart-contract analysis, contract-risk assessment, public blockchain-data analysis, developer guidance and human-readable security reports.

### Crakbit Chain — v0.14 Research / External-BFT Integration Alpha

A runnable experimental blockchain/application-state prototype exists in [`blockchain/`](blockchain/).

The original Python devnet now includes signed transactions, a research prevote/precommit pipeline, quorum-certified view changes, authenticated validator communication, mTLS/certificate pinning, snapshots, resumable recovery, verified history archives, backups, metrics, fault/soak tooling and bounded RPC/mempool controls.

**v0.14 adds a separate external-consensus integration path:**

```text
CometBFT v0.40.0
      │ ABCI socket
      ▼
Crakbit Go ABCI bridge
      │ authenticated loopback HTTP
      ▼
crakbit-execution/2
      │ staged FinalizeBlock → atomic Commit
      ▼
Dedicated external application SQLite state
```

v0.14 also adds:

- deterministic application hashes for external consensus,
- persisted non-mutating FinalizeBlock staging,
- atomic crash-safe Commit semantics,
- pending-finalize recovery across restart,
- identical committed FinalizeBlock replay handling,
- a Go ABCI bridge pinned to CometBFT `v0.40.0`,
- signed strict >2/3 Crakbit application-genesis ceremony tooling,
- Python + Go blockchain CI,
- local integration/operator runbooks.

The proposed devnet parameters use 8 decimals and a 21,000,000 CRKBIT maximum genesis supply. These remain development parameters subject to technical, security, economic and legal review.

**Important:** v0.14 is still a research/testnet integration. It is not a production mainnet, has not completed independent consensus/network/security review, and must not be used to custody real value.

Test CRKBIT units are not a production token, investment product or public presale.

See [`blockchain/README.md`](blockchain/README.md), [`blockchain/V0.14.md`](blockchain/V0.14.md), [`blockchain/docs/EXTERNAL_CONSENSUS_V2.md`](blockchain/docs/EXTERNAL_CONSENSUS_V2.md), [`blockchain/SPEC.md`](blockchain/SPEC.md) and [`blockchain/SECURITY.md`](blockchain/SECURITY.md).

## Developer Platform Direction

Planned developer-facing components include:

- Web application
- `crak` security CLI
- Security API / SDK
- Git and CI/CD integrations
- Future IDE integrations
- Blockchain security/reporting tools
- Crakbit Chain node/application tooling

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

## Run the Research Crakbit Chain Devnet

Requires Python 3.11+ and Docker.

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
python scripts/bootstrap_devnet.py
docker compose up --build
```

Default local research RPC endpoints:

- `http://127.0.0.1:9101`
- `http://127.0.0.1:9102`
- `http://127.0.0.1:9103`
- `http://127.0.0.1:9104`

The normal `crakchain node` command remains the research Python-consensus path for backwards-compatible local development.

## Try the v0.14 External-Consensus Application Path

Start the dedicated application service with a **fresh data directory**:

```bash
cd blockchain
python scripts/run_execution_service_v14.py \
  --genesis runtime/genesis.json \
  --data runtime/comet-app \
  --token REPLACE_WITH_LONG_RANDOM_SECRET \
  --host 127.0.0.1 \
  --port 26659
```

Build/test the Go ABCI bridge:

```bash
cd cometbft-app
go mod download
go test -mod=mod ./...
go build -o crakbit-cometbft-bridge .
```

Run the bridge:

```bash
export CRAKBIT_EXECUTION_URL=http://127.0.0.1:26659
export CRAKBIT_EXECUTION_TOKEN=REPLACE_WITH_LONG_RANDOM_SECRET
export CRAKBIT_ABCI_LISTEN=tcp://127.0.0.1:26658
./crakbit-cometbft-bridge
```

The external application DB and ABCI bridge should be loopback/private by default. CometBFT node/validator keys are separate from Crakbit wallet, release, faucet, TLS and research-validator keys.

See [`blockchain/deploy/cometbft-poc/README.md`](blockchain/deploy/cometbft-poc/README.md).

## Signed Application-Genesis Ceremony

```bash
crakchain ceremony-create \
  --genesis runtime/genesis.json \
  --output runtime/genesis-ceremony.json
```

Each configured validator signs locally:

```bash
crakchain ceremony-sign \
  --ceremony runtime/genesis-ceremony.json \
  --key runtime/node1/validator.json
```

Verify strict >2/3 validator attestations:

```bash
crakchain ceremony-verify \
  --ceremony runtime/genesis-ceremony.json \
  --genesis runtime/genesis.json
```

Never share validator private keys to construct a ceremony file. Exchange only the signed public ceremony artifact.

## Architecture Direction

```text
Developer / Researcher
        |
        v
   Crakbit Web / CLI
        |
        +----------------------------+
        |                            |
        v                            v
 Security Engine              Blockchain Research
 |-- Static analysis          |-- Research Python devnet
 |-- Secret detection         |-- Snapshot/archive recovery
 |-- Dependency checks        |-- Validator transport hardening
 |-- Solidity analysis        |-- CometBFT ABCI bridge PoC
 `-- AI remediation           `-- crakbit-execution/2 app state
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
| Crakbit Chain research devnet | **v0.14 alpha code available** |
| CometBFT ABCI bridge | **v0.14 integration PoC implemented** |
| Crash-safe external execution commit | **v0.14 prototype implemented** |
| Signed application-genesis ceremony | **v0.14 prototype implemented** |
| Multi-host public external-BFT testnet | Not launched |
| Independent consensus/security audit | Not completed |
| Production CRKBIT | **Not launched** |

The status of planned features is intentionally shown clearly. Roadmap work is not presented as completed production infrastructure.

## Roadmap

The high-level sequence is:

1. Foundation and public project infrastructure
2. Security MVP
3. Security CLI/API and developer integrations
4. Blockchain-security tooling
5. Crakbit Chain research/devnet and recovery/security hardening
6. External reviewed-BFT integration PoC
7. Repeatable multi-process/multi-host external-BFT test network
8. Long-running public testnet, fault testing and independent review
9. Mainnet consideration only after technical, economic, operational and legal validation

See [`ROADMAP.md`](ROADMAP.md).

## Open Source

Crakbit AI intends to release useful developer-security and blockchain research components openly where practical, including selected scanners, rules, SDKs, documentation and testnet tooling.

## Public-Benefit Funding

Crakbit AI is raising funds to support development of the Security MVP, security research, infrastructure, developer tools, documentation, testing and carefully staged blockchain/testnet research.

The current fundraising target is **USD 150,000** with milestone-based allocation.

See [`docs/FUNDING.md`](docs/FUNDING.md) for the proposed allocation and transparency model.

**The current fundraising campaign is not a CRKBIT token sale and does not promise investment returns.**

## CRKBIT Notice

**Production CRKBIT has not been launched. There is currently no official CRKBIT presale or production token contract.**

The repository contains test-only CRKBIT accounting used in development/research networks. These units have no represented production value and should not be marketed or sold as mainnet CRKBIT.

Any future production utility asset remains subject to public testing, security review, economic design and applicable legal/regulatory consideration.

## Security and Responsible Use

Crakbit AI is being developed primarily for defensive security, secure software development, code review, research and educational use.

Please read [`SECURITY.md`](SECURITY.md) before reporting a vulnerability in this repository or project infrastructure. Blockchain-specific limitations are documented in [`blockchain/SECURITY.md`](blockchain/SECURITY.md).

## Contributing

Contributions, research, documentation improvements and security-focused ideas are welcome as the project opens more components.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) before participating.

## Official Links

- Website: https://crakbit.space
- Repository: https://github.com/navindusasmitha/CrakbitAI
- Funding / Giveth: Crakbit AI is publicly listed on Giveth

Additional official community links will be added as they are launched.

## Transparency

We intend to publish development milestones, architecture decisions, releases, funding-allocation updates where practical, open-source components, security/testing progress and devnet/testnet limitations.

See [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for the current development snapshot.

## License

Unless otherwise noted, source code in this repository is released under the Apache License 2.0. See [`LICENSE`](LICENSE).

---

**Crakbit AI** — Secure Code. Secure Chains. Build the Future.
