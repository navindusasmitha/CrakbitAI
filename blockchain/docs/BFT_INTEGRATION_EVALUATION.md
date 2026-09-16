# Crakbit Chain — External BFT Integration Evaluation

**Status:** engineering evaluation document. No BFT engine is selected or integrated by this document.

Crakbit Chain v0.13 stops treating the bespoke Python consensus prototype as the production path. The next production-oriented architecture should place a reviewed external BFT engine in charge of ordering/finality while the Crakbit application layer remains deterministic and independently testable.

## Primary reference model

A Tendermint/CometBFT-style architecture is the primary reference because it separates a Byzantine-fault-tolerant consensus engine from an application state machine through a versioned application interface. This is an architectural reference, not an endorsement or a claim that CometBFT has already been integrated.

## Required capabilities

Any candidate must be evaluated for:

1. independently reviewed BFT safety/liveness design,
2. deterministic proposer/consensus behavior under faults,
3. validator-set and key-rotation support,
4. authenticated/encrypted peer networking or a clear secure deployment model,
5. crash/restart and WAL/replay semantics,
6. application-state commitment support,
7. deterministic application callbacks,
8. snapshot/state-sync integration options,
9. observability and evidence collection,
10. maintained security-update process and reproducible releases.

## Crakbit-side compatibility requirements

The Crakbit application must provide:

- deterministic transaction validation,
- deterministic ordered-batch state transition,
- deterministic application hash,
- explicit height/chain context,
- replay-safe commit semantics,
- idempotent crash recovery,
- versioned protocol negotiation,
- authenticated local/process transport,
- bounded request sizes and transaction counts,
- clear separation between consensus metadata and application state.

v0.13 implements the non-mutating first half through `crakbit-execution/1`.

## Candidate experiment sequence

### Experiment A — read/check boundary

External process calls:

```text
Info -> /v1/info
CheckTx -> /v1/check-tx
Proposal preview -> /v1/preview-batch
```

Expected invariant: identical state plus identical ordered transactions must return identical transaction/state commitments.

### Experiment B — deterministic replay harness

Run two independent Crakbit application instances from identical genesis/snapshot state and feed identical ordered transaction batches. Compare application hashes after every simulated step.

### Experiment C — crash boundary

Terminate the application and consensus process at each future commit boundary, restart and confirm there is no double-apply, skipped apply or divergent application hash.

### Experiment D — fault network

Run at least four independent validator hosts and introduce latency, partitions, restarts and resource pressure while collecting signed release metadata, node integrity output and soak evidence.

## Hard gates before adding a mutating external finalize endpoint

- candidate BFT engine/version pinned and reviewed,
- exact callback/commit semantics documented,
- authentication and authorization model reviewed,
- application commit is atomic and replay-safe,
- state hash persistence has crash tests,
- duplicate finalize requests are idempotent,
- stale/future heights are rejected,
- invalid transaction batches cannot mutate state,
- independent review covers both sides of the boundary.

## Not yet complete

v0.13 does not implement actual CometBFT/ABCI connectivity and does not permit an external process to finalize blocks. Those are intentional v0.14+ tasks after the boundary, release and operational tooling can be reviewed in isolation.
