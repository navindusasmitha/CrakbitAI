from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .crypto import KeyPair
from .external_commit_v16 import ExternalExecutionStoreV16
from .external_state_sync import export_external_snapshot, import_external_snapshot
from .genesis import Genesis
from .models import Transaction
from .storage import Ledger, LedgerError


def _signed_transfer(
    genesis: Genesis,
    sender: KeyPair,
    recipient: str,
    *,
    nonce: int,
    amount: int,
) -> Transaction:
    tx = Transaction(
        chain_id=genesis.chain_id,
        sender=sender.address,
        recipient=recipient,
        amount=int(amount),
        fee=genesis.min_fee,
        nonce=int(nonce),
        public_key=sender.public_key_b64,
        memo="v0.16 crash-matrix",
    )
    tx.signature = sender.sign(tx.signing_bytes())
    return tx


def run_crash_matrix(
    *,
    genesis: Genesis,
    funded_key: KeyPair,
    root: str | Path | None = None,
) -> dict[str, Any]:
    account = genesis.allocations.get(funded_key.address, 0)
    if int(account) <= genesis.min_fee + 2:
        raise ValueError("crash-matrix key must be funded in genesis")

    owned_temp = None
    if root is None:
        owned_temp = tempfile.TemporaryDirectory(prefix="crakbit-v16-crash-")
        root_path = Path(owned_temp.name)
    else:
        root_path = Path(root)
        root_path.mkdir(parents=True, exist_ok=True)

    recipient = KeyPair.generate()
    amount = max(1, min(int(account) // 10, int(account) - genesis.min_fee - 1))
    tx1 = _signed_transfer(
        genesis,
        funded_key,
        recipient.address,
        nonce=1,
        amount=amount,
    )
    block_hash_1 = "11" * 32
    app1 = root_path / "app1"
    ledger = Ledger(app1 / "chain.sqlite3", genesis)
    store = ExternalExecutionStoreV16(ledger)
    staged = store.stage_finalize(
        height=1,
        consensus_block_hash=block_hash_1,
        transactions=[tx1.to_dict()],
    )

    # Simulated crash: abandon all Python objects after persisted FinalizeBlock stage.
    reopened = ExternalExecutionStoreV16(Ledger(app1 / "chain.sqlite3", genesis))
    pending_survived = reopened.status()["pending_finalize"] is not None
    committed = reopened.commit_pending()
    after_commit = ExternalExecutionStoreV16(Ledger(app1 / "chain.sqlite3", genesis))
    committed_survived = after_commit.status()["height"] == 1

    replay = after_commit.stage_finalize(
        height=1,
        consensus_block_hash=block_hash_1,
        transactions=[tx1.to_dict()],
    )
    conflict_rejected = False
    try:
        after_commit.stage_finalize(
            height=1,
            consensus_block_hash="22" * 32,
            transactions=[tx1.to_dict()],
        )
    except LedgerError:
        conflict_rejected = True

    snapshot = export_external_snapshot(after_commit.ledger)
    restored_dir = root_path / "restored"
    restore = import_external_snapshot(
        envelope=snapshot,
        genesis=genesis,
        data_dir=restored_dir,
        expected_height=1,
        expected_application_hash=snapshot["snapshot"]["application_hash"],
    )

    tx2 = _signed_transfer(
        genesis,
        funded_key,
        recipient.address,
        nonce=2,
        amount=1,
    )
    restored = ExternalExecutionStoreV16(Ledger(restored_dir / "chain.sqlite3", genesis))
    restored.stage_finalize(
        height=2,
        consensus_block_hash="33" * 32,
        transactions=[tx2.to_dict()],
    )
    second_commit = restored.commit_pending()

    result = {
        "format": "crakbit-external-crash-matrix-v1",
        "stage_persisted_without_state_mutation": bool(staged.get("state_mutated") is False),
        "pending_finalize_survived_restart": pending_survived,
        "commit_after_restart_succeeded": bool(committed.get("committed")),
        "commit_survived_second_restart": committed_survived,
        "identical_finalize_replay_idempotent": bool(replay.get("already_committed")),
        "conflicting_finalize_replay_rejected": conflict_rejected,
        "checkpoint_restore_succeeded": bool(restore.get("imported")),
        "post_checkpoint_next_commit_succeeded": int(second_commit.get("height", 0)) == 2,
        "final_height": int(restored.status()["height"]),
        "passed": False,
    }
    result["passed"] = all(
        bool(result[key])
        for key in (
            "stage_persisted_without_state_mutation",
            "pending_finalize_survived_restart",
            "commit_after_restart_succeeded",
            "commit_survived_second_restart",
            "identical_finalize_replay_idempotent",
            "conflicting_finalize_replay_rejected",
            "checkpoint_restore_succeeded",
            "post_checkpoint_next_commit_succeeded",
        )
    ) and result["final_height"] == 2

    if owned_temp is not None:
        owned_temp.cleanup()
    return result
