from __future__ import annotations

import json

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.pow_pool_v31 import PoolLedger
from crakbit_chain.pow_v31 import COIN, MAX_UINT256, PowChain, PowConfig, PowV31Error, mine_block, transaction_id


def _config() -> PowConfig:
    return PowConfig(
        chain_id="crakbit-pow-test-v31",
        target_block_time_seconds=60,
        retarget_interval=100,
        initial_target=MAX_UINT256,
        initial_subsidy=10 * COIN,
        halving_interval=1000,
        coinbase_maturity=1,
        scrypt_n=16,
        scrypt_r=1,
        scrypt_p=1,
    )


def _mine(chain: PowChain, address: str):
    template = chain.get_block_template(address)
    found, hashes = mine_block(template["block"], chain.config, max_hashes=10)
    assert found is not None
    assert hashes >= 1
    result = chain.submit_block(found)
    assert result["accepted"] is True
    return result


def test_v31_real_pow_blocks_utxo_payment_and_fees(tmp_path):
    miner = KeyPair.generate()
    recipient = KeyPair.generate()
    chain = PowChain(tmp_path / "pow.sqlite3", _config(), create=True)
    try:
        assert chain.tip()["height"] == 0
        first = _mine(chain, miner.address)
        assert first["height"] == 1
        assert chain.balance(miner.address)["immature"] == 10 * COIN

        _mine(chain, miner.address)
        assert chain.balance(miner.address)["confirmed"] >= 10 * COIN

        payment = chain.create_payment(miner, recipient.address, 3 * COIN, 1000)
        accepted = chain.submit_transaction(payment)
        assert accepted["accepted"] is True
        assert accepted["fee"] == 1000
        assert transaction_id(payment) == accepted["txid"]

        template = chain.get_block_template(miner.address)
        assert template["fees"] == 1000
        assert template["coinbase_value"] == 10 * COIN + 1000
        found, _ = mine_block(template["block"], chain.config, max_hashes=10)
        assert found is not None
        chain.submit_block(found)
        assert chain.balance(recipient.address)["confirmed"] == 3 * COIN
        assert chain.info()["pow_algo"] == "crakpow-scrypt-v1"
        assert chain.info()["production_mainnet_ready"] is False
    finally:
        chain.close()


def test_v31_rejects_invalid_pow_and_coinbase_value(tmp_path):
    miner = KeyPair.generate()
    chain = PowChain(tmp_path / "pow.sqlite3", _config(), create=True)
    try:
        template = chain.get_block_template(miner.address)
        block = template["block"]
        block["transactions"][0]["outputs"][0]["amount"] += 1
        # Updating the coinbase changes the merkle root; even if the PoW target is easy,
        # consensus must reject the altered block.
        with pytest.raises(PowV31Error):
            chain.submit_block(block)
    finally:
        chain.close()


def test_v31_mempool_prevents_double_spend(tmp_path):
    miner = KeyPair.generate()
    a = KeyPair.generate()
    b = KeyPair.generate()
    chain = PowChain(tmp_path / "pow.sqlite3", _config(), create=True)
    try:
        _mine(chain, miner.address)
        _mine(chain, miner.address)
        tx1 = chain.create_payment(miner, a.address, 2 * COIN, 100)
        chain.submit_transaction(tx1)
        tx2 = chain.create_payment(miner, b.address, 2 * COIN, 100)
        with pytest.raises(PowV31Error):
            chain.submit_transaction(tx2)
    finally:
        chain.close()


def test_v31_pool_pplns_internal_accounting(tmp_path):
    ledger = PoolLedger(tmp_path / "pool.sqlite3")
    try:
        template = {"block": {"header": {}}, "coinbase_value": 1000}
        ledger.put_job({"job_id": "job-1", "height": 1, "network_target": "f" * 64, "share_target": "f" * 64, "template": template})
        ledger.add_share(job_id="job-1", worker="a", payout_address="crk1a", hash_hex="1" * 64, is_block=False, block_hash_value=None)
        ledger.add_share(job_id="job-1", worker="b", payout_address="crk1b", hash_hex="2" * 64, is_block=True, block_hash_value="2" * 64)
        credits = ledger.credit_pplns(block_hash_value="2" * 64, height=1, reward=1000, window=100)
        assert sum(credits.values()) == 1000
        assert ledger.balances()["crk1a"] == 500
        assert ledger.balances()["crk1b"] == 500
    finally:
        ledger.close()


def test_v31_config_is_explicitly_devnet_and_not_production(tmp_path):
    config = _config()
    chain = PowChain(tmp_path / "pow.sqlite3", config, create=True)
    try:
        info = chain.info()
        assert info["network"] == "devnet"
        assert info["production_mainnet_ready"] is False
        assert info["production_crkbit_launched"] is False
    finally:
        chain.close()
