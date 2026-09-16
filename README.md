# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent technology project building defensive-security tooling plus experimental blockchain infrastructure.

## Current status

- Security scanner / CLI: early alpha
- AI Security Assistant: in development
- Crakbit Chain package: **v0.33.0a1**
- Primary chain research direction: **native Proof of Work + UTXO**
- Active devnet PoW: **`crakpow-scrypt-v1`**
- P2P protocol: **`crakbit-p2p/1`**
- Fork choice: **highest cumulative valid work**
- Side chains / orphan handling / higher-work reorg: implemented in v0.32
- v0.33 multi-thread CPU solo/pool mining: implemented
- v0.33 hardened pool protocol: **`crakbit-pool/2`** with vardiff, stale/duplicate-share protection and optional TLS/auth
- Native RandomX `v1.1.8` adapter: implemented as an **optional candidate**, not active consensus
- XMRig `rx/0` candidate job/submit verification: implemented; live stock-XMRig pool compatibility is not claimed yet
- Previous CometBFT/BFT path: retained as legacy/research infrastructure
- Production mainnet: **not launched**
- Production CRKBIT: **not launched**
- Official CRKBIT presale: **none**

Do not use the current alpha to custody real value.

## Crakbit Chain v0.33 — mining hardening

v0.33 keeps the working scrypt devnet consensus stable while adding the tooling needed to evaluate a CPU-first RandomX future safely.

Implemented now:

- multi-thread CPU mining against node RPC,
- multi-thread first-party pool miner,
- per-worker vardiff,
- stale-work rejection,
- duplicate/replayed-share rejection,
- pool connection rate limits,
- optional pool TLS 1.2+ and token authorization,
- native ctypes binding to pinned upstream RandomX `v1.1.8`,
- RandomX light/full-dataset modes,
- official upstream self-test vector,
- deterministic candidate key schedule (`2048` interval / `64` delay),
- candidate hashing blob with the common XMRig RandomX nonce offset,
- XMRig `rx/0` candidate job construction and submitted-hash verification,
- deterministic v0.33 algorithm/interoperability vectors.

See [`blockchain/V0.33.md`](blockchain/V0.33.md).

## Quick test

```bash
git clone https://github.com/navindusasmitha/CrakbitAI.git
cd CrakbitAI/blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## PoW P2P devnet

The v0.32 node remains the active network node:

```bash
crakchain pow-p2p-key-v32-new --output private/node1-p2p.json
crakchain pow-network-v32-init --db runtime/node1/chain.sqlite3
crakchain pow-node-v32-run \
  --db runtime/node1/chain.sqlite3 \
  --network-key private/node1-p2p.json \
  --rpc-port 28443 \
  --p2p-port 28444
```

Mine it with multiple CPU threads:

```bash
crakchain pow-mine-v33-rpc \
  --node-url http://127.0.0.1:28443 \
  --miner-address crk1YOUR_ADDRESS \
  --threads 8 \
  --blocks 1
```

## Hardened pool

```bash
crakchain pow-pool-v33-run \
  --db runtime/pow-v33/pool.sqlite3 \
  --node-url http://127.0.0.1:28443 \
  --pool-address crk1POOL_ADDRESS \
  --host 0.0.0.0 \
  --port 3333
```

Multi-thread pool miner:

```bash
python scripts/run_pow_pool_miner_v33.py \
  --host 127.0.0.1 \
  --port 3333 \
  --address crk1MINER_ADDRESS \
  --worker cpu-01 \
  --threads 8
```

## RandomX candidate

The repository does not ship a prebuilt RandomX binary. Build the pinned upstream source and point Crakbit at the resulting shared library.

Windows helper:

```powershell
cd blockchain
.\scripts\build_randomx_v33.ps1
```

Then:

```powershell
crakchain pow-randomx-v33-info
crakchain pow-randomx-v33-selftest --mode light
crakchain pow-randomx-v33-benchmark --mode light --seconds 5
```

RandomX is **not activated in v0.33 consensus**. This avoids splitting the network before the hashing blob, target semantics, benchmarks, test vectors and activation rules have been reviewed.

## Important boundary

v0.33 is a multi-node PoW devnet alpha, not a production Bitcoin-equivalent network. Remaining work includes final PoW algorithm selection, efficient production reorg/undo storage, deeper P2P/DoS/eclipsing/fuzz testing, end-to-end stock XMRig/Stratum interoperability if RandomX is selected, mature on-chain pool payouts, long-running independent public testnet operation, independent node/wallet/pool reviews, final economics and applicable legal/regulatory review.

The previous CometBFT/BFT code is retained as legacy/research infrastructure and is not mixed with PoW consensus.

## Funding

Crakbit AI is raising development funding for security tooling, infrastructure, testing, documentation and staged blockchain research. The fundraising campaign is **not a CRKBIT token sale and does not promise investment returns**.

## Links

- Website: https://crakbit.space
- Repository: https://github.com/navindusasmitha/CrakbitAI
- Giveth: Crakbit AI is publicly listed on Giveth

## License

Unless otherwise noted, source code in this repository is released under the Apache License 2.0. See [`LICENSE`](LICENSE).
