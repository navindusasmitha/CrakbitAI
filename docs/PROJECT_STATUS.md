# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.20 public-testnet review-candidate infrastructure alpha**

Crakbit AI has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and an experimental blockchain/application stack with browser wallet, public gateway, CometBFT integration, native ABCI state sync, indexed explorer tooling, signed review/release evidence and upgrade-rehearsal tooling.

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
| Crakbit Chain package | **v0.20.0a1** | Public-testnet/review-candidate infrastructure alpha |
| Python research consensus | Research-only | Local experiments only; not intended production BFT path |
| CometBFT bridge | Integration implemented | Candidate dependency remains CometBFT `v0.40.0` |
| External execution | Prototype implemented | Crash-safe staged FinalizeBlock → atomic Commit |
| Native ABCI state sync | Code implemented | Live independent-host recovery evidence still required |
| Browser wallet | Alpha implemented | Local Ed25519 signing + encrypted browser vault |
| Public gateway | Hardened alpha | Same-origin default, CSP/security headers, durable write limits |
| External explorer index | Prototype implemented | Dedicated commit/tx/address/account index |
| Review / release provenance | Implemented | Signed source/genesis/artifact binding |
| External app schema versioning | **v0.20 implemented** | v19 baseline → explicit schema 20 |
| Offline copy migration | **v0.20 implemented** | Source is not modified by migration command |
| Rollback verification | **v0.20 implemented** | Logical pre-upgrade fingerprint must be restored |
| Compatibility matrix | **v0.20 implemented** | Package/schema/CometBFT compatibility checks |
| Upgrade rehearsal | **v0.20 implemented** | Migration + rollback + integrity + genesis + compatibility checks |
| Signed migration evidence | **v0.20 implemented** | Rehearsal report/fingerprints tied to dedicated signer |
| Validator lifecycle drill plans | **v0.20 implemented** | Signed join/remove/replace plans; no live ABCI update emission |
| Live validator-set updates | **Not enabled** | Requires deterministic replicated authorization/application state |
| Independent-host public testnet | Not yet evidenced | Sustained external operation/results still required |
| Independent consensus/security audit | Not completed | Mandatory before production-value consideration |
| Production CRKBIT | **Not launched** | No official presale or production token contract |

## v0.20 Completed Blockchain Work

- package/CLI advanced to `0.20.0a1`,
- explicit external-application schema versioning,
- v19 → v20 offline-copy migration path,
- source-state logical fingerprint preservation checks,
- rollback verification on a disposable database copy,
- protocol/schema/CometBFT compatibility matrix,
- full offline upgrade rehearsal with SQLite integrity and genesis checks,
- signed migration/rollback evidence,
- signed validator join/remove/replace lifecycle drill plans,
- explicit CometBFT update emission/effective-height modeling,
- v0.20 regression tests and documentation.

## Important v0.20 Boundary

v0.20 does **not** apply operator-local validator plans to live CometBFT consensus. The plan format intentionally records `consensus_change_applied=false` and `live_abci_validator_updates_emitted=false`.

A live validator-set update must be derived from deterministic replicated application state. Otherwise two validators could return different `FinalizeBlock` responses. A future phase must design and review the replicated authorization/activation path before enabling live validator changes.

## External Gates Still Open

The following remain open until actually performed and independently reviewable:

- long-running four-validator operation across independently managed hosts/providers,
- live clean-host CometBFT state-sync recovery with application-hash convergence,
- real partition/packet-loss/latency/process-kill/sustained-load campaigns,
- deployed and drilled remote-signer/HSM-equivalent validator custody,
- multi-operator genesis ceremony using independently held keys,
- independent browser-wallet, consensus/application and network security review,
- complete transitive SBOM and independent reproducible-build evidence,
- reviewed deterministic live validator-set update mechanism,
- production multi-edge WAF/DDoS/capacity engineering,
- finalized production economics/validator incentives,
- applicable legal/regulatory review for any future production-value asset.

## Immediate Blockchain Priorities — v0.21

1. Define a deterministic replicated validator-change authorization object.
2. Commit pending lifecycle state into the application state machine.
3. Include lifecycle state in the application hash.
4. Emit ABCI validator updates only from committed replicated state.
5. Add activation-height replay/restart safety tests.
6. Run multi-node validator join/remove/replace lab drills.
7. Coordinate schema activation/rollback across a full testnet.
8. Continue remediation/regression work for any real independent-review findings.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The repository contains test-only CRKBIT accounting for research/public-testnet work. The proposed development parameters of 21,000,000 maximum genesis units and 8 decimals are not final production economics and remain subject to technical, security, economic and applicable legal review.

See `blockchain/V0.20.md`, `blockchain/docs/MAINNET_GATES.md`, `blockchain/docs/WALLET_THREAT_MODEL.md`, `blockchain/docs/VALIDATOR_REMOTE_SIGNER.md` and GitHub Issue #1.
