# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.17 public-testnet/mainnet-candidate infrastructure alpha**

Crakbit AI has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and a runnable experimental blockchain/application stack with browser wallet, public gateway, CometBFT integration, native ABCI state-sync code and public-testnet evidence tooling.

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
| Crakbit Chain package | **v0.17.0a1** | Public-testnet/mainnet-candidate infrastructure alpha |
| Python research consensus | Research-only | Retained for local experiments; not intended production BFT path |
| CometBFT bridge | **v0.17 integration implemented** | Candidate dependency remains CometBFT `v0.40.0` |
| External execution | **Prototype implemented** | Crash-safe staged FinalizeBlock → atomic Commit |
| Native ABCI state sync | **v0.17 code implemented** | List/Offer/Load/Apply snapshot lifecycle; live independent-host recovery evidence still required |
| Browser wallet | **Alpha implemented** | Local Ed25519 signing + encrypted browser vault |
| Public gateway | **Hardened alpha** | Same-origin default, CSP/security headers, durable write limits |
| Test faucet | **Prototype implemented** | Persistent distribution/cooldown + durable request limits |
| Mining Lab | **Test-only prototype** | Browser work reward; not consensus block mining or minting |
| External explorer index | **Prototype implemented** | Dedicated commit/tx/address/account SQLite index |
| CometBFT lab generator | **Implemented** | Creates independent validator homes/shared consensus genesis |
| Multi-host health checker | **Implemented** | Reachability, catch-up and height-spread checks |
| Fault campaign runner | **v0.17 implemented** | Dry-run by default; operator must execute real campaigns separately |
| Signed evidence bundle | **v0.17 implemented** | Binds exact source commit, CometBFT version, genesis and evidence hashes |
| Public-testnet edge profile | **v0.17 scaffold** | TLS/rate limits for one controlled edge; not a complete distributed WAF/DDoS system |
| Remote-signer config helper | **v0.17 scaffold** | Configures CometBFT signer address only; does not implement/protect an HSM signer |
| Independent-host public testnet | Not yet evidenced | Sustained external operation/results still required |
| Independent consensus/security audit | Not completed | Mandatory before production-value consideration |
| Production CRKBIT | **Not launched** | No official presale or production token contract |

## v0.17 Completed Blockchain Work

- package/CLI advanced to `0.17.0a1`,
- deterministic CometBFT state-sync snapshot materialization,
- ABCI `ListSnapshots`, `OfferSnapshot`, `LoadSnapshotChunk` and `ApplySnapshotChunk` bridge wiring,
- snapshot acceptance bound to the application hash supplied by CometBFT,
- whole-artifact and per-chunk SHA-256 verification,
- pristine-database-only state restore with explicit snapshot-base semantics,
- authenticated v0.17 execution-service state-sync endpoints,
- signed public-testnet evidence bundles tied to exact Git source commit and declared CometBFT version,
- dry-run-by-default controlled fault-campaign evidence runner,
- single-edge NGINX TLS/rate-limit public-testnet profile,
- guarded CometBFT remote-signer configuration helper,
- expanded Python and Go state-sync/evidence tests,
- updated v0.17 security/operations documentation.

## What v0.17 Does Not Prove

v0.17 is not evidence that a production network is ready. Specifically:

- a long-running four-validator network on independently managed VPS/providers has not yet been published as sustained evidence,
- live clean-host CometBFT state-sync recovery still needs to be demonstrated on that network,
- no completed real partition/packet-loss/latency/process-kill/load campaign is claimed merely because tooling exists,
- the NGINX profile is a single-edge scaffold and not horizontally distributed DDoS/WAF infrastructure,
- remote-signer/HSM-equivalent validator custody is not deployed or independently reviewed,
- browser wallet, consensus/application integration and network surfaces have not completed independent security review,
- explorer indexing still needs clean-host reconciliation/rebuild evidence,
- a final multi-operator production genesis ceremony has not occurred,
- production economics/validator incentives are not finalized,
- applicable legal/regulatory review for any future production asset is not complete.

## Immediate Security-Platform Priorities

1. Expand scanner unit tests and rule coverage.
2. Add structured configuration checks.
3. Reduce false positives and document rules.
4. Build AI-assisted explanation/remediation on deterministic findings.
5. Publish a simple Security MVP demo.
6. Begin developer API work after scanner core stabilization.

## Immediate Blockchain Priorities — v0.18 evidence freeze

1. Operate four validators continuously across independently managed hosts/providers.
2. Demonstrate live clean-host state sync and application-hash convergence.
3. Execute controlled partition, latency, packet-loss, process-kill and sustained-load campaigns using v0.17 tooling.
4. Publish signed raw health/fault/recovery/soak evidence tied to exact source commit and CometBFT version.
5. Reconcile/rebuild explorer indexes from clean hosts.
6. Deploy and drill a protected remote-signer/HSM-compatible validator workflow.
7. Exercise a multi-operator genesis ceremony without sharing validator private keys.
8. Freeze a review candidate and commission independent consensus/application/network/wallet review.
9. Remediate review findings before any production-mainnet decision.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The repository contains test-only CRKBIT accounting for research/public-testnet work. The proposed development parameters of 21,000,000 maximum genesis units and 8 decimals are not final production economics and remain subject to technical, security, economic and applicable legal review.

## Evidence and Transparency

Crakbit AI distinguishes between implemented code, test evidence, public-testnet operation and production readiness. A feature being present in source code is not the same as that feature being independently reviewed, operated at scale or approved for real-value use.

See:

- `blockchain/V0.17.md`
- `blockchain/docs/MAINNET_GATES.md`
- `blockchain/docs/WALLET_THREAT_MODEL.md`
- `blockchain/docs/VALIDATOR_REMOTE_SIGNER.md`
- GitHub Issue #1 implementation tracker
