from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import secrets
import sqlite3
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .crypto import KeyPair, canonical_json, verify_signature
from .pow_v31 import (
    BLOCK_VERSION,
    MAX_UINT256,
    PowChain,
    PowConfig,
    PowV31Error,
    block_hash,
    merkle_root,
    parse_target,
    transaction_id,
    verify_pow,
    work_for_target,
)

P2P_PROTOCOL = "crakbit-p2p/1"
P2P_VERSION = 1
MAX_P2P_MESSAGE_BYTES = 2_000_000
MAX_BLOCK_BYTES = 1_500_000
MAX_HEADERS = 2_000
MAX_INV = 500
MAX_PEERS = 32
MAX_ORPHANS = 1_024
MAX_MESSAGES_PER_SECOND = 50
MAX_CLOCK_SKEW_SECONDS = 7_200
MTP_WINDOW = 11


class PowNetworkV32Error(ValueError):
    pass


def _json_size(value: Any) -> int:
    return len(canonical_json(value))


def node_id_from_public_key(public_key_b64: str) -> str:
    try:
        raw = base64.b64decode(public_key_b64, validate=True)
    except Exception as exc:
        raise PowNetworkV32Error("invalid peer public key") from exc
    if len(raw) != 32:
        raise PowNetworkV32Error("peer public key must be Ed25519-32")
    return hashlib.sha256(raw).hexdigest()[:40]


def parse_peer_endpoint(value: str) -> tuple[str, int]:
    text = str(value).strip()
    if not text or "://" in text or "@" in text:
        raise PowNetworkV32Error("peer endpoint must use host:port without credentials")
    if text.startswith("["):
        end = text.find("]")
        if end <= 1 or end + 2 > len(text) or text[end + 1] != ":":
            raise PowNetworkV32Error("invalid IPv6 peer endpoint")
        host, port_text = text[1:end], text[end + 2 :]
    else:
        if text.count(":") != 1:
            raise PowNetworkV32Error("peer endpoint must use host:port")
        host, port_text = text.rsplit(":", 1)
    host = host.strip()
    try:
        port = int(port_text)
    except ValueError as exc:
        raise PowNetworkV32Error("invalid peer port") from exc
    if not host or port <= 0 or port > 65535:
        raise PowNetworkV32Error("invalid peer endpoint")
    return host, port


def _header_summary(block_hash_value: str, block: dict[str, Any], chainwork: int | str) -> dict[str, Any]:
    header = block["header"]
    return {
        "hash": str(block_hash_value),
        "height": int(header["height"]),
        "previous_hash": str(header["previous_hash"]),
        "timestamp": int(header["timestamp"]),
        "target": str(header["target"]),
        "chainwork": str(chainwork),
    }


