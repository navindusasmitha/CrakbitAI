# Crakbit Chain — v0.36 Controlled PoW Integration Alpha

**Current package:** `0.36.0a1`  
**Primary research consensus:** native Proof of Work  
**Active devnet PoW:** `crakpow-scrypt-v1`  
**RandomX:** optional candidate; not consensus-enabled  
**P2P:** `crakbit-p2p/1`  
**Pool:** `crakbit-pool/2`  
**Ledger:** UTXO  
**Fork choice:** highest cumulative valid work  
**Status:** controlled public-testnet integration alpha — **not production mainnet**.

Production CRKBIT has not launched. There is no official presale or production token contract. Do not use this alpha to custody real value.

## What v0.36 adds

v0.36 builds on the v0.35 public-testnet evidence layer and adds controlled integration tooling for a real multi-host PoW campaign:

- append-only signed campaign observation logs,
- periodic probing of multiple `/pow/v2` nodes,
- campaign verification and 24h / 72h / 7d summaries,
- minimum node and sample-success-ratio gates,
- same-chain/genesis/algorithm convergence checks,
- controlled UTXO undo/disconnect rehearsal on a disposable database copy,
- persistent peer-book seed selection for live node startup,
- coarse peer-bucket diversity limits,
- v0.36 node launcher using selected peer-book seeds,
- signed PoW algorithm activation proposal format,
- activation proposals require prior v0.34 human algorithm decision,
- RandomX proposals require deterministic consensus-vector and native-library hashes,
- minimum activation notice window,
- proposal tooling never silently activates consensus,
- regression tests for campaign logs, reorg rehearsal, peer diversity and activation policy.

See [`V0.36.md`](V0.36.md).

## Install / test

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## v0.36 commands

```text
pow-campaign-v36-probe
pow-campaign-v36-verify
pow-campaign-v36-summarize
pow-undo-v36-rehearse
pow-peer-seeds-v36-select
pow-node-v36-run
pow-activation-v36-build
pow-activation-v36-verify
```

All v0.35 and earlier commands remain available through CLI delegation.

## Campaign collector

Append a signed sample from multiple real nodes:

```powershell
crakchain pow-campaign-v36-probe `
  --key private\campaign-evidence.json `
  --log evidence\campaign-v36.jsonl `
  --rpc-url https://node-a.example `
  --rpc-url https://node-b.example `
  --rpc-url https://node-c.example `
  --rpc-url https://node-d.example
```

Summarize only after real elapsed time exists:

```powershell
crakchain pow-campaign-v36-summarize `
  --log evidence\campaign-v36.jsonl `
  --required-level 24h `
  --minimum-nodes 4 `
  --minimum-sample-success-ratio 0.99 `
  --output evidence\campaign-summary-24h.json
```

The collector cannot fabricate elapsed time or external operators.

## UTXO undo rehearsal

v0.34 created verified undo metadata. v0.36 adds a disposable-copy disconnect rehearsal so undo state can be tested without mutating the operator's live database:

```powershell
crakchain pow-undo-v36-rehearse `
  --db runtime\node1\chain.sqlite3 `
  --disconnect-blocks 3 `
  --output evidence\undo-rehearsal.json
```

This is still rehearsal tooling; the canonical live reorg engine continues to use the reviewed v0.32 replay/state-replacement path until incremental disconnect/connect logic receives deeper testing and review.

## Peer-book node startup

```powershell
crakchain pow-peer-seeds-v36-select `
  --peer-db runtime\node1\peers.sqlite3 `
  --limit 16 `
  --max-per-bucket 2
```

Run a node with persistent peer-book seed selection:

```powershell
crakchain pow-node-v36-run `
  --db runtime\node1\chain.sqlite3 `
  --network-key private\node1-p2p.json `
  --peer-db runtime\node1\peers.sqlite3 `
  --rpc-port 28443 `
  --p2p-port 28444
```

The bucket policy reduces accidental concentration but is not complete Sybil/ASN anti-eclipse protection.

## Algorithm activation boundary

A v0.34 human decision may be converted into a signed v0.36 activation **proposal**. The proposal binds source commit, chain ID, genesis hash, current height, activation height and, for RandomX, deterministic vector/library hashes.

```powershell
crakchain pow-activation-v36-build `
  --key private\release-evidence.json `
  --algorithm-decision evidence\algorithm-decision.json `
  --source-commit <40-char-git-sha> `
  --chain-id crakbit-pow-testnet-v1 `
  --genesis-hash <64-hex-genesis> `
  --current-height 1000 `
  --activation-height 3000 `
  --output evidence\activation-proposal.json
```

The proposal always records that consensus is **not automatically activated**. A separate reviewed versioned consensus implementation is required.

## External work still required

- 4+ independently operated public nodes,
- multiple independent miners/pools,
- real 24h → 72h → 7d+ campaigns,
- real partition/restart/reorg/load/invalid-input drills,
- real cross-machine scrypt/RandomX benchmark evidence,
- independent consensus/network/wallet/pool review,
- high/critical remediation and retest,
- final mining algorithm/economics/legal review.

```text
production_mainnet_ready=false
production_crkbit_launched=false
```
