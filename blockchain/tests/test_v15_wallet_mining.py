from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from crakbit_chain.crypto import KeyPair
from crakbit_chain.execution_service_v14 import ExecutionServiceV14Config, create_app as create_execution_app
from crakbit_chain.models import ATOMIC_UNITS
from crakbit_chain.pow_mining import MiningStore, meets_difficulty, work_digest
from crakbit_chain.public_gateway import GatewayConfig


def make_genesis(tmp_path: Path):
    validator = KeyPair.generate()
    treasury = KeyPair.generate()
    reward = KeyPair.generate()
    data = {
        "chain_id": "crakbit-v15-test-1",
        "network_name": "Crakbit v0.15 Test",
        "symbol": "CRKBIT",
        "decimals": 8,
        "max_supply": 21_000_000 * ATOMIC_UNITS,
        "block_time_ms": 100,
        "view_timeout_ms": 200,
        "min_fee": 1000,
        "validators": [
            {
                "name": "validator-1",
                "address": validator.address,
                "public_key": validator.public_key_b64,
                "peer_url": "http://127.0.0.1:9101",
            }
        ],
        "allocations": {
            treasury.address: 100 * ATOMIC_UNITS,
            reward.address: 50 * ATOMIC_UNITS,
        },
    }
    path = tmp_path / "genesis.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, validator, treasury, reward


def test_pow_digest_and_persistent_claim_state(tmp_path):
    store_path = tmp_path / "mining.sqlite3"
    store = MiningStore(store_path)
    address = "crk1" + "a" * 40
    challenge = store.issue_challenge(
        address,
        difficulty_bits=8,
        reward_atomic=ATOMIC_UNITS,
        ttl_seconds=300,
        cooldown_seconds=60,
        daily_limit=10,
        now_ms=1_000_000,
    )

    nonce = 0
    while True:
        digest = work_digest(
            challenge["challenge_id"],
            address,
            challenge["seed"],
            nonce,
        )
        if meets_difficulty(digest, challenge["difficulty_bits"]):
            break
        nonce += 1
        assert nonce < 20_000

    reserved = store.reserve_solution(
        challenge["challenge_id"],
        address,
        nonce,
        now_ms=1_001_000,
    )
    assert reserved["status"] == "submitting"
    assert reserved["digest"] == digest
    store.mark_submitted(challenge["challenge_id"], "f" * 64)

    restarted = MiningStore(store_path)
    assert restarted.stats()["submitted_rewards"] == 1
    with pytest.raises(ValueError, match="cooldown"):
        restarted.issue_challenge(
            address,
            difficulty_bits=8,
            reward_atomic=ATOMIC_UNITS,
            ttl_seconds=300,
            cooldown_seconds=60,
            daily_limit=10,
            now_ms=1_020_000,
        )


def test_external_execution_read_api_for_gateway(tmp_path):
    genesis_path, _, treasury, _ = make_genesis(tmp_path)
    token = "v15-test-token-" + "x" * 24
    config = ExecutionServiceV14Config(
        genesis_path=str(genesis_path),
        data_dir=str(tmp_path / "external-app"),
        bearer_token=token,
    )
    client = TestClient(create_execution_app(config))
    headers = {"Authorization": f"Bearer {token}"}

    info = client.get("/v2/info", headers=headers)
    assert info.status_code == 200
    assert info.json()["symbol"] == "CRKBIT"

    account = client.get(f"/v2/account/{treasury.address}", headers=headers)
    assert account.status_code == 200
    assert account.json()["account"]["balance"] == 100 * ATOMIC_UNITS

    commits = client.get("/v2/commits?limit=10", headers=headers)
    assert commits.status_code == 200
    assert commits.json()["count"] == 0


def test_gateway_config_and_packaged_wallet_ui(tmp_path):
    genesis_path, _, _, _ = make_genesis(tmp_path)
    config = GatewayConfig(genesis_path=str(genesis_path), mode="research")
    config.validate()

    package_dir = Path(__file__).resolve().parents[1] / "crakbit_chain" / "webui"
    html = (package_dir / "index.html").read_text(encoding="utf-8")
    js = (package_dir / "app.js").read_text(encoding="utf-8")
    assert "Local wallet vault" in html
    assert "This is not consensus block mining" in html
    assert "PBKDF2" in js
    assert "Ed25519" in js
    assert "crakbit-encrypted-wallet/1" in js
