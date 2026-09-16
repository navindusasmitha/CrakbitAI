from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .genesis import Genesis
from .storage import Ledger
from .validator_governance_v21 import ValidatorGovernanceStore


def governance_history(ledger: Ledger, *, limit: int = 100) -> dict[str, Any]:
    limit = max(1, min(int(limit), 1000))
    store = ValidatorGovernanceStore(ledger, allow_pristine_initialize=True)
    status = store.status()
    with ledger.connect() as conn:
        history_rows = conn.execute(
            "SELECT change_id,emit_height,effective_height,source_set_hash,target_set_hash,"
            "envelope_json,target_validators_json,updates_json,applied_height,applied_at_ms "
            "FROM validator_governance_history ORDER BY applied_height DESC, change_id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        emission_rows = conn.execute(
            "SELECT height,change_id,updates_json FROM validator_governance_emissions "
            "ORDER BY height DESC LIMIT ?",
            (limit,),
        ).fetchall()
    history: list[dict[str, Any]] = []
    for row in history_rows:
        envelope = json.loads(str(row["envelope_json"]))
        history.append(
            {
                "change_id": str(row["change_id"]),
                "kind": str((envelope.get("request") or {}).get("kind", "")),
                "emit_height": int(row["emit_height"]),
                "effective_height": int(row["effective_height"]),
                "applied_height": int(row["applied_height"]),
                "applied_at_ms": int(row["applied_at_ms"]),
                "source_validator_set_hash": str(row["source_set_hash"]),
                "target_validator_set_hash": str(row["target_set_hash"]),
                "updates": json.loads(str(row["updates_json"])),
                "target_validators": json.loads(str(row["target_validators_json"])),
            }
        )
    emissions = [
        {
            "height": int(row["height"]),
            "change_id": str(row["change_id"]),
            "updates": json.loads(str(row["updates_json"])),
        }
        for row in emission_rows
    ]
    return {
        "chain_id": ledger.genesis.chain_id,
        "height": ledger.height,
        "active_validator_set_hash": status["active_validator_set_hash"],
        "active_validators": status["active_validators"],
        "pending": status["pending"],
        "governance_hash": status["governance_hash"],
        "history": history,
        "emissions": emissions,
        "history_limit": limit,
        "production_mainnet_ready": False,
    }


def governance_history_from_paths(
    *, genesis_path: str | Path, data_dir: str | Path, limit: int = 100
) -> dict[str, Any]:
    genesis = Genesis.load(genesis_path)
    ledger = Ledger(Path(data_dir) / "chain.sqlite3", genesis)
    return governance_history(ledger, limit=limit)
