# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.18 public-testnet review-candidate infrastructure alpha**

Crakbit AI has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and a runnable experimental blockchain/application stack with browser wallet, public gateway, CometBFT integration, native ABCI state sync, indexed explorer tooling and signed evidence/review-candidate tooling.

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
| Crakbit Chain package | **v0.18.0a1** | Public-testnet/review-candidate infrastructure alpha |
| Python research consensus | Research-only | Local experiments only; not intended production BFT path |
| CometBFT bridge | Integration implemented | Candidate dependency remains CometBFT `v0.40.0` |
| External execution | Prototype implemented | Crash-safe staged FinalizeBlock → atomic Commit |
| Native ABCI state sync | Code implemented | Live independent-host recovery evidence still required |
| Browser wallet | Alpha implemented | Local Ed25519 signing + encrypted browser vault |
| Public gateway | Hardened alpha | Same-origin default, CSP/security headers, durable write limits |
| External explorer index | Prototype implemented | Dedicated commit/tx/address/account index |
| Explorer clean-rebuild reconciliation | **v0.18 implemented** | Deterministic table fingerprints + metadata comparison |
| Multi-host health checker | Implemented | Reachability, catch-up and height-spread checks |
| Sustained soak collector | **v0.18 implemented** | Repeated health evidence; does not infer host independence |
| Fault campaign runner | Implemented | Dry-run by default; real campaigns still operator-executed |
| Signed evidence bundle | Implemented | Binds exact source commit, CometBFT version, genesis and evidence hashes |
| Signed review-candidate freeze | **v0.18 implemented** | Binds source/version/genesis/review artifact hashes; does not certify an audit |
| Remote-signer config helper | Scaffold | Configures signer address only; no HSM deployment claim |
| Independent-host public testnet | Not yet evidenced | Sustained external operation/results still required |
| Independent consensus/security audit | Not completed | Mandatory before production-value consideration |
| Production CRKBIT | **Not launched** | No official presale or production token contract |

## v0.18 Completed Blockchain Work

- package/CLI advanced to `0.18.0a1`,
- signed review-candidate freeze manifest format,
- exact source commit/package/CometBFT/genesis binding,
- review artifact SHA-256 binding and verification,
- conservative review claims that reject production-mainnet/audit-complete claims,
- clean explorer rebuild/reconciliation without silently mutating the deployed index,
- deterministic commit/transaction/address/account index fingerprints,
- sustained multi-host health/soak evidence collector,
- v0.18 unit tests while retaining native state-sync and Go bridge CI coverage,
- v0.18 review/evidence documentation.

## What v0.18 Does Not Prove

v0.18 provides tooling to freeze and verify a candidate, but repository changes cannot prove external operation by themselves. The following remain open until actually performed and published:

- long-running four-validator operation across independently managed hosts/providers,
- live clean-host CometBFT state-sync recovery with application-hash convergence,
- real partition/packet-loss/latency/process-kill/sustained-load campaigns,
- deployed and drilled remote-signer/HSM-equivalent validator custody,
- a multi-operator genesis ceremony using independently held keys,
- independent browser-wallet, consensus/application and network security review,
- production multi-edge WAF/DDoS/capacity engineering,
- finalized production economics/validator incentives,
- applicable legal/regulatory review for any future production-value asset.

## Immediate Blockchain Priorities — external evidence / review

1. Run the v0.18 candidate continuously on independently managed hosts.
2. Produce signed health/soak/fault/recovery evidence tied to the exact source commit.
3. Demonstrate a clean-host state-sync recovery and explorer reconciliation.
4. Exercise protected remote-signer/HSM-compatible validator custody.
5. Perform a documented multi-operator genesis ceremony without sharing private keys.
6. Build a signed review-freeze artifact set.
7. Commission independent consensus/application/network/wallet review.
8. Remediate findings and create a new freeze for any changed source.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The repository contains test-only CRKBIT accounting for research/public-testnet work. The proposed development parameters of 21,000,000 maximum genesis units and 8 decimals are not final production economics and remain subject to technical, security, economic and applicable legal review.

See `blockchain/V0.18.md`, `blockchain/docs/MAINNET_GATES.md`, `blockchain/docs/WALLET_THREAT_MODEL.md`, `blockchain/docs/VALIDATOR_REMOTE_SIGNER.md` and GitHub Issue #1.
