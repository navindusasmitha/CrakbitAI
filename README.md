# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent technology project building defensive-security tooling for developers, researchers, students and open-source communities. The repository contains an early secure-code scanner plus the Crakbit Chain research/public-testnet stack.

## Current status

- Security scanner: early alpha
- Security CLI: early alpha
- AI Security Assistant: in development
- Crakbit Chain: **v0.29.0a1 real independent-host execution/evidence alpha**
- External consensus candidate: CometBFT `v0.40.0`
- Governed execution protocol: `crakbit-execution/3`
- Browser wallet/public gateway: alpha
- Public-testnet, review/remediation, final-candidate, launch-rehearsal and real-host evidence tooling: implemented
- Production CRKBIT: **not launched**
- Official CRKBIT presale: **none**

Crakbit Chain is **not a production mainnet** and should not be used to custody real value.

## Crakbit Chain v0.29

The chain stack now includes the v0.28 launch-rehearsal layer plus a new real-host evidence path:

- live CometBFT `/status` + `/abci_info` probing,
- signed per-validator live host observations,
- exact source/candidate/application-genesis/consensus-genesis binding,
- 4+ validator/operator/evidence-signer cluster checks,
- provider/region diversity gates,
- bounded observation windows and height spread,
- same-height application-hash divergence detection,
- signed multi-operator genesis ceremony attestations,
- signed long-lived soak evidence with a default seven-day target,
- signed fault/recovery results bound to raw evidence SHA-256,
- required restart/process-kill/partition/latency/packet-loss/load/storage/state-sync/governance/upgrade campaign coverage,
- exact v0.28 release-freeze/rehearsal-gate binding,
- final signed v0.29 real-evidence freeze for human/independent review only.

A passing v0.29 real-execution gate still does **not** automatically launch validators, change DNS, move funds or create production-value CRKBIT. Production readiness/launch claims remain false in the tooling.

See [`blockchain/V0.29.md`](blockchain/V0.29.md) and [`blockchain/README.md`](blockchain/README.md).

## Quick test

```bash
git clone https://github.com/navindusasmitha/CrakbitAI.git
cd CrakbitAI/blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## v0.29 real-host workflow

```bash
crakchain live-host-v29-probe --help
crakchain cluster-v29-build --help
crakchain genesis-attest-v29-build --help
crakchain genesis-gate-v29-build --help
crakchain soak-v29-build --help
crakchain fault-result-v29-build --help
crakchain real-gate-v29-build --help
crakchain real-freeze-v29-build --help
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
