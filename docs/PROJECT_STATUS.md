# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.30 continuous-operations / evidence-publication alpha**

Crakbit AI has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and an experimental blockchain/application stack with browser wallet, public gateway, CometBFT integration, native ABCI state sync, validator governance, review/remediation controls, launch-rehearsal policy, live-host evidence and v0.30 long-running operations/evidence tooling.

None of these alpha components should be described as a production mainnet or as safe for custody of real value.

## Current Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| Public website | Active | Project information and funding positioning available |
| GitHub repository | Active | Open documentation, scanner and blockchain research code |
| Fundraising | Publicly listed on Giveth | Campaign is not a CRKBIT token sale |
| AI Security Assistant | In development | Security MVP work remains active |
| Secure Code Scanner | Early alpha | Deterministic static-analysis rules implemented |
| Crakbit Chain package | **v0.30.0a1** | Continuous-operations / evidence-publication alpha |
| CometBFT candidate | **v0.40.0** | External BFT candidate used by the ABCI bridge |
| Governed execution | **`crakbit-execution/3`** | Crash-safe staged FinalizeBlock → atomic Commit |
| Validator governance | Implemented for testnet research | Strict `>2/3` current voting-power join/remove/replace approvals |
| Native ABCI state sync | Governance-aware | Real external recovery campaign still required |
| Final-candidate policy | v0.27 implemented | Upgrade/governance/economics/review/multi-party release gate |
| Launch rehearsal | v0.28 implemented | Runbook/cutover/SLO/signer/upgrade/risk/review/repro evidence |
| Real-host evidence | v0.29 implemented | Live validator/cluster/genesis/soak/fault evidence path |
| Monitor inventory | **v0.30 implemented** | Non-secret 4+ validator monitoring inventory with secret-field rejection |
| Continuous read-only monitor | **v0.30 implemented** | Live CometBFT samples, divergence/height-spread checks |
| Resumable 7-day checkpointing | **v0.30 implemented** | Hash-chained signed checkpoints, default 604800s and >=0.99 ratio |
| Evidence archive/retention | **v0.30 implemented** | File size/SHA-256 + minimum 30-day retention manifest |
| Public-edge monitoring | **v0.30 implemented** | RPC/explorer/gateway health + redundant two-per-role gate |
| Protected signer monitoring | **v0.30 implemented** | TCP connectivity check without reading private keys |
| Public evidence publication bundle | **v0.30 implemented** | Exact v0.29 freeze binding + monitor/archive/edge/signer evidence |
| Independent-host public testnet | **Not yet actually run here** | Tooling exists; real VPS operation/evidence remains external |
| Independent security audit | **Not completed** | Review tooling does not equal completed independent review |
| Production mainnet | **Not launched** | No software gate automatically launches production |
| Production CRKBIT | **Not launched** | No official presale or production token contract |

## v0.30 Completed Code Work

- package/CLI advanced to `0.30.0a1`,
- signed non-secret monitoring inventory for 4+ validators,
- secret-bearing inventory-field rejection,
- read-only live CometBFT monitor sampling,
- height-spread and same-height application-hash divergence checks,
- resumable signed checkpoint chain with session identity and immutable target parameters,
- seven-day target + >=0.99 success ratio support,
- continuous collector script with checkpoint/resume behavior,
- signed raw-evidence archive/retention manifest,
- active RPC/explorer/gateway health probes,
- redundant public-edge gate with minimum two healthy endpoints per role by default,
- protected signer/HSM-equivalent connectivity monitoring without private-key access,
- public evidence bundle bound to the exact v0.29 real-evidence freeze,
- signed final operator checklist with explicit manual DNS/treasury/launch controls,
- v0.30 regression tests and documentation.

## Important v0.30 Boundary

The v0.30 monitor can make real read-only network observations and create tamper-evident evidence, but a monitoring signature does not prove that a provider/operator is independent or that a physical HSM is secure. A central monitor also does not replace the v0.29 multi-operator signatures.

A passing public evidence bundle still records:

```text
production_mainnet_ready=false
production_mainnet_launched=false
production_crkbit_launched=false
```

## External Gates Still Open

- provision and operate four or more independently managed validators on real hosts,
- run the real multi-operator genesis ceremony with separately held keys,
- collect genuine continuous 24h → 72h → 7-day or longer observations,
- execute authorized real fault/load/storage/state-sync/governance/upgrade campaigns,
- deploy and independently inspect protected remote-signer/HSM-equivalent custody,
- deploy redundant production-style RPC/explorer/gateway edges and measure real capacity/failover,
- complete independent consensus/application/governance/network/cryptography/browser-wallet review,
- independently retest every high/critical fix against the exact final candidate,
- complete external reproducible-build/transitive dependency review,
- finalize and independently review production economics/validator incentives,
- complete applicable legal/regulatory review,
- make an explicit human launch/no-launch decision after reviewing the real evidence.

## Immediate Blockchain Priorities — v0.31

The next useful phase should focus on **real operator deployment ergonomics and review publication**, not another readiness label:

1. Generate non-secret Ansible/systemd deployment bundles from the v0.30 inventory.
2. Add signed configuration-drift detection for validator, CometBFT, firewall and public-edge configs without embedding secrets.
3. Add alert/SLO incident correlation across monitor samples and public edges.
4. Add signed backup-age/state-sync freshness checks.
5. Add public evidence index/HTML or JSON feed that exposes hashes/status without private infrastructure details.
6. Add release-candidate supersession rules when source/genesis/evidence changes after publication.
7. Continue to keep production launch as a separate human decision.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The repository contains test-only CRKBIT accounting for research/public-testnet work. The 21,000,000 maximum-supply and 8-decimal values remain development proposals unless intentionally frozen and independently reviewed through the v0.27 economics process.

See `blockchain/V0.30.md`, `blockchain/docs/MAINNET_GATES.md`, `ROADMAP.md` and GitHub Issue #1.
