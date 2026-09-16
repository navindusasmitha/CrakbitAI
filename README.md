# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent technology project building defensive-security tooling plus experimental blockchain infrastructure.

## Current status

- Security scanner / CLI: early alpha
- AI Security Assistant: in development
- Crakbit Chain package: **v0.31.0a1**
- New primary chain research direction: **native Proof of Work + UTXO**
- Working v0.31 PoW: **`crakpow-scrypt-v1` CPU-mineable devnet**
- First-party solo miner + mining-pool prototype: implemented
- Previous CometBFT/BFT path: retained as legacy/research infrastructure
- Production mainnet: **not launched**
- Production CRKBIT: **not launched**
- Official CRKBIT presale: **none**

Do not use the current alpha to custody real value.

## Crakbit Chain v0.31 — PoW pivot

v0.31 introduces an actual proof-of-work block-production path instead of pretending the previous validator-based CometBFT path is Bitcoin-like mining.

Implemented now:

- deterministic PoW genesis,
- Bitcoin-style UTXO accounting,
- Ed25519 `crk1...` ownership/signatures,
- signed transfers + transaction fees,
- mempool double-spend policy,
- coinbase block rewards + maturity,
- Merkle roots,
- memory-hard scrypt PoW,
- 256-bit targets + bounded difficulty retargeting,
- cumulative chain-work accounting,
- CPU solo mining,
- SQLite persistent chain/UTXO/mempool state,
- FastAPI node RPC (`getblocktemplate`, `submitblock`, transaction/balance/block endpoints),
- first-party `crakbit-pool/1` mining-pool protocol,
- pool share difficulty separated from network target,
- test PPLNS accounting,
- native CPU pool-miner script.

The production PoW algorithm is **not frozen**. A real RandomX adapter/benchmark remains a future evaluation item; v0.31 uses Python's real scrypt primitive so CPU-mined blocks are working/testable now without claiming unimplemented RandomX support.

See [`blockchain/V0.31.md`](blockchain/V0.31.md).

## Quick test

```bash
git clone https://github.com/navindusasmitha/CrakbitAI.git
cd CrakbitAI/blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## Quick PoW devnet

```bash
crakchain pow-wallet-v31-new --output private/miner.json
crakchain pow-chain-v31-init --db runtime/pow-v31/chain.sqlite3
crakchain pow-mine-v31 --db runtime/pow-v31/chain.sqlite3 --miner-address crk1YOUR_ADDRESS --blocks 1
crakchain pow-chain-v31-info --db runtime/pow-v31/chain.sqlite3
```

Run the node RPC:

```bash
crakchain pow-node-v31-run --db runtime/pow-v31/chain.sqlite3 --host 127.0.0.1 --port 28443
```

Run the first-party pool:

```bash
crakchain pow-pool-v31-run --db runtime/pow-v31/pool.sqlite3 --node-url http://127.0.0.1:28443 --pool-address crk1POOL_ADDRESS --host 127.0.0.1 --port 3333
```

Then a native CPU pool miner can connect with:

```bash
python scripts/run_pow_pool_miner_v31.py --host 127.0.0.1 --port 3333 --address crk1MINER_ADDRESS --worker cpu-01
```

## Important v0.31 boundary

This is a CPU-mineable PoW **devnet prototype**, not yet a decentralized Bitcoin-like production network. v0.31 currently accepts blocks extending the local canonical tip only. P2P peer discovery/gossip, competing forks, highest-cumulative-work reorganization/undo data, RandomX interoperability, mature Stratum/XMRig compatibility, hardened pool payouts and long-lived multi-node PoW testing still need to be completed.

The previous v0.23–v0.30 operations/review/evidence tooling remains useful and is retained, but CometBFT validator consensus is not silently mixed into the new PoW consensus path.

## Funding

Crakbit AI is raising development funding for security tooling, infrastructure, testing, documentation and staged blockchain research. The fundraising campaign is **not a CRKBIT token sale and does not promise investment returns**.

## Links

- Website: https://crakbit.space
- Repository: https://github.com/navindusasmitha/CrakbitAI
- Giveth: Crakbit AI is publicly listed on Giveth

## License

Unless otherwise noted, source code in this repository is released under the Apache License 2.0. See [`LICENSE`](LICENSE).
