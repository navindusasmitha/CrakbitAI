# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.19 public-testnet review-candidate infrastructure alpha**

Crakbit AI has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and an experimental blockchain/application stack with browser wallet, public gateway, CometBFT integration, native ABCI state sync, indexed explorer tooling and signed review/release evidence.

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
| Crakbit Chain package | **v0.19.0a1** | Public-testnet/review-candidate infrastructure alpha |
| Python research consensus | Research-only | Local experiments only; not intended production BFT path |
| CometBFT bridge | Integration implemented | Candidate dependency remains CometBFT `v0.40.0` |
| External execution | Prototype implemented | Crash-safe staged FinalizeBlock → atomic Commit |
| Native ABCI state sync | Code implemented | Live independent-host recovery evidence still required |
| Browser wallet | Alpha implemented | Local Ed25519 signing + encrypted browser vault |
| Public gateway | Hardened alpha | Same-origin default, CSP/security headers, durable write limits |
| External explorer index | Prototype implemented | Dedicated commit/tx/address/account index |
| Explorer reconciliation | Implemented | Clean rebuild + deterministic fingerprints |
| Sustained soak collector | Implemented | Repeated health evidence; does not infer host independence |
| Review remediation matrix | **v0.19 implemented** | High/critical blockers + regression-test gate |
| Reproducible artifact comparison | **v0.19 implemented** | Byte-for-byte SHA-256 comparison for supplied outputs |
| CI reproducible build checks | **v0.19 implemented** | Double-build Python wheel + Go bridge comparison |
| Direct dependency SBOM | **v0.19 implemented** | CycloneDX 1.5 direct dependency inventory; not fully transitive |
| Signed release provenance | **v0.19 implemented** | Exact source/genesis/version/artifact hash binding |
| Signed operations-drill evidence | **v0.19 implemented** | Upgrade/rollback/IR/DR/validator-lifecycle evidence format |
| Signed review-candidate freeze | Implemented | Review freeze does not certify independent audit completion |
| Remote-signer config helper | Scaffold | Configures signer address only; no HSM deployment claim |
| Independent-host public testnet | Not yet evidenced | Sustained external operation/results still required |
| Independent consensus/security audit | Not completed | Mandatory before production-value consideration |
| Production CRKBIT | **Not launched** | No official presale or production token contract |

## v0.19 Completed Blockchain Work

- package/CLI advanced to `0.19.0a1`,
- machine-readable review finding/remediation matrix,
- automated high/critical release blocker logic,
- regression-test reference requirement for remediated high/critical findings,
- reproducible artifact comparison reports,
- CI double-build verification for Python wheel and Go bridge,
- direct-dependency CycloneDX SBOM generation,
- signed release provenance manifests,
- signed operations-drill evidence format,
- v0.19 unit tests and release-engineering documentation.

## What v0.19 Does Not Prove

v0.19 improves reproducibility and review/remediation evidence but does not complete external production gates. The following remain open until actually performed and independently reviewable:

- long-running four-validator operation across independently managed hosts/providers,
- live clean-host CometBFT state-sync recovery with application-hash convergence,
- real partition/packet-loss/latency/process-kill/sustained-load campaigns,
- deployed and drilled remote-signer/HSM-equivalent validator custody,
- multi-operator genesis ceremony using independently held keys,
- independent browser-wallet, consensus/application and network security review,
- complete transitive SBOM and supply-chain review,
- production multi-edge WAF/DDoS/capacity engineering,
- finalized production economics/validator incentives,
- applicable legal/regulatory review for any future production-value asset.

## Immediate Blockchain Priorities — v0.20

1. Add versioned application/database migration framework.
2. Add offline migration dry-run and rollback verification.
3. Publish protocol/application compatibility matrix.
4. Add validator-set lifecycle application boundary and testnet-only drill tooling.
5. Verify explorer/history migration and rebuild after schema changes.
6. Sign migration/rollback evidence using the v0.19 operations evidence format.
7. Continue ingesting and regression-testing any real independent review findings.
8. Keep production launch blocked until external testnet, security, operational, economic and legal gates are satisfied.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The repository contains test-only CRKBIT accounting for research/public-testnet work. The proposed development parameters of 21,000,000 maximum genesis units and 8 decimals are not final production economics and remain subject to technical, security, economic and applicable legal review.

See `blockchain/V0.19.md`, `blockchain/docs/MAINNET_GATES.md`, `blockchain/docs/WALLET_THREAT_MODEL.md`, `blockchain/docs/VALIDATOR_REMOTE_SIGNER.md` and GitHub Issue #1.
