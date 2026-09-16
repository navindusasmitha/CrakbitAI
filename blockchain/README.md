# Crakbit Chain — v0.33 PoW Mining-Hardening Alpha

**Current package:** `0.33.0a1`  
**Primary research consensus:** native Proof of Work  
**Active devnet PoW:** `crakpow-scrypt-v1`  
**RandomX candidate:** `crakpow-randomx-v1-candidate` — optional/native, not consensus-enabled  
**P2P:** `crakbit-p2p/1`  
**Pool:** `crakbit-pool/2`  
**Ledger:** UTXO  
**Fork choice:** highest cumulative valid work  
**Status:** multi-node PoW devnet alpha — **not production mainnet**.

Production CRKBIT has **not** launched. There is no official presale or production token contract. Do not use this software to custody real value.

## v0.33 scope

v0.32 remains the active P2P/fork-choice network layer. v0.33 hardens mining around it:

- multi-thread CPU solo mining over the existing node RPC,
- multi-thread native pool miner,
- `crakbit-pool/2` vardiff,
- stale-job rejection,
- duplicate/replayed-share rejection,
- connection message-rate limits,
- optional TLS 1.2+ pool transport,
- optional pool authorization token,
- pool stats,
- optional native RandomX `v1.1.8` ctypes adapter,
- RandomX light and fast/full-dataset modes,
- official upstream self-test vector,
- deterministic RandomX candidate key schedule,
- deterministic candidate blob using XMRig's common RandomX nonce offset,
- XMRig `rx/0` candidate job builder,
- native recomputation/verification of XMRig-style submits,
- deterministic candidate vector output,
- Windows pinned-source RandomX build helper,
- regression coverage with RandomX remaining optional in CI.

See [`V0.33.md`](V0.33.md).

## Install / test

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## Active network node

The v0.32 P2P node remains the active devnet node:

```bash
crakchain pow-p2p-key-v32-new --output private/node1-p2p.json
crakchain pow-network-v32-init --db runtime/node1/chain.sqlite3
crakchain pow-node-v32-run \
  --db runtime/node1/chain.sqlite3 \
  --network-key private/node1-p2p.json \
  --rpc-port 28443 \
  --p2p-port 28444
```

## v0.33 commands

```text
pow-randomx-v33-info
pow-randomx-v33-selftest
pow-randomx-v33-benchmark
pow-randomx-v33-key-height
pow-randomx-v33-vectors
pow-mine-v33-rpc
pow-pool-v33-run
pow-pool-v33-stats
pow-xmrig-v33-job
pow-xmrig-v33-verify-submit
```

All v0.32/v0.31 commands remain available through CLI delegation.

## Multi-thread CPU mining

```bash
crakchain pow-mine-v33-rpc \
  --node-url http://127.0.0.1:28443 \
  --miner-address crk1YOUR_ADDRESS \
  --threads 8 \
  --blocks 1
```

The node independently verifies the resulting block. The miner cannot bypass network target validation.

## Hardened pool

```bash
crakchain pow-pool-v33-run \
  --db runtime/pow-v33/pool.sqlite3 \
  --node-url http://127.0.0.1:28443 \
  --pool-address crk1POOL_ADDRESS \
  --host 0.0.0.0 \
  --port 3333 \
  --vardiff-target-seconds 15 \
  --stale-job-seconds 120
```

Native multi-thread miner:

```bash
python scripts/run_pow_pool_miner_v33.py \
  --host 127.0.0.1 \
  --port 3333 \
  --address crk1MINER_ADDRESS \
  --worker cpu-01 \
  --threads 8
```

For a public test pool, use TLS and external DDoS/reverse-proxy/monitoring controls. Do not commit pool TLS private keys or hot-wallet keys.

## RandomX candidate

Crakbit does not ship a RandomX binary. The candidate uses the official C API from a pinned upstream build.

Windows:

```powershell
.\scripts\build_randomx_v33.ps1
$env:CRAKBIT_RANDOMX_LIBRARY="C:\path\to\randomx.dll"
crakchain pow-randomx-v33-selftest --mode light
crakchain pow-randomx-v33-benchmark --mode light --seconds 5
```

The current consensus still uses scrypt. RandomX activation requires a separately reviewed/versioned consensus change so old and new nodes cannot disagree silently.

## XMRig boundary

v0.33 has a candidate `rx/0` job format and verifier matching key XMRig RandomX expectations: `job_id`, `blob`, `target`, `height`, `seed_hash`, and a four-byte nonce at offset 39.

This is **not yet a live stock-XMRig mining claim**. End-to-end XMRig support depends on final RandomX consensus/blob/target semantics and must be tested against an actual stock XMRig release before being advertised.

## Fork/reorg boundary

The v0.32 network already stores competing branches and activates a strictly higher-work replay-valid branch. It still uses full branch replay/state replacement rather than a production-optimized UTXO undo journal. Efficient reorg storage and deeper adversarial reorg testing remain open.

## Next priorities — v0.34

- decide whether RandomX remains the preferred production candidate after real CPU/GPU benchmarks,
- if selected, add explicit versioned RandomX consensus activation and fork tests,
- run stock XMRig end-to-end interoperability against the selected job format,
- add production-grade pool payout transactions after coinbase maturity,
- pool hot/cold key separation and payout limits,
- persistent peer reputation/address database + anti-eclipse controls,
- PoW explorer hashrate/difficulty/miner views,
- wallet confirmations/fee estimation/reorg awareness,
- larger fuzz/load/fork/reorg campaigns,
- long-running multi-host public PoW testnet.

## Monetary-policy boundary

Subsidy, halving and difficulty values remain configurable devnet parameters. The proposed `21,000,000 CRKBIT` and 8-decimal design are not final production economics until deliberately frozen and independently reviewed.
