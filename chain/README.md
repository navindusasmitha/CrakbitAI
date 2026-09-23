# Crakbit Chain v0.1

This directory begins the production engineering work for an independent Crakbit blockchain. It is **pre-mainnet** until every launch gate passes.

## Network parameters (provisional until code freeze)
- Name: Crakbit Chain
- Ticker: CBIT
- Base lineage: Bitcoin Core 31.1
- Consensus: RandomX Proof of Work
- Target spacing: 120 seconds
- Initial subsidy: 10 CBIT
- Halving interval: 1,051,200 blocks (~4 years at target spacing)
- Treasury: 5% of subsidy, included within the 10 CBIT subsidy
- Premine: 0
- Address/network prefixes, magic bytes, ports and genesis values: generated uniquely before public testnet

## Non-negotiable mainnet rules
- No unsigned release binaries.
- No mainnet genesis before consensus code freeze.
- Monetary schedule must have automated boundary tests.
- Treasury output must never mint above the scheduled subsidy.
- RandomX epoch/seed transitions must be deterministic across nodes.
- No mainnet launch while known consensus-critical defects remain.
- Reorg monitoring and conservative confirmation recommendations ship with v1.

A young PoW chain cannot honestly promise zero 51% risk. Security comes from correct consensus code, distributed hash power, monitoring, conservative finality assumptions, and a carefully controlled release process.
