# Independent Review Handoff — Crakbit Chain v0.25

This document is a **review handoff checklist**, not an audit report and not a statement that Crakbit Chain is production-ready.

Production CRKBIT has not launched. There is no official presale or production token contract.

## Candidate identity

An independent reviewer should receive one frozen v0.25 candidate envelope and independently verify:

- exact Git source commit,
- package version,
- pinned CometBFT version,
- application genesis SHA-256,
- CometBFT genesis SHA-256,
- v0.25 review-gate SHA-256,
- every attached evidence artifact hash,
- review-freeze signature and signer identity.

Use `crakchain review-freeze-v25-verify` against a separately obtained copy of the expected source/genesis/artifacts.

## Required review scopes

The project should request review of at least:

1. deterministic application execution and crash-safe FinalizeBlock/Commit behavior,
2. CometBFT ABCI integration and state-sync behavior,
3. validator join/remove/replace governance and update-height semantics,
4. application-hash/state-root determinism and replay behavior,
5. networking, RPC exposure, gateway limits and public-edge trust boundaries,
6. validator/governance/evidence/release key separation and protected signer design,
7. snapshot, backup, clean-host recovery and disaster-recovery procedures,
8. browser-wallet signing/storage threat model,
9. release provenance, reproducible build and dependency/SBOM process,
10. operational evidence quality, incident response and monitoring assumptions.

## Evidence expected from operators

The frozen candidate should contain or reference hashed artifacts for:

- v0.24 host preflight results,
- raw multi-host health/soak JSONL,
- 24-hour, 72-hour and 7-day summaries,
- restart and process-kill campaign results,
- partition/latency/packet-loss results,
- sustained-load and storage-fault results,
- backup/restore recovery evidence,
- clean-host state-sync evidence,
- protected remote-signer/HSM-equivalent drill evidence,
- validator-governance campaign evidence,
- public RPC/explorer redundancy evidence,
- incident-response drill records,
- signed per-operator v0.25 host attestations,
- exact release/source/genesis provenance artifacts.

Operator host attestations are deliberately marked as self-attested. Reviewers should independently corroborate infrastructure ownership/independence, logs, timestamps and provider/region claims where those claims matter to the assessment.

## Findings handling

Every finding should have:

- stable finding ID,
- affected component/version/commit,
- severity and rationale,
- reproduction conditions,
- remediation status,
- remediation commit or operational change,
- retest result,
- explicit residual risk if accepted.

High and critical findings should remain release blockers until remediated and retested or explicitly accepted through a documented security-governance process appropriate to the future production model.

## What a successful review still does not decide

A technical security review does not by itself finalize:

- production CRKBIT economics,
- validator incentives,
- jurisdiction/legal classification,
- treasury/fundraising structure,
- production launch date,
- operational provider choices,
- whether mainnet should launch.

Those remain separate engineering, economic, operational and applicable legal/regulatory decisions.
