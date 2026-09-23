# Crakbit Chain — Mainnet Release Gates

Mainnet is permitted only when every CRITICAL gate below is green. These gates are not optional simulations; they are release engineering requirements for production consensus software.

## 1. Consensus correctness — CRITICAL
- All consensus changes are isolated and reviewed line-by-line.
- Two independently built nodes agree on genesis, headers, chainwork, block validity, subsidy, treasury output and RandomX seed/epoch transitions.
- Boundary-height tests cover block 0, 1, treasury start/end, every halving boundary, final subsidy boundary and post-emission behavior.
- A block that overpays miner + treasury by one satoshi is rejected.
- A block that underpays the mandatory treasury output (while treasury rules are active) is rejected.
- Founder/premine outputs do not exist.

## 2. Monetary invariant — CRITICAL
For height h, the total permitted coinbase subsidy is a deterministic function S(h). The treasury share is carved out of S(h), never added on top.

Initial subsidy: 10 CBIT
Target spacing: 120 seconds
Halving interval: 1,051,200 blocks
Treasury share: 5% of subsidy while the treasury window is active
Premine: 0

Invariant:
`miner_subsidy(h) + treasury_subsidy(h) == S(h)`

Total scheduled emission must be computed from integer base units and verified by an executable supply test.

## 3. Proof of Work — CRITICAL
- RandomX verification must be deterministic on all supported architectures.
- Hash seed/epoch selection must depend only on consensus-visible chain state.
- No wall-clock, hostname, local cache state or platform-specific behavior may affect block validity.
- Invalid target, invalid nBits, malformed header and incorrect RandomX digest are rejected.
- Difficulty transition rules are unit- and functional-tested around extreme timestamp and hash-rate changes.

## 4. Chain identity — CRITICAL
Before public testnet, generate unique:
- message-start/magic bytes
- mainnet P2P/RPC ports
- Base58/Bech32 address prefixes
- BIP32 extended-key prefixes
- genesis timestamp text
- genesis nonce/hash/merkle root

No Bitcoin, Litecoin, WAM, testnet or regtest identity values may be reused on mainnet.

## 5. Network/reorg safety — CRITICAL
- Nodes prefer the valid chain with the most cumulative work.
- Deep reorgs generate high-severity operator alerts.
- Exchange/merchant documentation publishes conservative confirmation guidance.
- No centralized checkpoint can silently override consensus.
- If checkpoints are shipped, they are explicit software constants for historical DoS protection only and are documented as such.

A new PoW chain cannot guarantee immunity to majority-hash attacks. Mainnet security therefore also requires distributed real hash power.

## 6. P2P/RPC hardening — CRITICAL
- RPC is localhost-only by default.
- RPC authentication uses cookie auth or strong credentials.
- Wallet RPCs are never exposed publicly by default.
- P2P parsers inherit current upstream Bitcoin Core protections except where explicitly modified and reviewed.
- Fuzz/functional tests cover custom message/consensus surfaces.

## 7. Wallet safety — CRITICAL
- Descriptor wallets enabled.
- Encrypted wallet backups verified by restore rehearsal.
- Seed/private-key material is never logged.
- Mainnet/testnet/regtest data directories and address prefixes are isolated.

## 8. Build/release integrity — CRITICAL
- Release source is tagged.
- Linux/Windows artifacts are built reproducibly where supported.
- SHA256SUMS generated for every artifact.
- SHA256SUMS is signed by an offline release key.
- Public signing-key fingerprint is pinned in SECURITY.md and release docs.
- Release binaries are verified against signed hashes before publication.

## 9. Operational readiness — CRITICAL
- At least 3 independently administered public seed/full nodes before launch.
- DNS seeds do not all resolve to one provider/account.
- Explorer runs from a non-wallet node.
- Pool hot wallet, treasury wallet and release-signing key are separate.
- Monitoring covers tip age, peer count, version drift, chain split indicators and reorg depth.

## 10. Security review — CRITICAL
- No known open consensus-critical defects.
- Consensus diff against upstream is reviewed independently.
- Custom RandomX integration and subsidy/treasury code receive dedicated review.
- Responsible disclosure contact and SECURITY.md are public before mainnet.

## Launch decision
Mainnet launch requires a signed release checklist recording the exact git commit, binary hashes, genesis values and each completed gate. A failed CRITICAL gate blocks launch.
