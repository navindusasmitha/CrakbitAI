# Crakbit Chain Security Notes — v0.19 Alpha

Crakbit Chain is currently **research/public-testnet/review-candidate infrastructure**, not an audited production mainnet. It must not be used to custody real value.

Production CRKBIT has not launched. There is no official presale or production token contract.

## Trust-domain separation

The repository separates browser-wallet, public-gateway, CometBFT consensus, ABCI bridge, external execution, explorer, release/review signing, faucet and Mining Lab roles. Keys must not be reused across these roles.

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
    └→ explorer/review/release evidence tooling
```

The older Python prevote/precommit chain remains research-only and is not the intended production BFT path.

## CometBFT state sync

The external application supports the ABCI snapshot lifecycle:

```text
ListSnapshots
OfferSnapshot
LoadSnapshotChunk
ApplySnapshotChunk
```

Snapshot acceptance is bound to the application hash supplied through the CometBFT state-sync trust path. Chunk hashes, full artifact hash, chain/genesis identity, fixed supply and deterministic application hash are rechecked before restore. Restore remains restricted to pristine application state.

Code-level lifecycle support does not prove production recovery. Clean-host independent-validator recovery, malicious-peer behavior, interrupted transfer, storage faults and large-snapshot behavior still require operational evidence and review.

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

## v0.19 review-remediation gate

`review-findings-build` and `review-findings-check` provide a machine-readable remediation gate. The automated gate remains blocked when a high/critical finding is unresolved or when a remediated high/critical finding has no recorded regression-test reference.

This is intentionally conservative. An `accepted` high/critical risk still blocks the automated gate. Clearing this matrix does not claim that the original review was independent, complete or sufficient for production.

## v0.19 reproducible-build evidence

The CI workflow builds the Python wheel twice under a fixed `SOURCE_DATE_EPOCH` and builds the Go bridge twice with `-trimpath -buildvcs=false`. The resulting artifacts are compared byte-for-byte using SHA-256.

A matching CI result proves only that the supplied outputs were identical in that CI environment. It is **not** independent reproducibility evidence from a second organization/toolchain/environment.

## v0.19 SBOM scope

The CycloneDX 1.5 SBOM records direct Python runtime dependencies, direct Go requirements and hashes of dependency input files. It deliberately marks transitive completeness as false.

A future production release still needs a complete transitive SBOM/dependency-lock/provenance process generated from the exact release environment and independently reviewed.

## Signed release provenance

The v0.19 release-provenance envelope binds:

- exact Git source commit,
- package version,
- declared CometBFT version,
- chain ID/genesis fingerprint and genesis-file SHA-256,
- selected artifact hashes,
- optional SBOM and reproducibility-report hashes,
- dedicated Ed25519 release signer identity.

The signed format keeps `independent_security_review_completed=false`, `production_mainnet_ready=false`, and `production_crkbit_launched=false`. A valid signature authenticates the manifest; it is not an audit certificate.

Release/review signing keys must be separated from validator, TLS, faucet, mining-reward and user-wallet keys.

## Operations-drill evidence

The signed operations-drill format can record upgrade, rollback, incident-response, disaster-recovery and validator-lifecycle exercises. It binds source commit, operator-reported timing/result and supporting artifact hashes.

The format explicitly distinguishes operator-reported success from independent verification. Creating an evidence file does not prove that a live production network, independent operator, remote signer or HSM was involved.

## Faucet and Mining Lab

Faucet and Mining Lab services require dedicated non-validator keys. The Mining Lab is **not consensus mining**: it verifies a test browser work challenge and pays from an already funded reward wallet. It must not mint new supply, produce CometBFT blocks, alter voting power or be marketed as guaranteed earnings.

## Explorer and SQLite state

The explorer remains separate from execution state and v0.18+ reconciliation can compare a deployed index with a clean rebuild. SQLite is still used across research/application/index/service state.

Production review must cover fsync/durability expectations, disk-full behavior, corruption, backup consistency, abrupt power loss, filesystem semantics, growth/retention limits, schema migrations and rollback behavior.

## Secrets

Never commit or share seed phrases, wallet private keys, CometBFT private-validator keys, signer/HSM credentials, TLS private keys, faucet/mining reward keys, release/review/evidence signing keys, execution-service bearer tokens or API secrets.

Do not send these through support chats or issue trackers.

## Required before production mainnet

Major open gates still include sustained independent-host validator operation, live clean-host state-sync evidence, real fault/partition/load campaigns, production WAF/DDoS/capacity engineering, deployed remote-signer/HSM custody, multi-operator genesis ceremony, complete transitive supply-chain review, independent consensus/application/network/cryptography/browser-wallet reviews, incident-response drills, finalized economics/incentives and applicable legal review.

The canonical gate list is [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md).

Until those gates are satisfied, use **research**, **public testnet**, **review candidate** or **mainnet-candidate infrastructure** — not production mainnet.
