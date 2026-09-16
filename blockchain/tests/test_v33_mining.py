from __future__ import annotations

import json

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.mining_v33 import mine_block_multithread
from crakbit_chain.pow_pool_v33 import HardenedPoolLedger, VardiffPolicy
from crakbit_chain.pow_v31 import COIN, MAX_UINT256, PowChain, PowConfig
from crakbit_chain.randomx_v33 import (
    OFFICIAL_EXAMPLE_HASH_HEX,
    XMRIG_NONCE_OFFSET,
    candidate_vectors,
    randomx_candidate_blob,
    randomx_key_height,
    randomx_runtime_info,
    xmrig_target_from_difficulty,
)
from crakbit_chain.xmrig_v33 import build_xmrig_candidate_job, parse_xmrig_submit


def _easy_config() -> PowConfig:
    return PowConfig(
        chain_id="crakbit-pow-v33-test",
        target_block_time_seconds=60,
        retarget_interval=100,
        initial_target=MAX_UINT256,
        initial_subsidy=5 * COIN,
        halving_interval=1000,
        coinbase_maturity=1,
        scrypt_n=16,
        scrypt_r=1,
        scrypt_p=1,
    )


def test_v33_randomx_key_schedule_and_candidate_blob_layout():
    assert randomx_key_height(0) == 0
    assert randomx_key_height(63) == 0
    assert randomx_key_height(64) == 0
    assert randomx_key_height(2111) == 0
    assert randomx_key_height(2112) == 2048
    assert randomx_key_height(4096 + 64) == 4096

    header = candidate_vectors()["header"]
    blob = randomx_candidate_blob(header)
    assert len(blob) == 75
    assert XMRIG_NONCE_OFFSET == 39
    assert blob[39:43] == int(header["nonce"]).to_bytes(4, "little")
    assert candidate_vectors()["official_upstream_selftest"]["hash_hex"] == OFFICIAL_EXAMPLE_HASH_HEX


def test_v33_randomx_runtime_missing_library_is_nonfatal():
    info = randomx_runtime_info("/definitely/not/a/randomx/library.so")
    # The explicit path must not make an absent library appear available. A globally
    # installed RandomX library may still be discovered and is acceptable in CI.
    if info.library_path == "/definitely/not/a/randomx/library.so":
        assert info.available is False
    assert info.consensus_enabled is False


def test_v33_xmrig_candidate_job_and_submit_parser():
    header = candidate_vectors()["header"]
    record = build_xmrig_candidate_job(
        job_id="job-v33-1",
        header=header,
        seed_hash="44" * 32,
        full_target=(1 << 248) - 1,
    )
    assert record["job"]["algo"] == "rx/0"
    assert len(bytes.fromhex(record["job"]["blob"])) == 75
    assert len(bytes.fromhex(record["job"]["target"])) == 8
    parsed = parse_xmrig_submit({
        "params": {
            "job_id": "job-v33-1",
            "nonce": "01000000",
            "result": "aa" * 32,
        }
    })
    assert parsed["job_id"] == "job-v33-1"
    assert parsed["nonce"] == "01000000"
    assert int.from_bytes(bytes.fromhex(xmrig_target_from_difficulty(1.0)), "little") == (1 << 64) - 1


def test_v33_multithread_miner_finds_and_submits_easy_block(tmp_path):
    miner = KeyPair.generate()
    chain = PowChain(tmp_path / "chain.sqlite3", _easy_config(), create=True)
    try:
        template = chain.get_block_template(miner.address)
        mined = mine_block_multithread(template["block"], chain.config, threads=2, max_hashes_per_thread=5)
        assert mined.block is not None
        assert mined.hashes >= 1
        assert mined.threads == 2
        accepted = chain.submit_block(mined.block)
        assert accepted["accepted"] is True
        assert accepted["height"] == 1
    finally:
        chain.close()


def test_v33_hardened_pool_duplicate_share_reservation_and_vardiff(tmp_path):
    ledger = HardenedPoolLedger(tmp_path / "pool.sqlite3")
    policy = VardiffPolicy(
        target_share_seconds=10.0,
        minimum_multiplier=4,
        maximum_multiplier=1024,
        initial_multiplier=256,
        retarget_every_shares=2,
    )
    try:
        assert ledger.reserve_share(job_id="job", extra_nonce=7, nonce=11, hash_hex="11" * 32) is True
        assert ledger.reserve_share(job_id="job", extra_nonce=7, nonce=11, hash_hex="11" * 32) is False
        assert ledger.worker_multiplier("crk1abc", "worker", policy) == 256
        first = ledger.record_worker_share("crk1abc", "worker", policy)
        assert first["share_count"] == 1
        assert first["multiplier"] == 256
        stats = ledger.stats()
        assert stats["unique_submissions"] == 1
        assert stats["workers"] == 1
    finally:
        ledger.close()
