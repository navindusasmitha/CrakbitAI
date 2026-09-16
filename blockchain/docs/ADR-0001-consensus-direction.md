# ADR-0001 — Consensus Direction Before Public-Value Use

**Status:** Accepted for the research roadmap, September 2026.

## Context

Crakbit Chain v0.2-v0.10 incrementally built a research consensus prototype with signed proposals, certified view changes, prevote/precommit phases, durable local votes and conservative cross-round locking.

That work is useful for learning, testing state execution and validating operational tooling. It is not sufficient evidence for a production Byzantine fault tolerant protocol. In particular, the current conservative lock does not implement a reviewed proof-based cross-round unlock rule and has not undergone formal safety/liveness analysis or independent consensus review.

## Decision

Crakbit will **not continue inventing additional production consensus rules ad hoc inside the current Python prototype**.

Before any public-value mainnet planning, the project will evaluate migration of the Crakbit execution/state layer to an established and independently reviewed BFT consensus core, with a Tendermint/CometBFT-style protocol as the primary architectural reference. A bespoke production consensus implementation would require a written protocol specification, safety/liveness arguments, extensive adversarial testing and independent review before it could replace that direction.

The current Python consensus remains a development-network research component only.

## Consequences

- v0.11 may harden transport, operations, fault testing and state tooling without claiming production consensus safety.
- No real-value custody or production mainnet claim is allowed while the consensus migration/review remains incomplete.
- The execution/state interface should become easier to separate from consensus in future phases.
- Fault harnesses should be reusable against both the current research node and a future reviewed BFT integration.
- External review is a release gate, not an optional post-launch activity.

## Exit Criteria For A Future Mainnet Candidate

At minimum:

1. reviewed BFT consensus implementation or independently reviewed complete protocol,
2. documented safety/liveness assumptions,
3. multi-host adversarial and partition testing,
4. authenticated encrypted validator transport and key lifecycle,
5. reproducible state recovery and archive synchronization,
6. independent consensus/network/security audit,
7. public testnet soak period with published incidents and remediation.
