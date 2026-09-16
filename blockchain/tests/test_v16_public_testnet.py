from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from crakbit_chain.comet_lab import build_consensus_genesis, rewrite_config
from crakbit_chain.crypto import KeyPair
from crakbit_chain.durable_limits import DurableFixedWindowLimiter
from crakbit_chain.explorer_index import ExternalExplorerIndex
from crakbit_chain.external_commit_v16 import ExternalExecutionStoreV16
from crakbit_chain.external_state_sync import (
    export_external_snapshot,
    import_external_snapshot,
    verify_external_snapshot,
)
from crakbit_chain.genesis import Genesis
from crakbit_chain.models import ATOMIC_UNITS, Transaction
from crakbit_chain.storage import Ledger
from crakbit_chain.testnet_health import evaluate_health


def make_env(tmp_path: Path):
    validator = KeyPair.generate()
    treasury = KeyPair.generate()
    recipient = KeyPair.generate()
    data = {
        "chain_id": "crakbit-v16-test-1",
        "network_name": "Crakbit v0.16 Test",
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
        "allocations": {treasury.address: 100 * ATOMIC_UNITS},
    }
    genesis_path = tmp_path / "genesis.json"
    genesis_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return genesis_path, Genesis.load(genesis_path), validator, treasury, recipient


def signed_tx(genesis: Genesis, sender: KeyPair, recipient: str, nonce: int = 1):
    tx = Transaction(
        chain_id=genesis.chain_id,
        sender=sender.address,
        recipient=recipient,
        amount=ATOMIC_UNITS,
        fee=genesis.min_fee,
        nonce=nonce,
        public_key=sender.public_key_b64,
        memo="v16-test",
    )
    tx.signature = sender.sign(tx.signing_bytes())
    return tx


def test_durable_fixed_window_survives_reopen(tmp_path):
    path = tmp_path / "limits.sqlite3"
    first = DurableFixedWindowLimiter(2, 60, path=path, namespace="test")
    assert first.allow("client", now=120.0) == (True, 1)
    second = DurableFixedWindowLimiter(2, 60, path=path, namespace="test")
    assert second.allow("client", now=121.0) == (True, 0)
    assert second.allow("client", now=122.0)[0] is False
    assert second.allow("client", now=181.0) == (True, 1)


def test_external_checkpoint_restore_and_continue(tmp_path):
    _, genesis, _, treasury, recipient = make_env(tmp_path)
    source_dir = tmp_path / "source"
    ledger = Ledger(source_dir / "chain.sqlite3", genesis)
    store = ExternalExecutionStoreV16(ledger)
    tx = signed_tx(genesis, treasury, recipient.address)
    store.stage_finalize(
        height=1,
        consensus_block_hash="11" * 32,
        transactions=[tx.to_dict()],
    )
    committed = store.commit_pending()
    assert committed["height"] == 1

    envelope = export_external_snapshot(store.ledger)
    verified = verify_external_snapshot(
        envelope,
        genesis,
        expected_height=1,
        expected_application_hash=envelope["snapshot"]["application_hash"],
    )
    assert verified["valid"] is True

    restored_dir = tmp_path / "restored"
    restored_result = import_external_snapshot(
        envelope=envelope,
        genesis=genesis,
        data_dir=restored_dir,
        expected_height=1,
        expected_application_hash=verified["application_hash"],
    )
    assert restored_result["height"] == 1
    restored = ExternalExecutionStoreV16(Ledger(restored_dir / "chain.sqlite3", genesis))
    assert restored.status()["snapshot_base"]["height"] == 1

    tx2 = signed_tx(genesis, treasury, recipient.address, nonce=2)
    restored.stage_finalize(
        height=2,
        consensus_block_hash="22" * 32,
        transactions=[tx2.to_dict()],
    )
    assert restored.commit_pending()["height"] == 2
    assert restored.status()["post_snapshot_commit_count"] == 1


