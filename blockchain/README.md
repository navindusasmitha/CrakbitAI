# Crakbit Chain — Development Network Prototype

**Status: research/devnet alpha (`0.13.0-alpha`)**

Crakbit Chain is the experimental blockchain component of the Crakbit AI ecosystem. The development network includes native test-only `CRKBIT` accounting, Ed25519-signed transactions, research prevote/precommit consensus, authenticated validator requests, quorum-certified snapshots, resumable recovery, verified history archives, mTLS/certificate pinning, bounded RPC behavior, signed release tooling, a deterministic external-consensus execution PoC, testnet provisioning scaffolds, a bounded test faucet and read-only explorer APIs.

> This is **not a production mainnet**, has not completed independent consensus/network review, and must not be used to custody real value.

## Devnet parameters

- Symbol: `CRKBIT`
- Decimals: `8`
- Proposed development genesis cap: `21,000,000 CRKBIT`
- Default validators: `4`
- Default quorum: `3 of 4`
- Address format: `crk1...`
- Signatures: Ed25519
- State storage: SQLite
- RPC: FastAPI / JSON

The 21M value is a development-network configuration parameter, not a promise of future token value or final mainnet economics.

## Consensus direction

The current Python consensus remains a **research implementation**. Crakbit will not keep extending it as if it were production BFT. Before public-value mainnet planning, the execution/state layer must be integrated with an established independently reviewed BFT core, or the complete consensus protocol must receive equivalent independent review.

Current research flow:

```text
proposal
   ↓
>2/3 PREVOTE certificate
   ↓
>2/3 PRECOMMIT certificate
   ↓
finalized block
```

See `docs/ADR-0001-consensus-direction.md`.

## v0.13 large phase

v0.13 adds:

- deterministic `crakbit-execution/1` application protocol boundary,
- deterministic application-state hash independent from consensus-local state,
- non-mutating transaction and ordered-batch execution previews,
- authenticated loopback execution-service process PoC,
- signed genesis/release manifests with Ed25519 signatures and artifact SHA-256 hashes,
- independent-host validator provisioning scaffold generator,
- strictly test-only faucet with per-address cooldown and global request limits,
- bounded read-only explorer summary/block/address APIs,
- reproducible soak-test summary generation,
- external consensus/network review package checklist,
- all v0.12 archive/recovery, v0.11 transport and v0.10 resource-hardening features.

See [`V0.13.md`](V0.13.md) for the full phase notes and limitations.

## Quick start — local devnet

Requirements: Python 3.11+ and Docker Desktop / Docker Engine.

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
python scripts/bootstrap_devnet.py
docker compose up --build
```

Local RPC endpoints:

- Node 1: `http://127.0.0.1:9101`
- Node 2: `http://127.0.0.1:9102`
- Node 3: `http://127.0.0.1:9103`
- Node 4: `http://127.0.0.1:9104`
- API docs: `http://127.0.0.1:9101/docs`

## Wallet / test transfers

```bash
crakchain keygen --output runtime/alice.json
crakchain address --key runtime/alice.json
crakchain balance YOUR_ADDRESS --rpc http://127.0.0.1:9101

crakchain send \
  --key runtime/treasury.json \
  --genesis runtime/genesis.json \
  --to crk1RECIPIENT \
  --amount 25 \
  --rpc http://127.0.0.1:9101
```

Never commit or share validator/private wallet key files.

## Deterministic execution protocol PoC

Read local application protocol state:

```bash
crakchain protocol-status \
  --genesis runtime/genesis.json \
  --data runtime/node1-data
```

Preview an ordered transaction batch without changing state:

```bash
crakchain protocol-preview \
  --genesis runtime/genesis.json \
  --data runtime/node1-data \
  --transactions runtime/transactions.json \
  --fee-recipient crk1VALIDATOR
```

Run the isolated process-boundary PoC on loopback:

```bash
python scripts/run_execution_service.py \
  --genesis runtime/genesis.json \
  --data runtime/node1-data \
  --token REPLACE_WITH_LONG_RANDOM_SECRET
```

The v0.13 execution service has **no external finalize/commit endpoint**. This is deliberate until a reviewed BFT integration and replay/crash contract are in place.

## Signed release / genesis manifest

Use a **dedicated release signing key**, not a validator key:

```bash
crakchain keygen --output runtime/release-signing-key.json

crakchain release-build \
  --genesis runtime/genesis.json \
  --key runtime/release-signing-key.json \
  --version 0.13.0a1 \
  --artifact dist/crakbit-chain.whl \
  --output runtime/release-0.13.json
```

Verify:

```bash
crakchain release-verify \
  --manifest runtime/release-0.13.json \
  --genesis runtime/genesis.json \
  --expected-signer crk1EXPECTED_RELEASE_SIGNER \
  --artifact-dir dist
```

