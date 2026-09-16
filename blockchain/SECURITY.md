# Crakbit Chain Security Notes — v0.20 Alpha

Crakbit Chain is currently **research/public-testnet/review-candidate infrastructure**, not an audited production mainnet. It must not be used to custody real value.

Production CRKBIT has not launched. There is no official presale or production token contract.

## Trust-domain separation

The repository separates browser-wallet, public-gateway, CometBFT consensus, ABCI bridge, external execution, explorer, release/review/migration signing, faucet and Mining Lab roles. Keys must not be reused across these roles.

```text
browser wallet
    │ signed transaction only
    ▼
public gateway / controlled edge
    │
    ▼
CometBFT v0.40.0
    │ ABCI
    ▼
Go bridge
    │ authenticated private HTTP
    ▼
crakbit-execution/2
    │
    ├→ application DB
    ├→ native ABCI state sync
    ├→ explorer/review/release evidence
    └→ offline schema/lifecycle rehearsal tooling
```

The older Python prevote/precommit chain remains research-only and is not the intended production BFT path.

## CometBFT state sync

The external application supports `ListSnapshots`, `OfferSnapshot`, `LoadSnapshotChunk` and `ApplySnapshotChunk`. Snapshot acceptance is bound to the application hash supplied through the CometBFT state-sync trust path. Chunk hashes, full artifact hash, chain/genesis identity, fixed supply and deterministic application hash are rechecked before restore. Restore remains restricted to pristine application state.

Code-level lifecycle support does not prove production recovery. Clean-host independent-validator recovery, malicious-peer behavior, interrupted transfer, storage faults and large-snapshot behavior still require operational evidence and review.

## v0.20 schema migration safety

v0.20 introduces explicit external-application schema version `20`. Legacy `crakbit-execution/2` databases without an explicit schema-version marker are treated as the v0.19 baseline.

The migration path is deliberately **offline-copy-first**:

- the source database is not mutated by `migration-copy` or `upgrade-rehearse`,
- SQLite backup API is used to create the candidate copy,
- source logical fingerprints are checked before and after the backup,
- the v19 → v20 migration runs on the copy only,
- existing application-state tables must keep the same logical fingerprint,
- rollback is rehearsed on a second disposable copy,
- rollback must recover the original logical fingerprint.

The v0.20 migration currently adds migration/lifecycle metadata tables and the explicit schema-version marker; it does not rewrite balances, nonces, transactions, consensus block hashes or external commit rows.

A successful rehearsal does **not** mean an online rolling upgrade is safe. Operators still need backups, maintenance windows, version coordination, state-sync recovery and independent testing across the actual deployment topology.

## v0.20 validator lifecycle boundary

v0.20 can build and verify signed `join`, `remove` and `replace` validator lifecycle **drill plans**. These plans model CometBFT public-key/power updates and record the FinalizeBlock emission height and expected effective height.

They deliberately do **not** alter live consensus. The plan records `live_abci_validator_updates_emitted=false` and `consensus_change_applied=false`.

This boundary is important: validator updates must be derived from deterministic replicated application state. Loading an operator-local plan on only one node could cause different ABCI `FinalizeBlock` responses across validators and create a consensus-safety risk. A future phase must define a reviewed replicated authorization/activation mechanism, include lifecycle state in the application hash and prove replay/restart behavior before live validator updates are enabled.

Lifecycle signing keys are evidence/authorization-research keys and must not be reused as CometBFT private-validator keys.

## Compatibility checks

The v0.20 compatibility matrix currently declares:

- package `0.20.0a1`,
- execution protocol `crakbit-execution/2`,
- supported external application schemas `19` and `20`,
- recommended schema `20`,
- CometBFT candidate `v0.40.0`,
- live validator updates disabled,
- production-mainnet readiness false.

Compatibility metadata is a deployment guardrail, not a substitute for multi-node upgrade testing or independent consensus/application review.

## Browser wallet

Wallet key generation/signing is local to the browser and the local vault uses PBKDF2-SHA256-derived key material with AES-GCM. The gateway should receive signed transactions, not private keys.

The wallet remains an alpha web wallet, not an audited hardware-wallet replacement. Important risks still include compromised same-origin JavaScript, malicious browser extensions, compromised endpoints, phishing/fake origins, vault-password guessing, clipboard substitution and compromised read data.

See [`docs/WALLET_THREAT_MODEL.md`](docs/WALLET_THREAT_MODEL.md).

## Public gateway / edge

The hardened gateway uses same-origin defaults, restrictive CSP/security headers and restart-persistent local rate limits. The public-testnet NGINX profile provides a single-edge TLS/rate-limit scaffold.

These controls are not a complete distributed WAF/DDoS system. Production design still requires reviewed proxy trust, certificate automation, redundant edges, shared abuse controls and capacity testing. Execution-service, ABCI, remote-signer and validator-operator surfaces should remain private/authorized.

## Validator key security

Disposable lab validator keys must never be promoted to a production network. A production candidate requires a remote signer, HSM or equivalent protected signing design with anti-double-sign protection, backup/recovery procedures and tested operator drills.

The current remote-signer helper only configures CometBFT's signer address. It does not implement or audit an HSM.

See [`docs/VALIDATOR_REMOTE_SIGNER.md`](docs/VALIDATOR_REMOTE_SIGNER.md).

## Review / reproducible-release controls

The v0.19+ review-finding gate blocks unresolved high/critical findings and requires regression-test references for remediated high/critical findings. CI also performs byte-for-byte reproducibility checks for supplied Python/Go artifacts and generates a direct-dependency CycloneDX SBOM.

These are useful engineering controls, but they are not independent security review, independent reproducible-build evidence or a complete transitive supply-chain audit.

Signed release, review, migration and operations manifests authenticate the exact metadata/artifact hashes they contain. A signature does not turn operator-reported evidence into independent evidence and does not make the chain production-ready.

## Faucet and Mining Lab

Faucet and Mining Lab services require dedicated non-validator keys. The Mining Lab is **not consensus mining**: it verifies a test browser work challenge and pays from an already funded reward wallet. It must not mint new supply, produce CometBFT blocks, alter voting power or be marketed as guaranteed earnings.

## Explorer and SQLite state

The explorer remains separate from execution state and v0.18+ reconciliation can compare a deployed index with a clean rebuild. SQLite is still used across research/application/index/service state.

Production review must cover fsync/durability expectations, disk-full behavior, corruption, backup consistency, abrupt power loss, filesystem semantics, growth/retention limits, schema migrations and rollback behavior.

## Secrets

Never commit or share seed phrases, wallet private keys, CometBFT private-validator keys, signer/HSM credentials, TLS private keys, faucet/mining reward keys, release/review/evidence/migration/lifecycle signing keys, execution-service bearer tokens or API secrets.

Do not send these through support chats or issue trackers.

## Required before production mainnet

Major open gates still include sustained independent-host validator operation, live clean-host state-sync evidence, real fault/partition/load campaigns, production WAF/DDoS/capacity engineering, deployed remote-signer/HSM custody, multi-operator genesis ceremony, complete transitive supply-chain review, deterministic reviewed live validator-set updates, independent consensus/application/network/cryptography/browser-wallet reviews, incident-response drills, finalized economics/incentives and applicable legal review.

The canonical gate list is [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md).

Until those gates are satisfied, use **research**, **public testnet**, **review candidate** or **mainnet-candidate infrastructure** — not production mainnet.
