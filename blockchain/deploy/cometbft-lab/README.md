# Crakbit v0.16 — CometBFT Lab Runbook

This runbook is for disposable local/public-testnet-candidate testing. It does **not** create a production mainnet.

## Requirements

- Python 3.11+
- Go toolchain supported by the bridge module
- Crakbit blockchain package installed from this repository
- Crakbit CometBFT bridge built from `blockchain/cometbft-app/`
- operator-supplied CometBFT `v0.40.0` binary
- a Crakbit application genesis under `runtime/genesis.json` or an explicitly supplied path

Verify the CometBFT version before generating the lab:

```bash
cometbft version
```

The version should match the repository's currently pinned integration candidate: `v0.40.0`.

## Build the bridge

```bash
cd blockchain/cometbft-app
go mod download
go test -mod=mod ./...
go build -o crakbit-cometbft-bridge .
cd ..
```

## Generate four validators

```bash
python scripts/generate_cometbft_lab.py \
  --cometbft /absolute/path/to/cometbft \
  --bridge ./cometbft-app/crakbit-cometbft-bridge \
  --application-genesis runtime/genesis.json \
  --chain-id crakbit-v16-local \
  --nodes 4 \
  --output runtime/cometbft-lab
```

The generator creates:

```text
runtime/cometbft-lab/
├── node1/ ... node4/       # CometBFT homes, including private validator keys
├── app1/ ... app4/         # external application state locations
├── .secrets/               # execution-service bearer tokens
├── lab-manifest.json       # non-secret topology metadata
└── commands.txt            # operator command reference
```

`runtime/` is intended to remain git-ignored. Do not copy generated private keys into the repository.

## Process topology per validator

Each validator requires three cooperating processes:

```text
CometBFT
  │ ABCI
  ▼
Crakbit Go bridge
  │ authenticated HTTP
  ▼
Crakbit v0.16 external execution service
```

Use the generated `commands.txt` as a reference. Replace `<TOKEN>` by reading that validator's token locally; do not paste bearer tokens into source-controlled scripts.

## Health checks

CometBFT RPC ports are generated with ten-port spacing. Inspect `lab-manifest.json` for exact ports.

Typical status checks:

```bash
curl http://127.0.0.1:27657/status
curl http://127.0.0.1:27667/status
curl http://127.0.0.1:27677/status
curl http://127.0.0.1:27687/status
```

Validators should converge on the same chain ID and progress without an excessive height spread.

For independent-host testing, create a private inventory from `inventory.example.json` and run:

```bash
python scripts/check_testnet_health.py \
  --inventory private/testnet-inventory.json \
  --output runtime/evidence/health.json
```

Do not make private validator RPC or signer endpoints public solely for the health checker. Place operator probes on an authorized management network or use appropriately protected endpoints.

## External application checkpoint test

On one execution data directory:

```bash
crakchain external-snapshot-export \
  --genesis runtime/genesis.json \
  --data runtime/cometbft-lab/app1 \
  --output runtime/evidence/app1-checkpoint.json
```

Verify against a separately trusted CometBFT height/application hash before import:

```bash
crakchain external-snapshot-verify \
  --genesis runtime/genesis.json \
  --snapshot runtime/evidence/app1-checkpoint.json \
  --expected-height EXPECTED_HEIGHT \
  --expected-app-hash EXPECTED_APP_HASH
```

The checkpoint adapter is not yet wired into CometBFT's native state-sync snapshot protocol.

## Crash/replay application drill

Use a wallet key that is funded only by the disposable test genesis:

```bash
python scripts/run_external_crash_matrix.py \
  --genesis runtime/genesis.json \
  --key runtime/treasury.json \
  --output runtime/evidence/crash-matrix.json
```

Do not point this drill at live/value-bearing state.

## Fault testing

Use existing Toxiproxy/soak tooling and ordinary process controls to test:

- latency,
- packet loss / disconnection,
- validator process restart,
- bridge restart,
- execution-service restart,
- one-validator unavailability,
- sustained transaction load.

Record commands, exact source commit, CometBFT version, timestamps and raw outputs. A test that was not actually run must not be published as successful evidence.

## Independent-host transition

A real public-testnet evidence campaign should move each validator to independently managed hosts/providers while keeping:

- consensus validator keys separate,
- execution tokens unique,
- ABCI/execution ports private,
- public RPC behind explicit controls,
- operator management paths authenticated,
- synchronized evidence collection.

See `../../docs/VALIDATOR_REMOTE_SIGNER.md`, `../../docs/WALLET_THREAT_MODEL.md`, `../../docs/MAINNET_GATES.md` and `../../V0.16.md`.
