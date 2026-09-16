# Crakbit External Execution Protocol v2

Protocol identifier: `crakbit-execution/2`

Status: research/testnet protocol. Not production-ready.

## Goal

v2 defines the first mutating process boundary intended for an independently reviewed external BFT engine. The protocol is intentionally narrow: transaction checking, deterministic finalize staging, application-hash return, and crash-safe commit.

The older `crakbit-execution/1` preview protocol remains useful for non-mutating compatibility experiments.

## Database isolation

The v2 execution service **must use a dedicated data directory**. It refuses to attach to an existing database that already contains research-consensus blocks or a non-zero height without v2 external commit records.

This prevents accidental mixing of two independent consensus owners.

## Application hash

The v2 application hash commits to:

```text
protocol = crakbit-execution/2
chain_id
height
consensus_block_hash
sorted(address, balance, nonce) application state
```

It intentionally excludes local consensus votes, peer health, local rounds, monitoring data and process-local metadata.

## Deterministic fee handling

v0.14 does not define production validator rewards. External-consensus transaction fees are credited to a deterministic, test-only application fee-pool address derived from the chain ID.

This avoids nondeterministic operator configuration and keeps economic design out of the consensus integration PoC.

## Finalize → Commit lifecycle

### 1. CheckTx

The BFT bridge submits the signed Crakbit transaction to:

```text
POST /v2/check-tx
```

The application verifies chain ID, amount, minimum fee, sender/recipient relationship, Ed25519 signature, nonce and current balance.

### 2. FinalizeBlock staging

The bridge submits:

```json
{
  "height": 42,
  "consensus_block_hash": "64-hex-characters",
  "transactions": []
}
```

to:

```text
POST /v2/finalize
```

The application:

1. verifies the next expected height,
2. validates every signed transaction in order,
3. simulates balances/nonces and fee collection,
4. computes the transaction Merkle root,
5. computes the next application hash,
6. derives a deterministic finalize request hash,
7. persists the pending finalize record,
8. does **not** mutate committed account state.

The returned `next_application_hash` is used as the ABCI `FinalizeBlock` application hash.

### 3. Commit

The bridge calls:

```text
POST /v2/commit
```

The application loads the persisted pending finalize and revalidates it against the current committed state. The account updates, transaction index, height, external consensus block hash, external commit record and pending-record deletion are then applied inside one SQLite `BEGIN IMMEDIATE` transaction.

If the process crashes before SQLite commit, the transition rolls back. If it crashes after commit, the committed state and external commit record are durable together.

## Replay behavior

- Repeating the same pending finalize request is accepted idempotently.
- A different finalize request for the same pending height is rejected.
- A duplicate `Commit` call with no pending finalize returns the current committed application state without applying anything again.
- Conflicting heights are rejected.

Further app-ahead/consensus-ahead replay testing is still required with a live multi-process CometBFT network before this can be considered mature.

## Endpoints

```text
GET  /health
GET  /v2/info
GET  /v2/pending
POST /v2/check-tx
POST /v2/preview-finalize
POST /v2/finalize
POST /v2/commit
```

All endpoints except `/health` require the execution-service bearer token.

## Security requirements

- Bind the execution service to loopback or an isolated private interface.
- Use a long random bearer token and secret management; do not commit it.
- Do not expose the service directly to the public Internet.
- Run the external execution database in a dedicated data directory.
- Do not reuse validator consensus keys as release, faucet, TLS or execution-service credentials.
- Treat all transaction bytes received from the BFT bridge as untrusted input.

## Release gate

The existence of this protocol does not make the network production BFT. Before public-value use, the integration needs sustained multi-host fault testing, state-replay validation, independent consensus/network review, production key custody and meaningful public-testnet operation.
