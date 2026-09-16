# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent, founder-led technology project building accessible security tooling for developers, security researchers, students and open-source communities.

The project is currently in **early development / Security MVP + blockchain public-testnet research**. The priority remains useful defensive-security technology and careful public testing before any production blockchain or production-value CRKBIT launch.

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

### Crakbit Chain — v0.15 Public-Testnet Infrastructure Alpha

The experimental blockchain/application-state project lives in [`blockchain/`](blockchain/).

Earlier phases built signed transactions, research prevote/precommit consensus, validator authentication, mTLS/pinning, snapshots, resumable recovery, verified history archives, backups, metrics, fault tooling and bounded RPC controls.

v0.14 introduced the separate external-consensus integration path:

```text
CometBFT v0.40.0
      │ ABCI
      ▼
Crakbit Go bridge
      │ authenticated private HTTP
      ▼
crakbit-execution/2
      │ staged FinalizeBlock → atomic Commit
      ▼
Dedicated application state
```

**v0.15 adds the user-facing public-testnet layer:**

- responsive Web wallet/explorer/validator console,
- browser-generated Ed25519 wallets and `crk1...` addresses,
- PBKDF2-SHA256 + AES-GCM encrypted local wallet vault,
- client-side canonical transaction signing,
- encrypted wallet backup/import,
- public gateway supporting both research and CometBFT paths,
- CometBFT transaction broadcast support,
- persistent test-faucet cooldown/distribution records,
- optional browser proof-of-work Mining Lab with persistent challenges/reward limits,
- explicit mainnet production-release checklist.

The Mining Lab is **not consensus block mining**. It verifies opt-in SHA-256 work and sends a testnet reward as an ordinary transaction from a dedicated non-validator reward wallet. The external consensus integration remains CometBFT-based.

The development parameters use 8 decimals and a proposed 21,000,000 CRKBIT maximum genesis supply. These are not final production economics.

**Important:** v0.15 is still research/public-testnet infrastructure. It is not a production mainnet, has not completed independent consensus/network/wallet security review, and must not be used to custody real value.

Production CRKBIT is not launched. There is no official presale or production token contract.

See [`blockchain/README.md`](blockchain/README.md), [`blockchain/V0.15.md`](blockchain/V0.15.md) and [`blockchain/docs/MAINNET_GATES.md`](blockchain/docs/MAINNET_GATES.md).

## Developer Platform Direction

Planned developer-facing components include:

- Web application
- `crak` security CLI
- Security API / SDK
- Git and CI/CD integrations
- Future IDE integrations
- Blockchain security/reporting tools
- Crakbit Chain node/application/wallet tooling

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

## Run Crakbit Chain v0.15 Locally

Requires Python 3.11+ and Docker.

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
python scripts/bootstrap_devnet.py
docker compose up --build
```

Local research RPC nodes:

- `http://127.0.0.1:9101`
- `http://127.0.0.1:9102`
- `http://127.0.0.1:9103`
- `http://127.0.0.1:9104`

Open the bundled browser wallet/explorer:

```text
http://127.0.0.1:9101/ui/
```

## Full Wallet + Faucet + Mining-Lab Stack

Create **dedicated test wallets** for faucet and mining rewards. Do not use validator keys:

```bash
crakchain keygen --output runtime/faucet.json
crakchain keygen --output runtime/mining-reward.json
```

Fund those wallets only with test CRKBIT, then run the public gateway:

```bash
python scripts/run_public_gateway.py \
  --genesis runtime/genesis.json \
  --mode research \
  --research-rpc http://127.0.0.1:9101 \
  --faucet-url http://127.0.0.1:9400 \
  --mining-url http://127.0.0.1:9500 \
  --host 127.0.0.1 \
  --port 9600
```

Persistent test faucet:

```bash
python scripts/run_faucet.py \
  --genesis runtime/genesis.json \
  --key runtime/faucet.json \
  --gateway http://127.0.0.1:9600 \
  --state runtime/faucet-state.sqlite3 \
  --amount 10
```

Mining Lab reward service:

```bash
python scripts/run_pow_mining.py \
  --genesis runtime/genesis.json \
  --key runtime/mining-reward.json \
  --gateway http://127.0.0.1:9600 \
  --state runtime/mining-state.sqlite3 \
  --reward 1 \
  --difficulty-bits 18
```

