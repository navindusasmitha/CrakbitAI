# Crakbit Chain — v0.29 Real Independent-Host Execution Alpha

**Current package:** `0.29.0a1`  
**Consensus candidate:** CometBFT `v0.40.0`  
**Execution path:** `crakbit-execution/3`  
**Status:** real independent-host execution/evidence tooling — **not production mainnet**.

Production CRKBIT has **not** launched. There is no official presale or production token contract. Do not use this software to custody real value.

## v0.29 scope

v0.29 builds on the v0.28 launch-rehearsal layer and introduces an evidence path designed around **running independent hosts**:

- live CometBFT `/status` and `/abci_info` probes,
- signed per-validator live host observations,
- exact source/candidate/application-genesis/consensus-genesis binding,
- explicit private execution/ABCI and protected-signer assertions,
- RPC URL credential rejection,
- signed 4+ validator cluster observations,
- unique validator/operator/evidence-signer checks,
- provider/region diversity gates,
- maximum observation-window and block-height-spread checks,
- same-height application-hash divergence detection,
- signed operator genesis attestations and a 4+ operator ceremony gate,
- signed soak evidence from signed cluster samples,
- minimum configured soak success ratio of 0.99,
- default mainnet-candidate soak target of 7 days,
- signed fault/recovery results bound to raw evidence-file SHA-256,
- required restart/process-kill/partition/latency/packet-loss/load/storage/state-sync/governance/upgrade campaign coverage,
- exact binding to the supplied v0.28 release freeze and rehearsal gate,
- signed v0.29 real-evidence freeze after the real-execution gate passes,
- v0.29 regression tests.

See [`V0.29.md`](V0.29.md).

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

## v0.29 commands

```text
live-host-v29-probe
live-host-v29-verify
cluster-v29-build
cluster-v29-verify
genesis-attest-v29-build
genesis-attest-v29-verify
genesis-gate-v29-build
genesis-gate-v29-verify
soak-v29-build
soak-v29-verify
fault-result-v29-build
fault-result-v29-verify
real-gate-v29-build
real-freeze-v29-build
real-freeze-v29-verify
```

All v0.28 and earlier commands remain available through CLI delegation.

## Live host evidence

`live-host-v29-probe` actively reads the CometBFT RPC endpoint and records:

- chain ID,
- node ID,
- latest CometBFT height,
- ABCI application height,
- application hash,
- catching-up status.

It rejects endpoints with embedded username/password credentials. The evidence artifact contains no validator private key or provider secret.

## Cluster gate

The default cluster gate requires at least four unique validators, four unique operators and four unique evidence signing keys, plus at least two providers and two regions. The observations must describe the same candidate/genesis/chain, remain within a small observation window, have a block-height spread at most 2 by default and show no conflicting application hash for the same ABCI height.

This is stronger than a static inventory but still does not independently prove that the declared providers/operators are genuinely independent.

## Genesis ceremony gate

Each operator independently signs the exact source commit, candidate identity, application genesis, consensus genesis, chain ID and its own validator/node public identity. The ceremony gate requires at least four unique validators/operators/signers and unanimous approval of the exact same genesis artifacts.

Do not centralize validator private keys to create this evidence.

## Soak evidence

The v0.29 soak builder consumes signed cluster samples. It requires at least two samples, rejects configured success thresholds below 0.99 and rejects configured durations below 24 hours. The intended v0.29 candidate campaign uses `604800` seconds (7 days) or longer.

A passing soak requires no same-height application-hash divergence.

## Fault/recovery evidence

A fault result must be authorized and must record a passed result, recovery verification, application-hash reconvergence and no data loss. It also hashes a raw evidence file so reviewers can verify that the result is tied to preserved logs/output.

The aggregate gate requires passing evidence for all ten campaign categories:

```text
restart
process-kill
partition
latency
packet-loss
load
storage
state-sync
governance
upgrade
```

Fault campaigns must only target infrastructure owned/administered by the operator or explicitly authorized for testing.

## Real execution gate

The v0.29 real-execution gate verifies the exact v0.28 release freeze and the exact rehearsal gate it commits to, then requires passing live cluster, multi-operator genesis, long-lived soak and complete fault/recovery evidence for the same source/candidate.

Even when all checks pass, the artifact deliberately records:

```text
real_execution_gate_satisfied=true
manual_launch_decision_required=true
automatic_launch=false
production_mainnet_ready=false
production_mainnet_launched=false
production_crkbit_launched=false
```

## Production boundary

v0.29 provides live observation and stronger evidence aggregation, but repository code cannot itself provision independent hosts, prove organizational independence, perform a seven-day campaign instantly, verify a physical HSM deployment or replace independent security/economic/legal review.

Those external tasks must actually happen before production-mainnet consideration.

See [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md).

## Mining note

The Mining Lab remains a **test-only work-reward service**, not consensus mining. It does not mint new supply and does not create CometBFT blocks.
