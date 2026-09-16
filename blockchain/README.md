# Crakbit Chain — Development Network Prototype

**Status: research/devnet alpha (`0.11.0-alpha`)**

Crakbit Chain is the experimental blockchain component of the Crakbit AI ecosystem. The current development network includes native test-only `CRKBIT` accounting, Ed25519-signed transactions, certified view changes, prevote/precommit finality, authenticated validator requests, durable replay protection, quorum-certified state snapshots, resumable snapshot transfer, integrity checks, verified backups, Prometheus/Grafana monitoring, bounded RPC/mempool controls and optional validator mTLS/certificate pinning.

> This is **not a production mainnet**, has not completed independent consensus/network review, and must not be used to custody real value.

## Devnet Parameters

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

## Consensus Direction

The current Python consensus remains a research implementation. `docs/ADR-0001-consensus-direction.md` records the decision that Crakbit will not keep extending this prototype as if it were production BFT. Before public-value mainnet planning, the project will evaluate migration of the execution/state layer to an established independently reviewed BFT core, with a Tendermint/CometBFT-style protocol as the primary architectural reference.

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

Later rounds require certified view changes. Local phase votes and locks survive restart. The current cross-round lock remains conservative and is **not a reviewed production BFT lock/unlock protocol**.

## v0.11 Transport Hardening

v0.11 adds:

- operator-managed validator mTLS support,
- CA/hostname verification for outbound validator connections,
- optional SHA-256 leaf-certificate pinning by validator address,
- `/transport/status`,
- validator certificate fingerprint helper,
- dedicated mutual-TLS validator launcher,
- transport fault harness based on Toxiproxy,
- validator certificate/key rotation and incident-response runbook,
- public-testnet reverse-proxy hardening example,
- CLI routing to the current v0.11 node implementation.

Environment variables for hardened validator transport:

```text
CRAKBIT_REQUIRE_MTLS=1
CRAKBIT_MTLS_CA=/run/secrets/validator-ca.crt
CRAKBIT_MTLS_CERT=/run/secrets/validator.crt
CRAKBIT_MTLS_KEY=/run/secrets/validator.key
CRAKBIT_PEER_CERT_PINS=/run/secrets/peer-pins.json
CRAKBIT_REQUIRE_PEER_PINS=1
CRAKBIT_PEER_PIN_CACHE_SECONDS=60
```

Start an inbound mTLS validator listener with:

```bash
python scripts/run_validator_mtls.py \
  --genesis runtime/genesis.json \
  --key runtime/node1/validator.json \
  --data runtime/node1-data \
  --port 9101 \
  --tls-cert /run/secrets/node1.crt \
  --tls-key /run/secrets/node1.key \
  --client-ca /run/secrets/validator-ca.crt \
  --peer-pins /run/secrets/peer-pins.json \
  --require-peer-pins
```

Every validator `peer_url` in an mTLS network must use `https://`, and certificate SANs must match those hostnames.

## v0.10 Resource Bounds Still Active

```text
CRAKBIT_MAX_PUBLIC_BODY_BYTES=262144
CRAKBIT_MAX_INTERNAL_BODY_BYTES=2097152
CRAKBIT_PUBLIC_TX_RPM=60
CRAKBIT_MAX_MEMPOOL_TXS=5000
CRAKBIT_MAX_BLOCK_TXS=1000
CRAKBIT_MAX_TX_BYTES=65536
```

These controls are defense-in-depth. A public testnet still requires reverse-proxy, firewall and network-level abuse controls.

## Quick Start — Local Non-mTLS Devnet

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

## Wallet / Test Transfers

```bash
crakchain keygen --output runtime/alice.json
crakchain address --key runtime/alice.json
crakchain balance YOUR_ADDRESS --rpc http://127.0.0.1:9101
```

Send test units:

```bash
crakchain send \
  --key runtime/treasury.json \
  --genesis runtime/genesis.json \
  --to crk1RECIPIENT \
  --amount 25 \
  --rpc http://127.0.0.1:9101
```

Never commit or share validator/private wallet key files.

## Snapshot Recovery

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

Snapshot bootstrap restores certified state but does not reconstruct historical block bodies before the snapshot base.

## Integrity & Backups

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

Restore drill:

```bash
python scripts/backup_restore_drill.py \
  --genesis runtime/genesis.json \
  --backup runtime/backups/node1.sqlite3 \
  --manifest runtime/backups/node1.sqlite3.manifest.json \
  --output-data runtime/restore-drill/node1
```

## Fault Harness

```bash
cd blockchain/faults
docker compose -f docker-compose.toxiproxy.yml up -d
python control.py setup
python control.py latency validator-2 --ms 1500 --jitter 250
python control.py down validator-4
python control.py reset validator-2
```

This models transport faults only. It is not proof of Byzantine consensus safety.

## Monitoring

```bash
cd ops
docker compose -f docker-compose.observability.yml up -d
```

- Prometheus: `http://127.0.0.1:9090`
- Grafana: `http://127.0.0.1:3000`

Useful node endpoints:

```text
GET /health
GET /status
GET /transport/status
GET /limits/status
GET /operations/status
GET /integrity/status
GET /validators
GET /peers
GET /evidence
GET /consensus/events
GET /metrics
GET /metrics/prometheus
GET /snapshot/latest
GET /recovery/status
GET /history/status
```

## Tests

```bash
cd blockchain
pip install -e ".[dev]"
pytest -q
```

GitHub Actions runs the blockchain test suite on blockchain changes.

## Main Remaining Blockers

- migration/integration with a reviewed BFT consensus core or independent review of a complete protocol,
- automatic certificate overlap/rotation rather than operator-coordinated single-pin rotation,
- archive/history synchronization for snapshot-bootstrapped nodes,
- consensus-level Byzantine-message fixtures,
- long-running multi-host partition/latency/load/soak testing,
- authenticated production monitoring/alert routing,
- production secrets/HSM strategy,
- independent consensus/network/security audit.

See [`V0.11.md`](V0.11.md), [`V0.10.md`](V0.10.md), [`docs/ADR-0001-consensus-direction.md`](docs/ADR-0001-consensus-direction.md), [`SPEC.md`](SPEC.md) and [`SECURITY.md`](SECURITY.md).