Open the full UI:

```text
http://127.0.0.1:9600/ui/
```

## External CometBFT Path

The v0.14+ external application path remains available. Run the dedicated application service with a **fresh data directory** and private bearer token:

```bash
python scripts/run_execution_service_v14.py \
  --genesis runtime/genesis.json \
  --data runtime/comet-app \
  --token REPLACE_WITH_LONG_RANDOM_SECRET \
  --host 127.0.0.1 \
  --port 26659
```

Build/test the Go ABCI bridge:

```bash
cd blockchain/cometbft-app
go mod download
go test -mod=mod ./...
go build -o crakbit-cometbft-bridge .
```

The execution service and ABCI bridge should remain on loopback/private networks. The execution token must never be embedded in browser JavaScript.

## Key Separation

Keep these roles separate:

```text
CometBFT consensus/node keys
Crakbit research-validator keys
user wallet keys
TLS keys
release-signing key
faucet key
mining-reward key
```

Never publish, commit or send private keys/seed material.

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
| Crakbit Chain package | **v0.15 alpha** |
| Browser wallet / Web UI | **v0.15 alpha implemented** |
| Public wallet/explorer gateway | **v0.15 alpha implemented** |
| Persistent test faucet | **v0.15 implemented** |
| Proof-of-work Mining Lab | **Test-reward prototype; not consensus mining** |
| CometBFT ABCI bridge | **Integration PoC implemented** |
| Crash-safe external execution commit | **Prototype implemented** |
| Signed application-genesis ceremony | **Prototype implemented** |
| Independent multi-host public testnet | Not yet completed |
| Independent consensus/network/wallet audit | Not completed |
| Production CRKBIT | **Not launched** |

Roadmap work is intentionally not presented as completed production infrastructure.

## Roadmap

The high-level sequence is:

1. Foundation and public project infrastructure
2. Security MVP
3. Security CLI/API and developer integrations
4. Blockchain-security tooling
5. Crakbit Chain research/recovery/network hardening
6. CometBFT external-consensus integration PoC
7. Public-testnet wallet/gateway/explorer/faucet/mining-lab infrastructure
8. Independent multi-host testnet, state sync and sustained fault/load testing
9. Independent consensus/application/network/wallet review
10. Mainnet consideration only after all production release gates are satisfied

See [`ROADMAP.md`](ROADMAP.md) and [`blockchain/docs/MAINNET_GATES.md`](blockchain/docs/MAINNET_GATES.md).

## Public-Benefit Funding

Crakbit AI is raising funds to support the Security MVP, security research, infrastructure, developer tools, documentation, testing and carefully staged blockchain/testnet research.

The current fundraising target is **USD 150,000** with milestone-based allocation.

See [`docs/FUNDING.md`](docs/FUNDING.md).

**The current fundraising campaign is not a CRKBIT token sale and does not promise investment returns.**

## CRKBIT Notice

**Production CRKBIT has not been launched. There is currently no official CRKBIT presale or production token contract.**

The repository contains test-only CRKBIT accounting used in development/research/test networks. These units have no represented production value and should not be marketed or sold as mainnet CRKBIT.

Any future production utility asset remains subject to public testing, security review, economic design and applicable legal/regulatory consideration.

## Security and Responsible Use

Crakbit AI is being developed primarily for defensive security, secure software development, code review, research and educational use.

Please read [`SECURITY.md`](SECURITY.md) and [`blockchain/SECURITY.md`](blockchain/SECURITY.md). The production launch checklist is in [`blockchain/docs/MAINNET_GATES.md`](blockchain/docs/MAINNET_GATES.md).

## Contributing

Contributions, research, documentation improvements and security-focused ideas are welcome.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Official Links

- Website: https://crakbit.space
- Repository: https://github.com/navindusasmitha/CrakbitAI
- Funding / Giveth: Crakbit AI is publicly listed on Giveth

## Transparency

We intend to publish development milestones, architecture decisions, releases, funding-allocation updates where practical, open-source components, security/testing progress and devnet/testnet limitations.

See [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md).

## License

Unless otherwise noted, source code in this repository is released under the Apache License 2.0. See [`LICENSE`](LICENSE).

---

**Crakbit AI** — Secure Code. Secure Chains. Build the Future.
