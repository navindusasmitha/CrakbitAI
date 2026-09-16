# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.16 public-testnet/mainnet-candidate infrastructure alpha**

Crakbit AI has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and a runnable experimental blockchain/application stack with a browser wallet, public gateway, CometBFT integration proof-of-concept and public-testnet recovery/operations tooling.

None of these alpha components should be described as a production mainnet or as safe for custody of real value.

## Current Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| Public website | Active | Project information and funding positioning available |
| GitHub repository | Active | Open documentation, scanner and blockchain research code |
| Fundraising | Publicly listed on Giveth | Fundraising campaign is not a CRKBIT token sale |
| AI Security Assistant | In development | Security MVP work remains active |
| Secure Code Scanner | Early alpha | Deterministic static-analysis rules implemented |
| Security CLI | Early alpha | `crak` CLI available |
| Security API | Planned | Follows scanner stabilization |
| Smart-contract scanner | Planned | Blockchain-security roadmap |
| Crakbit Chain package | **v0.16.0a1** | Public-testnet/mainnet-candidate infrastructure alpha |
| Python research consensus | Research-only | Retained for local experiments; not production BFT path |
| CometBFT bridge | **Integration PoC implemented** | Candidate pinned at CometBFT `v0.40.0` |
| External execution | **Prototype implemented** | Crash-safe staged FinalizeBlock → atomic Commit |
| Browser wallet | **Alpha implemented** | Local Ed25519 signing + encrypted browser vault |
| Public gateway | **v0.16 hardened alpha** | Same-origin default, CSP/security headers, durable write limits |
| Test faucet | **Prototype implemented** | Persistent distribution/cooldown + durable request limits |
| Mining Lab | **Test-only prototype** | Browser work reward; not consensus block mining or minting |
| External state checkpoint | **v0.16 adapter implemented** | Export/verify/restore; native CometBFT state-sync wiring still pending |
| External explorer index | **v0.16 prototype implemented** | Dedicated commit/tx/address/account SQLite index |
| Local CometBFT lab generator | **v0.16 implemented** | Creates independent validator homes/shared consensus genesis |
| Multi-host health checker | **v0.16 implemented** | Reachability, catch-up and height-spread checks |
| Crash/replay evidence matrix | **v0.16 implemented** | Deterministic application restart/replay/checkpoint checks |
| Independent-host public testnet | Not yet evidenced | Sustained external operation/results still required |
| Independent consensus/security audit | Not completed | Mandatory before production-value consideration |
| Production CRKBIT | **Not launched** | No official presale or production token contract |

## v0.16 Completed Blockchain Work

- package/CLI advanced to `0.16.0a1`,
- repeatable multi-node CometBFT lab generator,
- shared consensus-genesis/persistent-peer generation from independent validator homes,
- deterministic external-application checkpoint export/verify/import,
- optional trusted CometBFT height/application-hash binding during checkpoint verification,
- explicit checkpoint-base metadata instead of invented historical commits,
- post-checkpoint next-height commit support,
- dedicated external explorer index and service,
- restart-persistent SQLite public write-rate limiting,
- durable faucet/mining challenge request controls,
- same-origin gateway default and restrictive CSP/security headers,
- multi-host validator health/divergence checker,
- external FinalizeBlock/Commit crash/replay/checkpoint evidence matrix,
- wallet threat-model documentation,
- validator remote-signer/HSM-equivalent guidance,
- automated v0.16 tests plus existing CometBFT Go bridge CI.

## What v0.16 Does Not Prove

v0.16 is not evidence that a production network is ready. Specifically:

- the application checkpoint adapter is not fully wired into native CometBFT state-sync snapshot lifecycle,
- a long-running four-validator network on independently managed VPS/providers has not yet been published as sustained evidence,
- no completed real partition/packet-loss/latency/load campaign is claimed,
- SQLite durable limits do not provide horizontally shared distributed rate limiting,
- remote-signer/HSM-equivalent validator custody is documented but not deployed/audited,
- browser wallet and gateway have not completed independent security review,
- external explorer indexing has not completed production reconciliation/rebuild drills,
- production economics and validator incentives are not finalized,
- applicable legal/regulatory review for any future production asset is not complete.

## Immediate Security-Platform Priorities

1. Expand scanner unit tests and rule coverage.
2. Add structured configuration checks.
3. Reduce false positives and document rules.
4. Build AI-assisted explanation/remediation on deterministic findings.
5. Publish a simple Security MVP demo.
6. Begin developer API work after scanner core stabilization.

## Immediate Blockchain Priorities — v0.17

1. Wire the v0.16 application checkpoint format into reviewed CometBFT state-sync lifecycle.
2. Operate generated validators continuously across independent hosts/providers.
3. Execute and publish partition, latency, packet-loss, restart and sustained-load evidence.
4. Add explorer reconciliation and clean-host rebuild drills.
5. Deploy shared upstream rate limiting, reverse-proxy and TLS profiles.
6. Integrate/test a protected remote-signer/HSM-compatible validator workflow.
7. Produce reproducible signed public-testnet release bundles.
8. Run a documented multi-operator genesis ceremony without sharing private keys.
9. Freeze a review candidate and commission independent consensus/application/network/wallet review.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The repository contains test-only CRKBIT accounting for research/public-testnet work. The proposed development parameters of 21,000,000 maximum genesis units and 8 decimals are not final production economics and remain subject to technical, security, economic and applicable legal review.

## Evidence and Transparency

Crakbit AI aims to distinguish clearly between implemented code, test evidence, public-testnet operation and production readiness. A feature being present in source code is not the same as that feature being independently reviewed, operated at scale or approved for real-value use.

See:

- `blockchain/V0.16.md`
- `blockchain/docs/MAINNET_GATES.md`
- `blockchain/docs/WALLET_THREAT_MODEL.md`
- `blockchain/docs/VALIDATOR_REMOTE_SIGNER.md`
- GitHub Issue #1 implementation tracker
