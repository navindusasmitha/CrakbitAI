# Crakbit Chain — v0.35 Public PoW Testnet Evidence Alpha

**Current package:** `0.35.0a1`  
**Primary research consensus:** native Proof of Work  
**Active devnet PoW:** `crakpow-scrypt-v1`  
**RandomX:** optional candidate; not consensus-enabled  
**P2P:** `crakbit-p2p/1`  
**Pool:** `crakbit-pool/2`  
**Ledger:** UTXO  
**Fork choice:** highest cumulative valid work  
**Status:** public-testnet evidence alpha — **not production mainnet**.

Production CRKBIT has not launched. There is no official presale or production token contract. Do not use this alpha to custody real value.

## What v0.35 adds

v0.35 builds on the working PoW network/mining stack and adds the evidence layer needed for a real multi-operator public testnet:

- signed operator/host attestations,
- exact source commit / package / chain / genesis binding,
- public `/pow/v2` node probes,
- 4+ node convergence checking,
- same-height tip-conflict detection,
- actual 24h / 72h / 7d soak-duration gates,
- restart/partition/reconnect/invalid-block/invalid-tx/load campaign records,
- higher-work reorg + post-partition convergence evidence fields,
- unique node/operator/evidence-signer checks,
- provider/region diversity checks,
- multiple miner-operator requirement,
- signed public-testnet gate,
- signed review freeze,
- regression tests including signer-reuse rejection.

See [`V0.35.md`](V0.35.md).

## Install / test

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## v0.35 commands

```text
pow-host-v35-attest
pow-host-v35-verify
pow-node-v35-probe
pow-convergence-v35-check
pow-soak-v35-summarize
pow-fault-v35-record
pow-testnet-gate-v35-build
pow-testnet-gate-v35-verify
pow-testnet-freeze-v35-build
pow-testnet-freeze-v35-verify
```

All earlier v0.34/v0.33/v0.32/v0.31 commands remain available through CLI delegation.

## Public-testnet flow

1. Provision 4+ independently managed nodes on multiple providers/regions.
2. Give each operator a dedicated evidence-signing key separate from wallet/mining/P2P keys.
3. Create one host attestation per operator.
4. Probe all nodes and check convergence.
5. Collect periodic samples until 24h, then 72h, then 7d+ duration gates are actually satisfied.
6. Run authorized restart/partition/reconnect/load/invalid-input/reorg campaigns.
7. Build the signed public-testnet gate.
8. Freeze the exact gated source/package/chain/genesis candidate for independent review.

The software cannot fake elapsed time or independent infrastructure. Host/provider/region statements remain self-attested until independently verified.

## v0.34 operations already available

- signed scrypt/RandomX benchmark records + multi-machine gate,
- explicit human algorithm decision with no auto-activation,
- UTXO undo-journal backfill/verification,
- persistent peer reputation/address book,
- difficulty/hashrate/miner stats,
- confirmations + fee-estimate helpers,
- watch-only records,
- mature coinbase-aware PPLNS payout planning and confirmation-depth reconciliation.

## Consensus / RandomX boundary

The active chain still uses `crakpow-scrypt-v1`. RandomX remains a real native candidate but is not activated. A future RandomX decision must be based on real benchmark evidence and followed by a separate versioned consensus change with deterministic vectors and multi-node fork/reorg testing.

## Reorg boundary

The live v0.32 reorg engine still performs full candidate replay/state replacement. v0.34 added verified undo metadata, but incremental disconnect/connect reorg mechanics are not active yet.

## External work still required

- 4+ real independently managed public nodes,
- multiple independent miners/pools,
- real 24h → 72h → 7d+ operation,
- real authorized partition/restart/reorg/load campaigns,
- real cross-machine algorithm benchmarks,
- independent consensus/network/wallet/pool review,
- high/critical remediation/retest,
- final economics and applicable legal/regulatory review.

## Monetary-policy boundary

Subsidy, halving and difficulty values remain configurable devnet parameters. The proposed `21,000,000 CRKBIT` and 8-decimal design are not final production economics until deliberately frozen and independently reviewed.
