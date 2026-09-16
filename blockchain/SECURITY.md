# Crakbit Chain Security Notes — v0.16 Alpha

Crakbit Chain is currently **research/public-testnet/mainnet-candidate infrastructure**, not an audited production mainnet. It must not be used to custody real value.

Production CRKBIT has not launched. There is no official presale or production token contract.

## Trust-domain separation

The repository deliberately separates security roles:

```text
browser wallet
    │ signed transaction only
    ▼
public gateway
    ├→ research RPC, or
    ├→ CometBFT JSON-RPC
    └→ private authenticated execution/index services

CometBFT
    │ ABCI
    ▼
Go application bridge
    │ authenticated private HTTP
    ▼
crakbit-execution/2
    │
    ├→ external application DB
    ├→ deterministic checkpoint adapter
    └→ read-only explorer index source
```

Keys for CometBFT consensus, P2P identity, Crakbit wallets, research validators, TLS, release signing, faucet and Mining Lab rewards must not be reused across roles.

## Consensus

The old Python prevote/precommit implementation remains research-only. It is not the intended production consensus path.

The external consensus integration candidate is CometBFT `v0.40.0`. The repository contains a Go ABCI bridge and a crash-safe `crakbit-execution/2` application boundary.

`FinalizeBlock`-style state is staged first and committed account/state changes are applied atomically in SQLite. Pending finalization survives an application restart. Identical finalized-height replay can be handled idempotently while conflicting replay is rejected.

This integration is still an alpha. Sustained multi-host external-consensus testing and independent review remain required.

## External application checkpoints

v0.16 adds deterministic checkpoint export/verify/import for the external application state.

A checkpoint commits to:

- chain ID,
- genesis fingerprint,
- consensus height,
- last consensus block hash,
- deterministic application hash,
- sorted account balances/nonces,
- account-state root,
- fixed issued-supply total,
- complete artifact hash.

Restore can require a separately trusted expected consensus height/application hash. Import is restricted to a pristine external application database.

A restored application records an explicit snapshot base and does **not** invent historical commits before that base.

### State-sync limitation

This checkpoint mechanism is not yet fully wired to CometBFT's native snapshot/state-sync lifecycle. It should be treated as application recovery infrastructure until multi-node offer/apply/recovery behavior is implemented and reviewed.

## Browser wallet

The browser wallet performs key generation/signing locally and encrypts its local vault with PBKDF2-SHA256-derived key material and AES-GCM.

The public gateway is not intended to receive private wallet keys.

v0.16 adds a restrictive gateway CSP/security-header profile and changes the default from wildcard CORS to same-origin access. These controls reduce some web attack surface but do not make the wallet an audited custody product.

Critical remaining threats include:

- compromised same-origin JavaScript,
- malicious extensions,
- compromised endpoint/browser,
- vault password guessing after encrypted-storage theft,
- phishing/fake origins,
- clipboard/address substitution,
- compromised gateway read data.

See [`docs/WALLET_THREAT_MODEL.md`](docs/WALLET_THREAT_MODEL.md).

## Public gateway / RPC

v0.16 defaults include:

- same-origin browser access unless origins are explicitly allow-listed,
- Content-Security-Policy,
- frame denial,
- `nosniff`,
- no-referrer policy,
- restrictive permissions policy,
- same-origin opener/resource policy,
- durable SQLite write-path rate limiting,
- no automatic trust of client-controlled forwarding headers.

SQLite rate-limit state survives process restart but is not a distributed rate-limit database. Multiple public gateway instances still require a shared upstream API gateway/load balancer/rate-limit layer and an explicit trusted-proxy design.

Execution service and ABCI sockets should remain loopback/private. Do not expose the execution-service bearer token to the browser.

## Faucet and Mining Lab

Faucet distribution history/cooldowns and Mining Lab challenges/claims are persistent. v0.16 also persists request-rate state.

Both services require dedicated non-validator keys.

The Mining Lab is **not consensus mining**. It verifies a test browser proof-of-work challenge and pays from an already funded reward wallet via an ordinary signed transaction. It must not:

- mint supply,
- select validators,
- alter CometBFT voting power,
- claim to mine consensus blocks,
- be marketed as guaranteed earnings.

## Dedicated explorer index

v0.16 adds a read-optimized explorer database separate from the external execution database. The index verifies source genesis identity and execution ownership before copying commits, transactions and account state.

It improves read isolation but is still an alpha index. Production use requires reconciliation/rebuild procedures, archive-retention decisions, clean-host rebuild tests and monitoring for index lag/divergence.

## Durable state and SQLite

SQLite is currently used for research/application/index/service state. Existing protections include WAL mode and explicit transactions for critical state transitions.

Production review must still cover:

- storage durability/fsync expectations,
- disk-full behavior,
- database corruption,
- backup consistency,
- abrupt power loss,
- filesystem semantics on actual deployment hosts,
- growth/retention limits,
- migration/versioning.

## Validator key security

The generated local CometBFT lab stores disposable private-validator keys in local runtime directories. Those keys are not suitable for reuse.

A production candidate should use a remote signer, HSM or equivalent protected signing design and tested anti-double-sign/recovery procedures. Documentation alone does not satisfy this gate.

See [`docs/VALIDATOR_REMOTE_SIGNER.md`](docs/VALIDATOR_REMOTE_SIGNER.md).

## Replay / crash testing

v0.16 contains an isolated application crash/replay matrix covering:

- persisted FinalizeBlock staging,
- restart before Commit,
- Commit after restart,
- restart after Commit,
- identical replay,
- conflicting replay,
- checkpoint restore,
- next-height commit after restore.

This is useful deterministic application evidence but is not equivalent to real process kills, filesystem faults and CometBFT/network failures on independent hosts.

## Multi-host monitoring

The testnet inventory checker can detect RPC reachability, catch-up state and validator-height divergence. Operator-only endpoints should stay private/authorized; do not expose sensitive interfaces merely to make monitoring easier.

## Secrets

Never commit or share:

- seed phrases,
- wallet private keys,
- CometBFT private-validator keys,
- signer/HSM credentials,
- TLS private keys,
- faucet/mining reward keys,
- release-signing private keys,
- execution-service bearer tokens,
- API secrets.

Do not send any of these through support chats or issue trackers.

## Required before production mainnet

Major open gates include:

- complete reviewed CometBFT state-sync integration,
- sustained independent-host testnet operation,
- reproducible partition/latency/packet-loss/restart/load evidence,
- production reverse-proxy/WAF/DDoS architecture,
- horizontally shared abuse controls,
- remote-signer/HSM-equivalent validator custody,
- explorer reconciliation/archive procedures,
- reproducible signed releases and final genesis ceremony,
- independent consensus/application/network/cryptography/wallet reviews,
- incident-response drills,
- finalized economics/incentives and applicable legal review.

The canonical gate list is [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md).

Until those gates are satisfied, the repository should use **research devnet**, **public testnet**, or **mainnet-candidate infrastructure**, not production mainnet.
