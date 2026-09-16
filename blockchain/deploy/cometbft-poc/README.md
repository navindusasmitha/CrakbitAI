# v0.14 CometBFT Integration PoC Runbook

This runbook is for a local or isolated development environment. It is not a public-mainnet deployment guide.

## Process layout

Run three separate processes:

1. Crakbit v0.14 Python execution service on `127.0.0.1:26659`.
2. Crakbit Go ABCI bridge on `127.0.0.1:26658`.
3. CometBFT node configured with `proxy_app = "tcp://127.0.0.1:26658"`.

Use a **dedicated external application data directory**. Do not reuse a `runtime/nodeX-data` directory from the research Python-consensus network.

## 1. Install the Python package

```bash
cd blockchain
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 2. Start the execution service

Generate a long local secret with your platform's secure random tooling. Do not put the real token in Git.

```bash
python scripts/run_execution_service_v14.py \
  --genesis runtime/genesis.json \
  --data runtime/comet-app \
  --token YOUR_LONG_RANDOM_SECRET \
  --host 127.0.0.1 \
  --port 26659
```

Check unauthenticated health:

```bash
curl http://127.0.0.1:26659/health
```

Authenticated application state:

```bash
curl -H "Authorization: Bearer YOUR_LONG_RANDOM_SECRET" \
  http://127.0.0.1:26659/v2/info
```

## 3. Build and run the Go bridge

```bash
cd blockchain/cometbft-app
go mod download
go test -mod=mod ./...
go build -o crakbit-cometbft-bridge .
```

Run:

```bash
export CRAKBIT_EXECUTION_URL=http://127.0.0.1:26659
export CRAKBIT_EXECUTION_TOKEN=YOUR_LONG_RANDOM_SECRET
export CRAKBIT_ABCI_LISTEN=tcp://127.0.0.1:26658
./crakbit-cometbft-bridge
```

## 4. Configure CometBFT

v0.14 pins the bridge module to CometBFT `v0.40.0` for reproducible integration testing.

Initialize a **separate CometBFT node home** using CometBFT's own tooling. Do not copy Crakbit application private keys into that node home.

In the CometBFT configuration, point the application proxy at:

```toml
proxy_app = "tcp://127.0.0.1:26658"
```

The CometBFT chain ID/genesis/validator set must be created and distributed consistently between CometBFT operators. Crakbit's signed application-genesis ceremony does not automatically replace CometBFT's own consensus-genesis procedures.

## 5. Crakbit application genesis ceremony

Separately attest the exact Crakbit application genesis:

```bash
crakchain ceremony-create \
  --genesis runtime/genesis.json \
  --output runtime/genesis-ceremony.json
```

Each Crakbit application validator signs locally. After strict >2/3 signatures:

```bash
crakchain ceremony-verify \
  --ceremony runtime/genesis-ceremony.json \
  --genesis runtime/genesis.json
```

Never transfer validator private key files between operators for the ceremony.

## Transaction framing

The ABCI bridge expects each CometBFT transaction byte array to contain one complete JSON-encoded Crakbit signed transaction object. `CheckTx` sends that object to `/v2/check-tx`; `FinalizeBlock` sends the ordered list to `/v2/finalize`.

## Recovery model

- `FinalizeBlock` persists a pending application transition without changing committed balances.
- `Commit` applies the pending transition atomically.
- Pending finalize data survives execution-service restart.
- An identical already-committed FinalizeBlock replay is accepted through the replay-safe v0.14 service path.
- Conflicting replays are rejected.

This still needs broader live CometBFT crash-point/replay testing before production use.

## Do not expose these ports publicly by default

- `26658` ABCI bridge: loopback only.
- `26659` execution HTTP service: loopback only.

CometBFT P2P/RPC exposure has its own security model and must be firewalled/reviewed separately.
