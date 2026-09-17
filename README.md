# Crakbit AI

**AI-powered cybersecurity, secure coding and blockchain security infrastructure.**

> Secure Code. Secure Chains. Build the Future.

Crakbit AI is an independent technology project building defensive-security tooling plus experimental blockchain infrastructure.

## Current status

- Security scanner / CLI: early alpha
- AI Security Assistant: in development
- Crakbit Chain package: **v0.35.0a1**
- Primary chain research direction: **native Proof of Work + UTXO**
- Active devnet PoW: **`crakpow-scrypt-v1`**
- P2P protocol: **`crakbit-p2p/1`**
- Pool protocol: **`crakbit-pool/2`**
- Highest-cumulative-work fork choice + competing-branch reorg: implemented alpha
- Multi-thread CPU solo/pool mining: implemented
- RandomX `v1.1.8` native adapter: implemented as an optional candidate, not active consensus
- v0.34 payout/undo/peer/benchmark preparation: implemented
- v0.35 public-testnet evidence gate: implemented
- Production mainnet: **not launched**
- Production CRKBIT: **not launched**
- Official CRKBIT presale: **none**

Do not use the current alpha to custody real value.

## Crakbit Chain v0.35 — public PoW testnet evidence phase

v0.35 adds signed operator-host attestations, public-node probing, 4+ node convergence checks, real-duration 24h/72h/7d soak gates, fault/recovery campaign records, miner/provider/region diversity checks, a signed public-testnet gate and a signed review freeze.

The tooling is deliberately evidence-driven: it cannot fabricate independent VPS operation, elapsed soak time, real partitions/restarts, higher-work reorgs or external review.

See [`blockchain/V0.35.md`](blockchain/V0.35.md).

## Quick test

```bash
git clone https://github.com/navindusasmitha/CrakbitAI.git
cd CrakbitAI/blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

## Public-testnet evidence flow

Create one dedicated evidence key per independent operator, then record host identity:

```bash
crakchain pow-host-v35-attest \
  --key private/operator-evidence.json \
  --operator-id operator-a \
  --node-id NODE_ID \
  --provider provider-a \
  --region region-a \
  --rpc-url https://node-a.example \
  --p2p-endpoint node-a.example:28444 \
  --source-commit <40-char-git-sha> \
  --chain-id crakbit-pow-testnet-v1 \
  --genesis-hash <64-hex-genesis> \
  --independently-managed \
  --miner-role \
  --output evidence/host-a.json
```

Probe public nodes:

```bash
crakchain pow-node-v35-probe --rpc-url https://node-a.example --output evidence/probe-a.json
```

After collecting 4+ node observations:

```bash
crakchain pow-convergence-v35-check \
  --observation evidence/probe-a.json \
  --observation evidence/probe-b.json \
  --observation evidence/probe-c.json \
  --observation evidence/probe-d.json \
  --output evidence/convergence.json
```

The remaining steps are real external work: sustained soak, authorized fault/reorg campaigns, multi-operator mining, benchmark collection and independent review.

## Mining / algorithm boundary

The active network still uses `crakpow-scrypt-v1`. RandomX remains a candidate. v0.34 introduced signed benchmark/decision evidence, but even a human `randomx` decision does not auto-activate consensus. A separate versioned consensus change plus deterministic vectors and fork testing would still be required.

## Important boundary

v0.35 is public-testnet tooling, not a production-mainnet claim. The project still needs real independent hosts/miners, long-lived operation, final PoW algorithm selection, efficient reviewed reorg mechanics, end-to-end third-party miner interoperability if selected, wallet/node/pool security review, high/critical remediation, final economics and applicable legal/regulatory review.

The previous CometBFT/BFT code is retained as legacy/research infrastructure and is not mixed with PoW consensus.

## Funding

Crakbit AI is raising development funding for security tooling, infrastructure, testing, documentation and staged blockchain research. The fundraising campaign is **not a CRKBIT token sale and does not promise investment returns**.

## Links

- Website: https://crakbit.space
- Repository: https://github.com/navindusasmitha/CrakbitAI
- Giveth: Crakbit AI is publicly listed on Giveth

## License

Unless otherwise noted, source code in this repository is released under the Apache License 2.0. See [`LICENSE`](LICENSE).
