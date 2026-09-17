# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent technology project building defensive-security tooling plus experimental blockchain infrastructure.

## Current status

- Security scanner / CLI: early alpha
- AI Security Assistant: in development
- Crakbit Chain package: **v0.36.0a1**
- Primary chain research direction: **native Proof of Work + UTXO**
- Active devnet PoW: **`crakpow-scrypt-v1`**
- P2P protocol: **`crakbit-p2p/1`**
- Pool protocol: **`crakbit-pool/2`**
- Highest-cumulative-work fork choice + competing-branch reorg: implemented alpha
- Multi-thread CPU solo/pool mining: implemented
- RandomX `v1.1.8` native adapter: optional candidate, not active consensus
- v0.34 payout/undo/peer/benchmark preparation: implemented
- v0.35 public-testnet evidence gate: implemented
- v0.36 controlled integration: real-time signed campaign log, peer-book node startup, incremental-undo rehearsal, explicit algorithm activation proposal and independent-review handoff tooling
- Production mainnet: **not launched**
- Production CRKBIT: **not launched**
- Official CRKBIT presale: **none**

Do not use the current alpha to custody real value.

## Crakbit Chain v0.36 — controlled public-testnet integration

v0.36 turns the v0.35 evidence layer into a resumable real campaign workflow. It adds append-only signed/hash-chained multi-node observations, real elapsed-time 24h/72h/7d campaign summaries, persistent peer-book seed selection in node startup, disposable incremental UTXO-undo rehearsals, explicit non-activating RandomX/scrypt testnet proposals, and an independent-review handoff artifact.

See [`blockchain/V0.36.md`](blockchain/V0.36.md).

## Quick test

```bash
git clone https://github.com/navindusasmitha/CrakbitAI.git
cd CrakbitAI/blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## Real-time public-testnet campaign

```bash
python scripts/run_pow_campaign_v36.py \
  --key private/campaign-evidence.json \
  --log evidence/campaign-v36.jsonl \
  --rpc-url https://node-a.example \
  --rpc-url https://node-b.example \
  --rpc-url https://node-c.example \
  --rpc-url https://node-d.example \
  --interval-seconds 60 \
  --duration-seconds 86400
```

Summarize only the elapsed time that was actually collected:

```bash
crakchain pow-campaign-v36-summarize \
  --log evidence/campaign-v36.jsonl \
  --required-level 24h \
  --minimum-nodes 4 \
  --minimum-sample-success-ratio 0.99 \
  --output evidence/campaign-summary-v36.json
```

## Peer-book integrated node

```bash
crakchain pow-node-v36-run \
  --db runtime/node1/chain.sqlite3 \
  --network-key private/node1-p2p.json \
  --peer-db runtime/node1/peers.sqlite3 \
  --rpc-port 28443 \
  --p2p-port 28444
```

The peer buckets are a coarse diversity defense only; they do not prove operator/ASN/provider independence.

## Reorg preparation

```bash
crakchain pow-undo-v36-rehearse \
  --db runtime/node1/chain.sqlite3 \
  --disconnect-blocks 5 \
  --output evidence/undo-rehearsal-v36.json
```

This modifies a disposable database copy and compares incremental rollback against a clean replay. The live reorg engine is **not** silently switched to incremental undo.

## Mining / algorithm boundary

The active chain still uses `crakpow-scrypt-v1`. RandomX remains an optional candidate. v0.36 can create a signed activation **proposal** after a human benchmark decision, but the artifact always records `consensus_activated=false`; an actual algorithm change needs a separately reviewed/versioned node release and multi-node fork/reorg testing.

## Important boundary

v0.36 is controlled public-testnet integration tooling, not production mainnet. Real independent nodes/miners, 24h→72h→7d operation, authorized fault/reorg campaigns, cross-machine algorithm benchmarks, independent consensus/network/wallet/pool review, high/critical remediation, final economics and applicable legal/regulatory review remain external gates.

The previous CometBFT/BFT code is retained as legacy/research infrastructure and is not mixed with PoW consensus.

## Funding

Crakbit AI is raising development funding for security tooling, infrastructure, testing, documentation and staged blockchain research. The fundraising campaign is **not a CRKBIT token sale and does not promise investment returns**.

## Links

- Website: https://crakbit.space
- Repository: https://github.com/navindusasmitha/CrakbitAI
- Giveth: Crakbit AI is publicly listed on Giveth

## License

Unless otherwise noted, source code in this repository is released under the Apache License 2.0. See [`LICENSE`](LICENSE).