def test_external_explorer_index_syncs_commits_transactions_and_accounts(tmp_path):
    _, genesis, _, treasury, recipient = make_env(tmp_path)
    source_dir = tmp_path / "external"
    store = ExternalExecutionStoreV16(Ledger(source_dir / "chain.sqlite3", genesis))
    tx = signed_tx(genesis, treasury, recipient.address)
    store.stage_finalize(
        height=1,
        consensus_block_hash="33" * 32,
        transactions=[tx.to_dict()],
    )
    store.commit_pending()

    index = ExternalExplorerIndex(tmp_path / "explorer.sqlite3", genesis)
    result = index.sync_from_source(source_dir)
    assert result["new_commits"] == 1
    assert result["new_transactions"] == 1
    assert index.summary()["indexed_height"] == 1
    assert index.transaction(tx.txid)["sender"] == treasury.address
    activity = index.account(recipient.address)
    assert activity["account"]["balance"] == ATOMIC_UNITS
    assert activity["activity"][0]["direction"] == "in"


def test_comet_lab_helpers_build_shared_genesis_and_rewrite_ports():
    template = {
        "genesis_time": "2026-01-01T00:00:00Z",
        "chain_id": "old",
        "initial_height": "0",
        "validators": [],
        "app_hash": "abc",
    }
    validators = [
        {
            "address": "AA",
            "pub_key": {"type": "tendermint/PubKeyEd25519", "value": "abc"},
            "power": "10",
            "name": "validator-1",
        },
        {
            "address": "BB",
            "pub_key": {"type": "tendermint/PubKeyEd25519", "value": "def"},
            "power": "10",
            "name": "validator-2",
        },
    ]
    genesis = build_consensus_genesis(template, validators, chain_id="crakbit-lab")
    assert genesis["chain_id"] == "crakbit-lab"
    assert len(genesis["validators"]) == 2
    assert genesis["app_hash"] == ""

    config = '''proxy_app = "tcp://127.0.0.1:26658"\n[rpc]\nladdr = "tcp://127.0.0.1:26657"\n[p2p]\nladdr = "tcp://0.0.0.0:26656"\npersistent_peers = ""\n'''
    rewritten = rewrite_config(
        config,
        rpc_port=27657,
        p2p_port=27656,
        abci_port=27658,
        persistent_peers="id@127.0.0.1:27666",
    )
    assert 'proxy_app = "tcp://127.0.0.1:27658"' in rewritten
    assert 'laddr = "tcp://127.0.0.1:27657"' in rewritten
    assert 'persistent_peers = "id@127.0.0.1:27666"' in rewritten


def test_gateway_v16_adds_same_origin_csp_and_durable_security_status(tmp_path, monkeypatch):
    genesis_path, _, _, _, _ = make_env(tmp_path)
    monkeypatch.setenv("CRAKBIT_GATEWAY_GENESIS", str(genesis_path))
    monkeypatch.setenv("CRAKBIT_GATEWAY_MODE", "research")
    monkeypatch.setenv("CRAKBIT_GATEWAY_RATE_LIMIT_DB", str(tmp_path / "gateway-limits.sqlite3"))
    monkeypatch.delenv("CRAKBIT_GATEWAY_ALLOWED_ORIGINS", raising=False)

    # Import after supplying the default module-level configuration. The production
    # launchers also set these variables before importing the application module.
    from crakbit_chain.public_gateway import GatewayConfig
    from crakbit_chain.public_gateway_v16 import create_app as create_gateway_v16

    config = GatewayConfig(genesis_path=str(genesis_path), mode="research")
    app = create_gateway_v16(config)
    client = TestClient(app)
    response = client.get("/api/security/status")
    assert response.status_code == 200
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert response.json()["cors"]["default_same_origin_only"] is True
    assert response.json()["durable_write_rate_limit"]["survives_process_restart"] is True


def test_health_evaluator_detects_height_divergence():
    healthy = evaluate_health(
        [
            {"name": "a", "reachable": True, "height": 100, "catching_up": False},
            {"name": "b", "reachable": True, "height": 101, "catching_up": False},
        ],
        max_height_spread=2,
    )
    assert healthy["healthy"] is True
    unhealthy = evaluate_health(
        [
            {"name": "a", "reachable": True, "height": 100, "catching_up": False},
            {"name": "b", "reachable": True, "height": 110, "catching_up": False},
        ],
        max_height_spread=2,
    )
    assert unhealthy["healthy"] is False
