# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.29 real independent-host execution/evidence alpha**

Crakbit AI has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and an experimental blockchain/application stack with browser wallet, public gateway, CometBFT integration, native ABCI state sync, validator governance, review/remediation controls, launch-rehearsal policy and a v0.29 live-host evidence path.

None of these alpha components should be described as a production mainnet or as safe for custody of real value.

## Current Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| Public website | Active | Project information and funding positioning available |
| GitHub repository | Active | Open documentation, scanner and blockchain research code |
| Fundraising | Publicly listed on Giveth | Campaign is not a CRKBIT token sale |
| AI Security Assistant | In development | Security MVP work remains active |
| Secure Code Scanner | Early alpha | Deterministic static-analysis rules implemented |
| Crakbit Chain package | **v0.29.0a1** | Real independent-host execution/evidence alpha |
| CometBFT candidate | **v0.40.0** | External BFT candidate used by the ABCI bridge |
| Governed execution | **`crakbit-execution/3`** | Crash-safe staged FinalizeBlock → atomic Commit |
| Validator governance | Implemented for testnet research | Strict `>2/3` current voting-power join/remove/replace approvals |
| Native ABCI state sync | Governance-aware | Real external recovery campaign still required |
| Final-candidate policy | v0.27 implemented | Upgrade/governance/economics/review/multi-party release gate |
| Launch rehearsal | v0.28 implemented | Runbook/cutover/SLO/signer/upgrade/risk/review/repro evidence |
| Live validator probing | **v0.29 implemented** | Reads CometBFT `/status` + `/abci_info` and signs observations |
| Live cluster gate | **v0.29 implemented** | 4+ validators/operators/signers + provider/region diversity + divergence detection |
| Genesis ceremony gate | **v0.29 implemented** | 4+ independently signed operator attestations for exact genesis |
| Long-lived soak gate | **v0.29 implemented** | Signed cluster samples; default seven-day target and >=0.99 success ratio |
| Fault/recovery gate | **v0.29 implemented** | Ten required campaign categories tied to raw evidence hashes |
| Real execution aggregate gate | **v0.29 implemented** | Exact v0.28 freeze/rehearsal binding + live/genesis/soak/fault evidence |
| Independent-host public testnet | **Not yet actually run here** | Tooling exists; real VPS operation/evidence still external |
| Independent security audit | **Not completed** | Review tooling does not equal completed independent review |
| Production mainnet | **Not launched** | No software gate automatically launches production |
| Production CRKBIT | **Not launched** | No official presale or production token contract |

## v0.29 Completed Code Work

- package/CLI advanced to `0.29.0a1`,
- live CometBFT RPC probe with credential-bearing endpoint rejection,
- signed host observations bound to source/candidate/genesis identity,
- cluster checks for unique validator/operator/evidence signers, provider/region diversity, height spread and same-height app-hash divergence,
- signed multi-operator genesis attestations + aggregate ceremony gate,
- signed soak evidence with default seven-day target and minimum 0.99 success threshold,
- signed fault/recovery evidence bound to raw evidence-file SHA-256,
- required restart/process-kill/partition/latency/packet-loss/load/storage/state-sync/governance/upgrade coverage,
- aggregate v0.29 real-execution gate bound to the exact v0.28 release freeze + rehearsal gate,
- signed v0.29 real-evidence freeze,
- v0.29 regression tests and documentation.

## Important v0.29 Boundary

v0.29 can perform real read-only RPC observations and verify signed evidence consistency, but repository code cannot independently prove organizational independence, provider ownership, physical HSM deployment, reviewer independence or that a seven-day campaign actually occurred unless those activities are genuinely performed and externally corroborated.

A passing `real_execution_gate_satisfied=true` still records:

```text
production_mainnet_ready=false
production_mainnet_launched=false
production_crkbit_launched=false
```

## External Gates Still Open

- provision and operate four or more independently managed validators on real hosts,
- perform the real multi-operator genesis ceremony with separately held keys,
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

## Immediate Blockchain Priorities — v0.30

The next phase should focus on **operator deployment automation and evidence collection**, not declaring mainnet ready:

1. Add non-secret Ansible/systemd inventory generation for real validator hosts.
2. Add continuous signed cluster-observation collector/rotation with resumable seven-day evidence.
3. Add archive/log bundle hashing and evidence-retention policy.
4. Add public RPC/explorer active health + failover collector.
5. Add validator remote-signer connectivity/rotation checks without reading private keys.
6. Add release-candidate publication bundle with hashes, SBOM, genesis, review summaries and operator runbooks.
7. Continue to keep production launch as a separate human decision.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The repository contains test-only CRKBIT accounting for research/public-testnet work. The 21,000,000 maximum-supply and 8-decimal values remain development proposals unless intentionally frozen and independently reviewed through the v0.27 economics process.

See `blockchain/V0.29.md`, `blockchain/docs/MAINNET_GATES.md`, `ROADMAP.md` and GitHub Issue #1.
