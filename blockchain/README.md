# Crakbit Chain — v0.31 Native Proof-of-Work Alpha

**Current package:** `0.31.0a1`  
**Primary research consensus path:** native Proof of Work  
**Working v0.31 algorithm:** `crakpow-scrypt-v1`  
**Ledger:** UTXO  
**Status:** CPU-mineable devnet alpha — **not production mainnet**.

Production CRKBIT has **not** launched. There is no official presale or production token contract. Do not use this software to custody real value.

## v0.31 scope

v0.31 is a major consensus pivot. Instead of treating CometBFT validator consensus as mining, the repository now contains a separate native PoW path in which miners build and solve block templates.

Implemented:

- deterministic PoW genesis,
- Bitcoin-style UTXO state,
- Ed25519 `crk1...` transaction ownership,
- signed transfers + fees,
- mempool double-spend protection,
- coinbase subsidy + maturity,
- Merkle roots,
- memory-hard scrypt PoW,
- explicit 256-bit network targets,
- bounded automatic difficulty retargeting,
- cumulative work tracking,
- persistent SQLite chain/UTXO/mempool state,
- CPU solo mining,
- FastAPI node RPC,
- first-party mining-pool protocol,
- pool share difficulty separated from network difficulty,
- PPLNS test accounting,
- native CPU pool-miner script,
- v0.31 regression tests.

See [`V0.31.md`](V0.31.md).

## Install / test

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## v0.31 PoW commands

```text
pow-wallet-v31-new
pow-chain-v31-init
pow-chain-v31-info
pow-balance-v31
pow-template-v31
pow-mine-v31
pow-send-v31
pow-submit-tx-v31
pow-node-v31-run
pow-pool-v31-run
pow-pool-v31-balances
```

All v0.30 and earlier tooling remains available through CLI delegation.

## Basic solo-mining flow

```bash
crakchain pow-wallet-v31-new --output private/miner.json
crakchain pow-chain-v31-init --db runtime/pow-v31/chain.sqlite3
crakchain pow-mine-v31 --db runtime/pow-v31/chain.sqlite3 --miner-address crk1YOUR_ADDRESS --blocks 1
crakchain pow-chain-v31-info --db runtime/pow-v31/chain.sqlite3
```

The miner iterates the block nonce and the node independently verifies the target before accepting the block.

## Node RPC

```bash
crakchain pow-node-v31-run --db runtime/pow-v31/chain.sqlite3 --host 127.0.0.1 --port 28443
```

Endpoints:

```text
GET  /pow/v1/health
GET  /pow/v1/info
GET  /pow/v1/block/{height}
GET  /pow/v1/balance/{address}
GET  /pow/v1/utxos/{address}
GET  /pow/v1/mempool
POST /pow/v1/getblocktemplate
POST /pow/v1/submitblock
POST /pow/v1/submittransaction
```

## First-party pool

```bash
crakchain pow-pool-v31-run \
  --db runtime/pow-v31/pool.sqlite3 \
  --node-url http://127.0.0.1:28443 \
  --pool-address crk1POOL_ADDRESS \
  --host 127.0.0.1 \
  --port 3333
```

Native CPU miner:

```bash
python scripts/run_pow_pool_miner_v31.py \
  --host 127.0.0.1 \
  --port 3333 \
  --address crk1MINER_ADDRESS \
  --worker cpu-01
```

The pool uses `crakbit-pool/1`, a JSON-line protocol for subscribe/authorize/job/share submission. It is not yet XMRig/RandomX Stratum compatible. PPLNS balances are test accounting only and automatic on-chain payout is disabled.

## PoW algorithm boundary

v0.31 uses Python's built-in memory-hard scrypt primitive so the project has a real, testable CPU mining path now. The final production algorithm is not frozen. RandomX remains a candidate for a later native integration/benchmark/review phase.

## Current decentralization boundary

The v0.31 SQLite node tracks cumulative work but currently accepts only blocks that extend its current tip. Full P2P discovery/gossip, side chains, competing-fork storage and highest-cumulative-work reorganization are still required before this can be called a decentralized Bitcoin-like production network.

The previous CometBFT/BFT code is retained as legacy/research infrastructure and is not combined with PoW consensus.

## Next PoW priorities

- P2P node protocol + peer discovery,
- header-first sync,
- block/transaction gossip,
- side-chain storage + UTXO undo data,
- highest-chainwork reorgs,
- orphan/fork handling,
- stronger time/mempool/fee rules,
- native optimized multi-core miner,
- RandomX adapter and performance/security comparison,
- final Stratum/XMRig compatibility,
- vardiff + anti-abuse pool hardening,
- on-chain PPLNS payout construction,
- PoW explorer/hashrate/difficulty views,
- long-running multi-node public PoW testnet.

## Monetary-policy boundary

Subsidy, halving and difficulty values are configurable devnet parameters. The proposed `21,000,000 CRKBIT` and 8-decimal design are not final production economics until deliberately frozen and independently reviewed.
