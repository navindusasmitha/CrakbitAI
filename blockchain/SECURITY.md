# Crakbit Chain Security Notes — v0.21 Alpha

Crakbit Chain is currently **research/public-testnet/review-candidate infrastructure**, not an audited production mainnet. It must not be used to custody real value.

Production CRKBIT has not launched. There is no official presale or production token contract.

## Trust-domain separation

The repository separates browser-wallet, public-gateway, CometBFT consensus, ABCI bridge, external execution, validator-governance state, explorer, release/review signing, faucet and Mining Lab roles. Keys must not be casually reused across these roles.

```text
browser wallet / governance tx
        │ signed input
        ▼
public gateway / controlled RPC
        │
        ▼
CometBFT v0.40.0
        │ ABCI
        ▼
Go bridge 0.21
        │ authenticated private HTTP
        ▼
crakbit-execution/3
        │
        ├→ account state
        ├→ active/pending validator-governance state
        ├→ governance-aware native ABCI state sync
        └→ explorer/review/release evidence tooling
```

The older Python prevote/precommit chain remains research-only and is not the intended production BFT path.

## Validator governance — v0.21

v0.21 introduces a replicated testnet validator-governance transaction for `join`, `remove` and `replace` operations. A request commits to chain/genesis identity, source and target validator-set hashes, update contents, ABCI emission height and modeled effective height.

Approvals are verified against the **currently committed source validator set** and require voting power strictly greater than two-thirds. Duplicate approvals, unknown validators, public-key/address mismatches, stale source-set hashes and invalid signatures are rejected.

For the default four-validator equal-power lab, quorum is 3 of 4 validators.

### Key handling

Each validator operator should inspect the same public governance request and sign it locally. Do not centralize validator private keys merely to reach quorum. A future production candidate requires stronger separation between consensus signing, governance authorization, operator access and recovery authority, preferably using reviewed remote-signer/HSM-equivalent controls.

## Application-hash binding

`crakbit-execution/3` includes active and pending validator governance state in the deterministic application hash. This is required so validators cannot honestly report an identical application hash while disagreeing about the validator-set transition state.

ABCI validator updates are returned from `FinalizeBlock` only after the governance transaction has been validated against replicated committed state. v0.21 models an update returned at height `H` becoming effective at `H+2` and separately activates the application-side validator state at that modeled effective height.

This height behavior and cross-node convergence still require independent multi-host testing and review before production use.

## Crash/replay behavior

The governed execution path preserves the staged FinalizeBlock → atomic Commit boundary. Governance state, transfers, transaction records and application metadata are committed in one SQLite transaction.

An identical FinalizeBlock replay at an already committed height can return the recorded validator update. A conflicting replay is rejected. Restart/fault behavior at `H`, `H+1` and `H+2` activation boundaries still needs multi-node campaign evidence.

## Schema migration

Schema `21` adds validator-governance tables. Existing non-pristine schema-19/20 external-application databases are not silently upgraded by the v0.21 service. Use the offline-copy migration and verify rollback before considering an operator-controlled testnet upgrade.

Migration success does not prove that a rolling multi-node upgrade is safe.

## Governance-aware CometBFT state sync

v0.21 state-sync snapshots include account state, active validator set, pending validator change, governance hash and the combined application hash. Snapshot acceptance remains bound to the application hash supplied by the CometBFT trust path, with chunk and full-artifact verification and pristine-state restore requirements.

State sync restores the deterministic current governance state needed for future execution; it does not fabricate historical governance events. Live independent-host recovery with a pending validator change remains an external test requirement.

## Browser wallet

Wallet key generation/signing is local to the browser and the local vault uses PBKDF2-SHA256-derived key material with AES-GCM. The gateway should receive signed transactions, not private keys.

The wallet remains an alpha web wallet, not an audited hardware-wallet replacement. Important risks include compromised same-origin JavaScript, malicious browser extensions, compromised endpoints, phishing/fake origins, vault-password guessing and clipboard substitution.

See [`docs/WALLET_THREAT_MODEL.md`](docs/WALLET_THREAT_MODEL.md).

## Public gateway / edge

The hardened gateway uses same-origin defaults, restrictive CSP/security headers and restart-persistent local rate limits. These controls are not a complete distributed WAF/DDoS system. Execution-service, ABCI, signer and validator-operator surfaces should remain private/authorized.

## Validator key security

Disposable lab validator keys must never be promoted to a production network. A production candidate requires protected signing, anti-double-sign controls, backup/recovery procedures, operator separation and tested incident drills.

See [`docs/VALIDATOR_REMOTE_SIGNER.md`](docs/VALIDATOR_REMOTE_SIGNER.md).

## Release/review evidence

v0.19+ remediation matrices, reproducible-build comparisons, direct-dependency SBOMs, signed release provenance and operations evidence remain useful review artifacts. They do not replace independent security review or complete transitive supply-chain verification.

## Faucet and Mining Lab

Faucet and Mining Lab services require dedicated non-validator keys. The Mining Lab is **not consensus mining**: it verifies a test browser work challenge and pays from an already funded reward wallet. It must not mint new supply, produce CometBFT blocks, alter voting power or be marketed as guaranteed earnings.

## Secrets

Never commit or share seed phrases, wallet private keys, CometBFT private-validator keys, governance signing keys, signer/HSM credentials, TLS private keys, faucet/mining reward keys, release/review/evidence signing keys, execution-service bearer tokens or API secrets.

Do not send these through support chats or issue trackers.

## Required before production mainnet

Major open gates include multi-host validator lifecycle campaigns, activation-boundary restart/partition/state-sync testing, sustained independent-host validator operation, real fault/load campaigns, protected remote/HSM signing and governance-key separation, multi-operator genesis ceremony, complete transitive supply-chain review, independent consensus/application/governance/network/cryptography/browser-wallet review, incident-response drills, production DDoS/capacity engineering, finalized economics/incentives and applicable legal review.

The canonical gate list is [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md).

Until those gates are satisfied, use **research**, **public testnet**, **review candidate** or **mainnet-candidate infrastructure** — not production mainnet.
