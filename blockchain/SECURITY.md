# Crakbit Chain Security Notes — v0.17 Alpha

Crakbit Chain is currently **research/public-testnet/mainnet-candidate infrastructure**, not an audited production mainnet. It must not be used to custody real value.

Production CRKBIT has not launched. There is no official presale or production token contract.

## Trust-domain separation

The repository deliberately separates security roles:

```text
browser wallet
    │ signed transaction only
    ▼
public gateway / controlled edge
    ├→ research RPC, or
    ├→ CometBFT JSON-RPC
    └→ private authenticated index/application services

CometBFT
    │ ABCI
    ▼
Go application bridge
    │ authenticated private HTTP
    ▼
crakbit-execution/2
    │
    ├→ external application DB
    ├→ ABCI snapshot state-sync lifecycle
    └→ read-only explorer index source
```

Keys for CometBFT consensus, P2P identity, Crakbit wallets, research validators, TLS, release/evidence signing, faucet and Mining Lab rewards must not be reused across roles.

## Consensus

The old Python prevote/precommit implementation remains research-only. It is not the intended production consensus path.

The external consensus integration candidate is CometBFT `v0.40.0`. The repository contains a Go ABCI bridge and a crash-safe `crakbit-execution/2` application boundary.

Finalized application state is staged first and committed account/state changes are applied atomically in SQLite. Pending finalization survives an application restart. Identical finalized-height replay can be handled idempotently while conflicting replay is rejected.

This integration is still an alpha. Sustained multi-host external-consensus testing and independent review remain required.

## CometBFT state sync

v0.17 wires the external application checkpoint format into the CometBFT ABCI snapshot lifecycle:

```text
ListSnapshots
OfferSnapshot
LoadSnapshotChunk
ApplySnapshotChunk
```

A materialized state-sync snapshot commits to:

- exact chain ID and genesis fingerprint,
- committed external-consensus height,
- last consensus block hash,
- deterministic application hash,
- sorted account balances/nonces,
- fixed issued-supply invariant,
- full transport SHA-256,
- per-chunk SHA-256 hashes.

Snapshot bytes are deterministic for the same committed state and chosen chunk size. Non-deterministic export timestamps are excluded from the ABCI transport artifact.

### Trust model

Snapshot metadata received from peers is **not trusted by itself**. `OfferSnapshot` accepts a snapshot only when the application hash declared in the snapshot metadata exactly matches the application hash supplied by CometBFT for the trusted height. After all chunks arrive, the complete artifact, each chunk, chain/genesis identity, fixed supply and deterministic application hash are verified again before import.

Restore is restricted to pristine external application state. Pre-checkpoint external commit rows are not fabricated.

### Remaining state-sync risk

The code-level ABCI lifecycle now exists, but this does not prove production recovery. Required evidence still includes live multi-validator state-sync from clean hosts, malicious/bad peer behavior, interrupted transfer/retry, storage faults, large snapshots and independent review of the exact CometBFT/application integration.

## Browser wallet

The browser wallet performs key generation/signing locally and encrypts its local vault with PBKDF2-SHA256-derived key material and AES-GCM.

The public gateway is not intended to receive private wallet keys.

The hardened gateway uses restrictive CSP/security headers and same-origin access by default. These controls reduce some web attack surface but do not make the wallet an audited custody product.

Critical remaining threats include compromised same-origin JavaScript, malicious extensions, compromised endpoint/browser, vault password guessing after encrypted-storage theft, phishing/fake origins, clipboard/address substitution and compromised gateway read data.

See [`docs/WALLET_THREAT_MODEL.md`](docs/WALLET_THREAT_MODEL.md).

## Public gateway / edge

Gateway controls include same-origin browser access unless explicitly allow-listed, Content-Security-Policy, frame denial, `nosniff`, no-referrer policy, restrictive permissions policy, same-origin opener/resource policy, durable SQLite write-path rate limiting and no automatic trust of arbitrary client forwarding headers.

v0.17 also provides [`deploy/public-testnet-edge/`](deploy/public-testnet-edge/) as a **single-edge testnet scaffold** with TLS termination, request/connection limits and separate transaction/faucet/Mining-Lab rate-limit zones.