def _median_time_past(timestamps: Iterable[int]) -> int:
    values = sorted(int(v) for v in list(timestamps)[-MTP_WINDOW:])
    if not values:
        return 0
    return values[len(values) // 2]


class PowNetworkChain:
    """v0.32 block graph + highest cumulative-work canonical chain.

    The canonical UTXO/transaction tables remain the v0.31 PowChain tables. v0.32
    adds a persistent all-branches block graph and atomically swaps canonical state
    after a fully replay-validated higher-work branch is found.
    """

    def __init__(self, db_path: str | Path, config: PowConfig | None = None, *, create: bool = False):
        self.path = Path(db_path)
        self.chain = PowChain(self.path, config, create=create)
        self.config = self.chain.config
        self.db = self.chain.db
        self._create_network_schema()
        self._bootstrap_graph()

    def close(self) -> None:
        self.chain.close()

    def _create_network_schema(self) -> None:
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS block_graph(
                block_hash TEXT PRIMARY KEY,
                previous_hash TEXT NOT NULL,
                height INTEGER NOT NULL,
                timestamp INTEGER NOT NULL,
                target TEXT NOT NULL,
                chainwork TEXT NOT NULL,
                status TEXT NOT NULL,
                received_at_ms INTEGER NOT NULL,
                block_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS block_graph_prev_idx ON block_graph(previous_hash);
            CREATE INDEX IF NOT EXISTS block_graph_height_idx ON block_graph(height);
            CREATE TABLE IF NOT EXISTS orphan_blocks(
                block_hash TEXT PRIMARY KEY,
                previous_hash TEXT NOT NULL,
                height INTEGER NOT NULL,
                received_at_ms INTEGER NOT NULL,
                block_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS orphan_prev_idx ON orphan_blocks(previous_hash);
            """
        )
        self.db.commit()

    def _bootstrap_graph(self) -> None:
        for row in self.db.execute("SELECT height,block_hash,previous_hash,timestamp,target,chainwork,block_json FROM blocks ORDER BY height"):
            self.db.execute(
                "INSERT OR IGNORE INTO block_graph(block_hash,previous_hash,height,timestamp,target,chainwork,status,received_at_ms,block_json) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    str(row["block_hash"]), str(row["previous_hash"]), int(row["height"]), int(row["timestamp"]),
                    str(row["target"]), str(row["chainwork"]), "canonical", int(time.time() * 1000), str(row["block_json"]),
                ),
            )
        self.db.commit()

    @property
    def genesis_hash(self) -> str:
        value = self.chain._meta_get("genesis_hash")
        if not value:
            raise PowNetworkV32Error("missing genesis hash")
        return value

    def info(self) -> dict[str, Any]:
        base = self.chain.info()
        graph_count = int(self.db.execute("SELECT COUNT(*) FROM block_graph").fetchone()[0])
        side_count = int(self.db.execute("SELECT COUNT(*) FROM block_graph WHERE status='side'").fetchone()[0])
        orphan_count = int(self.db.execute("SELECT COUNT(*) FROM orphan_blocks").fetchone()[0])
        return {
            **base,
            "p2p_protocol": P2P_PROTOCOL,
            "fork_choice": "highest-cumulative-work",
            "block_graph_count": graph_count,
            "side_chain_blocks": side_count,
            "orphan_blocks": orphan_count,
            "mtp_window": MTP_WINDOW,
            "production_mainnet_ready": False,
        }

    def has_block(self, block_hash_value: str) -> bool:
        return self.db.execute("SELECT 1 FROM block_graph WHERE block_hash=?", (str(block_hash_value),)).fetchone() is not None

    def get_block_by_hash(self, block_hash_value: str) -> dict[str, Any]:
        row = self.db.execute("SELECT block_json,chainwork,status FROM block_graph WHERE block_hash=?", (str(block_hash_value),)).fetchone()
        if row is None:
            raise PowNetworkV32Error("block not found")
        block = json.loads(row["block_json"])
        block["block_hash"] = str(block_hash_value)
        block["chainwork"] = str(row["chainwork"])
        block["branch_status"] = str(row["status"])
        return block

    def graph(self, *, limit: int = 200) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT block_hash,previous_hash,height,timestamp,target,chainwork,status FROM block_graph ORDER BY height DESC, received_at_ms DESC LIMIT ?",
            (max(1, min(int(limit), 5_000)),),
        ).fetchall()
        return [dict(row) for row in rows]

    def _row(self, block_hash_value: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM block_graph WHERE block_hash=?", (str(block_hash_value),)).fetchone()

    def _path_hashes(self, tip_hash: str) -> list[str]:
        current = str(tip_hash)
        seen: set[str] = set()
        reverse: list[str] = []
        while True:
            if current in seen:
                raise PowNetworkV32Error("block graph cycle detected")
            seen.add(current)
            row = self._row(current)
            if row is None:
                raise PowNetworkV32Error("branch references unknown ancestor")
            reverse.append(current)
            if int(row["height"]) == 0:
                if current != self.genesis_hash:
                    raise PowNetworkV32Error("branch terminates at unexpected genesis")
                break
            current = str(row["previous_hash"])
            if len(reverse) > 2_000_000:
                raise PowNetworkV32Error("branch path exceeds safety bound")
        reverse.reverse()
        return reverse

    def _path_blocks(self, tip_hash: str) -> list[dict[str, Any]]:
        return [json.loads(self._row(h)["block_json"]) for h in self._path_hashes(tip_hash)]  # type: ignore[index]

    def _basic_block_checks(self, block: dict[str, Any]) -> str:
        if _json_size(block) > MAX_BLOCK_BYTES:
            raise PowNetworkV32Error("block exceeds v0.32 wire-size limit")
        header = block.get("header")
        if not isinstance(header, dict):
            raise PowNetworkV32Error("block header missing")
        if int(header.get("version", 0)) != BLOCK_VERSION or str(header.get("chain_id", "")) != self.config.chain_id:
            raise PowNetworkV32Error("block version/chain mismatch")
        height = int(header.get("height", -1))
        previous_hash = str(header.get("previous_hash", ""))
        if height <= 0 or len(previous_hash) != 64:
            raise PowNetworkV32Error("invalid block height/previous hash")
        parse_target(header.get("target", ""))
        txs = list(block.get("transactions", []))
        if not txs or len(txs) > self.config.max_transactions_per_block:
            raise PowNetworkV32Error("invalid transaction count")
        if str(header.get("merkle_root", "")) != merkle_root(transaction_id(tx) for tx in txs):
            raise PowNetworkV32Error("merkle root mismatch")
        if not verify_pow(block, self.config):
            raise PowNetworkV32Error("insufficient proof of work")
        return block_hash(block, self.config)

    def _validate_path_replay(self, blocks: list[dict[str, Any]]) -> tuple[int, str]:
        if not blocks or int(blocks[0]["header"]["height"]) != 0:
            raise PowNetworkV32Error("candidate path is missing genesis")
        with tempfile.TemporaryDirectory(prefix="crakbit-v32-replay-") as directory:
            replay_path = Path(directory) / "replay.sqlite3"
            replay = PowChain(replay_path, self.config, create=True)
            try:
                if replay.tip()["block_hash"] != self.genesis_hash:
                    raise PowNetworkV32Error("replay genesis mismatch")
                timestamps = [int(blocks[0]["header"]["timestamp"])]
                expected_height = 1
                for block in blocks[1:]:
                    header = block["header"]
                    if int(header["height"]) != expected_height:
                        raise PowNetworkV32Error("candidate branch has non-contiguous heights")
                    mtp = _median_time_past(timestamps)
                    if int(header["timestamp"]) <= mtp:
                        raise PowNetworkV32Error("block timestamp does not exceed median-time-past")
                    replay.submit_block(block)
                    timestamps.append(int(header["timestamp"]))
                    expected_height += 1
                tip = replay.tip()
                return int(tip["chainwork"]), str(tip["block_hash"])
            except PowV31Error as exc:
                raise PowNetworkV32Error(str(exc)) from exc
            finally:
                replay.close()

    def _candidate_path(self, block: dict[str, Any]) -> list[dict[str, Any]]:
        parent_hash = str(block["header"]["previous_hash"])
        parent = self._row(parent_hash)
        if parent is None:
            raise PowNetworkV32Error("unknown parent")
        path = self._path_blocks(parent_hash)
        path.append(json.loads(json.dumps(block)))
        return path

    def _store_orphan(self, digest: str, block: dict[str, Any]) -> dict[str, Any]:
        header = block["header"]
        self.db.execute(
            "INSERT OR IGNORE INTO orphan_blocks(block_hash,previous_hash,height,received_at_ms,block_json) VALUES(?,?,?,?,?)",
            (digest, str(header["previous_hash"]), int(header["height"]), int(time.time() * 1000), json.dumps(block, sort_keys=True)),
        )
        count = int(self.db.execute("SELECT COUNT(*) FROM orphan_blocks").fetchone()[0])
        if count > MAX_ORPHANS:
            excess = count - MAX_ORPHANS
            self.db.execute(
                "DELETE FROM orphan_blocks WHERE block_hash IN (SELECT block_hash FROM orphan_blocks ORDER BY received_at_ms ASC LIMIT ?)",
                (excess,),
            )
        self.db.commit()
        return {"accepted": False, "orphan": True, "block_hash": digest, "production_mainnet_ready": False}

    def accept_block(self, block: dict[str, Any], *, source: str = "local") -> dict[str, Any]:
        digest = self._basic_block_checks(block)
        existing = self._row(digest)
        if existing is not None:
            return {
                "accepted": True,
                "known": True,
                "block_hash": digest,
                "height": int(existing["height"]),
                "status": str(existing["status"]),
                "production_mainnet_ready": False,
            }
        parent_hash = str(block["header"]["previous_hash"])
        if self._row(parent_hash) is None:
            return self._store_orphan(digest, block)

        path = self._candidate_path(block)
        chainwork, replay_tip_hash = self._validate_path_replay(path)
        if replay_tip_hash != digest:
            raise PowNetworkV32Error("replay tip hash mismatch")
        parent = self._row(parent_hash)
        assert parent is not None
        expected_work = int(parent["chainwork"]) + work_for_target(parse_target(block["header"]["target"]))
        if chainwork != expected_work:
            raise PowNetworkV32Error("candidate cumulative work mismatch")

        header = block["header"]
        self.db.execute(
            "INSERT INTO block_graph(block_hash,previous_hash,height,timestamp,target,chainwork,status,received_at_ms,block_json) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                digest, parent_hash, int(header["height"]), int(header["timestamp"]), str(header["target"]), str(chainwork),
                "side", int(time.time() * 1000), json.dumps(block, sort_keys=True),
            ),
        )
        self.db.execute("DELETE FROM orphan_blocks WHERE block_hash=?", (digest,))
        self.db.commit()

        old_tip = self.chain.tip()
        reorg = False
        fork_height: int | None = None
        if chainwork > int(old_tip["chainwork"]):
            fork_height = self._activate_chain(digest)
            reorg = old_tip["block_hash"] != parent_hash
        self._process_orphans(digest)
        active = self.chain.tip()
        return {
            "accepted": True,
            "known": False,
            "block_hash": digest,
            "height": int(header["height"]),
            "source": str(source),
            "became_canonical": active["block_hash"] == digest,
            "reorg": bool(reorg),
            "fork_height": fork_height,
            "best_block_hash": active["block_hash"],
            "best_height": active["height"],
            "chainwork": str(chainwork),
            "production_mainnet_ready": False,
        }

    def _canonical_hashes(self) -> list[str]:
        return [str(row["block_hash"]) for row in self.db.execute("SELECT block_hash FROM blocks ORDER BY height")]

    def _activate_chain(self, best_hash: str) -> int:
        new_hashes = self._path_hashes(best_hash)
        old_hashes = self._canonical_hashes()
        fork_height = -1
        for index in range(min(len(old_hashes), len(new_hashes))):
            if old_hashes[index] != new_hashes[index]:
                break
            fork_height = index
        if fork_height < 0 or new_hashes[0] != self.genesis_hash:
            raise PowNetworkV32Error("candidate does not share genesis")

        new_blocks = [json.loads(self._row(h)["block_json"]) for h in new_hashes]  # type: ignore[index]
        disconnected: list[dict[str, Any]] = []
        for row in self.db.execute("SELECT block_height,tx_index,tx_json FROM transactions WHERE block_height>? ORDER BY block_height,tx_index", (fork_height,)):
            if int(row["tx_index"]) > 0:
                disconnected.append(json.loads(row["tx_json"]))
        mempool_existing = [json.loads(row["tx_json"]) for row in self.db.execute("SELECT tx_json FROM mempool ORDER BY received_at_ms")]

        with tempfile.TemporaryDirectory(prefix="crakbit-v32-activate-") as directory:
            candidate_path = Path(directory) / "candidate.sqlite3"
            candidate = PowChain(candidate_path, self.config, create=True)
            try:
                for block in new_blocks[1:]:
                    candidate.submit_block(block)
                if candidate.tip()["block_hash"] != best_hash:
                    raise PowNetworkV32Error("candidate replay did not reach selected tip")
            finally:
                candidate.close()

            self.db.execute("ATTACH DATABASE ? AS candidate_chain", (str(candidate_path),))
            try:
                self.db.execute("BEGIN IMMEDIATE")
                self.db.execute("DELETE FROM transactions")
                self.db.execute("DELETE FROM utxos")
                self.db.execute("DELETE FROM blocks")
                self.db.execute("INSERT INTO blocks SELECT * FROM candidate_chain.blocks")
                self.db.execute("INSERT INTO transactions SELECT * FROM candidate_chain.transactions")
                self.db.execute("INSERT INTO utxos SELECT * FROM candidate_chain.utxos")
                self.db.execute("DELETE FROM mempool")
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            finally:
                self.db.execute("DETACH DATABASE candidate_chain")

        self.db.execute("UPDATE block_graph SET status='side' WHERE status='canonical'")
        for block_hash_value in new_hashes:
            self.db.execute("UPDATE block_graph SET status='canonical' WHERE block_hash=?", (block_hash_value,))
        self.db.commit()

        confirmed = {str(row["txid"]) for row in self.db.execute("SELECT txid FROM transactions")}
        seen: set[str] = set()
        for tx in mempool_existing + disconnected:
            txid = transaction_id(tx)
            if txid in seen or txid in confirmed:
                continue
            seen.add(txid)
            try:
                self.chain.submit_transaction(tx)
            except Exception:
                continue
        return fork_height

    def _process_orphans(self, parent_hash: str) -> None:
        queue = [str(parent_hash)]
        processed = 0
        while queue and processed < MAX_ORPHANS:
            current = queue.pop(0)
            rows = self.db.execute(
                "SELECT block_hash,block_json FROM orphan_blocks WHERE previous_hash=? ORDER BY received_at_ms ASC LIMIT 64",
                (current,),
            ).fetchall()
            for row in rows:
                child_hash = str(row["block_hash"])
                block = json.loads(row["block_json"])
                self.db.execute("DELETE FROM orphan_blocks WHERE block_hash=?", (child_hash,))
                self.db.commit()
                try:
                    result = self.accept_block(block, source="orphan-resolution")
                    if result.get("accepted"):
                        queue.append(child_hash)
                except Exception:
                    pass
                processed += 1
                if processed >= MAX_ORPHANS:
                    break

    def block_locator(self, *, max_entries: int = 32) -> list[str]:
        rows = self.db.execute("SELECT height,block_hash FROM blocks ORDER BY height DESC").fetchall()
        by_height = {int(row["height"]): str(row["block_hash"]) for row in rows}
        if not by_height:
            return []
        height = max(by_height)
        locator: list[str] = []
        step = 1
        while height >= 0 and len(locator) < max(2, int(max_entries)):
            if height in by_height:
                locator.append(by_height[height])
            if len(locator) > 10:
                step *= 2
            height -= step
        if locator[-1] != self.genesis_hash:
            locator.append(self.genesis_hash)
        return locator

    def headers_after(self, locator: Iterable[str], *, limit: int = 200) -> list[dict[str, Any]]:
        common_height = 0
        for candidate in locator:
            row = self.db.execute("SELECT height FROM blocks WHERE block_hash=?", (str(candidate),)).fetchone()
            if row is not None:
                common_height = int(row["height"])
                break
        rows = self.db.execute(
            "SELECT block_hash,chainwork,block_json FROM blocks WHERE height>? ORDER BY height ASC LIMIT ?",
            (common_height, max(1, min(int(limit), MAX_HEADERS))),
        ).fetchall()
        return [_header_summary(str(row["block_hash"]), json.loads(row["block_json"]), row["chainwork"]) for row in rows]

    def mempool_transaction(self, txid: str) -> dict[str, Any] | None:
        row = self.db.execute("SELECT tx_json FROM mempool WHERE txid=?", (str(txid),)).fetchone()
        return None if row is None else json.loads(row["tx_json"])

    def has_transaction(self, txid: str) -> bool:
        return self.db.execute("SELECT 1 FROM transactions WHERE txid=? UNION SELECT 1 FROM mempool WHERE txid=? LIMIT 1", (str(txid), str(txid))).fetchone() is not None

    def submit_transaction(self, tx: dict[str, Any]) -> dict[str, Any]:
        return self.chain.submit_transaction(tx)


def _hello_unsigned(hello: dict[str, Any]) -> dict[str, Any]:
    body = dict(hello)
    body.pop("signature", None)
    return body


def build_peer_hello(
    keypair: KeyPair,
    chain: PowNetworkChain,
    *,
    listen_port: int,
    advertised_endpoint: str | None = None,
    now: int | None = None,
) -> dict[str, Any]:
    if advertised_endpoint:
        parse_peer_endpoint(advertised_endpoint)
    tip = chain.chain.tip()
    hello = {
        "protocol": P2P_PROTOCOL,
        "version": P2P_VERSION,
        "chain_id": chain.config.chain_id,
        "genesis_hash": chain.genesis_hash,
        "node_id": node_id_from_public_key(keypair.public_key_b64),
        "public_key": keypair.public_key_b64,
        "listen_port": int(listen_port),
        "advertised_endpoint": advertised_endpoint,
        "best_height": int(tip["height"]),
        "best_block_hash": str(tip["block_hash"]),
        "chainwork": str(tip["chainwork"]),
        "timestamp": int(time.time() if now is None else now),
        "nonce": secrets.token_hex(16),
    }
    hello["signature"] = keypair.sign(canonical_json({"domain": "crakbit-p2p-hello-v1", "hello": hello}))
    return hello


def verify_peer_hello(hello: dict[str, Any], chain: PowNetworkChain, *, now: int | None = None) -> dict[str, Any]:
    if str(hello.get("protocol")) != P2P_PROTOCOL or int(hello.get("version", 0)) != P2P_VERSION:
        raise PowNetworkV32Error("unsupported P2P protocol/version")
    if str(hello.get("chain_id")) != chain.config.chain_id or str(hello.get("genesis_hash")) != chain.genesis_hash:
        raise PowNetworkV32Error("peer is on a different chain/genesis")
    public_key = str(hello.get("public_key", ""))
    node_id = node_id_from_public_key(public_key)
    if str(hello.get("node_id")) != node_id:
        raise PowNetworkV32Error("peer node ID/public key mismatch")
    current = int(time.time() if now is None else now)
    if abs(current - int(hello.get("timestamp", 0))) > MAX_CLOCK_SKEW_SECONDS:
        raise PowNetworkV32Error("peer hello clock skew is too large")
    endpoint = hello.get("advertised_endpoint")
    if endpoint:
        parse_peer_endpoint(str(endpoint))
    signature = str(hello.get("signature", ""))
    if not signature or not verify_signature(
        public_key,
        canonical_json({"domain": "crakbit-p2p-hello-v1", "hello": _hello_unsigned(hello)}),
        signature,
    ):
        raise PowNetworkV32Error("invalid peer hello signature")
    return {
        "node_id": node_id,
        "best_height": int(hello.get("best_height", 0)),
        "best_block_hash": str(hello.get("best_block_hash", "")),
        "chainwork": int(hello.get("chainwork", 0)),
        "advertised_endpoint": endpoint,
    }


@dataclass
class PeerSession:
    node_id: str
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    endpoint: str
    inbound: bool
    score: int = 0
    connected_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    recent_messages: list[float] = field(default_factory=list)

    async def send(self, message_type: str, payload: dict[str, Any] | None = None) -> None:
        message = {"protocol": P2P_PROTOCOL, "type": str(message_type), "payload": payload or {}}
        encoded = canonical_json(message) + b"\n"
        if len(encoded) > MAX_P2P_MESSAGE_BYTES:
            raise PowNetworkV32Error("outbound P2P message exceeds size limit")
        self.writer.write(encoded)
        await self.writer.drain()

    def note_message(self) -> None:
        now = time.monotonic()
        self.recent_messages = [value for value in self.recent_messages if now - value <= 1.0]
        self.recent_messages.append(now)
        if len(self.recent_messages) > MAX_MESSAGES_PER_SECOND:
            self.score -= 25
            raise PowNetworkV32Error("peer message rate limit exceeded")
        self.last_seen = time.time()


class PowP2PNode:
    def __init__(
        self,
        chain: PowNetworkChain,
        identity: KeyPair,
        *,
        listen_host: str = "0.0.0.0",
        listen_port: int = 28444,
        advertised_endpoint: str | None = None,
        seed_peers: Iterable[str] = (),
        max_peers: int = MAX_PEERS,
    ):
        self.chain = chain
        self.identity = identity
        self.node_id = node_id_from_public_key(identity.public_key_b64)
        self.listen_host = str(listen_host)
        self.listen_port = int(listen_port)
        self.advertised_endpoint = advertised_endpoint
        if advertised_endpoint:
            parse_peer_endpoint(advertised_endpoint)
        self.max_peers = max(2, min(int(max_peers), 128))
        self.known_endpoints: set[str] = set()
        for peer in seed_peers:
            parse_peer_endpoint(str(peer))
            self.known_endpoints.add(str(peer))
        self.sessions: dict[str, PeerSession] = {}
        self.server: asyncio.AbstractServer | None = None
        self.maintenance_task: asyncio.Task[Any] | None = None
        self.connection_tasks: set[asyncio.Task[Any]] = set()
        self._stopping = False

    async def start(self) -> None:
        self.server = await asyncio.start_server(
            self._accept,
            host=self.listen_host,
            port=self.listen_port,
            limit=MAX_P2P_MESSAGE_BYTES + 1,
        )
        if self.server.sockets:
            self.listen_port = int(self.server.sockets[0].getsockname()[1])
        self.maintenance_task = asyncio.create_task(self._maintenance(), name="crakbit-p2p-maintenance")

    async def stop(self) -> None:
        self._stopping = True
        if self.maintenance_task:
            self.maintenance_task.cancel()
        for session in list(self.sessions.values()):
            session.writer.close()
        for task in list(self.connection_tasks):
            task.cancel()
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    def peer_snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "node_id": session.node_id,
                "endpoint": session.endpoint,
                "inbound": session.inbound,
                "score": session.score,
                "connected_seconds": max(0, int(time.time() - session.connected_at)),
                "last_seen_seconds_ago": max(0, int(time.time() - session.last_seen)),
            }
            for session in sorted(self.sessions.values(), key=lambda item: item.node_id)
        ]

    async def _read_json(self, reader: asyncio.StreamReader, *, timeout: float | None = None) -> dict[str, Any]:
        try:
            raw = await asyncio.wait_for(reader.readline(), timeout=timeout) if timeout else await reader.readline()
        except asyncio.LimitOverrunError as exc:
            raise PowNetworkV32Error("P2P line exceeds size limit") from exc
        if not raw:
            raise EOFError
        if len(raw) > MAX_P2P_MESSAGE_BYTES:
            raise PowNetworkV32Error("P2P message exceeds size limit")
        try:
            value = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise PowNetworkV32Error("invalid P2P JSON") from exc
        if not isinstance(value, dict):
            raise PowNetworkV32Error("P2P message must be an object")
        return value

    async def _write_hello(self, writer: asyncio.StreamWriter) -> None:
        hello = build_peer_hello(
            self.identity,
            self.chain,
            listen_port=self.listen_port,
            advertised_endpoint=self.advertised_endpoint,
        )
        writer.write(canonical_json({"type": "hello", "hello": hello}) + b"\n")
        await writer.drain()

    async def _read_hello(self, reader: asyncio.StreamReader) -> tuple[dict[str, Any], dict[str, Any]]:
        envelope = await self._read_json(reader, timeout=15.0)
        if envelope.get("type") != "hello" or not isinstance(envelope.get("hello"), dict):
            raise PowNetworkV32Error("first P2P message must be hello")
        hello = envelope["hello"]
        verified = verify_peer_hello(hello, self.chain)
        if verified["node_id"] == self.node_id:
            raise PowNetworkV32Error("refusing self-connection")
        return hello, verified

    async def _accept(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        if len(self.sessions) >= self.max_peers:
            writer.close()
            await writer.wait_closed()
            return
        task = asyncio.create_task(self._peer_loop(reader, writer, inbound=True, endpoint_hint=None))
        self.connection_tasks.add(task)
        task.add_done_callback(self.connection_tasks.discard)

    async def _connect(self, endpoint: str) -> None:
        if len(self.sessions) >= self.max_peers:
            return
        if self.advertised_endpoint and endpoint == self.advertised_endpoint:
            return
        if any(session.endpoint == endpoint for session in self.sessions.values()):
            return
        host, port = parse_peer_endpoint(endpoint)
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, limit=MAX_P2P_MESSAGE_BYTES + 1),
                timeout=5.0,
            )
        except Exception:
            return
        task = asyncio.create_task(self._peer_loop(reader, writer, inbound=False, endpoint_hint=endpoint))
        self.connection_tasks.add(task)
        task.add_done_callback(self.connection_tasks.discard)

    async def _peer_loop(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        *,
        inbound: bool,
        endpoint_hint: str | None,
    ) -> None:
        session: PeerSession | None = None
        try:
            if inbound:
                hello, verified = await self._read_hello(reader)
                await self._write_hello(writer)
            else:
                await self._write_hello(writer)
                hello, verified = await self._read_hello(reader)
            peername = writer.get_extra_info("peername")
            endpoint = endpoint_hint or (f"{peername[0]}:{int(hello.get('listen_port', peername[1]))}" if peername else "unknown")
            advertised = verified.get("advertised_endpoint")
            if advertised:
                endpoint = str(advertised)
                self.known_endpoints.add(endpoint)
            node_id = str(verified["node_id"])
            if node_id in self.sessions:
                raise PowNetworkV32Error("duplicate peer identity")
            session = PeerSession(node_id=node_id, reader=reader, writer=writer, endpoint=endpoint, inbound=inbound)
            self.sessions[node_id] = session
            await session.send("getheaders", {"locator": self.chain.block_locator(), "limit": 200})
            await session.send("getpeers", {})
            while not self._stopping:
                message = await self._read_json(reader)
                session.note_message()
                await self._handle_message(session, message)
                if session.score <= -100:
                    raise PowNetworkV32Error("peer score reached disconnect threshold")
        except (EOFError, asyncio.CancelledError):
            pass
        except Exception:
            if session:
                session.score -= 10
        finally:
            if session and self.sessions.get(session.node_id) is session:
                self.sessions.pop(session.node_id, None)
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _handle_message(self, session: PeerSession, message: dict[str, Any]) -> None:
        if str(message.get("protocol")) != P2P_PROTOCOL:
            session.score -= 25
            raise PowNetworkV32Error("invalid message protocol")
        message_type = str(message.get("type", ""))
        payload = message.get("payload", {})
        if not isinstance(payload, dict):
            session.score -= 10
            raise PowNetworkV32Error("invalid message payload")

        if message_type == "ping":
            await session.send("pong", {"nonce": payload.get("nonce")})
            return
        if message_type == "pong":
            return
        if message_type == "getheaders":
            locator = payload.get("locator", [])
            if not isinstance(locator, list) or len(locator) > 64:
                raise PowNetworkV32Error("invalid header locator")
            limit = min(MAX_HEADERS, max(1, int(payload.get("limit", 200))))
            await session.send("headers", {"headers": self.chain.headers_after([str(v) for v in locator], limit=limit)})
            return
        if message_type == "headers":
            headers = payload.get("headers", [])
            if not isinstance(headers, list) or len(headers) > MAX_HEADERS:
                raise PowNetworkV32Error("too many headers")
            unknown: list[str] = []
            previous_height = -1
            for item in headers:
                if not isinstance(item, dict):
                    raise PowNetworkV32Error("malformed header announcement")
                block_hash_value = str(item.get("hash", ""))
                height = int(item.get("height", -1))
                if len(block_hash_value) != 64 or height < 0 or (previous_height >= 0 and height <= previous_height):
                    raise PowNetworkV32Error("invalid header sequence")
                previous_height = height
                if not self.chain.has_block(block_hash_value):
                    unknown.append(block_hash_value)
            for block_hash_value in unknown[:32]:
                await session.send("getblock", {"hash": block_hash_value})
            return
        if message_type == "getblock":
            block_hash_value = str(payload.get("hash", ""))
            if len(block_hash_value) != 64:
                raise PowNetworkV32Error("invalid getblock hash")
            try:
                block = self.chain.get_block_by_hash(block_hash_value)
            except PowNetworkV32Error:
                return
            block.pop("branch_status", None)
            block.pop("chainwork", None)
            block.pop("block_hash", None)
            await session.send("block", {"block": block})
            return
        if message_type == "block":
            block = payload.get("block")
            if not isinstance(block, dict):
                raise PowNetworkV32Error("block payload missing")
            try:
                result = self.chain.accept_block(block, source=f"peer:{session.node_id}")
                session.score += 1
            except Exception:
                session.score -= 50
                raise
            if result.get("accepted") and not result.get("known"):
                await self.broadcast("inv", {"blocks": [result["block_hash"]], "transactions": []}, exclude=session.node_id)
                await session.send("getheaders", {"locator": self.chain.block_locator(), "limit": 200})
            return
        if message_type == "inv":
            blocks = payload.get("blocks", [])
            txs = payload.get("transactions", [])
            if not isinstance(blocks, list) or not isinstance(txs, list) or len(blocks) > MAX_INV or len(txs) > MAX_INV:
                raise PowNetworkV32Error("inventory exceeds limit")
            for block_hash_value in [str(v) for v in blocks[:32]]:
                if len(block_hash_value) == 64 and not self.chain.has_block(block_hash_value):
                    await session.send("getblock", {"hash": block_hash_value})
            for txid in [str(v) for v in txs[:32]]:
                if len(txid) == 64 and not self.chain.has_transaction(txid):
                    await session.send("gettx", {"txid": txid})
            return
        if message_type == "gettx":
            txid = str(payload.get("txid", ""))
            tx = self.chain.mempool_transaction(txid)
            if tx is not None:
                await session.send("tx", {"transaction": tx})
            return
        if message_type == "tx":
            tx = payload.get("transaction")
            if not isinstance(tx, dict) or _json_size(tx) > 500_000:
                raise PowNetworkV32Error("invalid transaction payload")
            try:
                result = self.chain.submit_transaction(tx)
                session.score += 1
            except Exception:
                session.score -= 20
                raise
            await self.broadcast("inv", {"blocks": [], "transactions": [result["txid"]]}, exclude=session.node_id)
            return
        if message_type == "getpeers":
            peers = sorted(self.known_endpoints)
            if self.advertised_endpoint:
                peers.append(self.advertised_endpoint)
            await session.send("peers", {"peers": list(dict.fromkeys(peers))[:64]})
            return
        if message_type == "peers":
            peers = payload.get("peers", [])
            if not isinstance(peers, list) or len(peers) > 64:
                raise PowNetworkV32Error("invalid peer list")
            for endpoint in peers:
                try:
                    parse_peer_endpoint(str(endpoint))
                    if endpoint != self.advertised_endpoint:
                        self.known_endpoints.add(str(endpoint))
                except Exception:
                    session.score -= 1
            return
        session.score -= 5
        raise PowNetworkV32Error("unknown P2P message type")

    async def broadcast(self, message_type: str, payload: dict[str, Any], *, exclude: str | None = None) -> None:
        for node_id, session in list(self.sessions.items()):
            if exclude and node_id == exclude:
                continue
            try:
                await session.send(message_type, payload)
            except Exception:
                session.score -= 5

    async def announce_block(self, block_hash_value: str) -> None:
        await self.broadcast("inv", {"blocks": [str(block_hash_value)], "transactions": []})

    async def announce_transaction(self, txid: str) -> None:
        await self.broadcast("inv", {"blocks": [], "transactions": [str(txid)]})

    async def _maintenance(self) -> None:
        try:
            while not self._stopping:
                endpoints = list(sorted(self.known_endpoints))[: self.max_peers]
                for endpoint in endpoints:
                    if len(self.sessions) >= self.max_peers:
                        break
                    await self._connect(endpoint)
                nonce = secrets.token_hex(8)
                for session in list(self.sessions.values()):
                    try:
                        await session.send("ping", {"nonce": nonce})
                        await session.send("getheaders", {"locator": self.chain.block_locator(), "limit": 200})
                    except Exception:
                        session.score -= 5
                await asyncio.sleep(10.0)
        except asyncio.CancelledError:
            pass
