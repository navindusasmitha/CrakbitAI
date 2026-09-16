# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.22 public-testnet review-candidate infrastructure alpha**

Crakbit AI has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and an experimental blockchain/application stack with browser wallet, public gateway, CometBFT integration, native ABCI state sync, validator governance, release/review evidence, migration rehearsal and governed multi-node campaign tooling.

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
| Crakbit Chain package | **v0.22.0a1** | Public-testnet/review-candidate infrastructure alpha |
| CometBFT candidate | **v0.40.0** | External BFT candidate used by the ABCI bridge |
| Governed external execution | **`crakbit-execution/3`** | Crash-safe staged FinalizeBlock → atomic Commit |
| Validator governance | **Implemented for testnet research** | Strict `>2/3` current voting-power join/remove/replace approvals |
| Governance application hash | **Implemented** | Active + pending validator state committed into app hash |
| ABCI validator updates | **Implemented in governed path** | Derived from replicated validated governance input |
| Governance activation model | **H → H+2** | Requires live multi-host evidence and independent review |
| App schema | **21** | v20 → v21 offline-copy migration + rollback rehearsal |
| Native ABCI state sync | **Governance-aware** | Live independent-host recovery evidence still required |
| Governed local lab | **v0.22 implemented** | 4–16 disposable validators; app/Comet identities aligned |
| Cluster divergence monitor | **v0.22 implemented** | Same-height app-hash + governance-state conflict detection |
| Governance history export | **v0.22 implemented** | Active/pending/history/emission read-only output |
| Signed campaign evidence | **v0.22 implemented** | Source/genesis/plan/observation hashes bound to signer |
| Browser wallet | Alpha implemented | Local Ed25519 signing + encrypted browser vault |
| Public gateway | Hardened alpha | Same-origin default, CSP/security headers, durable write limits |
| Explorer index | Prototype implemented | Dedicated public governance UX still pending |
| Review/release provenance | Implemented | Signed source/genesis/artifact binding |
| Independent-host public testnet | Not yet evidenced | Sustained external operation/results still required |
| Independent consensus/security audit | Not completed | Mandatory before production-value consideration |
| Production CRKBIT | **Not launched** | No official presale or production token contract |

## v0.22 Completed Code Work

- package/CLI advanced to `0.22.0a1`,
- one-command governed CometBFT local-lab generation,
- application-genesis validator identities derived from the disposable CometBFT lab validator public keys,
- disposable lab-only treasury and governance-signing views stored under `.secrets`,
- governed operator inventory with RPC/execution endpoints,
- cluster reachability/height/application-hash/governance convergence checks,
- same-height application-hash divergence detection,
- same-height validator-set/pending-governance divergence detection,
- governance history and validator-update emission export,
- `H`, `H+1`, `H+2` governance campaign plans,
- signed campaign evidence tied to exact source commit, genesis and artifact hashes,
- v0.22 regression tests and documentation.

## Important v0.22 Boundary

v0.22 provides **repeatable local testnet and evidence tooling**. It does not prove that a real four-validator campaign has been executed, that an independent VPS testnet has been stable, or that validator governance is production-safe.

The generated `.secrets/*DISPOSABLE*` governance key views intentionally mirror the local CometBFT validator identities so the governed lab can exercise the v0.21 authorization rule. They are not a production key-custody design and must never be reused for a public network.

## External Gates Still Open

The following remain open until actually performed and independently reviewable:

- execute real join/remove/replace campaigns on four running validators,
- restart/process-kill nodes at `H`, `H+1`, and `H+2`,
- run partition/latency/packet-loss/load tests during pending validator activation,
- state-sync clean hosts while governance state is pending and after activation,
- repeat the campaigns on independently managed VPS/providers,
- long-running 24h → 72h → 7-day public-testnet soak evidence,
- deployed and drilled remote-signer/HSM-equivalent validator/governance key custody,
- multi-operator genesis ceremony using independently held keys,
- independent browser-wallet, consensus/application, governance, cryptography/key-management and network security review,
- complete transitive SBOM and independent reproducible-build evidence,
- production multi-edge WAF/DDoS/capacity/TLS/secret-management engineering,
- finalized production economics/validator incentives,
- applicable legal/regulatory review for any future production-value asset.

## Immediate Blockchain Priorities — v0.23

1. Provision four or more independently managed VPS validators.
2. Deploy the governed v0.22/v0.21 execution path with private ABCI/execution/operator surfaces.
3. Deploy public RPC/gateway/explorer/faucet separately behind TLS and rate/DDoS controls.
4. Run 24-hour, 72-hour and 7-day soak windows with signed evidence.
5. Execute validator join/remove/replace activation campaigns.
6. Run clean-host state-sync and backup/disaster-recovery drills.
7. Run real restart/partition/latency/packet-loss/load campaigns.
8. Prepare a frozen independent-review candidate only after the evidence exists.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The repository contains test-only CRKBIT accounting for research/public-testnet work. The proposed development parameters of 21,000,000 maximum genesis units and 8 decimals are not final production economics and remain subject to technical, security, economic and applicable legal review.

See `blockchain/V0.22.md`, `blockchain/docs/MAINNET_GATES.md`, `ROADMAP.md` and GitHub Issue #1.
