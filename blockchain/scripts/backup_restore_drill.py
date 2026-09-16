from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from crakbit_chain.backups import verify_ledger_backup
from crakbit_chain.genesis import Genesis
from crakbit_chain.integrity import verify_ledger_integrity
from crakbit_chain.storage import Ledger, LedgerError


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore a verified Crakbit SQLite backup into a fresh drill directory and re-check it"
    )
    parser.add_argument("--genesis", required=True)
    parser.add_argument("--backup", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-data", required=True)
    args = parser.parse_args()

    genesis = Genesis.load(args.genesis)
    verification = verify_ledger_backup(args.backup, args.manifest, genesis, full=True)
    if not verification["ok"]:
        print(json.dumps({"restored": False, "verification": verification}, indent=2))
        return 2

    target_dir = Path(args.output_data)
    target_db = target_dir / "chain.sqlite3"
    target_dir.mkdir(parents=True, exist_ok=True)
    if target_db.exists():
        raise LedgerError(f"restore drill target already contains chain.sqlite3: {target_db}")

    shutil.copy2(args.backup, target_db)
    restored = Ledger(target_db, genesis)
    integrity = verify_ledger_integrity(restored, full=True)
    if not integrity["ok"]:
        target_db.unlink(missing_ok=True)
        print(json.dumps({"restored": False, "integrity": integrity}, indent=2))
        return 2

    result = {
        "restored": True,
        "database": str(target_db),
        "height": restored.height,
        "last_hash": restored.last_hash,
        "integrity": integrity,
        "note": "This is a restore drill copy. Stop the real validator before replacing any live database.",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
