# Crakbit ↔ CometBFT ABCI Bridge (v0.14 PoC)

This directory contains the Go ABCI bridge used by the Crakbit Chain v0.14 external-consensus proof-of-concept.

- CometBFT dependency is pinned to `v0.40.0`.
- The bridge speaks ABCI socket protocol on `tcp://127.0.0.1:26658` by default.
- It forwards deterministic application operations to the authenticated Python execution service over loopback HTTP.
- The Python service owns application-state validation and crash-safe SQLite commit semantics.
- The bridge does **not** reuse Crakbit validator private keys as CometBFT validator keys.

This is a research/testnet integration. It is not a production-mainnet claim.

## Architecture

```text
CometBFT v0.40.0
      │ ABCI socket
      ▼
crakbit-cometbft bridge (Go)
      │ authenticated loopback HTTP
      ▼
Crakbit execution service v0.14
      │ crakbit-execution/2
      ▼
Dedicated external application SQLite state
```

The dedicated application database must not be the same database used by the older research Python consensus node.

## Build

Requires Go 1.25+.

```bash
cd blockchain/cometbft-app
go mod download
go test -mod=mod ./...
go build -o crakbit-cometbft-bridge .
```

## Start the Python execution service

From `blockchain/`:

```bash
python scripts/run_execution_service_v14.py \
  --genesis runtime/genesis.json \
  --data runtime/comet-app \
  --token REPLACE_WITH_LONG_RANDOM_SECRET \
  --host 127.0.0.1 \
  --port 26659
```

## Start the ABCI bridge

```bash
export CRAKBIT_EXECUTION_URL=http://127.0.0.1:26659
export CRAKBIT_EXECUTION_TOKEN=REPLACE_WITH_LONG_RANDOM_SECRET
export CRAKBIT_ABCI_LISTEN=tcp://127.0.0.1:26658
./crakbit-cometbft-bridge
```

Then configure the CometBFT node's `proxy_app` to the bridge socket.

## Implemented ABCI methods

The bridge implements/overrides:

- `Info`
- `CheckTx`
- `PrepareProposal`
- `ProcessProposal`
- `FinalizeBlock`
- `Commit`
- a minimal `/app/info` `Query`

Other ABCI methods inherit CometBFT's `BaseApplication` defaults in this PoC.

`FinalizeBlock` stages the deterministic transition in the Python service and returns the predicted application hash. `Commit` atomically applies the staged transition. SQLite transactions make the application commit all-or-nothing, and pending finalize state is persisted for restart recovery.

## Important limitations

- This is an integration PoC, not an audited production ABCI application.
- Full CometBFT state-sync integration is not implemented.
- Validator-set updates are not driven by Crakbit application transactions.
- Production key management, HSMs, remote signer design and DDoS architecture are not implemented.
- Multi-host CometBFT networks still require independent node homes, consensus keys, secure P2P configuration, firewall policy and sustained fault/soak testing.
- CRKBIT in this environment is test-only. Production CRKBIT has not launched and there is no official token sale.
