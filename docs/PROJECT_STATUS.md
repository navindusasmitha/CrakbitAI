# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.27 final mainnet-candidate policy/evidence tooling alpha**

Crakbit AI has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and an experimental blockchain/application stack with browser wallet, public gateway, CometBFT integration, native ABCI state sync, validator governance, public-testnet deployment/monitoring, operational fault/recovery evidence, independent-review remediation tooling and a v0.27 final candidate policy layer.

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
| Crakbit Chain package | **v0.27.0a1** | Final mainnet-candidate policy/evidence tooling alpha |
| CometBFT candidate | **v0.40.0** | External BFT candidate used by the ABCI bridge |
| Governed execution | **`crakbit-execution/3`** | Crash-safe staged FinalizeBlock → atomic Commit |
| Validator governance | Implemented for testnet research | Strict `>2/3` current voting-power join/remove/replace approvals |
| Native ABCI state sync | Governance-aware | Real independent-host recovery evidence still required |
| Public-testnet deployment layer | **v0.23 implemented** | 4+ validator inventory, genesis/deployment bundles, monitoring |
| Operational hardening | **v0.24 implemented** | Preflight, fault/recovery, redundancy, signer evidence, 24h/72h/7d gates |
| Initial independent-review freeze | **v0.25 implemented** | Signed host evidence, incident records and exact candidate freeze |
| Review remediation/retest | **v0.26 implemented** | Stable findings + exact-candidate high/critical retest gate |
| Coordinated upgrade policy | **v0.27 implemented** | Signed source/schema/migration/rollback plan + strict >2/3 readiness |
| Governance timelock policy | **v0.27 implemented** | Normal/emergency delay + cancellation + strict-supermajority emergency approval |
| Economics/genesis freeze | **v0.27 implemented** | Explicit CRKBIT supply/fee/incentive/distribution parameter commitment |
| Economic/legal review hooks | **v0.27 implemented** | Signed external attestations bound to exact economics freeze/candidate commit |
| Multi-party release approval | **v0.27 implemented** | Minimum 3 unique release approver IDs/signers |
| Final candidate identity/gate | **v0.27 implemented** | Deterministic identity across operations/review/governance/economics/release evidence |
| Browser wallet | Alpha implemented | Local Ed25519 signing + encrypted browser vault |
| Independent-host public testnet | **Not yet evidenced** | Tooling exists; real sustained external operation still required |
| Independent security audit | **Not completed** | Review tooling does not equal a completed independent audit |
| Production mainnet | **Not launched** | Final candidate gate is evidence policy only |
| Production CRKBIT | **Not launched** | No official presale or production token contract |

## v0.27 Completed Code Work

- package/CLI advanced to `0.27.0a1`,
- signed coordinated upgrade plan with strict `>2/3` validator-readiness requirement,
- migration/rollback hash binding, activation height and rollback deadline,
- signed governance policy with normal/emergency timelocks and pre-activation cancellation,
- emergency strict-supermajority rule and no arbitrary balance/supply bypass,
- signed explicit economics/genesis parameter freeze,
- economics freeze records no investment-return promise and no token-sale authorization,
- signed economic-security and legal/regulatory review attestation formats,
- exact candidate source/genesis/economics cross-artifact binding,
- deterministic final candidate identity SHA-256,
- signed release approval records,
- minimum three unique release approvers/signers,
- final candidate gate that consumes operational readiness, v0.26 remediation, governance, economics, upgrade, external review and release approvals,
- signed final readiness report,
- v0.27 regression tests and documentation.

## Important v0.27 Boundary

A passing `mainnet_candidate_gate_satisfied=true` is **not** equivalent to `production_mainnet_ready=true`. v0.27 deliberately keeps production readiness and launch claims false.

The gate verifies consistency of supplied signed evidence. It does not independently prove that validators ran for seven days, reviewers were independent, HSMs were deployed, public-edge protections performed as claimed, or all launch obligations have been satisfied. Those facts still require real operation and independent corroboration.

## External Gates Still Open

The following remain open until actually performed and independently reviewable:

- provision and operate four or more independently managed validators across suitable operators/providers/regions,
- perform a real multi-operator genesis ceremony with independently held keys,
- run actual continuous 24h → 72h → 7-day soak windows,
- execute authorized validator-governance, restart/process-kill/partition/latency/packet-loss/load/storage campaigns,
- complete real clean-host state-sync and backup/restore disaster-recovery drills,
- deploy and drill protected remote-signer/HSM-equivalent validator/governance key custody,
- deploy production-style redundant RPC/explorer/gateway edges and independently corroborate TLS/WAF/DDoS/capacity evidence,
- complete independent consensus/application/governance/network/cryptography/browser-wallet review,
- independently retest every high/critical remediation against the final exact candidate,
- complete independent reproducible-build/transitive supply-chain review,
- finalize and independently review production economics/validator incentives,
- complete applicable legal/regulatory review,
- make an explicit human launch/no-launch decision after reviewing the evidence.

## Immediate Blockchain Priorities — v0.28

1. Execute the existing v0.23–v0.27 tooling against real independently managed infrastructure instead of adding more self-attestation layers.
2. Add launch rehearsal/runbook tooling for genesis ceremony, DNS/RPC cutover, validator start order, rollback and incident escalation without performing an automatic launch.
3. Add live multi-edge capacity/SLO evidence and outage/failover drills.
4. Add remote-signer/HSM key-rotation and catastrophic-recovery evidence.
5. Add final independent reviewer sign-off aggregation and explicit unresolved-risk register.
6. Freeze a release candidate only from real independently corroborated evidence.
7. Keep production launch as an explicit human decision; never auto-launch from a passing software gate.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The repository contains test-only CRKBIT accounting for research/public-testnet work. The 21,000,000 maximum-supply and 8-decimal values remain development proposals unless intentionally frozen and independently reviewed through the v0.27 economics process.

See `blockchain/V0.27.md`, `blockchain/docs/MAINNET_GATES.md`, `ROADMAP.md` and GitHub Issue #1.
