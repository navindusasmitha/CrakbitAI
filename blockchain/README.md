# Crakbit Chain — v0.37 Public-Testnet Execution and Review-Hardening Alpha

**Current package:** `0.37.0a1`
**Primary research consensus:** native Proof of Work
**Active devnet PoW:** `crakpow-scrypt-v1`
**RandomX:** optional candidate; not consensus-enabled
**P2P:** `crakbit-p2p/1`
**Pool:** `crakbit-pool/2`
**Ledger:** UTXO
**Fork choice:** highest cumulative valid work
**Status:** public-testnet execution and review-preparation alpha — **not production mainnet**.

Production CRKBIT has not launched. There is no official presale or production token contract. Do not use this alpha to custody real value.

## What v0.37 adds

v0.37 builds on the v0.36 campaign workflow and adds signed execution/review artifacts:

- signed multi-host deployment plans with operator runbooks,
- node/operator/provider/region/network/miner diversity gates,
- secret-like metadata and credential-bearing RPC URL rejection,
- signed hot/cold pool payout-policy controls,
- multi-operator approvals, caps, holds and confirmation-depth requirements,
- final algorithm-review gate bound to benchmark, human decision and v0.36 handoff records,
- optional RandomX testnet-proposal binding without automatic consensus activation,
- cross-bound public-testnet independent-review candidate bundle,
- semantic verification and regression coverage for the new artifacts.

See [`V0.37.md`](V0.37.md). The v0.36 campaign collector, node integration and undo-rehearsal commands remain available.

## Install / test

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## v0.37 commands

```text
pow-deployment-v37-build
pow-deployment-v37-verify
pow-payout-policy-v37-build
pow-payout-policy-v37-verify
pow-algorithm-review-v37-build
pow-algorithm-review-v37-verify
pow-review-bundle-v37-build
pow-review-bundle-v37-verify
```

All v0.36 and earlier commands remain available through CLI delegation.

## Execution/review workflow

1. Complete the real v0.36 multi-node campaign and handoff evidence.
2. Build a v0.37 deployment plan from reviewed public node metadata.
3. Build a payout policy using public hot/cold watch addresses and conservative operator limits.
4. Bind the real benchmark gate and human algorithm decision to the v0.36 handoff.
5. Build and verify the v0.37 public-testnet review candidate bundle.

The resulting bundle always records that independent review is not completed and production mainnet is not ready. See `V0.37.md` for commands and input formats.

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
