# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent technology project building defensive-security tooling for developers, researchers, students and open-source communities. The repository contains an early secure-code scanner plus the Crakbit Chain research/public-testnet stack.

## Current status

- Security scanner: early alpha
- Security CLI: early alpha
- AI Security Assistant: in development
- Crakbit Chain: **v0.30.0a1 continuous-operations / evidence-publication alpha**
- External consensus candidate: CometBFT `v0.40.0`
- Governed execution protocol: `crakbit-execution/3`
- Browser wallet/public gateway: alpha
- Public-testnet, review/remediation, final-candidate, launch-rehearsal, live-host and continuous-evidence tooling: implemented
- Production CRKBIT: **not launched**
- Official CRKBIT presale: **none**

Crakbit Chain is **not a production mainnet** and should not be used to custody real value.

## Crakbit Chain v0.30

v0.30 adds an operations layer on top of the v0.29 real-host evidence path:

- signed non-secret 4+ validator monitoring inventory,
- rejection of secret-bearing inventory fields,
- read-only live CometBFT cluster monitoring,
- signed height-spread/app-hash-divergence monitoring samples,
- resumable hash-chained monitoring checkpoints,
- default seven-day monitoring target with >=0.99 success ratio,
- `scripts/run_v30_monitor.py` for continuous checkpoint/resume collection,
- raw evidence archive manifests with SHA-256 + retention policy,
- active RPC/explorer/gateway health probes,
- redundant public-edge gate with two healthy endpoints per role by default,
- protected HSM/remote-signer connectivity checks without reading private keys,
- signed public evidence bundle bound to the exact v0.29 real-evidence freeze,
- signed operator checklist that keeps DNS, treasury movement and launch execution manual.

A passing v0.30 evidence bundle still does **not** automatically start validators, change DNS, move funds or create production-value CRKBIT. Production readiness and launch flags stay false.

See [`blockchain/V0.30.md`](blockchain/V0.30.md) and [`blockchain/README.md`](blockchain/README.md).

## Quick test

```bash
git clone https://github.com/navindusasmitha/CrakbitAI.git
cd CrakbitAI/blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## v0.30 operations workflow

```bash
crakchain monitor-inventory-v30-build --help
crakchain monitor-sample-v30-probe --help
crakchain monitor-checkpoint-v30-build --help
crakchain archive-v30-build --help
crakchain edge-v30-probe --help
crakchain edge-gate-v30-build --help
crakchain signer-v30-probe --help
crakchain public-evidence-v30-build --help
crakchain operator-checklist-v30-build --help
```

For a resumable seven-day read-only campaign:

```bash
python scripts/run_v30_monitor.py --help
```

## Mainnet path

Production launch remains gated by actual independently managed validators, genuine long-running/fault/load/storage/state-sync evidence, protected remote/HSM signing, production RPC/TLS/WAF/DDoS/capacity/secret-management engineering, independently corroborated consensus/application/governance/network/cryptography/browser-wallet review, high/critical remediation/retest, finalized economics/incentives, applicable legal/regulatory review and an explicit human launch/no-launch decision.

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
