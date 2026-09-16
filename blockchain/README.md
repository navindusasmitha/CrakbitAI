# Crakbit Chain — v0.32 Native Proof-of-Work P2P Alpha

**Current package:** `0.32.0a1`  
**Primary research consensus:** native Proof of Work  
**Current PoW algorithm:** `crakpow-scrypt-v1`  
**P2P:** `crakbit-p2p/1`  
**Ledger:** UTXO  
**Fork choice:** highest cumulative valid work  
**Status:** multi-node PoW devnet alpha — **not production mainnet**.

Production CRKBIT has **not** launched. There is no official presale or production token contract. Do not use this software to custody real value.

## v0.32 scope

v0.32 builds on the v0.31 CPU-mineable chain and adds the decentralized networking/fork layer:

- persistent all-branches block graph,
- competing side-chain storage,
- bounded orphan handling,
- complete branch replay before fork activation,
- highest-cumulative-work fork selection,
- atomic canonical block/transaction/UTXO replacement from replayed state,
- disconnected-transaction/mempool reconciliation after reorg,
- median-time-past branch timestamp rule,
- exponential block locators,
- signed Ed25519 P2P identities,
- signed chain-ID/genesis-bound handshakes,
- static seed peers + bounded peer discovery,
- header announcement followed by block fetch,
- block/transaction inventory gossip,
- P2P ping/pong,
- peer scoring and basic rate/size limits,
- combined v1-compatible mining RPC and v2 P2P-aware node RPC,
- peer + branch graph inspection,
- real two-node TCP synchronization regression coverage.

See [`V0.32.md`](V0.32.md).

## Install / test

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## v0.32 commands

```text
pow-p2p-key-v32-new
pow-network-v32-init
pow-network-v32-info
pow-network-v32-graph
pow-network-v32-locator
pow-network-v32-import-block
pow-node-v32-run
```

All v0.31 wallet/mining/pool commands remain available through CLI delegation.

## Start a two-node local devnet

```bash
crakchain pow-p2p-key-v32-new --output private/node1-p2p.json
crakchain pow-p2p-key-v32-new --output private/node2-p2p.json

crakchain pow-network-v32-init --db runtime/node1/chain.sqlite3
crakchain pow-network-v32-init --db runtime/node2/chain.sqlite3
```

Node 1:

```bash
crakchain pow-node-v32-run \
  --db runtime/node1/chain.sqlite3 \
  --network-key private/node1-p2p.json \
  --rpc-port 28443 \
  --p2p-port 28444
```

Node 2:

```bash
crakchain pow-node-v32-run \
  --db runtime/node2/chain.sqlite3 \
  --network-key private/node2-p2p.json \
  --rpc-port 29443 \
  --p2p-port 29444 \
  --peer 127.0.0.1:28444
```

Both nodes must have exactly the same chain configuration/genesis.

## Mining against v0.32

The node keeps `/pow/v1/*` mining RPC compatibility, so v0.31 mining/pool tooling can point at a v0.32 node. Blocks accepted through RPC are announced to peers.

Example node mining RPC:

```text
POST /pow/v1/getblocktemplate
POST /pow/v1/submitblock
POST /pow/v1/submittransaction
```

Additional v0.32 inspection endpoints:

```text
GET /pow/v2/info
GET /pow/v2/peers
GET /pow/v2/graph
GET /pow/v2/blockhash/{hash}
```

## Fork choice / reorg model

A valid side block no longer has to extend the local tip. The node stores it in the block graph. Candidate branches are replayed from deterministic genesis before activation. When a branch has strictly more cumulative work than the current canonical branch, the replayed candidate state becomes canonical.

Equal-work branches do not replace the current tip. A later valid block that gives one branch more cumulative work resolves the fork.

Disconnected non-coinbase transactions are returned to the mempool only when they are still valid against the new canonical UTXO set.

## P2P security boundary

The handshake is signed and binds node identity, chain ID, genesis hash, best tip and cumulative work. Peers on a different chain/genesis are rejected. The alpha also has bounded message size, block size, inventories, headers, orphan count, peer count and per-second message rate.

This is **not** enough to call the P2P layer production hardened. More adversarial fuzzing, network-level DoS testing, durable address management, eclipse/Sybil analysis, NAT/privacy decisions and independent review remain required.

## Mining-pool boundary

The first-party pool remains `crakbit-pool/1`, not standard Stratum/XMRig. Pool PPLNS balances are test accounting and automatic on-chain payout remains disabled.

## PoW algorithm boundary

The current `crakpow-scrypt-v1` path is a working bootstrap algorithm. It is **not frozen for production**. RandomX remains a candidate for native integration/benchmarking and the final algorithm must be independently reviewed before mainnet consideration.

## Next priorities — v0.33

- native RandomX adapter candidate + deterministic test vectors,
- CPU/GPU benchmarking and validation-cost analysis,
- optimized multi-core miner,
- standard Stratum compatibility,
- XMRig interoperability if compatible with the selected algorithm,
- pool vardiff / duplicate / stale / replay protection,
- TLS/auth/rate limits for pool endpoints,
- on-chain PPLNS payout construction,
- persistent peer database + anti-eclipse controls,
- more adversarial fork/reorg/fuzz tests,
- long-running multi-host PoW testnet.

## Monetary-policy boundary

Subsidy, halving and difficulty values remain configurable devnet parameters. The proposed `21,000,000 CRKBIT` and 8-decimal design are not final production economics until deliberately frozen and independently reviewed.
