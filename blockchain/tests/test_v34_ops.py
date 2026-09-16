from __future__ import annotations

from crakbit_chain.algorithm_gate_v34 import (
    build_algorithm_decision,
    build_benchmark_gate,
    build_benchmark_record,
    verify_algorithm_decision,
    verify_benchmark_gate,
    verify_benchmark_record,
)
from crakbit_chain.crypto import KeyPair
from crakbit_chain.pool_payout_v34 import build_payout_plan, mark_submitted, reconcile_payout_plan
from crakbit_chain.pow_ops_v34 import (
    PeerBookV34,
    UndoJournalV34,
    build_watch_only,
    chain_statistics,
    fee_estimate,
    transaction_confirmations,
)
from crakbit_chain.pow_pool_v31 import PoolLedger
from crakbit_chain.pow_v31 import COIN, MAX_UINT256, PowChain, PowConfig, mine_block


def _config() -> PowConfig:
    return PowConfig(
        chain_id="crakbit-v34-test",
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


def _mine(chain: PowChain, address: str) -> dict:
    template = chain.get_block_template(address)
    found, hashes = mine_block(template["block"], chain.config, max_hashes=10)
    assert found is not None
    assert hashes >= 1
    return chain.submit_block(found)


def test_v34_signed_benchmark_gate_requires_human_decision(tmp_path):
    a = KeyPair.generate()
    b = KeyPair.generate()
    gate_key = KeyPair.generate()
    a_path = tmp_path / "a.json"
    b_path = tmp_path / "b.json"
    gate_path = tmp_path / "gate.json"
    a.save(a_path)
    b.save(b_path)
    gate_key.save(gate_path)

    record_a = build_benchmark_record(
        signing_key_path=a_path,
        machine_id="machine-a",
        cpu_model="CPU A",
        logical_threads=8,
        ram_mib=8192,
        scrypt_hps=100.0,
        randomx_hps=500.0,
        randomx_mode="light",
        randomx_selftest_passed=True,
    )
    record_b = build_benchmark_record(
        signing_key_path=b_path,
        machine_id="machine-b",
        cpu_model="CPU B",
        logical_threads=16,
        ram_mib=16384,
        scrypt_hps=200.0,
        randomx_hps=900.0,
        randomx_mode="fast",
        randomx_selftest_passed=True,
    )
    assert verify_benchmark_record(record_a)["valid"] is True
    gate = build_benchmark_gate(signing_key_path=gate_path, records=[record_a, record_b])
    verified_gate = verify_benchmark_gate(gate)
    assert verified_gate["benchmark_gate_satisfied"] is True
    assert verified_gate["human_algorithm_decision_required"] is True

    decision = build_algorithm_decision(
        signing_key_path=gate_path,
        benchmark_gate=gate,
        decision="randomx",
        rationale="Synthetic regression fixture; activation still requires a separate versioned consensus change.",
    )
    verified = verify_algorithm_decision(decision)
    assert verified["decision"] == "randomx"
    assert verified["consensus_activation_authorized"] is False


def test_v34_peer_book_coarse_diversity(tmp_path):
    book = PeerBookV34(tmp_path / "peers.sqlite3")
    try:
        book.note("10.1.1.1:28444", success=True)
        book.note("10.1.2.2:28444", success=True)
        book.note("10.2.1.1:28444", success=True)
        book.note("192.168.1.10:28444", success=True)
        selected = book.select(limit=10, max_per_bucket=1)
        assert len(selected) == 3
        assert sum(1 for endpoint in selected if endpoint.startswith("10.1.")) == 1
    finally:
        book.close()


def test_v34_watch_only_contains_no_private_key():
    key = KeyPair.generate()
    record = build_watch_only(key.address, label="cold watch")
    assert record["address"] == key.address
    assert record["contains_private_key"] is False
    assert "private_key" not in record


def test_v34_mature_payout_plan_reconcile_undo_and_stats(tmp_path):
    pool_wallet = KeyPair.generate()
    miner_a = KeyPair.generate()
    miner_b = KeyPair.generate()
    wallet_path = tmp_path / "pool-wallet.json"
    pool_wallet.save(wallet_path)

    chain_path = tmp_path / "chain.sqlite3"
    chain = PowChain(chain_path, _config(), create=True)
    try:
        _mine(chain, pool_wallet.address)
        _mine(chain, pool_wallet.address)
        assert chain.balance(pool_wallet.address)["confirmed"] >= 5 * COIN
    finally:
        chain.close()

    pool_path = tmp_path / "pool.sqlite3"
    ledger = PoolLedger(pool_path)
    try:
        ledger.db.execute("INSERT INTO balances(payout_address,pending_amount) VALUES(?,?)", (miner_a.address, 1 * COIN))
        ledger.db.execute("INSERT INTO balances(payout_address,pending_amount) VALUES(?,?)", (miner_b.address, 2 * COIN))
        ledger.db.commit()
    finally:
        ledger.close()

    plan = build_payout_plan(
        chain_db=chain_path,
        pool_db=pool_path,
        wallet_path=wallet_path,
        minimum_payout=COIN // 2,
        fee=1000,
        max_recipients=10,
    )
    assert plan["total_payout"] == 3 * COIN
    assert plan["automatic_submit"] is False
    assert len(plan["payouts"]) == 2

    mark_submitted(pool_path, plan["plan_id"])
    chain = PowChain(chain_path)
    try:
        accepted = chain.submit_transaction(plan["transaction"])
        assert accepted["txid"] == plan["txid"]
        assert transaction_confirmations(chain_path, plan["txid"])["state"] == "mempool"
        _mine(chain, pool_wallet.address)
        status = transaction_confirmations(chain_path, plan["txid"])
        assert status["state"] == "confirmed"
        assert status["confirmations"] >= 1
    finally:
        chain.close()

    finalized = reconcile_payout_plan(
        chain_db=chain_path,
        pool_db=pool_path,
        plan_id=plan["plan_id"],
        minimum_confirmations=1,
    )
    assert finalized["finalized"] is True

    ledger = PoolLedger(pool_path)
    try:
        balances = ledger.balances()
        assert balances[miner_a.address] == 0
        assert balances[miner_b.address] == 0
    finally:
        ledger.close()

    journal = UndoJournalV34(chain_path)
    try:
        backfill = journal.backfill()
        assert backfill["count"] == 3
        verified = journal.verify()
        assert verified["valid"] is True
        assert verified["checked"] == 3
        assert verified["live_reorg_engine_uses_incremental_undo"] is False
    finally:
        journal.close()

    stats = chain_statistics(chain_path, window=10)
    assert stats["height"] == 3
    assert stats["estimated_network_hashrate_hps"] is not None
    estimate = fee_estimate(chain_path)
    assert estimate["median_atomic_per_byte"] >= 1
