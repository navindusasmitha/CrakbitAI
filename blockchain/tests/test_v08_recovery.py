from __future__ import annotations

import json

import pytest

from crakbit_chain.crypto import KeyPair, canonical_json, sha256_hex
from crakbit_chain.genesis import Genesis
from crakbit_chain.snapshot_transfer import (
    build_snapshot_bundle,
    load_cached_chunks,
    save_bundle_cache,
    verify_snapshot_bundle,
)
from crakbit_chain.snapshots import (
    IMPORT_JOURNAL_FORMAT,
    build_snapshot_certificate,
    import_snapshot_certificate,
    sign_snapshot,
    snapshot_import_journal_path,
    snapshot_import_journal_status,
)
from crakbit_chain.storage import Ledger, LedgerError


def make_genesis(tmp_path, validator_count: int = 4):
    validators = [KeyPair.generate() for _ in range(validator_count)]
    treasury = KeyPair.generate()
    data = {
        "chain_id": "crakbit-v08-test-1",
        "network_name": "Crakbit v0.8 Test",
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
    return Genesis.load(path), validators


def test_snapshot_bundle_roundtrip_and_chunk_tamper_detection(tmp_path):
    artifact = {"kind": "test", "payload": "x" * 5000}
    manifest, chunks = build_snapshot_bundle(artifact, chunk_size=1024)
    assert manifest["total_chunks"] > 1
    assert verify_snapshot_bundle(manifest, chunks) == artifact

    target = save_bundle_cache(tmp_path / "cache", manifest, chunks)
    cached, reused = load_cached_chunks(target, manifest)
    assert reused == manifest["total_chunks"]
    assert verify_snapshot_bundle(manifest, [chunk for chunk in cached if chunk is not None]) == artifact

    tampered = list(chunks)
    tampered[0] = b"!" + tampered[0][1:]
    with pytest.raises(LedgerError, match="chunk 0 hash mismatch"):
        verify_snapshot_bundle(manifest, tampered)


def test_snapshot_bundle_missing_chunk_is_rejected():
    artifact = {"payload": "y" * 4000}
    manifest, chunks = build_snapshot_bundle(artifact, chunk_size=1024)
    with pytest.raises(LedgerError, match="incomplete"):
        verify_snapshot_bundle(manifest, chunks[:-1])


def test_snapshot_import_journal_is_removed_after_commit_and_stale_committed_journal_recovers(tmp_path):
    genesis, validators = make_genesis(tmp_path)
    source = Ledger(tmp_path / "source.sqlite3", genesis)
    envelopes = [sign_snapshot(source, key) for key in validators[: genesis.quorum_size]]
    certificate = build_snapshot_certificate(envelopes, genesis)

    recovered_dir = tmp_path / "recovered"
    recovered = Ledger(recovered_dir / "chain.sqlite3", genesis)
    snapshot = import_snapshot_certificate(recovered, certificate)
    journal_path = snapshot_import_journal_path(recovered)
    assert not journal_path.exists()
    assert snapshot_import_journal_status(recovered)["present"] is False
    assert recovered.height == snapshot["height"]
    assert recovered.last_hash == snapshot["last_hash"]

    certificate_hash = sha256_hex(canonical_json(certificate))
    journal_path.write_text(
        json.dumps(
            {
                "format": IMPORT_JOURNAL_FORMAT,
                "state": "prepared",
                "certificate_hash": certificate_hash,
                "target_height": snapshot["height"],
                "target_last_hash": snapshot["last_hash"],
                "accounts_root": snapshot["accounts_root"],
                "prepared_at_ms": 1,
            }
        ),
        encoding="utf-8",
    )

    repeated = import_snapshot_certificate(recovered, certificate)
    assert repeated["accounts_root"] == snapshot["accounts_root"]
    assert not journal_path.exists()


def test_snapshot_import_journal_for_different_certificate_blocks_automatic_overwrite(tmp_path):
    genesis, validators = make_genesis(tmp_path)
    source = Ledger(tmp_path / "source.sqlite3", genesis)
    certificate = build_snapshot_certificate(
        [sign_snapshot(source, key) for key in validators[: genesis.quorum_size]],
        genesis,
    )
    recovered = Ledger(tmp_path / "recovered" / "chain.sqlite3", genesis)
    journal_path = snapshot_import_journal_path(recovered)
    journal_path.write_text(
        json.dumps(
            {
                "format": IMPORT_JOURNAL_FORMAT,
                "state": "prepared",
                "certificate_hash": "f" * 64,
                "target_height": 99,
                "target_last_hash": "e" * 64,
                "accounts_root": "d" * 64,
                "prepared_at_ms": 1,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(LedgerError, match="different certificate"):
        import_snapshot_certificate(recovered, certificate)
