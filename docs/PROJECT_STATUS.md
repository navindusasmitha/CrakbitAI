# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.25 public-testnet independent-review-candidate tooling alpha**

Crakbit AI has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and an experimental blockchain/application stack with browser wallet, public gateway, CometBFT integration, native ABCI state sync, validator governance, release/review evidence, migration rehearsal, public-testnet deployment/monitoring, operational fault/recovery evidence and v0.25 review-freeze tooling.

None of these alpha components should be described as a production mainnet or as safe for custody of real value.

## Current Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| Public website | Active | Project information and funding positioning available |
| GitHub repository | Active | Open documentation, scanner and blockchain research code |
| Fundraising | Publicly listed on Giveth | Campaign is not a CRKBIT token sale |
| AI Security Assistant | In development | Security MVP work remains active |
| Secure Code Scanner | Early alpha | Deterministic static-analysis rules implemented |
| Security CLI | Early alpha | `crak` CLI available |
| Crakbit Chain package | **v0.25.0a1** | Public-testnet / independent-review-candidate tooling alpha |
| CometBFT candidate | **v0.40.0** | External BFT candidate used by the ABCI bridge |
| Governed external execution | **`crakbit-execution/3`** | Crash-safe staged FinalizeBlock → atomic Commit |
| Validator governance | Implemented for testnet research | Strict `>2/3` current voting-power join/remove/replace approvals |
| Governance activation model | **H → H+2** | Still requires real multi-host evidence and independent review |
| Native ABCI state sync | Governance-aware | Real independent-host recovery evidence still required |
| Public-testnet deployment layer | **v0.23 implemented** | 4+ validator inventory, genesis/deployment bundles, monitoring |
| Operational hardening | **v0.24 implemented** | Preflight, fault/recovery, redundancy, signer evidence, 24h/72h/7d gates |
| Incident-response records | **v0.25 implemented** | Timeline, escalation and recovery-verification checks |
| Signed operator host attestations | **v0.25 implemented** | Bound to exact commit/package/CometBFT/genesis identity |
| Aggregate review gate | **v0.25 implemented** | Requires v0.24 readiness + 4+ unique operators/signers + diversity + incident drill |
| Exact review-candidate freeze | **v0.25 implemented** | Signed artifact/genesis/gate binding + explicit reviewer scope |
| Browser wallet | Alpha implemented | Local Ed25519 signing + encrypted browser vault |
| Public gateway | Hardened alpha | Same-origin default, CSP/security headers, durable write limits |
| Review/release provenance | Implemented | Signed source/genesis/artifact binding |
| Independent-host public testnet | **Not yet evidenced** | Tooling exists; real sustained external operation still required |
| Independent security audit | **Not completed** | Mandatory before production-value consideration |
| Production CRKBIT | **Not launched** | No official presale or production token contract |

## v0.25 Completed Code Work

- package/CLI advanced to `0.25.0a1`,
- alert/incident-response record format,
- monotonic started → acknowledged → resolved timing checks,
- escalation requirement for high/critical incidents,
- recovery-verification requirement before an incident is closed,
- signed per-operator host attestations using dedicated evidence keys,
- exact source commit/package/CometBFT/application-genesis/consensus-genesis binding,
- required 7-day soak, protected signer, backup/restore, clean-host state sync and validator-governance assertions,
- required restart/process-kill/partition/latency/packet-loss/load/storage coverage,
- four-or-more unique operator/validator/evidence-signer gate,
- provider and region diversity gates,
- single candidate identity checks across all operator attestations,
- dependency on successful v0.24 operational readiness,
- dependency on closed incident-response drill evidence,
- signed exact review-freeze manifest with reviewer scope and artifact hashes,
- v0.25 regression tests and independent-review handoff documentation.

## Important v0.25 Boundary

v0.25 improves **evidence consistency and review handoff**, not real-world verification. Signed host records are explicitly marked `operator_self_attested=true` and `independently_verified=false`.

A valid evidence signature proves that the evidence-key holder signed the record. It does not independently prove the claimed VPS/provider/region/soak/fault/recovery event occurred. Reviewers must corroborate those claims against infrastructure/logs/raw observations where relevant.

A successful v0.25 review gate can allow a candidate to be frozen **for independent review**. It does not mean that independent review has been completed, that high/critical findings are absent, or that production mainnet is approved.

## External Gates Still Open

The following remain open until actually performed and independently reviewable:

- provision and operate four or more independently managed validators across suitable operators/providers/regions,
- perform a real multi-operator genesis ceremony using independently held keys,
- run actual continuous 24h → 72h → 7-day soak windows,
- execute real validator join/remove/replace campaigns on independent hosts,
- execute authorized restart/process-kill/partition/latency/packet-loss/load/storage campaigns and preserve raw evidence,
- complete real clean-host state-sync and backup/restore disaster-recovery drills,
- deploy and drill protected remote-signer/HSM-equivalent validator/governance key custody,
- deploy production-style redundant RPC/explorer/gateway edges with TLS/WAF/DDoS/capacity controls,
- independently review consensus/application, governance, network/RPC, cryptography/key management and browser wallet,
- remediate and retest high/critical findings,
- complete transitive supply-chain/SBOM review,
- finalize production economics/validator incentives,
- complete applicable legal/regulatory review for any future production-value asset.

## Immediate Blockchain Priorities — v0.26

1. Use the v0.23/v0.24/v0.25 tooling on real independently managed hosts.
2. Add structured independent-review finding import, severity tracking, remediation commits and retest records.
3. Add a hard release blocker for unresolved high/critical independent-review findings.
4. Add candidate supersession/re-freeze rules when source, genesis, dependencies or operational evidence changes.
5. Add independent reproducible-build/supply-chain attestation hooks.
6. Add production-edge capacity/TLS/WAF/DDoS evidence formats without embedding provider secrets.
7. Keep production-mainnet consideration disabled until external evidence and independent review actually exist.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The repository contains test-only CRKBIT accounting for research/public-testnet work. The proposed development parameters of 21,000,000 maximum genesis units and 8 decimals are not final production economics and remain subject to technical, security, economic and applicable legal review.

See `blockchain/V0.25.md`, `blockchain/docs/INDEPENDENT_REVIEW_HANDOFF_V25.md`, `blockchain/docs/MAINNET_GATES.md`, `ROADMAP.md` and GitHub Issue #1.
