# Crakbit Chain Status

## Implemented in this repository
- production-oriented chain area (`chain/`)
- consensus and monetary specification
- exact integer emission reference model
- boundary tests for subsidy/treasury invariants
- mandatory mainnet release gates
- pinned upstream source bootstrap for Bitcoin Core v31.1 and RandomX v1.2.3

## Not yet implemented
- actual Bitcoin Core consensus patch set
- unique chain parameters and final genesis
- RandomX C++ integration into header validation/mining
- difficulty algorithm implementation and test vectors
- production miner/pool/explorer
- wallet branding/network isolation
- seed infrastructure
- reproducible signed release pipeline
- independent security review

Mainnet must not be launched until these remaining items and every gate in MAINNET_GATES.md are complete.
