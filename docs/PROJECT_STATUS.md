# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.26 public-testnet independent-review-remediation tooling alpha**

Crakbit AI has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and an experimental blockchain/application stack with browser wallet, public gateway, CometBFT integration, native ABCI state sync, validator governance, public-testnet deployment/monitoring, operational fault/recovery evidence, review-freeze tooling and v0.26 remediation/retest/re-freeze controls.

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
| Crakbit Chain package | **v0.26.0a1** | Public-testnet / independent-review-remediation tooling alpha |
| CometBFT candidate | **v0.40.0** | External BFT candidate used by the ABCI bridge |
| Governed execution | **`crakbit-execution/3`** | Crash-safe staged FinalizeBlock → atomic Commit |
| Validator governance | Implemented for testnet research | Strict `>2/3` current voting-power join/remove/replace approvals |
| Governance activation model | **H → H+2** | Still requires real multi-host evidence and independent review |
| Native ABCI state sync | Governance-aware | Real independent-host recovery evidence still required |
| Public-testnet deployment layer | **v0.23 implemented** | 4+ validator inventory, genesis/deployment bundles, monitoring |
| Operational hardening | **v0.24 implemented** | Preflight, fault/recovery, redundancy, signer evidence, 24h/72h/7d gates |
| Independent-review freeze layer | **v0.25 implemented** | Signed host evidence, incident records and exact candidate freeze |
| Signed review findings | **v0.26 implemented** | Stable IDs + severity/component/affected-commit/remediation metadata |
| Independent retest records | **v0.26 implemented** | High/critical gate requires latest pass on exact candidate commit |
| Supply-chain attestation hook | **v0.26 implemented** | Candidate commit/package + lockfile/SBOM hashes + reproducibility checks |
| Public-edge evidence | **v0.26 implemented** | TLS/WAF/DDoS/load/failover evidence without provider secrets |
| Candidate supersession / re-freeze | **v0.26 implemented** | New signed immutable freeze after remediation/evidence changes |
| Browser wallet | Alpha implemented | Local Ed25519 signing + encrypted browser vault |
| Public gateway | Hardened alpha | Same-origin default, CSP/security headers, durable write limits |
| Independent-host public testnet | **Not yet evidenced** | Tooling exists; real sustained external operation still required |
| Independent security audit | **Not completed** | Review tooling does not equal a completed independent audit |
| Production CRKBIT | **Not launched** | No official presale or production token contract |

## v0.26 Completed Code Work

- package/CLI advanced to `0.26.0a1`,
- signed findings register with deterministic stable finding IDs,
- severity/component/title/affected-commit/reproduction metadata,
- remediation commit/config/regression-test binding,
- signed independent retest records,
- hard re-freeze blocker until every high/critical finding is remediated and the latest retest passes on the exact candidate commit,
- signed reproducible-build/supply-chain attestation hooks,
- dependency-lock + SBOM hash binding,
- signed public-edge TLS/WAF/DDoS/load/failover evidence format,
- minimum two passing public-edge attestations in the remediation gate,
- stale-candidate supersession reasons when source/package/CometBFT/genesis/dependency/review evidence changes,
- signed post-remediation review re-freeze,
- v0.26 regression tests and documentation.

## Important v0.26 Boundary

The v0.26 artifacts remain **signed evidence**, not independent proof of every real-world claim. A signature proves who signed a record and detects later tampering. It does not prove that an external reviewer is independent, that a provider/DDoS control exists, or that a load/recovery drill actually happened unless reviewers corroborate the underlying evidence.

A passing `refreeze_allowed=true` gate means the supplied evidence satisfies the modeled v0.26 rules. It does **not** set `production_mainnet_ready=true`, does not complete all independent-review scopes and does not launch CRKBIT.

## External Gates Still Open

The following remain open until actually performed and independently reviewable:

- provision and operate four or more independently managed validators across suitable operators/providers/regions,
- perform a real multi-operator genesis ceremony using independently held keys,
- run actual continuous 24h → 72h → 7-day soak windows,
- execute real validator join/remove/replace campaigns on independent hosts,
- execute authorized restart/process-kill/partition/latency/packet-loss/load/storage campaigns and preserve raw evidence,
- complete real clean-host state-sync and backup/restore disaster-recovery drills,
- deploy and drill protected remote-signer/HSM-equivalent validator/governance key custody,
- deploy production-style redundant RPC/explorer/gateway edges with independently reviewable TLS/WAF/DDoS/capacity evidence,
- complete independent consensus/application, governance, network/RPC, cryptography/key-management and browser-wallet review,
- independently retest every high/critical remediation against the final candidate,
- complete independent reproducible-build/transitive supply-chain review,
- finalize production economics/validator incentives and economic-security analysis,
- complete applicable legal/regulatory review for any future production-value asset.

## Immediate Blockchain Priorities — v0.27

1. Add explicit mainnet-candidate release policy that consumes only real v0.25/v0.26 evidence.
2. Add coordinated protocol/schema upgrade proposal + activation/rollback evidence across independent hosts.
3. Add governance emergency/cancel/timelock research artifacts without enabling unsafe emergency powers by default.
4. Add final genesis/economics parameter freeze format with independent economic-security review hooks.
5. Add multi-party release-signing / threshold-approval evidence rather than a single release signer.
6. Add complete transitive dependency inventory and external reproducible-build attestation import.
7. Add a final `mainnet-gate` report that remains false unless operational, security, economic and legal gates are all explicitly satisfied.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The repository contains test-only CRKBIT accounting for research/public-testnet work. The proposed development parameters of 21,000,000 maximum genesis units and 8 decimals are not final production economics and remain subject to technical, security, economic and applicable legal review.

See `blockchain/V0.26.md`, `blockchain/docs/MAINNET_GATES.md`, `ROADMAP.md` and GitHub Issue #1.
