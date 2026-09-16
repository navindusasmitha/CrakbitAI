from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from .crypto import canonical_json, sha256_hex
from .explorer_index import ExternalExplorerIndex
from .genesis import Genesis
from .storage import LedgerError


TABLE_QUERIES = {
    "commits": (
        "SELECT height,consensus_block_hash,application_hash,transaction_root,"
        "transaction_count,committed_at_ms FROM explorer_commits ORDER BY height ASC"
    ),
    "transactions": (
        "SELECT txid,height,sender,recipient,amount,fee,nonce,memo,body "
        "FROM explorer_transactions ORDER BY txid ASC"
    ),
    "activity": (
        "SELECT address,txid,height,direction,counterparty,amount,fee "
        "FROM explorer_address_activity ORDER BY address ASC,txid ASC"
    ),
    "accounts": (
        "SELECT address,balance,nonce FROM explorer_accounts ORDER BY address ASC"
    ),
}


def _table_digest(path: Path, query: str) -> tuple[str, int]:
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        rows = [dict(row) for row in conn.execute(query).fetchall()]
    finally:
        conn.close()
    return sha256_hex(canonical_json(rows)), len(rows)


def index_fingerprint(path: str | Path) -> dict[str, Any]:
    index_path = Path(path)
    if not index_path.is_file():
        raise FileNotFoundError(f"explorer index not found: {index_path}")
    tables: dict[str, dict[str, Any]] = {}
    for name, query in TABLE_QUERIES.items():
        digest, count = _table_digest(index_path, query)
        tables[name] = {"sha256": digest, "rows": count}
    combined = sha256_hex(canonical_json(tables))
    return {"sha256": combined, "tables": tables}


def reconcile_explorer_index(
    *,
    genesis: Genesis,
    source_data_dir: str | Path,
    index_path: str | Path,
    rebuilt_output: str | Path | None = None,
) -> dict[str, Any]:
    current_path = Path(index_path)
    if not current_path.is_file():
        raise FileNotFoundError(f"explorer index not found: {current_path}")

    current = ExternalExplorerIndex(current_path, genesis)
    current_summary = current.summary()

    with tempfile.TemporaryDirectory(prefix="crakbit-explorer-reconcile-") as temp_dir:
        fresh_path = Path(temp_dir) / "explorer-rebuilt.sqlite3"
        fresh = ExternalExplorerIndex(fresh_path, genesis)
        sync = fresh.sync_from_source(source_data_dir)
        fresh_summary = fresh.summary()

        current_fp = index_fingerprint(current_path)
        fresh_fp = index_fingerprint(fresh_path)
        mismatches = [
            name
            for name in TABLE_QUERIES
            if current_fp["tables"][name]["sha256"] != fresh_fp["tables"][name]["sha256"]
        ]

        expected_supply = sum(int(value) for value in genesis.allocations.values())
        if int(fresh_summary["issued_atomic_units"]) != expected_supply:
            raise LedgerError("clean explorer rebuild violates fixed issued-supply invariant")

        metadata_match = (
            int(current_summary["indexed_height"]) == int(fresh_summary["indexed_height"])
            and int(current_summary["snapshot_base_height"])
            == int(fresh_summary["snapshot_base_height"])
            and str(current_summary["source_last_hash"])
            == str(fresh_summary["source_last_hash"])
            and int(current_summary["issued_atomic_units"])
            == int(fresh_summary["issued_atomic_units"])
        )
        matches = not mismatches and metadata_match

        copied_to = None
        if rebuilt_output is not None:
            output = Path(rebuilt_output)
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists():
                raise FileExistsError(f"rebuilt explorer output already exists: {output}")
            shutil.copy2(fresh_path, output)
            copied_to = str(output)

        return {
            "format": "crakbit-explorer-reconciliation-v1",
            "matches_clean_rebuild": matches,
            "mismatched_tables": mismatches,
            "metadata_match": metadata_match,
            "current": {
                "summary": current_summary,
                "fingerprint": current_fp,
            },
            "clean_rebuild": {
                "summary": fresh_summary,
                "fingerprint": fresh_fp,
                "sync": sync,
                "copied_to": copied_to,
            },
            "production_mainnet_ready": False,
        }
