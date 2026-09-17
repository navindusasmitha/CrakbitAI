# Crakbit AI — Project Status

**Last updated:** 2026-09-17

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.37 Proof-of-Work public-testnet execution/review-preparation alpha**

Crakbit AI keeps two separated blockchain research tracks:

1. the earlier CometBFT/BFT validator stack, retained as legacy/research infrastructure;
2. the primary v0.31+ native Proof-of-Work UTXO path, now at v0.37 public-testnet execution and review-preparation tooling.

The PoW path is **not production mainnet** and must not be used for real-value custody.

## Current Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| Public website | Active | Project/funding information |
| GitHub repository | Active | Security + blockchain research code |
| Secure Code Scanner | Early alpha | Deterministic static-analysis rules |
| AI Security Assistant | In development | Security MVP work ongoing |
| Crakbit Chain package | **v0.37.0a1** | Public-testnet execution / review-hardening alpha |
| Active devnet PoW | **`crakpow-scrypt-v1`** | CPU-mineable; not production-frozen |
| RandomX | Candidate only | Native `v1.1.8` adapter; not consensus-enabled |
| Ledger | UTXO | Coinbase, fees, maturity, mempool |
| P2P | `crakbit-p2p/1` | Signed hello, peer discovery, gossip, forks/reorg |
| Pool | `crakbit-pool/2` | Vardiff, stale/duplicate protection, TLS/auth options |
| Multi-thread mining | Implemented | Solo + first-party pool miner |
| v0.34 operations | Implemented alpha | benchmark evidence, undo journal, peer book, stats, watch-only, mature payout planning |
| v0.35 public-testnet evidence gate | Implemented | host/convergence/soak/fault/diversity gate + review freeze |
| v0.36 campaign collector | Implemented | append-only signed observations and campaign summaries |
| v0.36 undo rehearsal | Implemented | disposable-copy rollback/fingerprint verification tooling |
| v0.36 peer integration | Implemented alpha | peer-book seed selection feeds node startup |
| v0.36 activation proposal | Implemented | signed proposal only; does not change consensus |
| v0.37 deployment evidence | Implemented | signed topology/runbooks plus declared diversity gates; does not provision hosts |
| v0.37 payout policy | Implemented | hot/cold addresses, caps, holds, confirmations and multi-operator approval evidence |
| v0.37 algorithm-review gate | Implemented | cross-binds signed benchmark/decision/handoff evidence; no automatic activation |
| v0.37 review candidate bundle | Implemented | internally cross-bound handoff artifact; does not mean independent review completed |
| Real 4+ independent public nodes | **Not yet evidenced** | Requires external operators/infrastructure |
| Long-lived 24h/72h/7d campaign | **Not yet evidenced** | Tooling exists; real elapsed operation still required |
| Real scrypt/RandomX cross-machine evidence | **Not yet collected** | Needed before algorithm decision |
| Independent security review | **Not completed** | Remains launch blocker |
| Production mainnet | **Not launched** | Alpha only |
| Production CRKBIT | **Not launched** | No official presale/token contract |

## v0.37 Completed Code Work

- package/CLI advanced to `0.37.0a1`,
- signed multi-host deployment plans with per-node runbooks,
- minimum node/operator/provider/region/network/miner diversity constraints,
- secret-like field and embedded RPC credential rejection,
- signed pool payout-policy evidence with public hot/cold addresses,
- payout caps, holds, confirmation depth and multi-operator approvals,
- final algorithm-review gate bound to the supplied benchmark gate, human decision and v0.36 handoff,
- RandomX path requiring the matching non-activating testnet proposal,
- public-testnet review candidate bundle cross-bound to v0.36 and v0.37 source evidence,
- correction of the cross-version source binding so the v0.36 handoff retains its own older commit,
- semantic verification of signed deployment and payout derived checks,
- CLI build/verify commands and v0.37 regression coverage,
- local full-suite result: 159 tests passed.

## Important Boundary

v0.37 can describe intended infrastructure and cross-bind review inputs, but it cannot create independent infrastructure, make time pass or prove reviewer independence. A 24h/72h/7d campaign is only satisfied after the real nodes have actually operated for that duration and the signed observations support it.

The incremental-undo path is still a rehearsal/verification path. The live canonical reorg engine is not being silently replaced until deeper fork/reorg testing and review are completed.

The active chain still uses `crakpow-scrypt-v1`. A signed `randomx` activation proposal is **not** an activation. RandomX would require a separate versioned consensus implementation, deterministic vectors, multi-node testing and review before any testnet activation.

## Immediate Priorities — remaining v0.37 external/integration work

1. Provision 4+ real independently managed PoW nodes across multiple providers/regions.
2. Run the v0.36 collector continuously and complete real 24h → 72h → 7d+ evidence.
3. Execute authorized restart/partition/reconnect/load/invalid-input/competing-fork campaigns and preserve signed evidence.
4. Collect real scrypt vs RandomX benchmark records on independent Windows/Linux hardware and make a human algorithm decision.
5. If RandomX is selected, implement a separately versioned testnet consensus path rather than relying on proposal metadata.
6. Exercise incremental undo under controlled reorgs before considering it for the live reorg engine.
7. Feed live peer health into persistent reputation/diversity logic and strengthen anti-eclipse controls.
8. Exercise the v0.37 payout policy in authorized testnet operations and verify reconciliation evidence without exposing private keys.
9. Expand explorer/wallet confirmation and reorg UX.
10. Populate the v0.37 review candidate bundle with actual public-testnet evidence and submit it for independent review.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The proposed 21,000,000 maximum supply and 8-decimal design remain proposals until deliberately finalized after technical, economic-security and applicable legal/regulatory review.

See `blockchain/V0.37.md`, `blockchain/README.md`, `ROADMAP.md` and GitHub Issue #1.
