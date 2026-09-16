# Crakbit AI — Project Status

**Last updated:** 2026-09-16

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.15 public-testnet infrastructure alpha**

Crakbit AI has a public website, a Giveth-listed fundraising project, an open GitHub repository, technical documentation, a deterministic security-scanner alpha and a runnable experimental blockchain stack with a browser wallet/public gateway and a CometBFT integration proof-of-concept.

None of these alpha components should be described as production-ready.

## Current Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| Public website | Active | Project information and funding positioning available |
| GitHub repository | Active | Documentation, scanner alpha and blockchain code published |
| Fundraising | Publicly listed on Giveth | GIVbacks verification/review is a separate process |
| AI Security Assistant | In development | MVP architecture/workflow definition |
| Secure Code Scanner | Early alpha | Initial deterministic rules and normalized findings implemented |
| Security CLI | Early alpha | `crak` command included with scanner package |
| Security API | Planned | To follow scanner core |
| Smart Contract Scanner | Planned | Blockchain-security phase |
| Crakbit Chain package | **v0.15 alpha** | Research/public-testnet infrastructure under `blockchain/` |
| Research Python consensus | Research only | Prevote/precommit/view-change prototype retained for local research |
| CometBFT integration | **v0.14+ PoC implemented** | Go ABCI bridge pinned to CometBFT `v0.40.0` |
| External execution protocol | **`crakbit-execution/2` prototype** | Persisted FinalizeBlock staging + atomic SQLite Commit |
| Signed genesis ceremony | **Prototype implemented** | Strict >2/3 configured validator attestations |
| Browser wallet/Web UI | **v0.15 alpha implemented** | Client-side Ed25519 signing and encrypted local vault |
| Public wallet gateway | **v0.15 alpha implemented** | Research and CometBFT backend modes |
| Test faucet | **Persistent v0.15 implementation** | SQLite address cooldown/distribution records |
| Mining Lab | **Test-reward prototype** | Browser proof-of-work reward; not consensus block mining |
| Snapshots/recovery/archives | Prototype implemented | Quorum snapshots, resumable recovery and verified research history tooling |
| Validator mTLS/pinning | Prototype/operator tooling | Research path transport hardening |
| Monitoring/limits | Prototype implemented | Prometheus/Grafana tooling and bounded node resources |
| Independent multi-host public testnet | Not completed | Sustained external-BFT operation/evidence still required |
| Independent consensus/network/wallet audit | Not completed | Required before production use |
| Production CRKBIT | **Not launched** | No official presale or production token contract |

## v0.15 User-Facing Additions

- responsive overview/wallet/explorer/validator Web UI,
- locally generated Ed25519 browser wallet,
- `crk1...` address compatibility,
- PBKDF2-SHA256 + AES-GCM encrypted browser vault,
- encrypted wallet backup/import,
- client-side canonical signed transfers,
- unified public gateway for research or CometBFT backends,
- CometBFT transaction broadcast path,
- external-state read APIs for accounts, transactions and commit history,
- persistent test faucet,
- opt-in SHA-256 proof-of-work Mining Lab with persistent server-side reward limits,
- explicit production mainnet release-gate checklist.

The Mining Lab does not decide blocks or mint new supply. Valid work is rewarded through an ordinary test CRKBIT transaction from a dedicated funded non-validator reward wallet.

## Immediate Security-Platform Priorities

1. Expand scanner unit tests and rule coverage.
2. Add structured configuration checks.
3. Reduce false positives and document rule behavior.
4. Build AI-assisted explanation/remediation on deterministic evidence.
5. Publish a simple public Security MVP demo.
6. Begin security API work after scanner core stabilizes.

## Immediate Blockchain Priorities — v0.16

1. Build a repeatable local 4-node CometBFT lab.
2. Complete external-consensus state-sync integration.
3. Add exhaustive FinalizeBlock/Commit/restart replay testing.
4. Deploy multiple independent testnet hosts and automate health/inventory checks.
5. Add a dedicated indexed external-consensus explorer database.
6. Run sustained partition, latency, packet-loss, restart and load campaigns.
7. Harden browser-wallet CSP/origin and publish wallet threat model.
8. Add remote-signer/HSM-equivalent validator key guidance.
9. Publish signed genesis/release/fault/soak evidence bundles.
10. Prepare independent consensus/application/network/wallet review.

## Production Mainnet Position

A Web UI, browser wallet, faucet, Mining Lab and CometBFT bridge do not by themselves make a production mainnet. The explicit production checklist is maintained in [`../blockchain/docs/MAINNET_GATES.md`](../blockchain/docs/MAINNET_GATES.md).

Key remaining gates include long-lived independent-host testing, external state sync, hardened Internet infrastructure, production key custody, indexed explorer/recovery systems, independent security review, incident-response readiness, and final economic/legal review.

## CRKBIT Status

**Production CRKBIT has not launched. There is no official CRKBIT presale or production token contract.**

The current chain code uses test-only CRKBIT units. The proposed 21,000,000 maximum genesis supply and 8-decimal setting are development parameters subject to technical, security, economic and legal review.

## Evidence and Transparency

Crakbit AI aims to distinguish clearly between completed work, active development, prototypes, public-testnet infrastructure, planned features and production systems. Testnet units and prototype features must not be presented as production assets or guaranteed future functionality.
