# Crakbit AI — Project Status

**Last updated:** 2026-09-17

## Current Stage

**Early development / Security MVP alpha + Crakbit Chain v0.35 public Proof-of-Work testnet evidence alpha**

Crakbit AI keeps two separated blockchain research tracks:

1. the earlier CometBFT/BFT validator stack, retained as legacy/research infrastructure;
2. the primary v0.31+ native Proof-of-Work UTXO path, now at v0.35 public-testnet evidence tooling.

The PoW path is **not production mainnet** and must not be used for real-value custody.

## Current Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| Public website | Active | Project/funding information |
| GitHub repository | Active | Security + blockchain research code |
| Secure Code Scanner | Early alpha | Deterministic static-analysis rules |
| AI Security Assistant | In development | Security MVP work ongoing |
| Crakbit Chain package | **v0.35.0a1** | Public PoW testnet evidence alpha |
| Active devnet PoW | **`crakpow-scrypt-v1`** | CPU-mineable; not production-frozen |
| RandomX | Candidate only | Native `v1.1.8` adapter; not consensus-enabled |
| Ledger | UTXO | Coinbase, fees, maturity, mempool |
| P2P | `crakbit-p2p/1` | Signed hello, peer discovery, gossip, forks/reorg |
| Pool | `crakbit-pool/2` | Vardiff, stale/duplicate protection, TLS/auth options |
| Multi-thread mining | Implemented | Solo + first-party pool miner |
| v0.34 operations | Implemented alpha | benchmark evidence, undo journal, peer book, stats, watch-only, mature payout planning |
| v0.35 host attestations | Implemented | signed operator/node/provider/region/source/genesis binding |
| v0.35 convergence probe | Implemented | `/pow/v2/info` + `/pow/v2/peers`, same-height conflict detection |
| v0.35 soak gates | Implemented | actual 24h / 72h / 7d elapsed-duration checks |
| v0.35 fault gate | Implemented | restart/partition/reconnect/invalid block/invalid tx/load evidence format |
| v0.35 public-testnet gate | Implemented | 4+ hosts, unique operators/signers, provider/region/miner diversity |
| v0.35 review freeze | Implemented | exact gated source/package/chain/genesis binding |
| Real 4+ independent public nodes | **Not yet evidenced** | Requires external operators/infrastructure |
| Long-lived 24h/72h/7d campaign | **Not yet evidenced** | Tooling exists; real elapsed operation still required |
| Independent security review | **Not completed** | Remains launch blocker |
| Production mainnet | **Not launched** | Alpha only |
| Production CRKBIT | **Not launched** | No official presale/token contract |

## v0.34 Completed Work

- signed scrypt/RandomX benchmark records and benchmark gate,
- explicit human `hold/scrypt/randomx` decision record with no automatic consensus activation,
- canonical UTXO undo-journal backfill/verification,
- persistent peer reputation/address book with coarse diversity selection,
- PoW stats, confirmations and fee-estimate helpers,
- watch-only records,
- mature coinbase-aware PPLNS payout transaction planning,
- confirmation-depth payout reconciliation.

## v0.35 Completed Code Work

- package/CLI advanced to `0.35.0a1`,
- signed host/operator attestations,
- exact Git SHA/package/chain/genesis binding,
- live public-node probe,
- 4+ node convergence checks,
- same-height tip conflict detection,
- actual-duration 24h/72h/7d soak summaries,
- required authorized fault/recovery campaign format,
- higher-work reorg and post-partition convergence evidence fields,
- unique operator/node/evidence-signer checks,
- provider/region diversity checks,
- multiple-miner-operator requirement,
- signed public-testnet gate,
- signed public-testnet review freeze,
- regression coverage including signer-reuse rejection,
- production/mainnet/review claims forced false in freeze artifacts.

## Important Boundary

The v0.35 software can verify evidence formats and observed node state, but it cannot independently prove that an operator/provider/region claim is true. Host attestations remain operator self-attestations. Real 4+ independently managed hosts, real miners/pools, real sustained operation, real authorized partitions/restarts/load, and independent review must still happen outside the repository.

The active chain still uses `crakpow-scrypt-v1`. RandomX remains a candidate and is not silently activated.

## Immediate Priorities — v0.36 target

1. Provision and operate 4+ real independently managed PoW nodes across multiple providers/regions.
2. Collect signed v0.35 host attestations and live convergence samples.
3. Complete real 24h → 72h → 7d+ campaigns.
4. Run authorized restart/partition/reconnect/load/invalid-input/reorg campaigns and preserve evidence.
5. Collect real scrypt vs RandomX benchmark records on independent hardware and make a human algorithm decision.
6. If RandomX is selected, implement a separate versioned consensus activation with deterministic vectors and multi-node fork tests.
7. Integrate the v0.34 peer book and undo journal into live node operation only after regression/property testing.
8. Complete independent consensus/network/wallet/pool review and remediation before any mainnet consideration.

## CRKBIT Status

Production CRKBIT has **not** launched. There is no official presale and no production token contract.

The proposed 21,000,000 maximum supply and 8-decimal design remain proposals until deliberately finalized after technical, economic-security and applicable legal/regulatory review.

See `blockchain/V0.35.md`, `blockchain/README.md`, `ROADMAP.md` and GitHub Issue #1.
