# Crakbit Execution Protocol v1 — PoC Boundary

**Status:** research-only interface for external-consensus experiments. It is not a production consensus API.

Crakbit Chain v0.13 introduces a deterministic application boundary so the execution/state layer can be evaluated independently from the current bespoke Python consensus prototype.

## Design goals

- deterministic state commitments,
- explicit chain/height/previous-hash context,
- transaction validation independent from peer/network code,
- ordered-batch preview without mutating state,
- a process boundary that can be exercised by an external reviewed BFT engine,
- no unauthenticated alternate finalization path.

Protocol identifier:

```text
crakbit-execution/1
```

## Application hash

The v1 application hash commits to:

- protocol version,
- chain ID,
- current finalized height,
- current finalized block hash,
- all application accounts sorted by address with balance and nonce.

Consensus-local material such as peer health, rounds, local votes and monitoring state is intentionally excluded.

## Operations

### `info`

Returns the protocol identifier, chain ID, height, finalized block hash and deterministic application hash.

### `check_transaction`

Parses and validates one signed Crakbit transaction against current state. It does not add the transaction to the mempool and does not mutate state.

### `preview_batch`

Accepts an ordered list of transaction objects and an explicit fee recipient. It returns:

- expected next height,
- previous finalized block hash,
- previous application hash,
- ordered transaction IDs,
- transaction Merkle root,
- simulated next state root,
- total fees,
- explicit `state_mutated: false`.

Duplicate transaction IDs are rejected.

## Process boundary PoC

`scripts/run_execution_service.py` runs a loopback-by-default FastAPI process exposing:

```text
GET  /health
GET  /v1/info
POST /v1/check-tx
POST /v1/preview-batch
```

All non-health operations require a bearer token of at least 24 characters.

Example:

```bash
python scripts/run_execution_service.py \
  --genesis runtime/genesis.json \
  --data runtime/node1-data \
  --token REPLACE_WITH_LONG_RANDOM_SECRET
```

The service intentionally has **no external finalize/commit endpoint** in v0.13. This prevents the PoC from bypassing consensus finality before a reviewed BFT integration owns ordering and commit authority.

## Mapping to an established BFT core

A future integration can map common BFT application callbacks roughly as follows:

```text
Info / Query            -> info / explorer read APIs
CheckTx                 -> check_transaction
Prepare/ProcessProposal -> preview_batch + deterministic policy
FinalizeBlock           -> future authenticated finalized-batch contract
Commit                  -> future application-hash persistence contract
```

The last two remain deliberately unimplemented until the external consensus engine, authentication model, crash semantics and replay rules have been reviewed together.

## Release gate

No production mainnet claim should be made until an independently reviewed BFT core is integrated or the complete consensus protocol receives equivalent independent review, followed by sustained fault/soak testing and security review.
