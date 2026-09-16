# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.21 public-testnet review-candidate infrastructure alpha**

Crakbit AI has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and an experimental blockchain/application stack with browser wallet, public gateway, CometBFT integration, native ABCI state sync, indexed explorer tooling, signed review/release evidence, upgrade-rehearsal tooling and deterministic validator-governance research code.

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
| Crakbit Chain package | **v0.21.0a1** | Public-testnet/review-candidate infrastructure alpha |
| Python research consensus | Research-only | Local experiments only; not intended production BFT path |
| CometBFT bridge | **v0.21 integration implemented** | Candidate dependency remains CometBFT `v0.40.0` |
| Governed external execution | **`crakbit-execution/3` implemented** | Crash-safe staged FinalizeBlock → atomic Commit |
| Validator governance | **v0.21 implemented for testnet research** | Quorum-approved join/remove/replace transaction path |
| Governance application hash | **Implemented** | Active + pending validator state committed into app hash |
| ABCI validator updates | **Code enabled in v0.21 path** | Derived from validated replicated governance transaction |
| Governance activation | **Implemented in application state** | Modeled emission at H, effective validator set at H+2 |
| App schema | **21** | Offline v20 → v21 copy migration + rollback rehearsal |
| Native ABCI state sync | **Governance-aware v0.21 code implemented** | Live independent-host recovery evidence still required |
| Browser wallet | Alpha implemented | Local Ed25519 signing + encrypted browser vault |
| Public gateway | Hardened alpha | Same-origin default, CSP/security headers, durable write limits |
| External explorer index | Prototype implemented | Governance-specific index UX still pending |
| Review/release provenance | Implemented | Signed source/genesis/artifact binding |
| Independent-host public testnet | Not yet evidenced | Sustained external operation/results still required |
| Independent consensus/security audit | Not completed | Mandatory before production-value consideration |
| Production CRKBIT | **Not launched** | No official presale or production token contract |

## v0.21 Completed Blockchain Work

- package/CLI advanced to `0.21.0a1`,
- `crakbit-execution/3` governed external execution path,
- canonical validator-governance change requests,
- strict `>2/3` current-validator voting-power approval verification,
- replicated active/pending validator lifecycle state,
- governance state included in deterministic application hash,
- Go ABCI bridge conversion of validated validator updates into CometBFT `ValidatorUpdate` values,
- crash/replay-safe validator update emission records,
- application-side modeled activation at `emit_height + 2`,
- schema 21 and offline v20 → v21 migration/rollback rehearsal,
- governance-aware external snapshots and native ABCI state sync,
- multi-operator build/sign/verify CLI flow,
- Python and Go regression tests,
- v0.21 technical documentation.

## Important v0.21 Boundary

The v0.21 implementation is a **controlled public-testnet research path**, not production governance. Code can derive a CometBFT validator update from a quorum-approved transaction in replicated state, but the project has not yet demonstrated independent multi-host join/remove/replace campaigns or completed an independent review of the activation semantics.

For a default four-validator/equal-power test network, strict `>2/3` approval requires 3 of 4 current validators. Operators should sign the same public request locally; validator private keys should not be collected on one machine.

## External Gates Still Open

The following remain open until actually performed and independently reviewable:

- multi-host validator join/remove/replace campaigns on independently managed hosts,
- restart/partition/state-sync tests at governance activation boundaries,
- long-running four-validator operation across independent providers,
- live clean-host CometBFT state-sync recovery with application-hash/governance-state convergence,
- real partition/packet-loss/latency/process-kill/sustained-load campaigns,
- deployed and drilled remote-signer/HSM-equivalent validator/governance key custody,
- multi-operator genesis ceremony using independently held keys,
- independent browser-wallet, consensus/application, governance and network security review,
- complete transitive SBOM and independent reproducible-build evidence,
- production multi-edge WAF/DDoS/capacity engineering,
- finalized production economics/validator incentives,
- applicable legal/regulatory review for any future production-value asset.

## Immediate Blockchain Priorities — v0.22

1. Build a one-command four-node governed CometBFT test lab/campaign runner.
2. Add controlled broadcast helpers for quorum-approved governance transactions.
3. Automate join/remove/replace validator campaigns and convergence checks.
4. Test restart/fault boundaries around `H`, `H+1`, and `H+2` activation.
5. Test native state-sync bootstrap while a validator change is pending.
6. Coordinate schema/protocol upgrade activation across the full test network.
7. Add explorer/index views for governance transactions and validator history.
8. Produce signed governance-campaign evidence with divergence detection.
9. Continue remote-signer/governance-key separation and review work.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The repository contains test-only CRKBIT accounting for research/public-testnet work. The proposed development parameters of 21,000,000 maximum genesis units and 8 decimals are not final production economics and remain subject to technical, security, economic and applicable legal review.

See `blockchain/V0.21.md`, `blockchain/docs/MAINNET_GATES.md`, `blockchain/docs/WALLET_THREAT_MODEL.md`, `blockchain/docs/VALIDATOR_REMOTE_SIGNER.md` and GitHub Issue #1.
