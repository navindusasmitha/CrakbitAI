# Crakbit Chain — v0.30 Continuous Operations / Evidence Publication Alpha

**Current package:** `0.30.0a1`  
**Consensus candidate:** CometBFT `v0.40.0`  
**Execution path:** `crakbit-execution/3`  
**Status:** continuous-operations / evidence-publication tooling — **not production mainnet**.

Production CRKBIT has **not** launched. There is no official presale or production token contract. Do not use this software to custody real value.

## v0.30 scope

v0.30 builds on v0.29 real-host evidence and adds long-running operator automation without turning monitoring evidence into an automatic launch mechanism:

- signed non-secret monitor inventory for 4+ validators,
- secret-bearing inventory fields rejected,
- read-only CometBFT monitoring samples,
- height-spread and same-height application-hash divergence detection,
- resumable hash-chained checkpoints,
- default seven-day target and minimum 0.99 success ratio,
- continuous collector script with resume behavior,
- raw evidence archive SHA-256 + retention manifests,
- active RPC/explorer/gateway HTTP health probes,
- redundant public-edge gate requiring two healthy endpoints per role by default,
- protected signer/HSM-equivalent connectivity checks without private-key access,
- public evidence bundle bound to the exact v0.29 real-evidence freeze,
- signed operator checklist with explicit manual DNS/treasury/launch controls,
- v0.30 regression tests.

See [`V0.30.md`](V0.30.md).

## Install / test

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q
```

Go bridge tests:

```bash
cd cometbft-app
go mod download
go test -mod=mod ./...
```

## v0.30 commands

```text
monitor-inventory-v30-build
monitor-inventory-v30-verify
monitor-sample-v30-probe
monitor-sample-v30-verify
monitor-checkpoint-v30-build
monitor-checkpoint-v30-verify
archive-v30-build
archive-v30-verify
edge-v30-probe
edge-v30-verify
edge-gate-v30-build
edge-gate-v30-verify
signer-v30-probe
signer-v30-verify
public-evidence-v30-build
public-evidence-v30-verify
operator-checklist-v30-build
operator-checklist-v30-verify
```

All v0.29 and earlier commands remain available through CLI delegation.

## Monitor inventory

The monitoring inventory is deliberately non-secret. It stores validator/operator/provider/region labels plus public read-only RPC endpoints. Private keys, passwords, seeds, tokens, API keys and provider credentials are rejected.

The central monitoring inventory does **not** replace v0.29 multi-operator evidence. It exists to run continuous read-only observation from a dedicated monitoring system.

## Continuous collector

Use the dedicated monitor script:

```bash
python scripts/run_v30_monitor.py \
  --inventory private/monitor-inventory-v30.json \
  --key private/monitor-evidence-key.json \
  --session-id public-testnet-7d-01 \
  --output-dir runtime/evidence/monitor-7d \
  --interval-seconds 30 \
  --target-duration-seconds 604800 \
  --minimum-success-ratio 0.99
```

Each successful observation is signed and written as a separate sample. The checkpoint is also signed and contains a hash-chain head covering the sequence of sample-manifest hashes. If the process restarts, the same session can resume from the last checkpoint.

The monitoring evidence key should be dedicated to monitoring. Do not reuse validator consensus keys.

## Archive / retention

`archive-v30-build` creates a signed inventory of raw evidence files, recording role, file name, size and SHA-256. The default retention recommendation is 90 days and the builder rejects values below 30 days.

The manifest contains hashes, not the raw evidence itself.

## Public-edge monitoring

`edge-v30-probe` supports read-only HTTP checks for:

```text
rpc
explorer
gateway
```

The aggregate edge gate requires at least two passing endpoints for every role by default. This verifies basic reachability/latency redundancy only; it is not a substitute for DDoS, WAF or independent capacity engineering.

## Protected signer monitoring

`signer-v30-probe` opens a TCP connection to an operator-specified protected signer/HSM-equivalent service and creates a signed observation bound to a prior rotation-drill manifest hash.

The tool does not request, read, copy or export the validator private key. Connectivity alone is not proof that the signer/HSM is securely configured.

## Public evidence bundle

`public-evidence-v30-build` requires:

- exact valid v0.29 real-evidence freeze,
- completed seven-day monitor checkpoint,
- monitor success ratio >= 0.99,
- archive retention >= 30 days,
- passing redundant edge gate,
- at least one passing protected-signer monitor record.

It can additionally hash SBOM, genesis, review summaries, runbooks or other publication artifacts.

Even if all checks pass:

```text
manual_launch_decision_required=true
automatic_launch=false
production_mainnet_ready=false
production_mainnet_launched=false
production_crkbit_launched=false
```

## Operator checklist

The final signed checklist requires operators to explicitly confirm validator services, backups, alerts, rollback, incident contacts, manual DNS control, manual treasury movement and manual launch approval.

The checklist is an operational record. It never performs those actions.

## Production boundary

v0.30 makes evidence collection more durable and reviewable, but software cannot prove provider/operator independence, a physical HSM deployment, reviewer independence or a real seven-day campaign unless those activities actually occur. Real independent-host operation, independent security/economic/legal review and an explicit human launch/no-launch decision remain required before production-mainnet consideration.

See [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md).

## Mining note

The Mining Lab remains a **test-only work-reward service**, not consensus mining. It does not mint new supply and does not create CometBFT blocks.
