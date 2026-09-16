# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.23 public-testnet operations/review-candidate infrastructure alpha**

Crakbit AI has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and an experimental blockchain/application stack with browser wallet, public gateway, CometBFT integration, native ABCI state sync, validator governance, release/review evidence, migration rehearsal, governed multi-node campaign tooling and public-testnet deployment/monitoring/evidence tooling.

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
| Crakbit Chain package | **v0.23.0a1** | Public-testnet/review-candidate infrastructure alpha |
| CometBFT candidate | **v0.40.0** | External BFT candidate used by the ABCI bridge |
| Governed external execution | **`crakbit-execution/3`** | Crash-safe staged FinalizeBlock → atomic Commit |
| Validator governance | **Implemented for testnet research** | Strict `>2/3` current voting-power join/remove/replace approvals |
| Governance application hash | **Implemented** | Active + pending validator state committed into app hash |
| ABCI validator updates | **Implemented in governed path** | Derived from replicated validated governance input |
| Governance activation model | **H → H+2** | Requires live multi-host evidence and independent review |
| App schema | **21** | v20 → v21 offline-copy migration + rollback rehearsal |
| Native ABCI state sync | **Governance-aware** | Live independent-host recovery evidence still required |
| Governed local lab | **v0.22 implemented** | 4–16 disposable validators; app/Comet identities aligned |
| Public validator identity export | **v0.23 implemented** | Public metadata only; secret fields rejected |
| Public-testnet inventory | **v0.23 implemented** | 4+ validators + operator/provider/region diversity gates |
| Shared genesis bundle | **v0.23 implemented** | Application + CometBFT genesis with SHA-256 manifest |
| Operator deployment bundle | **v0.23 implemented** | Non-secret per-validator systemd/persistent-peer bundle |
| Independent-node monitor | **v0.23 implemented** | `/status` + `/abci_info`, height/app-hash convergence checks |
| Soak evidence | **v0.23 implemented** | JSONL collection + 24h gate semantics |
| Public-testnet readiness report | **v0.23 implemented** | Distinguishes testnet candidate from production readiness |
| Signed operations evidence | **v0.23 implemented** | Git commit/inventory/readiness/artifact hashes bound to signer |
| Browser wallet | Alpha implemented | Local Ed25519 signing + encrypted browser vault |
| Public gateway | Hardened alpha | Same-origin default, CSP/security headers, durable write limits |
| Explorer index | Prototype implemented | Dedicated public governance UX still pending |
| Review/release provenance | Implemented | Signed source/genesis/artifact binding |
| Independent-host public testnet | **Not yet evidenced** | Tooling exists; real sustained external operation still required |
| Independent consensus/security audit | Not completed | Mandatory before production-value consideration |
| Production CRKBIT | **Not launched** | No official presale or production token contract |

## v0.23 Completed Code Work

- package/CLI advanced to `0.23.0a1`,
- public-only validator identity exporter,
- public metadata validation with secret/private-field rejection,
- 4+ validator public-testnet inventory format,
- independent-operator/provider/region diversity checks,
- shared application/CometBFT genesis generation,
- SHA-256 genesis bundle manifest,
- non-secret operator deployment bundles,
- systemd service templates and persistent-peer artifacts,
- independent-node CometBFT status/ABCI monitoring,
- same-height application-hash divergence detection,
- JSONL soak collector and summary,
- 24-hour minimum soak gate semantics,
- public-testnet readiness report,
- signed operations evidence bound to exact source commit/artifact hashes,
- v0.23 regression tests and documentation.

## Important v0.23 Boundary

v0.23 provides tooling to **deploy and measure** an independent public testnet. It does not prove that four independent VPS validators have been deployed, that a multi-operator genesis ceremony has happened, that a 24-hour/72-hour/7-day soak has actually run, or that independent security review has been completed.

Operator bundles intentionally contain no validator private keys and no execution tokens. Each operator must control and protect their own validator key and generate local execution credentials. Production-candidate operations still require a reviewed protected remote-signer/HSM-equivalent custody model.

## External Gates Still Open

The following remain open until actually performed and independently reviewable:

- provision and operate four or more independently managed validators,
- perform a real multi-operator genesis ceremony using independently held keys,
- run actual 24h → 72h → 7-day soak windows,
- execute real validator join/remove/replace campaigns on independent hosts,
- restart/process-kill nodes at governance activation boundaries,
- run partition/latency/packet-loss/load/storage-fault tests,
- state-sync clean hosts while governance state is pending and after activation,
- complete backup/restore and disaster-recovery drills,
- deploy and drill remote-signer/HSM-equivalent validator/governance key custody,
- independently review browser wallet, consensus/application, governance, cryptography/key management and network security,
- complete transitive SBOM and independent reproducible-build evidence,
- production multi-edge WAF/DDoS/capacity/TLS/secret-management engineering,
- finalize production economics/validator incentives,
- applicable legal/regulatory review for any future production-value asset.

## Immediate Blockchain Priorities — v0.24

1. Add operator-safe host/deployment preflight validation.
2. Add automated clean-host state-sync and backup/restore drill tooling.
3. Add signed restart/partition/latency/packet-loss/load/storage-fault campaign records.
4. Run governance campaigns across real independent hosts once those hosts exist.
5. Add public RPC/explorer redundancy and recovery verification.
6. Add alert/incident evidence and operator escalation records.
7. Add explicit 72-hour and 7-day readiness gates.
8. Produce a frozen independent-review candidate only after real evidence exists.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The repository contains test-only CRKBIT accounting for research/public-testnet work. The proposed development parameters of 21,000,000 maximum genesis units and 8 decimals are not final production economics and remain subject to technical, security, economic and applicable legal review.

See `blockchain/V0.23.md`, `blockchain/docs/MAINNET_GATES.md`, `ROADMAP.md` and GitHub Issue #1.
