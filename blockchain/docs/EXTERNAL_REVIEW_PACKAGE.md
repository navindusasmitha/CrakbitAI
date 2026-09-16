# Crakbit Chain — External Review Package

This document defines the evidence package that should be assembled before asking independent reviewers to assess Crakbit Chain. It does not represent an audit or certification.

## Scope statement

Reviewers should be told explicitly that:

- the current Python consensus is a research/devnet implementation,
- the intended production direction is migration/integration with an established reviewed BFT core,
- CRKBIT on the current network is test-only,
- no real-value custody claim is made,
- v0.13 adds a deterministic execution-process boundary but does not add an external finalization endpoint.

## Required source artifacts

Include immutable commit/tag references for:

- `crakbit_chain/models.py`
- `crakbit_chain/storage.py`
- `crakbit_chain/node.py`
- `crakbit_chain/app_protocol.py`
- `crakbit_chain/execution_service.py`
- `crakbit_chain/transport_security.py`
- `crakbit_chain/history_archive.py`
- `crakbit_chain/release_artifacts.py`
- `crakbit_chain/limits.py`
- genesis/bootstrap tooling
- validator deployment templates

## Required protocol documentation

- `SPEC.md`
- `SECURITY.md`
- `docs/ADR-0001-consensus-direction.md`
- `docs/EXECUTION_PROTOCOL_V1.md`
- `V0.11.md`
- `V0.12.md`
- `V0.13.md`

## Evidence to attach

1. GitHub Actions test logs for the exact reviewed commit.
2. Signed release/genesis manifest and its expected release-signer address.
3. Genesis file used by the test network.
4. Validator public inventory without private keys.
5. Soak-test JSONL plus generated summary.
6. Fault-injection scenarios and observed results.
7. Backup/restore-drill output.
8. `crakchain doctor --full` results from representative validators.
9. Network/firewall/reverse-proxy configuration used during the test.
10. Incident log covering crashes, divergence, certificate rotation and operator interventions.

## Review questions

### Consensus / state-machine safety

- Are transaction ordering and application state transitions deterministic?
- Can two honest application instances produce different application hashes from identical inputs?
- Are replay/nonces/balances handled consistently across crash/restart boundaries?
- Is the proposed external-consensus process boundary sufficient to prevent unauthorized state mutation?
- What invariants must be enforced before a future `FinalizeBlock`/`Commit` interface exists?

### Networking and validator identity

- Is mTLS identity correctly bound to the configured validator identity?
- Are certificate pin overlap and rotation procedures safe under partial rollout?
- Can replay, stale requests or forged validator identities bypass request authentication?
- Are operator and public RPC surfaces adequately isolated?

### Recovery and history

- Can snapshot and archive recovery produce a state/history combination inconsistent with the finalized chain?
- Are backup/restore and snapshot-import crash cases safe?
- Are archive hashes, state roots and genesis anchors sufficient for auditability?

### Abuse resistance

- Are request-size, mempool, transaction-size and rate limits applied before expensive work?
- What upstream DDoS/reverse-proxy protections remain mandatory?
- Is the test faucet isolated from validator keys and sufficiently bounded for a public test network?

## Required reviewer outputs

Request findings grouped by severity and component, with reproduction conditions, affected commit, recommended remediation and whether the finding blocks continued public-testnet operation.

Any mainnet planning should remain blocked until critical/high findings are resolved, a reviewed BFT integration exists, and the test network has completed a meaningful sustained public-testnet period without unexplained safety failures.