## Snapshot and archive recovery

```bash
crakchain snapshot-fetch-chunked \
  --genesis runtime/genesis.json \
  --output runtime/snapshot-cert.json \
  --cache-dir runtime/snapshot-cache

crakchain snapshot-verify \
  --snapshot runtime/snapshot-cert.json \
  --genesis runtime/genesis.json

crakchain snapshot-import \
  --snapshot runtime/snapshot-cert.json \
  --genesis runtime/genesis.json \
  --data runtime/recovered-node
```

Export/verify/backfill full genesis-anchored history:

```bash
crakchain archive-export \
  --genesis runtime/genesis.json \
  --data runtime/node1-data \
  --output runtime/history.json

crakchain archive-verify \
  --genesis runtime/genesis.json \
  --archive runtime/history.json

crakchain archive-import \
  --genesis runtime/genesis.json \
  --data runtime/recovered-node \
  --archive runtime/history.json
```

## Independent-host operator scaffolds

Generate non-secret per-validator deployment bundles:

```bash
python scripts/provision_testnet.py \
  --genesis runtime/genesis.json \
  --output runtime/operator-bundles
```

The generated folders contain public metadata and configuration templates only. They intentionally contain no private validator keys, TLS private keys or monitoring secrets.

## Strictly test-only faucet

Create/fund a **dedicated non-validator faucet key** and run:

```bash
python scripts/run_faucet.py \
  --genesis runtime/genesis.json \
  --key runtime/faucet.json \
  --rpc http://127.0.0.1:9101 \
  --amount 10 \
  --cooldown-seconds 3600 \
  --global-rpm 10
```

Default listener: `127.0.0.1:9400`. Put any public testnet faucet behind a hardened reverse proxy and upstream abuse controls. Faucet units are test-only and represent no production value.

## Explorer/read APIs

v0.13 adds:

```text
GET /protocol/status
GET /explorer/summary
GET /explorer/blocks?limit=20
GET /explorer/address/{address}?limit=50
```

Existing recovery/history/operator APIs remain available. Address activity is bounded and is not yet a dedicated indexed explorer backend.

## Validator transport security

v0.11+ supports operator-managed mTLS, CA/hostname verification and optional certificate SHA-256 pinning. v0.12+ supports a bounded two-pin overlap during certificate rotation.

```json
{
  "crk1VALIDATOR": [
    "old_certificate_sha256",
    "new_certificate_sha256"
  ]
}
```

Operator monitoring can additionally require:

```text
CRAKBIT_MONITORING_BEARER_TOKEN=<secret-at-least-24-characters>
```

This does not replace private networking, firewall policy or reverse-proxy access controls.

## Integrity & backups

```bash
crakchain doctor --genesis runtime/genesis.json --data runtime/node1-data --full

crakchain backup-create \
  --genesis runtime/genesis.json \
  --data runtime/node1-data \
  --output runtime/backups/node1.sqlite3

crakchain backup-verify \
  --genesis runtime/genesis.json \
  --backup runtime/backups/node1.sqlite3 \
  --manifest runtime/backups/node1.sqlite3.manifest.json \
  --full
```

## Soak evidence

```bash
python scripts/soak_test.py \
  --node http://127.0.0.1:9101 \
  --node http://127.0.0.1:9102 \
  --node http://127.0.0.1:9103 \
  --node http://127.0.0.1:9104 \
  --duration-seconds 3600 \
  --interval-seconds 5 \
  --output runtime/soak-results.jsonl \
  --fail-on-divergence

python scripts/soak_summary.py \
  --input runtime/soak-results.jsonl \
  --output runtime/soak-summary.json
```

These outputs are operational evidence, not a formal consensus-safety proof.

## Tests

```bash
cd blockchain
pip install -e ".[dev]"
pytest -q
```

GitHub Actions runs the blockchain suite on blockchain changes.

## Main remaining blockers

- actual integration with an established independently reviewed BFT core,
- reviewed mutating finalize/commit protocol and crash/replay semantics,
- sustained independent-host partition/latency/Byzantine/load/soak campaigns,
- production validator/release-key custody or HSM-equivalent strategy,
- production monitoring/alert routing and secret management,
- production reverse-proxy/firewall/DDoS architecture review,
- independent consensus/network/security review,
- meaningful public-testnet operation before any mainnet planning.

See [`V0.13.md`](V0.13.md), [`V0.12.md`](V0.12.md), [`docs/EXECUTION_PROTOCOL_V1.md`](docs/EXECUTION_PROTOCOL_V1.md), [`docs/EXTERNAL_REVIEW_PACKAGE.md`](docs/EXTERNAL_REVIEW_PACKAGE.md), [`SPEC.md`](SPEC.md) and [`SECURITY.md`](SECURITY.md).
