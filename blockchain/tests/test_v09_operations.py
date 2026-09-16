from __future__ import annotations

import json

from crakbit_chain.backups import create_ledger_backup, verify_ledger_backup
from crakbit_chain.crypto import KeyPair
from crakbit_chain.genesis import Genesis
from crakbit_chain.integrity import verify_ledger_integrity
from crakbit_chain.storage import Ledger


def make_genesis(tmp_path):
    validators = [KeyPair.generate() for _ in range(2)]
    treasury = KeyPair.generate()
    data = {
        "chain_id": "crakbit-v09-test-1",
        "network_name": "Crakbit v0.9 Test",
        "symbol": "CRKBIT",
        "decimals": 8,
        "max_supply": 21_000_000 * 100_000_000,
        "block_time_ms": 100,
        "view_timeout_ms": 200,
        "min_fee": 1000,
        "validators": [
            {
                "name": f"validator-{index + 1}",
                "address": key.address,
                "public_key": key.public_key_b64,
                "peer_url": f"http://127.0.0.1:{9101 + index}",
            }
            for index, key in enumerate(validators)
        ],
        "allocations": {treasury.address: 100 * 100_000_000},
    }
    path = tmp_path / "genesis.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return Genesis.load(path)


def test_integrity_checker_accepts_clean_genesis_database(tmp_path):
    genesis = make_genesis(tmp_path)
    ledger = Ledger(tmp_path / "chain.sqlite3", genesis)

    quick = verify_ledger_integrity(ledger, full=False)
    full = verify_ledger_integrity(ledger, full=True)

    assert quick["ok"] is True
    assert full["ok"] is True
    assert full["checks"]["tip"]["height"] == 0
    assert full["checks"]["issued_supply"]["actual"] == sum(genesis.allocations.values())


def test_integrity_checker_detects_tip_metadata_tamper(tmp_path):
    genesis = make_genesis(tmp_path)
    ledger = Ledger(tmp_path / "chain.sqlite3", genesis)

    with ledger.connect() as conn:
        conn.execute("UPDATE metadata SET value=? WHERE key='last_hash'", ("f" * 64,))

    report = verify_ledger_integrity(ledger, full=True)
    assert report["ok"] is False
    assert any("genesis-height database" in item for item in report["errors"])


def test_integrity_checker_understands_snapshot_base_without_local_history(tmp_path):
    genesis = make_genesis(tmp_path)
    ledger = Ledger(tmp_path / "snapshot-node.sqlite3", genesis)
    base_hash = "a" * 64
    base_root = "b" * 64

    with ledger.connect() as conn:
        conn.execute("UPDATE metadata SET value='5' WHERE key='height'")
        conn.execute("UPDATE metadata SET value=? WHERE key='last_hash'", (base_hash,))
        conn.execute("INSERT INTO metadata(key,value) VALUES('snapshot_base_height','5')")
        conn.execute("INSERT INTO metadata(key,value) VALUES('snapshot_base_hash',?)", (base_hash,))
        conn.execute("INSERT INTO metadata(key,value) VALUES('snapshot_accounts_root',?)", (base_root,))

    report = verify_ledger_integrity(ledger, full=True)
    assert report["ok"] is True
    assert report["checks"]["snapshot_base"]["bootstrapped"] is True
    assert report["checks"]["local_history"]["start"] == 6
    assert report["checks"]["local_history"]["stored_blocks"] == 0


def test_verified_backup_roundtrip_and_manifest_tamper_detection(tmp_path):
    genesis = make_genesis(tmp_path)
    ledger = Ledger(tmp_path / "source" / "chain.sqlite3", genesis)
    backup_path = tmp_path / "backups" / "chain-backup.sqlite3"

    created = create_ledger_backup(ledger, backup_path)
    verified = verify_ledger_backup(
        created["backup"],
        created["manifest"],
        genesis,
        full=True,
    )
    assert verified["ok"] is True

    manifest_path = tmp_path / "backups" / "chain-backup.sqlite3.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["database_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    rejected = verify_ledger_backup(backup_path, manifest_path, genesis, full=False)
    assert rejected["ok"] is False
    assert any("SHA-256" in item for item in rejected["errors"])
