# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent technology project building defensive-security tooling plus experimental blockchain infrastructure.

## Current status

- Security scanner / CLI: early alpha
- AI Security Assistant: in development
- Crakbit Chain package: **v0.32.0a1**
- Primary chain research direction: **native Proof of Work + UTXO**
- Current PoW: **`crakpow-scrypt-v1` CPU-mineable devnet**
- P2P protocol: **`crakbit-p2p/1`**
- Fork choice: **highest cumulative valid work**
- Side chains / orphan handling / automatic higher-work reorg: implemented in v0.32
- First-party solo miner + mining-pool prototype: implemented
- Previous CometBFT/BFT path: retained as legacy/research infrastructure
- Production mainnet: **not launched**
- Production CRKBIT: **not launched**
- Official CRKBIT presale: **none**

Do not use the current alpha to custody real value.

## Crakbit Chain v0.32 — decentralized PoW network layer

v0.31 introduced actual CPU-mined blocks and a UTXO ledger. v0.32 adds a separate signed peer-to-peer layer and changes the node from a tip-only prototype into a block-graph node capable of retaining competing branches and selecting a higher-work canonical chain.

Implemented now:

- native PoW genesis + UTXO accounting,
- Ed25519 `crk1...` ownership/signatures,
- coinbase rewards, fees and maturity,
- CPU scrypt mining + difficulty/chainwork,
- persistent all-branches block graph,
- side-chain retention,
- bounded orphan queue,
- full candidate-branch replay before activation,
- highest-cumulative-work fork choice,
- canonical reorganization,
- reorg mempool/disconnected-transaction reconciliation,
- median-time-past branch timestamp rule,
- exponential block locators,
- signed chain/genesis-bound P2P handshakes,
- static seed peers + bounded peer discovery,
- header announcements + block fetch,
- block/transaction inventory gossip,
- peer scoring/rate/size limits,
- v1 mining RPC compatibility plus v2 P2P-aware node RPC,
- live peer/branch inspection,
- a regression test that synchronizes a mined block between two real TCP nodes.

See [`blockchain/V0.32.md`](blockchain/V0.32.md).

## Quick test

```bash
git clone https://github.com/navindusasmitha/CrakbitAI.git
cd CrakbitAI/blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## Quick PoW P2P devnet

Create a dedicated P2P identity and chain database:

```bash
crakchain pow-p2p-key-v32-new --output private/node1-p2p.json
crakchain pow-network-v32-init --db runtime/node1/chain.sqlite3
```

Run node 1:

```bash
crakchain pow-node-v32-run \
  --db runtime/node1/chain.sqlite3 \
  --network-key private/node1-p2p.json \
  --rpc-port 28443 \
  --p2p-port 28444
```

A second node initialized with the exact same chain config/genesis can connect with:

```bash
crakchain pow-node-v32-run \
  --db runtime/node2/chain.sqlite3 \
  --network-key private/node2-p2p.json \
  --rpc-port 29443 \
  --p2p-port 29444 \
  --peer 127.0.0.1:28444
```

The v0.31 solo miner and pool remain usable against the v0.32 node's `/pow/v1` compatibility RPC.

## Mining / algorithm boundary

The current bootstrap algorithm is `crakpow-scrypt-v1`. It is real CPU-verifiable PoW, but the **production PoW algorithm is not frozen**. RandomX/native optimized mining and standard Stratum/XMRig interoperability remain separate future work.

The first-party `crakbit-pool/1` pool is not yet standard Stratum and its PPLNS balances remain test accounting only.

## Important v0.32 boundary

v0.32 is now a genuine multi-node PoW devnet architecture with competing-branch storage and higher-work reorganization, but it is still not a production Bitcoin-equivalent network. Remaining work includes deeper adversarial reorg/network testing, stronger peer/address persistence and DoS hardening, optimized sync, final PoW selection, mature Stratum/XMRig support, hardened pool payout construction, long-running independent public testnet operation and independent node/wallet/pool security review.

The previous CometBFT/BFT code is retained as legacy/research infrastructure and is not silently mixed with PoW consensus.

## Funding

Crakbit AI is raising development funding for security tooling, infrastructure, testing, documentation and staged blockchain research. The fundraising campaign is **not a CRKBIT token sale and does not promise investment returns**.

## Links

- Website: https://crakbit.space
- Repository: https://github.com/navindusasmitha/CrakbitAI
- Giveth: Crakbit AI is publicly listed on Giveth

## License

Unless otherwise noted, source code in this repository is released under the Apache License 2.0. See [`LICENSE`](LICENSE).
