# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.24 public-testnet operational-hardening/review-candidate infrastructure alpha**

Crakbit AI has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and an experimental blockchain/application stack with browser wallet, public gateway, CometBFT integration, native ABCI state sync, validator governance, release/review evidence, migration rehearsal, governed multi-node campaign tooling, public-testnet deployment/monitoring and v0.24 operational fault/recovery evidence tooling.

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
| Crakbit Chain package | **v0.24.0a1** | Public-testnet/operational-review-candidate alpha |
| CometBFT candidate | **v0.40.0** | External BFT candidate used by the ABCI bridge |
| Governed external execution | **`crakbit-execution/3`** | Crash-safe staged FinalizeBlock → atomic Commit |
| Validator governance | **Implemented for testnet research** | Strict `>2/3` current voting-power join/remove/replace approvals |
| Governance application hash | **Implemented** | Active + pending validator state committed into app hash |
| ABCI validator updates | **Implemented in governed path** | Derived from replicated validated governance input |
| Governance activation model | **H → H+2** | Requires live multi-host evidence and independent review |
| App schema | **21** | v20 → v21 offline-copy migration + rollback rehearsal |
| Native ABCI state sync | **Governance-aware** | Live independent-host recovery evidence still required |
| Public-testnet operator inventory | **v0.23 implemented** | 4+ validators + operator/provider/region diversity gates |
| Shared genesis/deployment bundles | **v0.23 implemented** | Non-secret application/CometBFT/operator artifacts |
| Independent-node monitor | **v0.23 implemented** | Height/app-hash convergence + long-running JSONL observations |
| Host/deployment preflight | **v0.24 implemented** | Exact package/CometBFT/genesis identity, private binds, token presence, disk checks |
| Fault campaign evidence | **v0.24 implemented** | Restart/process-kill/partition/latency/packet-loss/load/storage plan/result formats |
| Recovery evidence | **v0.24 implemented** | Backup/restore + clean-host state-sync convergence records |
| RPC/explorer redundancy | **v0.24 implemented** | Requires 2+ endpoints and rejects same-height app-hash conflicts |
| Remote signer evidence | **v0.24 implemented** | No-key-export, double-sign protection, recovery/failover/private endpoint gates |
| Long-soak gates | **v0.24 implemented** | Separate actual-duration 24h, 72h and 7-day gates |
| Signed operations evidence | **v0.24 implemented** | Exact Git commit and SHA-256 artifact binding |
| Browser wallet | Alpha implemented | Local Ed25519 signing + encrypted browser vault |
| Public gateway | Hardened alpha | Same-origin default, CSP/security headers, durable write limits |
| Explorer index | Prototype implemented | Dedicated public governance UX still pending |
| Review/release provenance | Implemented | Signed source/genesis/artifact binding |
| Independent-host public testnet | **Not yet evidenced** | Tooling exists; real sustained external operation still required |
| Independent consensus/security audit | Not completed | Mandatory before production-value consideration |
| Production CRKBIT | **Not launched** | No official presale or production token contract |

## v0.24 Completed Code Work

- package/CLI advanced to `0.24.0a1`,
- operator-safe host preflight with exact package/CometBFT/application-genesis/consensus-genesis checks,
- loopback execution/ABCI bind checks,
- execution-token presence check that does not read or emit the secret,
- writable-data-directory and minimum-free-space gates,
- typed dry-run-by-default fault plans for restart/process-kill/partition/latency/packet-loss/load/storage,
- mandatory recovery command for every planned fault,
- normalized evidence for explicitly executed fault campaigns,
- backup/restore and clean-host state-sync convergence records,
- remote-signer/HSM-style drill records without private-key material,
- redundant RPC/explorer health + same-height application-hash consistency checks,
- separate 24-hour, 72-hour and 7-day soak readiness gates,
- aggregate operational-review-candidate readiness report,
- signed v0.24 operations evidence tied to exact source commit/artifact hashes,
- v0.24 regression tests and documentation.

## Important v0.24 Boundary

v0.24 supplies machinery to **collect and verify operator-generated operational evidence**. It does not prove that any VPS validator has been deployed, that a fault campaign has actually run, that a 24h/72h/7-day soak has elapsed, that a protected HSM/remote signer is deployed, or that an independent security review has completed.

`operational_review_candidate` can only become true when the modeled operator evidence is supplied and passes. Even then, the v0.24 readiness artifact deliberately keeps `independent_security_review_completed=false`, `production_mainnet_ready=false` and `production_crkbit_launched=false`.

## External Gates Still Open

The following remain open until actually performed and independently reviewable:

- provision and operate four or more independently managed validators across suitable operators/providers/regions,
- perform a real multi-operator genesis ceremony using independently held keys,
- run actual 24h → 72h → 7-day soak windows,
- execute real validator join/remove/replace campaigns on independent hosts,
- run restart/process-kill/partition/latency/packet-loss/load/storage campaigns and preserve raw evidence,
- state-sync clean hosts and complete backup/restore disaster-recovery drills,
- deploy and drill remote-signer/HSM-equivalent validator/governance key custody,
- deploy production-style redundant RPC/explorer edges with TLS/WAF/DDoS/capacity controls,
- independently review browser wallet, consensus/application, governance, cryptography/key management and network security,
- complete transitive SBOM and independent reproducible-build evidence,
- finalize production economics/validator incentives,
- complete applicable legal/regulatory review for any future production-value asset.

## Immediate Blockchain Priorities — v0.25

1. Use the v0.23/v0.24 tooling on four or more real independently managed VPS validators.
2. Perform the real multi-operator genesis ceremony and publish hashes/attestations without private keys.
3. Run real 24h, 72h and 7-day soak windows.
4. Execute real authorized restart/process-kill/partition/latency/packet-loss/load/storage campaigns.
5. Execute clean-host state-sync and backup/restore disaster-recovery drills.
6. Deploy/drill protected remote signer or HSM-equivalent custody.
7. Put redundant public RPC/explorer/gateway infrastructure behind production-style TLS/WAF/DDoS controls.
8. Sign and publish the resulting evidence, then freeze an independent-review candidate.
9. Commission independent consensus/application/governance/network/cryptography/browser-wallet review and remediate findings before any production-mainnet consideration.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The repository contains test-only CRKBIT accounting for research/public-testnet work. The proposed development parameters of 21,000,000 maximum genesis units and 8 decimals are not final production economics and remain subject to technical, security, economic and applicable legal review.

See `blockchain/V0.24.md`, `blockchain/docs/MAINNET_GATES.md`, `ROADMAP.md` and GitHub Issue #1.
