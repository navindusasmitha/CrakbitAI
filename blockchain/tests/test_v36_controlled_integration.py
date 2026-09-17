from __future__ import annotations

from crakbit_chain.algorithm_gate_v34 import build_algorithm_decision, build_benchmark_gate, build_benchmark_record
from crakbit_chain.crypto import KeyPair
from crakbit_chain.pow_activation_v36 import build_activation_proposal, verify_activation_proposal
from crakbit_chain.pow_campaign_v36 import CampaignLogV36, load_campaign_log, summarize_campaign, verify_campaign_log
from crakbit_chain.pow_node_v36 import select_seed_peers_v36
from crakbit_chain.pow_ops_v34 import PeerBookV34
from crakbit_chain.pow_reorg_v36 import rehearse_incremental_undo
from crakbit_chain.pow_testnet_v35 import OBSERVATION_FORMAT
from crakbit_chain.pow_v31 import COIN, MAX_UINT256, PowChain, PowConfig, mine_block


def _config() -> PowConfig:
    return PowConfig(
        chain_id="crakbit-v36-test",
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


def _mine(chain: PowChain, address: str) -> None:
    template = chain.get_block_template(address)
    block, hashes = mine_block(template["block"], chain.config, max_hashes=10)
    assert block is not None and hashes >= 1
    assert chain.submit_block(block)["accepted"] is True


def _observation(node_id: str, *, height: int = 10, block_hash: str = "11" * 32) -> dict:
    return {
        "format": OBSERVATION_FORMAT,
        "observed_at_unix": 0,
        "rpc_url": f"https://{node_id}.example",
        "reachable": True,
        "latency_ms": 5,
        "chain_id": "crakbit-v36-test",
        "genesis_hash": "22" * 32,
        "height": height,
        "best_block_hash": block_hash,
        "chainwork": "1000",
        "pow_algo": "crakpow-scrypt-v1",
        "peer_count": 3,
        "node_id": node_id,
        "production_mainnet_ready": False,
    }


def test_v36_campaign_log_is_signed_hash_chained_and_real_duration_gated(tmp_path, monkeypatch):
    import crakbit_chain.pow_campaign_v36 as campaign

    evidence = KeyPair.generate()
    key_path = tmp_path / "evidence.json"
    evidence.save(key_path)
    log_path = tmp_path / "campaign.jsonl"
    observations = [_observation(f"node-{i}") for i in range(4)]

    monkeypatch.setattr(campaign.time, "time", lambda: 1_800_000_000)
    log = CampaignLogV36(log_path, key_path)
    log.append_observations(observations, label="start")

    monkeypatch.setattr(campaign.time, "time", lambda: 1_800_000_000 + 24 * 3600)
    log.append_observations(observations, label="end")

    records = load_campaign_log(log_path)
    verified = verify_campaign_log(records)
    assert verified["valid"] is True
    assert verified["entry_count"] == 2
    summary = summarize_campaign(records, required_level="24h", minimum_nodes=4)
    assert summary["actual_seconds"] == 24 * 3600
    assert summary["campaign_gate_satisfied"] is True
    assert summary["production_mainnet_ready"] is False


def test_v36_incremental_undo_rehearsal_matches_clean_replay(tmp_path):
    miner = KeyPair.generate()
    chain_path = tmp_path / "chain.sqlite3"
    chain = PowChain(chain_path, _config(), create=True)
    try:
        _mine(chain, miner.address)
        _mine(chain, miner.address)
        _mine(chain, miner.address)
        assert chain.tip()["height"] == 3
    finally:
        chain.close()

    result = rehearse_incremental_undo(chain_path, disconnect_blocks=2)
    assert result["rehearsal_passed"] is True
    assert result["target_height"] == 1
    assert result["incremental_utxo_sha256"] == result["clean_replay_utxo_sha256"]
    assert result["live_reorg_engine_switched_to_incremental_undo"] is False

    original = PowChain(chain_path)
    try:
        assert original.tip()["height"] == 3
    finally:
        original.close()


def test_v36_peer_book_is_used_for_live_seed_selection(tmp_path):
    peer_db = tmp_path / "peers.sqlite3"
    book = PeerBookV34(peer_db)
    try:
        book.note("10.1.1.1:28444", success=True)
        book.note("10.1.2.2:28444", success=True)
        book.note("10.2.1.1:28444", success=True)
        book.note("192.168.1.1:28444", success=True)
    finally:
        book.close()

    selected = select_seed_peers_v36(
        peer_db=peer_db,
        explicit_peers=["127.0.0.1:28444"],
        limit=10,
        max_per_bucket=1,
    )
    assert selected["selected_peers"][0] == "127.0.0.1:28444"
    assert len(selected["selected_peers"]) == 4
    assert selected["coarse_diversity_only"] is True


def test_v36_randomx_decision_only_builds_nonactivating_testnet_proposal(tmp_path):
    machine_a = KeyPair.generate()
    machine_b = KeyPair.generate()
    release = KeyPair.generate()
    a_path = tmp_path / "a.json"
    b_path = tmp_path / "b.json"
    release_path = tmp_path / "release.json"
    machine_a.save(a_path)
    machine_b.save(b_path)
    release.save(release_path)

    a = build_benchmark_record(
        signing_key_path=a_path,
        machine_id="machine-a",
        cpu_model="CPU A",
        logical_threads=8,
        ram_mib=8192,
        scrypt_hps=100,
        randomx_hps=500,
        randomx_mode="light",
        randomx_selftest_passed=True,
    )
    b = build_benchmark_record(
        signing_key_path=b_path,
        machine_id="machine-b",
        cpu_model="CPU B",
        logical_threads=16,
        ram_mib=16384,
        scrypt_hps=200,
        randomx_hps=900,
        randomx_mode="fast",
        randomx_selftest_passed=True,
    )
    gate = build_benchmark_gate(signing_key_path=release_path, records=[a, b])
    decision = build_algorithm_decision(
        signing_key_path=release_path,
        benchmark_gate=gate,
        decision="randomx",
        rationale="Regression fixture only; no production activation.",
    )
    proposal = build_activation_proposal(
        key_path=release_path,
        algorithm_decision=decision,
        source_commit="ab" * 20,
        chain_id="crakbit-v36-test",
        genesis_hash="cd" * 32,
        current_height=10_000,
        activation_height=12_000,
        consensus_vectors_sha256="11" * 32,
        randomx_library_sha256="22" * 32,
        minimum_notice_blocks=1000,
    )
    verified = verify_activation_proposal(proposal)
    assert verified["valid"] is True
    assert verified["decision"] == "randomx"
    assert verified["consensus_activated"] is False
    assert verified["testnet_proposal_only"] is True
