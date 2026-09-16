# Crakbit Chain Security Notes — v0.15 Alpha

Crakbit Chain is currently **research/public-testnet infrastructure**, not an audited production mainnet. It must not be used to custody real value.

Production CRKBIT has not launched. There is no official presale or production token contract.

## Current security architecture

The repository deliberately separates several trust domains:

```text
browser wallet
    ↓ signed transaction only
public gateway
    ├→ research RPC, or
    ├→ CometBFT JSON-RPC
    └→ authenticated read-only execution API

CometBFT
    ↓ ABCI
Go bridge
    ↓ authenticated private HTTP
crakbit-execution/2
    ↓ crash-safe staged finalize / atomic commit
SQLite application state
```

The older Python prevote/precommit consensus remains for research compatibility and is **not** the intended production consensus path.

## Key-role separation

Do not reuse keys across security roles. Keep separate:

1. CometBFT validator/node keys,
2. Crakbit research-validator keys,
3. user wallet keys,
4. TLS keys,
5. release-signing keys,
6. faucet keys,
7. mining-reward keys.

Never commit private keys, wallet seeds, bearer tokens or production secrets to GitHub.

## Browser wallet security

v0.15 adds a browser wallet using WebCrypto Ed25519. The browser derives `crk1...` addresses from the raw public key, signs canonical Crakbit transactions locally and sends only signed transactions to the gateway.

The local vault uses:

- PBKDF2-SHA256,
- 250,000 iterations,
- random 16-byte salt,
- AES-GCM-256,
- random 12-byte IV.

This reduces exposure from plain-text local storage, but it does **not** protect against a compromised browser origin, malicious extension, active XSS, hostile injected JavaScript, unlocked-device access or credential phishing.

Before production use, the wallet still needs:

- independent cryptographic and Web security review,
- a formal browser-wallet threat model,
- strict CSP and reviewed production headers,
- dependency/integrity controls,
- anti-phishing/network identity UX,
- transaction confirmation review,
- hardware-wallet/external-signer strategy for high-value use,
- tested cross-client backup/recovery procedures.

The v0.15 browser wallet must not be marketed as hardware-wallet-grade custody.

## Public gateway security

The public gateway is intended to be the browser-facing boundary. It validates transaction structure, chain ID and Ed25519 signatures before forwarding a signed transaction.

In CometBFT mode, the browser never receives the execution-service bearer token. The gateway talks privately to the authenticated execution-service API and broadcasts transaction bytes through CometBFT JSON-RPC.

For a real Internet deployment, the gateway still requires:

- production TLS,
- reverse proxy/load balancer,
- upstream connection/request limits,
- WAF/DDoS strategy,
- trusted-proxy/IP handling,
- horizontal/persistent rate-limit storage,
- strict CORS/origin policy rather than development-wide origins,
- audit logging without secret leakage,
- secret manager integration,
- independent API/Web penetration testing.

## Execution service / ABCI boundary

`crakbit-execution/2` uses a dedicated application database and refuses to attach to research-consensus history. Finalize requests are persisted before committed state is changed. Commit revalidates and applies the staged transition inside one SQLite transaction.

The design supports replay/idempotency testing, but it is still a PoC. Keep the execution service and ABCI socket on loopback or explicitly authorized private networking.

Outstanding work includes:

- complete app-ahead/consensus-ahead crash matrix,
- sustained multi-process restart testing,
- external-consensus state sync,
- validator-set lifecycle rules,
- independent consensus/application review.

## Research validator transport

Earlier phases added signed internal validator requests, durable replay nonces, mTLS deployment support, certificate pinning and rotation overlap. Those controls remain useful for the research path, but the Python consensus remains research-only.

## Snapshots, archives and backups

The repository includes quorum-certified snapshot experiments, chunked verified transfer, import journaling, genesis-anchored history verification, integrity checks and verified backups.

These tools improve recovery, but the external CometBFT path still needs reviewed state-sync integration and multi-host recovery evidence before production use.

## Persistent test faucet

v0.15 stores successful faucet distributions in SQLite so per-address cooldown survives process restart. Faucet transactions use a dedicated funded non-validator wallet.

The faucet remains **test-only**. Process-local global RPM is not sufficient for Internet-scale abuse prevention. A public testnet deployment still needs upstream distributed rate limiting, bot/abuse controls and monitored funding limits.

Never use a validator consensus key as the faucet key.

## Mining Lab security

The Mining Lab is a visible, opt-in Hashcash-style work-reward experiment. It is **not block mining and is not part of consensus**.

A browser receives a random challenge and searches for a SHA-256 digest under a configured target. The server verifies the solution. A dedicated non-validator reward wallet then submits an ordinary test CRKBIT transfer.

The service persists challenge, solution and reward metadata in SQLite and enforces per-address cooldown/daily limits. It still requires upstream abuse controls before public Internet exposure.

Important properties:

- mining does not mint new supply,
- mining does not choose or finalize blocks,
- reward funds must already exist in the dedicated reward wallet,
- reward key must never be a validator key,
- work is opt-in and visible in the UI,
- closing/stopping the worker stops browser hashing.

Changing Crakbit to proof-of-work consensus would be a separate protocol redesign and security model.

## DoS and resource limits

Earlier phases added request body, transaction, mempool and block bounds plus development metrics. These are node-level controls, not a replacement for production edge/network protection.

Before public production use, test:

- concurrent connection exhaustion,
- expensive query patterns,
- broadcast floods,
- state growth,
- snapshot/archive bandwidth,
- CometBFT P2P/RPC pressure,
- wallet/faucet/mining gateway abuse.

## Release and genesis integrity

The repository includes signed release manifests and strict >2/3 application-genesis ceremony attestations.

A production launch must still use reproducible builds, independently held operator keys, verified final artifacts, documented ceremony procedures, rollback/upgrade plans and protected release-signing custody.

## Required before a production mainnet claim

The authoritative checklist is [`docs/MAINNET_GATES.md`](docs/MAINNET_GATES.md). Major outstanding gates include:

- long-lived independent-host CometBFT testnet,
- external state-sync completion,
- sustained fault/restart/partition/load evidence,
- remote-signer/HSM-equivalent validator custody,
- production gateway/TLS/WAF/DDoS/secrets design,
- indexed explorer and recovery plan,
- independent wallet review,
- independent consensus/application/network review,
- incident-response drills,
- final economic and legal/regulatory review.

Security findings should be reported through the repository-level [`SECURITY.md`](../SECURITY.md) process.
