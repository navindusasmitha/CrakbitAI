# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.28 launch-rehearsal / independently-corroborated-evidence tooling alpha**

Crakbit AI has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and an experimental blockchain/application stack with browser wallet, public gateway, CometBFT integration, native ABCI state sync, validator governance, public-testnet deployment/monitoring, operational fault/recovery tooling, independent-review remediation controls, final-candidate policy and v0.28 launch-rehearsal evidence tooling.

None of these alpha components should be described as a production mainnet or as safe for custody of real value.

## Current Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| Public website | Active | Project information and funding positioning available |
| GitHub repository | Active | Open documentation, scanner and blockchain research code |
| Fundraising | Publicly listed on Giveth | Campaign is not a CRKBIT token sale |
| AI Security Assistant | In development | Security MVP work remains active |
| Secure Code Scanner | Early alpha | Deterministic static-analysis rules implemented |
| Crakbit Chain package | **v0.28.0a1** | Launch-rehearsal / corroborated-evidence tooling alpha |
| CometBFT candidate | **v0.40.0** | External BFT candidate used by the ABCI bridge |
| Governed execution | **`crakbit-execution/3`** | Crash-safe staged FinalizeBlock → atomic Commit |
| Validator governance | Implemented for testnet research | Strict `>2/3` current voting-power join/remove/replace approvals |
| Native ABCI state sync | Governance-aware | Real independent-host recovery evidence still required |
| Public-testnet deployment layer | v0.23 implemented | 4+ validator inventory, genesis/deployment bundles, monitoring |
| Operational hardening | v0.24 implemented | Preflight, fault/recovery, redundancy, signer evidence, 24h/72h/7d gates |
| Initial independent-review freeze | v0.25 implemented | Signed host evidence, incident records and exact candidate freeze |
| Review remediation/retest | v0.26 implemented | Stable findings + exact-candidate high/critical retest gate |
| Final candidate policy | v0.27 implemented | Upgrade/governance/economics/review/multi-party release gate |
| Launch rehearsal runbook | **v0.28 implemented** | Genesis/start order/rollback; dry-run only |
| DNS/RPC/explorer cutover rehearsal | **v0.28 implemented** | Redundant failover + rollback; no automatic production DNS change |
| Edge SLO/capacity evidence | **v0.28 implemented** | Explicit thresholds + measured availability/latency/error/capacity/failover |
| Protected signer recovery drill | **v0.28 implemented** | Rotation/revocation/recovery/catastrophic drill evidence; no key export |
| Upgrade/rollback rehearsal | **v0.28 implemented** | Bound to signed v0.27 upgrade plan |
| Final risk register | **v0.28 implemented** | Unmitigated high/critical risk blocks modeled release gate |
| Technical reviewer sign-offs | **v0.28 implemented** | Exact v0.27 final-report binding + required technical scopes |
| External reproducible-build attestation | **v0.28 implemented** | Source/package/lock/SBOM/wheel/Go hashes + transitive review assertions |
| Launch-rehearsal aggregate gate | **v0.28 implemented** | Manual launch decision remains required |
| Independent-host public testnet | **Not yet evidenced** | Tooling exists; real sustained external operation still required |
| Independent security audit | **Not completed** | Review tooling does not equal completed independent review |
| Production mainnet | **Not launched** | No software gate automatically launches production |
| Production CRKBIT | **Not launched** | No official presale or production token contract |

## v0.28 Completed Code Work

- package/CLI advanced to `0.28.0a1`,
- signed launch runbook with at least four validators, genesis steps, explicit start order and rollback,
- hard-coded dry-run / no automatic DNS/network/fund mutation boundary,
- signed cutover rehearsal for DNS/RPC/explorer failover and rollback,
- configurable public-edge SLO/capacity/failover evidence,
- protected signer/HSM-equivalent rotation + catastrophic recovery drill evidence,
- signed coordinated upgrade/rollback rehearsal tied to the v0.27 upgrade plan,
- signed final unresolved-risk register with high/critical launch blockers,
- signed independent technical reviewer sign-offs bound to the exact v0.27 final report,
- required technical review scopes for consensus/application, network/RPC, cryptography/key-management and browser wallet,
- external reproducible-build/transitive-dependency attestation,
- aggregate v0.28 rehearsal gate,
- signed final release-candidate freeze for manual launch review only,
- signed human `hold` / `approve-launch-window` record with no automatic execution,
- v0.28 regression tests and documentation.

## Important v0.28 Boundary

A cryptographic signature proves which evidence key signed a statement and detects later tampering. It does not independently prove that a claimed VPS, provider control, HSM, outage test, capacity measurement or reviewer independence exists in the real world.

A passing `launch_rehearsal_gate_satisfied=true` therefore remains an evidence-model result, not a production launch. Every v0.28 final artifact deliberately keeps production readiness and launch claims false.

## External Gates Still Open

The following remain open until actually performed and independently corroborated:

- operate four or more independently managed validators across suitable operators/providers/regions,
- perform a genuine multi-operator genesis ceremony with separately held keys,
- complete genuine continuous 24h → 72h → 7-day or longer soak windows,
- execute real validator-governance, restart/process-kill/partition/latency/packet-loss/load/storage campaigns,
- complete real clean-host state-sync and backup/restore disaster-recovery drills,
- deploy and drill protected remote-signer/HSM-equivalent validator/governance custody,
- deploy production-style redundant RPC/explorer/gateway edges and measure real SLO/capacity/failover behavior,
- execute a real coordinated upgrade + rollback rehearsal on independent hosts,
- complete independent consensus/application/governance/network/cryptography/browser-wallet review,
- independently retest all high/critical fixes against the exact final candidate,
- complete independent reproducible-build/transitive supply-chain review,
- finalize and independently review production economics/validator incentives,
- complete applicable legal/regulatory review,
- make and execute a deliberate human launch/no-launch decision only after reviewing the real evidence.

## Immediate Blockchain Priorities — Real v0.29 Work

The next meaningful phase is **real infrastructure execution**, not another self-attestation-only layer:

1. Provision 4+ independent VPS validators and keep execution/ABCI/signer surfaces private.
2. Run the real multi-operator genesis ceremony and preserve signed public evidence.
3. Start 24h, then 72h, then 7-day monitoring/soak evidence.
4. Run authorized fault/state-sync/governance/upgrade/rollback campaigns on those hosts.
5. Deploy protected signer/HSM-equivalent custody and exercise rotation/recovery.
6. Deploy redundant public RPC/explorer/gateway edges and collect real v0.28 SLO/cutover evidence.
7. Commission independent technical review and import the real sign-offs/findings/retests.
8. Only then freeze the final release candidate and make a human launch/no-launch decision.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The repository contains test-only CRKBIT accounting for research/public-testnet work. The 21,000,000 maximum-supply and 8-decimal values remain development proposals unless intentionally frozen and independently reviewed through the v0.27 economics process.

See `blockchain/V0.28.md`, `blockchain/docs/MAINNET_GATES.md`, `ROADMAP.md` and GitHub Issue #1.
