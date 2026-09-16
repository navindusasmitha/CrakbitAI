# Crakbit v0.22 Governed Testnet Campaign Runbook

This runbook is for **local/public-testnet research only**. It is not a production mainnet launch procedure.

Production CRKBIT has not launched. There is no official presale or production token contract.

## 1. Build and test

```bash
cd blockchain
python -m venv .venv
pip install -e ".[dev]"
pytest -q

cd cometbft-app
go mod download
go test -mod=mod ./...
go build -o crakbit-cometbft-bridge .
cd ..
```

Use the pinned CometBFT candidate version documented by the project (`v0.40.0`).

## 2. Generate a governed four-node lab

```bash
crakchain governed-lab-create \
  --cometbft /path/to/cometbft \
  --bridge ./cometbft-app/crakbit-cometbft-bridge \
  --output runtime/governed-v22-lab \
  --chain-id crakbit-v22-local \
  --nodes 4
```

Generated `.secrets` material is disposable lab-only material. Never reuse it on a public or production network.

## 3. Start the nodes

Use the generated:

```text
runtime/governed-v22-lab/commands.txt
```

Each validator requires three processes:

1. v0.22 execution service,
2. Crakbit CometBFT ABCI bridge,
3. CometBFT node.

The execution service remains private/loopback in the local lab. Do not expose it directly to the Internet.

## 4. Verify convergence

```bash
crakchain cluster-v22-check \
  --inventory runtime/governed-v22-lab/governed-lab-inventory.json \
  --max-height-spread 1 \
  --output runtime/evidence/cluster-before.json
```

Do not start a governance campaign if same-height application hashes or governance state diverge.

## 5. Create a validator-change request

Example join request:

```bash
crakchain validator-change-build \
  --genesis runtime/governed-v22-lab/application-genesis.json \
  --data runtime/governed-v22-lab/app1 \
  --kind join \
  --emit-height 101 \
  --new-public-key BASE64_ED25519_PUBLIC_KEY \
  --new-name validator-5 \
  --output runtime/governance/join-validator-5.json
```

The request must be built from the currently committed validator set and must not overlap an already pending change.

## 6. Collect validator approvals

For the disposable local lab only, each generated validator has a corresponding `.secrets/*DISPOSABLE-governance-key.json` view. Sign the same request sequentially with enough active voting power to exceed two-thirds.

For four equal-power validators, this means 3-of-4 approvals.

Example pattern:

```bash
crakchain validator-change-sign \
  --genesis runtime/governed-v22-lab/application-genesis.json \
  --data runtime/governed-v22-lab/app1 \
  --request runtime/governance/join-validator-5.json \
  --key runtime/governed-v22-lab/.secrets/validator-1-DISPOSABLE-governance-key.json \
  --output runtime/governance/join-validator-5-s1.json
```

Use the previous signed output as the input to the next validator signature until quorum is reached.

Verify:

```bash
crakchain validator-change-verify \
  --genesis runtime/governed-v22-lab/application-genesis.json \
  --data runtime/governed-v22-lab/app1 \
  --request runtime/governance/join-validator-5-quorum.json
```

## 7. Build the campaign plan

```bash
crakchain campaign-v22-plan-build \
  --genesis runtime/governed-v22-lab/application-genesis.json \
  --kind join \
  --emit-height 101 \
  --change-request runtime/governance/join-validator-5-quorum.json \
  --output runtime/evidence/join-plan.json
```

The plan records the important boundary sequence:

```text
H-1  pre-emission
H    ABCI validator update emission + pending application state
H+1  pending state remains
H+2  application-side target validator set becomes active
```

## 8. Guarded broadcast

The governance request must not be broadcast too early because v0.21 validates the request against an exact `emit_height` during FinalizeBlock.

Use the guarded helper:

```bash
crakchain governance-v22-broadcast \
  --request runtime/governance/join-validator-5-quorum.json \
  --rpc http://127.0.0.1:28657 \
  --wait-for-preheight \
  --wait-timeout-seconds 300 \
  --output runtime/evidence/join-broadcast.json
```

The helper waits for `emit_height - 1`, then submits the canonical JSON governance transaction via CometBFT `broadcast_tx_sync`.

A successful `broadcast_tx_sync` means CheckTx accepted the transaction. It **does not prove FinalizeBlock inclusion or activation**. Verify subsequent state separately.

## 9. Observe H / H+1 / H+2

Capture cluster observations around the activation boundary:

```bash
crakchain cluster-v22-check \
  --inventory runtime/governed-v22-lab/governed-lab-inventory.json \
  --output runtime/evidence/cluster-H.json
```

Repeat at H+1 and H+2. Also export governance history:

```bash
crakchain governance-history-v22 \
  --genesis runtime/governed-v22-lab/application-genesis.json \
  --data runtime/governed-v22-lab/app1 \
  --output runtime/evidence/governance-history.json
```

Expected evidence should show one validator-update emission at H, a pending change until activation, then an applied governance-history entry at H+2.

## 10. Restart / crash campaign

For a disposable lab, repeat the campaign with controlled node restarts at:

- H,
- H+1,
- H+2.

After every restart, rerun `cluster-v22-check` and capture the output. Do not claim success merely because the processes restarted; verify height/app-hash/governance convergence.

## 11. State-sync campaign

Use a clean application/node home and the existing v0.21 governance-aware ABCI state-sync path. Test at least:

- before governance emission,
- while a change is pending,
- after H+2 activation.

The restored node must converge to the trusted application hash and governance state.

## 12. Build signed campaign evidence

Use a dedicated evidence signing key, separate from validator/wallet/faucet/release keys.

```bash
SOURCE_COMMIT=$(git rev-parse HEAD)

crakchain campaign-v22-evidence-build \
  --genesis runtime/governed-v22-lab/application-genesis.json \
  --key private/campaign-evidence-key.json \
  --source-commit "$SOURCE_COMMIT" \
  --plan runtime/evidence/join-plan.json \
  --observation runtime/evidence/cluster-before.json \
  --observation runtime/evidence/join-broadcast.json \
  --observation runtime/evidence/cluster-H.json \
  --observation runtime/evidence/cluster-H1.json \
  --observation runtime/evidence/cluster-H2.json \
  --observation runtime/evidence/governance-history.json \
  --executed \
  --output runtime/evidence/join-campaign-evidence.json
```

The signature authenticates the operator's evidence package. It is not an independent audit certificate.

## 13. What must still happen before mainnet

A local campaign is only one step. The same tests must be repeated across independently managed hosts/providers with protected signing, real network faults/load, clean-host state sync, long-duration soak, production RPC/TLS/DDoS/secret-management controls and independent security review.

See `docs/MAINNET_GATES.md` for the canonical production release gates.