That NGINX profile is not a complete WAF/DDoS design. Its shared-memory limits coordinate one edge host, not multiple geographically distributed edge hosts. A production deployment still needs a reviewed trusted-proxy model, certificate automation, capacity tests, redundancy and shared upstream controls.

Execution service, ABCI socket, remote signer and validator operator surfaces should remain private/authorized. Do not expose the execution-service bearer token to the browser.

## Faucet and Mining Lab

Faucet distribution history/cooldowns and Mining Lab challenges/claims are persistent, including durable request-rate state.

Both services require dedicated non-validator keys.

The Mining Lab is **not consensus mining**. It verifies a test browser proof-of-work challenge and pays from an already funded reward wallet via an ordinary signed transaction. It must not mint supply, select validators, alter CometBFT voting power, claim to mine consensus blocks or be marketed as guaranteed earnings.

## Dedicated explorer index

The read-optimized explorer database remains separate from the external execution database. The index verifies source genesis identity and execution ownership before copying commits, transactions and account state.

Production use still requires reconciliation/rebuild procedures, archive-retention decisions, clean-host rebuild tests and monitoring for index lag/divergence.

## Validator key security

The generated local CometBFT lab stores disposable private-validator keys in local runtime directories. Those keys are not suitable for reuse.

A production candidate should use a remote signer, HSM or equivalent protected signing design and tested anti-double-sign/recovery procedures.

v0.17 includes `scripts/configure_comet_remote_signer.py`, which only changes the CometBFT `priv_validator_laddr` configuration. It does **not** read, copy, migrate or protect the validator key and does not implement an HSM. Loopback signer endpoints are allowed by default; non-loopback use requires explicit override and still needs separately authenticated/encrypted private transport.

See [`docs/VALIDATOR_REMOTE_SIGNER.md`](docs/VALIDATOR_REMOTE_SIGNER.md).

## Fault/soak evidence

v0.17 adds a controlled fault-campaign runner. It is dry-run by default and only executes operator-supplied commands with explicit `--execute`. Every step must contain a recovery command, and recovery is attempted even if the fault command fails.

The runner can record network health before/during/after operator-defined process restart, impairment or load scenarios. Merely adding the runner does not prove those scenarios have been executed on independent infrastructure.

## Signed evidence bundles

Signed public-testnet evidence bundles bind an exact source commit, declared CometBFT version, genesis identity and supplied evidence-file hashes to a dedicated Ed25519 signer.

The bundle format explicitly records that independent-host operation, independent review and production-mainnet readiness are **false unless separately established**. A signature authenticates the evidence manifest; it does not convert unperformed tests into evidence.

The evidence/release signing key must be protected separately from validator and wallet keys.

## Durable state and SQLite

SQLite is currently used for research/application/index/service state. Existing protections include WAL mode and explicit transactions for critical state transitions.

Production review must still cover storage durability/fsync expectations, disk-full behavior, database corruption, backup consistency, abrupt power loss, filesystem semantics on actual deployment hosts, growth/retention limits and migration/versioning.

## Secrets

Never commit or share:

- seed phrases,
- wallet private keys,
- CometBFT private-validator keys,
- signer/HSM credentials,
- TLS private keys,
- faucet/mining reward keys,
- release/evidence-signing private keys,
- execution-service bearer tokens,
- API secrets.

Do not send any of these through support chats or issue trackers.

## Required before production mainnet

Major open gates include:

- sustained independent-host testnet operation,
- successful live state-sync/recovery evidence from clean hosts,
- reproducible partition/latency/packet-loss/restart/load evidence,
- production reverse-proxy/WAF/DDoS architecture and capacity testing,
- horizontally shared abuse controls,
- deployed and tested remote-signer/HSM-equivalent validator custody,
- explorer reconciliation/archive procedures,
- reproducible signed releases and final multi-operator genesis ceremony,
- independent consensus/application/network/cryptography/wallet reviews,
- incident-response drills,
- finalized economics/incentives and applicable legal review.

The canonical gate list is [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md).

Until those gates are satisfied, the repository should use **research devnet**, **public testnet**, or **mainnet-candidate infrastructure**, not production mainnet.
