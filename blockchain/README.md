# Crakbit Chain — v0.28 Launch Rehearsal / Corroborated Evidence Alpha

**Current package:** `0.28.0a1`  
**Consensus candidate:** CometBFT `v0.40.0`  
**Execution path:** `crakbit-execution/3`  
**Status:** launch-rehearsal / independently-corroborated-evidence tooling — **not production mainnet**.

Production CRKBIT has **not** launched. There is no official presale or production token contract. Do not use this software to custody real value.

## v0.28 scope

v0.28 builds on the v0.27 final mainnet-candidate policy layer and adds the rehearsal/evidence boundary immediately before any real launch/no-launch decision:

- signed launch runbook with 4+ validators, genesis steps, exact validator start order and rollback steps,
- dry-run/no automatic network mutation, DNS change or fund movement,
- signed DNS/RPC/explorer cutover rehearsal with rollback and redundant failover checks,
- configurable public-edge availability/latency/error-rate/capacity/failover evidence,
- protected HSM/remote-signer rotation + catastrophic-recovery drill records,
- coordinated upgrade + rollback rehearsal bound to the signed v0.27 upgrade plan,
- final signed risk register with unmitigated high/critical risks as hard blockers,
- signed technical reviewer sign-offs bound to the exact v0.27 final report,
- required technical review scopes for consensus/application, network/RPC, cryptography/key-management and browser wallet,
- external reproducible-build/transitive-dependency attestation,
- aggregate launch-rehearsal gate,
- signed exact release-candidate freeze after the rehearsal gate passes,
- signed manual human decision record (`hold` or `approve-launch-window`) with no automatic execution,
- v0.28 regression tests.

See [`V0.28.md`](V0.28.md).

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

## v0.28 commands

```text
launch-runbook-v28-build
launch-runbook-v28-verify
cutover-rehearsal-v28-build
cutover-rehearsal-v28-verify
edge-slo-v28-build
edge-slo-v28-verify
signer-drill-v28-build
signer-drill-v28-verify
upgrade-rehearsal-v28-build
upgrade-rehearsal-v28-verify
risk-register-v28-build
risk-register-v28-verify
review-signoff-v28-build
review-signoff-v28-verify
repro-attestation-v28-build
repro-attestation-v28-verify
rehearsal-gate-v28-build
release-freeze-v28-build
release-freeze-v28-verify
launch-decision-v28-record
launch-decision-v28-verify
```

All v0.27 and earlier review/public-testnet/governance commands remain available through CLI delegation.

## Exact candidate binding

The v0.28 aggregate gate takes a signed v0.27 final report as its root candidate identity. Every launch-runbook, cutover, SLO, protected-signer, upgrade, risk, reviewer and reproducible-build artifact must match the exact source commit and candidate identity.

Technical reviewer sign-offs must additionally bind the exact v0.27 final-report manifest SHA-256. A review signed for an older or different final report does not satisfy the gate.

## Launch-rehearsal gate

The modeled gate requires:

- a valid v0.27 final report with `mainnet_candidate_gate_satisfied=true`,
- a passing launch runbook,
- a passing cutover rehearsal,
- at least two unique passing edge-SLO records,
- a passing protected-signer recovery drill,
- a passing coordinated upgrade/rollback rehearsal,
- no unmitigated high/critical risks,
- a passing external reproducible-build/transitive-dependency attestation,
- passed independent technical review sign-offs covering all required technical scopes,
- at least three unique reviewer signing identities by default.

Even after all checks pass the artifact records:

```text
launch_rehearsal_gate_satisfied=true
manual_launch_decision_required=true
automatic_launch=false
production_mainnet_ready=false
production_mainnet_launched=false
production_crkbit_launched=false
```

## Risk boundary

`risk-register-v28-build` allows low/medium residual risks to be documented, including accepted risks with explicit rationale. High/critical risks block the modeled rehearsal gate unless they are marked mitigated.

This does not replace independent risk judgment; it prevents the release evidence model from silently treating an unmitigated high/critical risk as launch-ready.

## Manual launch decision boundary

`launch-decision-v28-record` supports only `hold` or `approve-launch-window`. The command records a signed human decision but does not:

- start validators,
- change production DNS,
- move treasury/user funds,
- enable a token sale,
- mark mainnet as launched.

Actual production launch remains a separate external operational act after real evidence is reviewed.

## Production boundary

The v0.28 code can model and verify evidence, but it does not independently prove the real-world claims behind that evidence. Before production-value launch consideration the project still needs genuine independent-host operation, real genesis ceremony, long soak/fault/state-sync/governance evidence, protected key custody, production public-edge measurements, genuinely independent review, final economics/legal conclusions and a deliberate human launch/no-launch decision.

See [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md).

## Mining note

The Mining Lab remains a **test-only work-reward service**, not consensus mining. It does not mint new supply and does not create CometBFT blocks.
