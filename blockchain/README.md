# Crakbit Chain — v0.27 Final Mainnet-Candidate Policy Alpha

**Current package:** `0.27.0a1`  
**Consensus candidate:** CometBFT `v0.40.0`  
**Execution path:** `crakbit-execution/3`  
**Status:** final mainnet-candidate policy/evidence tooling — **not production mainnet**.

Production CRKBIT has **not** launched. There is no official presale or production token contract. Do not use this software to custody real value.

## v0.27 scope

v0.27 builds on the v0.26 remediation/re-freeze gate and adds the final modeled policy/evidence layer before any production-mainnet consideration:

- signed coordinated upgrade plan,
- exact source/package/schema/migration/rollback binding,
- strict `>2/3` validator-readiness threshold,
- signed normal/emergency governance timelock policy,
- pre-activation cancellation window,
- emergency strict-supermajority requirement,
- emergency policy cannot authorize arbitrary user-balance reassignment or silent supply changes,
- signed CRKBIT economics/genesis parameter freeze,
- supply/decimals/fees/incentive/distribution commitment hash binding,
- explicit no-investment-return and no-token-sale-authorization claims,
- signed independent economic-security review attestation,
- signed independent legal/regulatory review attestation,
- exact review binding to the frozen economics manifest and candidate source commit,
- deterministic candidate-identity SHA-256,
- separate signed release approvals,
- minimum three unique release approvers/signers,
- final candidate gate consuming operational readiness + v0.26 remediation + governance + economics + upgrade + external review + release approvals,
- signed final readiness report,
- v0.27 regression tests.

See [`V0.27.md`](V0.27.md).

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

## v0.27 commands

```text
upgrade-plan-v27-build
upgrade-plan-v27-verify
governance-policy-v27-build
governance-policy-v27-verify
economics-freeze-v27-build
economics-freeze-v27-verify
external-review-v27-build
external-review-v27-verify
candidate-identity-v27-build
release-approval-v27-build
release-approval-v27-verify
final-gate-v27-build
final-report-v27-build
final-report-v27-verify
```

All v0.26 and earlier review/public-testnet/governance commands remain available through CLI delegation.

## Final candidate identity

The v0.27 candidate identity commits to:

- exact Git source commit,
- package and CometBFT versions,
- application + consensus genesis hashes,
- dependency-lock + SBOM hashes inherited from v0.26,
- v0.24 operational-readiness artifact hash,
- v0.26 remediation-gate artifact hash,
- governance-policy manifest hash,
- economics-freeze manifest hash,
- coordinated-upgrade manifest hash,
- economic-security review manifest hash,
- legal/regulatory review manifest hash.

Release approvals must sign this exact identity. An approval for a different identity or source commit is rejected.

## Release approval model

A single release signer is intentionally insufficient. The modeled final gate requires at least three unique approver IDs and three unique signing identities, and every decision must be `approve`.

This is evidence tooling, not an automatic launch mechanism. The final gate never starts validators, changes DNS, publishes a token contract, moves funds or changes chain state.

## Economics boundary

v0.27 accepts economics parameters only from an explicit JSON file. It does not invent final economics. The 21,000,000 / 8-decimal values used during development remain proposals unless they are deliberately frozen and independently reviewed.

The economics artifact explicitly records:

```text
investment_return_promised=false
token_sale_authorized_by_this_artifact=false
requires_independent_economic_and_legal_review=true
production_mainnet_ready=false
```

## Production boundary

Even when `mainnet_candidate_gate_satisfied=true`, v0.27 deliberately keeps:

```text
production_mainnet_ready=false
production_mainnet_launched=false
production_crkbit_launched=false
```

Actual production launch still requires real independently managed validators, independently corroborated operations and review evidence, protected key custody, production public-edge engineering/capacity, final operator procedures, an explicit human launch decision and any required legal/regulatory steps.

See [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md).

## Mining note

The Mining Lab remains a **test-only work-reward service**, not consensus mining. It does not mint new supply and does not create CometBFT blocks.
