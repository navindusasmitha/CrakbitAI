from __future__ import annotations

import asyncio
import json

import pytest

from crakbit_chain.crypto import KeyPair
from crakbit_chain.pow_network_v32 import (
    PowNetworkChain,
    PowNetworkV32Error,
    PowP2PNode,
    build_peer_hello,
    verify_peer_hello,
)
from crakbit_chain.pow_v31 import COIN, MAX_UINT256, PowChain, PowConfig, mine_block


def _config() -> PowConfig:
    return PowConfig(
        chain_id="crakbit-pow-net-test-v32",
        target_block_time_seconds=30,
        retarget_interval=100,
        initial_target=MAX_UINT256,
        initial_subsidy=10 * COIN,
        halving_interval=1000,
        coinbase_maturity=1,
        scrypt_n=16,
        scrypt_r=1,
        scrypt_p=1,
    )


def _mine_linear(chain: PowChain, address: str, count: int) -> list[dict]:
    blocks = []
    for _ in range(count):
        template = chain.get_block_template(address)
        found, _ = mine_block(template["block"], chain.config, max_hashes=10)
        assert found is not None
        chain.submit_block(found)
        blocks.append(found)
    return blocks


def test_v32_highest_chainwork_reorgs_from_competing_branch(tmp_path):
    miner_a = KeyPair.generate()
    miner_b = KeyPair.generate()
    network = PowNetworkChain(tmp_path / "network.sqlite3", _config(), create=True)
    branch = PowChain(tmp_path / "branch.sqlite3", _config(), create=True)
    try:
        a_template = network.chain.get_block_template(miner_a.address)
        a1, _ = mine_block(a_template["block"], network.config, max_hashes=10)
        assert a1 is not None
        accepted_a = network.accept_block(a1)
        assert accepted_a["became_canonical"] is True
        a_hash = accepted_a["block_hash"]

        b1, b2 = _mine_linear(branch, miner_b.address, 2)
        accepted_b1 = network.accept_block(b1, source="test-side-branch")
        assert accepted_b1["accepted"] is True
        assert accepted_b1["became_canonical"] is False
        assert network.chain.tip()["block_hash"] == a_hash

        accepted_b2 = network.accept_block(b2, source="test-side-branch")
        assert accepted_b2["accepted"] is True
        assert accepted_b2["became_canonical"] is True
        assert accepted_b2["reorg"] is True
        assert accepted_b2["fork_height"] == 0
        assert network.chain.tip()["height"] == 2
        assert network.chain.tip()["block_hash"] == accepted_b2["block_hash"]

        graph = {item["block_hash"]: item for item in network.graph(limit=20)}
        assert graph[a_hash]["status"] == "side"
        assert graph[accepted_b2["block_hash"]]["status"] == "canonical"
    finally:
        branch.close()
        network.close()


def test_v32_orphan_is_resolved_when_parent_arrives(tmp_path):
    miner = KeyPair.generate()
    network = PowNetworkChain(tmp_path / "network.sqlite3", _config(), create=True)
    branch = PowChain(tmp_path / "branch.sqlite3", _config(), create=True)
    try:
        b1, b2 = _mine_linear(branch, miner.address, 2)
        orphan = network.accept_block(b2, source="out-of-order")
        assert orphan["orphan"] is True
        assert network.info()["orphan_blocks"] == 1

        first = network.accept_block(b1, source="out-of-order")
        assert first["accepted"] is True
        assert network.chain.tip()["height"] == 2
        assert network.info()["orphan_blocks"] == 0
    finally:
        branch.close()
        network.close()


def test_v32_signed_peer_hello_binds_chain_and_identity(tmp_path):
    chain = PowNetworkChain(tmp_path / "chain.sqlite3", _config(), create=True)
    key = KeyPair.generate()
    try:
        hello = build_peer_hello(key, chain, listen_port=28444, advertised_endpoint="127.0.0.1:28444", now=1_900_000_000)
        checked = verify_peer_hello(hello, chain, now=1_900_000_000)
        assert checked["node_id"] == hello["node_id"]

        tampered = json.loads(json.dumps(hello))
        tampered["chainwork"] = "999999"
        with pytest.raises(PowNetworkV32Error):
            verify_peer_hello(tampered, chain, now=1_900_000_000)
    finally:
        chain.close()


def test_v32_locator_and_headers_follow_canonical_chain(tmp_path):
    miner = KeyPair.generate()
    chain = PowNetworkChain(tmp_path / "chain.sqlite3", _config(), create=True)
    try:
        for _ in range(3):
            template = chain.chain.get_block_template(miner.address)
            block, _ = mine_block(template["block"], chain.config, max_hashes=10)
            assert block is not None
            chain.accept_block(block)
        locator = chain.block_locator()
        assert locator[0] == chain.chain.tip()["block_hash"]
        assert locator[-1] == chain.genesis_hash
        headers = chain.headers_after([chain.genesis_hash])
        assert [item["height"] for item in headers] == [1, 2, 3]
    finally:
        chain.close()


def test_v32_two_nodes_sync_blocks_over_signed_p2p(tmp_path):
    async def scenario() -> None:
        miner = KeyPair.generate()
        chain_a = PowNetworkChain(tmp_path / "a.sqlite3", _config(), create=True)
        chain_b = PowNetworkChain(tmp_path / "b.sqlite3", _config(), create=True)
        key_a = KeyPair.generate()
        key_b = KeyPair.generate()
        node_a = PowP2PNode(chain_a, key_a, listen_host="127.0.0.1", listen_port=0)
        node_b: PowP2PNode | None = None
        try:
            template = chain_a.chain.get_block_template(miner.address)
            block, _ = mine_block(template["block"], chain_a.config, max_hashes=10)
            assert block is not None
            chain_a.accept_block(block)
            assert chain_a.chain.tip()["height"] == 1

            await node_a.start()
            endpoint_a = f"127.0.0.1:{node_a.listen_port}"
            node_b = PowP2PNode(chain_b, key_b, listen_host="127.0.0.1", listen_port=0, seed_peers=[endpoint_a])
            await node_b.start()

            deadline = asyncio.get_running_loop().time() + 5.0
            while asyncio.get_running_loop().time() < deadline and chain_b.chain.tip()["height"] < 1:
                await asyncio.sleep(0.05)
            assert chain_b.chain.tip()["height"] == 1
            assert chain_b.chain.tip()["block_hash"] == chain_a.chain.tip()["block_hash"]
            assert len(node_a.sessions) >= 1
            assert len(node_b.sessions) >= 1
        finally:
            if node_b is not None:
                await node_b.stop()
            await node_a.stop()
            chain_a.close()
            chain_b.close()

    asyncio.run(scenario())
