from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .crypto import KeyPair, address_from_public_key, canonical_json, verify_signature

POW_PROTOCOL = "crakbit-pow/1"
POW_ALGO = "crakpow-scrypt-v1"
TX_VERSION = 1
BLOCK_VERSION = 1
COIN = 100_000_000
MAX_UINT256 = (1 << 256) - 1


class PowV31Error(ValueError):
    pass


def sha256d(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def sha256d_hex(data: bytes) -> str:
    return sha256d(data).hex()


def now_seconds() -> int:
    return int(time.time())


def target_hex(target: int) -> str:
    value = int(target)
    if value <= 0 or value > MAX_UINT256:
        raise PowV31Error("target out of range")
    return f"{value:064x}"


def parse_target(value: str | int) -> int:
    if isinstance(value, int):
        target = value
    else:
        text = str(value).strip().lower()
        if text.startswith("0x"):
            text = text[2:]
        if len(text) > 64 or not text:
            raise PowV31Error("invalid target")
        try:
            target = int(text, 16)
        except ValueError as exc:
            raise PowV31Error("invalid target") from exc
    if target <= 0 or target > MAX_UINT256:
        raise PowV31Error("target out of range")
    return target


def work_for_target(target: int) -> int:
    return (MAX_UINT256 // (int(target) + 1)) + 1


def merkle_root(txids: Iterable[str]) -> str:
    layer = [bytes.fromhex(str(txid)) for txid in txids]
    if not layer:
        return sha256d_hex(b"")
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [sha256d(layer[i] + layer[i + 1]) for i in range(0, len(layer), 2)]
    return layer[0].hex()


def transaction_id(tx: dict[str, Any]) -> str:
    return sha256d_hex(canonical_json(tx))


def unsigned_transaction(tx: dict[str, Any]) -> dict[str, Any]:
    body = json.loads(json.dumps(tx))
    for item in body.get("inputs", []):
        item.pop("signature", None)
        item.pop("public_key", None)
    return body


def input_signing_payload(tx: dict[str, Any], input_index: int, prevout: dict[str, Any]) -> bytes:
    payload = {
        "protocol": POW_PROTOCOL,
        "domain": "utxo-input-v1",
        "transaction": unsigned_transaction(tx),
        "input_index": int(input_index),
        "prevout": {
            "txid": str(prevout["txid"]),
            "vout": int(prevout["vout"]),
            "address": str(prevout["address"]),
            "amount": int(prevout["amount"]),
        },
    }
    return canonical_json(payload)


def is_coinbase(tx: dict[str, Any]) -> bool:
    return bool(tx.get("coinbase", False))


def build_coinbase(height: int, address: str, amount: int, message: str = "Crakbit PoW") -> dict[str, Any]:
    if int(height) <= 0:
        raise PowV31Error("coinbase height must be positive")
    if int(amount) < 0:
        raise PowV31Error("coinbase amount may not be negative")
    if not str(address).startswith("crk1"):
        raise PowV31Error("invalid Crakbit payout address")
    return {
        "version": TX_VERSION,
        "coinbase": True,
        "height": int(height),
        "message": str(message)[:128],
        "inputs": [],
        "outputs": [{"address": str(address), "amount": int(amount)}],
        "lock_time": 0,
    }


def build_unsigned_transaction(inputs: list[dict[str, Any]], outputs: list[dict[str, Any]]) -> dict[str, Any]:
    if not inputs:
        raise PowV31Error("regular transaction requires at least one input")
    if not outputs:
        raise PowV31Error("regular transaction requires at least one output")
    normalized_inputs = []
    for item in inputs:
        txid = str(item.get("txid", "")).strip().lower()
        vout = int(item.get("vout", -1))
        if len(txid) != 64 or vout < 0:
            raise PowV31Error("invalid input outpoint")
        normalized_inputs.append({"txid": txid, "vout": vout, "public_key": "", "signature": ""})
    normalized_outputs = []
    for item in outputs:
        address = str(item.get("address", "")).strip()
        amount = int(item.get("amount", 0))
        if not address.startswith("crk1") or amount <= 0:
            raise PowV31Error("invalid transaction output")
        normalized_outputs.append({"address": address, "amount": amount})
    return {
        "version": TX_VERSION,
        "coinbase": False,
        "inputs": normalized_inputs,
        "outputs": normalized_outputs,
        "lock_time": 0,
    }


def sign_transaction(tx: dict[str, Any], keypair: KeyPair, prevouts: list[dict[str, Any]]) -> dict[str, Any]:
    if len(prevouts) != len(tx.get("inputs", [])):
        raise PowV31Error("prevout count does not match inputs")
    signed = json.loads(json.dumps(tx))
    for index, prevout in enumerate(prevouts):
        if str(prevout["address"]) != keypair.address:
            raise PowV31Error("wallet does not own every selected input")
        signed["inputs"][index]["public_key"] = keypair.public_key_b64
        payload = input_signing_payload(signed, index, prevout)
        signed["inputs"][index]["signature"] = keypair.sign(payload)
    return signed


@dataclass(frozen=True)
class PowConfig:
    chain_id: str = "crakbit-pow-devnet-v1"
    network: str = "devnet"
    pow_algo: str = POW_ALGO
    decimals: int = 8
    target_block_time_seconds: int = 60
    retarget_interval: int = 20
    initial_target: int = (1 << 248) - 1
    initial_subsidy: int = 50 * COIN
    halving_interval: int = 210_000
    coinbase_maturity: int = 10
    max_future_seconds: int = 7_200
    max_transactions_per_block: int = 2_000
    scrypt_n: int = 1024
    scrypt_r: int = 8
    scrypt_p: int = 1

    def __post_init__(self) -> None:
        if not self.chain_id or self.pow_algo != POW_ALGO:
            raise PowV31Error("invalid PoW configuration")
        if self.decimals != 8:
            raise PowV31Error("v0.31 currently requires 8 decimal places")
        if self.target_block_time_seconds <= 0 or self.retarget_interval < 2:
            raise PowV31Error("invalid retarget parameters")
        parse_target(self.initial_target)
        if self.initial_subsidy < 0 or self.halving_interval <= 0 or self.coinbase_maturity < 0:
            raise PowV31Error("invalid monetary/devnet parameters")
        if self.scrypt_n < 2 or self.scrypt_n & (self.scrypt_n - 1):
            raise PowV31Error("scrypt_n must be a power of two >= 2")
        if self.scrypt_r <= 0 or self.scrypt_p <= 0:
            raise PowV31Error("invalid scrypt parameters")

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "network": self.network,
            "pow_algo": self.pow_algo,
            "decimals": self.decimals,
            "target_block_time_seconds": self.target_block_time_seconds,
            "retarget_interval": self.retarget_interval,
            "initial_target": target_hex(self.initial_target),
            "initial_subsidy": self.initial_subsidy,
            "halving_interval": self.halving_interval,
            "coinbase_maturity": self.coinbase_maturity,
            "max_future_seconds": self.max_future_seconds,
            "max_transactions_per_block": self.max_transactions_per_block,
            "scrypt_n": self.scrypt_n,
            "scrypt_r": self.scrypt_r,
            "scrypt_p": self.scrypt_p,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PowConfig":
        kwargs = dict(data)
        kwargs["initial_target"] = parse_target(kwargs.get("initial_target", target_hex((1 << 248) - 1)))
        return cls(**kwargs)


def pow_seed(config: PowConfig, height: int, previous_hash: str) -> str:
    return hashlib.sha256(f"{config.chain_id}:{int(height)}:{previous_hash}".encode("utf-8")).hexdigest()


def header_bytes(header: dict[str, Any]) -> bytes:
    fields = {
        "version": int(header["version"]),
        "chain_id": str(header["chain_id"]),
        "height": int(header["height"]),
        "previous_hash": str(header["previous_hash"]),
        "merkle_root": str(header["merkle_root"]),
        "timestamp": int(header["timestamp"]),
        "target": str(header["target"]),
        "pow_algo": str(header["pow_algo"]),
        "pow_seed": str(header["pow_seed"]),
        "extra_nonce": int(header.get("extra_nonce", 0)),
        "nonce": int(header.get("nonce", 0)),
    }
    return canonical_json(fields)


def pow_hash(header: dict[str, Any], config: PowConfig) -> bytes:
    if str(header.get("pow_algo")) != POW_ALGO:
        raise PowV31Error("unsupported PoW algorithm")
    try:
        seed = bytes.fromhex(str(header["pow_seed"]))
    except ValueError as exc:
        raise PowV31Error("invalid PoW seed") from exc
    if len(seed) != 32:
        raise PowV31Error("invalid PoW seed")
    return hashlib.scrypt(
        header_bytes(header),
        salt=seed,
        n=config.scrypt_n,
        r=config.scrypt_r,
        p=config.scrypt_p,
        dklen=32,
    )


def block_hash(block: dict[str, Any], config: PowConfig) -> str:
    return pow_hash(block["header"], config).hex()


def verify_pow(block: dict[str, Any], config: PowConfig) -> bool:
    digest = pow_hash(block["header"], config)
    return int.from_bytes(digest, "big") <= parse_target(block["header"]["target"])


def mine_block(block: dict[str, Any], config: PowConfig, *, start_nonce: int = 0, max_hashes: int | None = None) -> tuple[dict[str, Any] | None, int]:
    candidate = json.loads(json.dumps(block))
    nonce = int(start_nonce)
    hashes = 0
    while nonce <= 0xFFFFFFFFFFFFFFFF:
        candidate["header"]["nonce"] = nonce
        digest = pow_hash(candidate["header"], config)
        hashes += 1
        if int.from_bytes(digest, "big") <= parse_target(candidate["header"]["target"]):
            return candidate, hashes
        nonce += 1
        if max_hashes is not None and hashes >= int(max_hashes):
            return None, hashes
    return None, hashes


def subsidy_for_height(config: PowConfig, height: int) -> int:
    halvings = int(height) // config.halving_interval
    if halvings >= 64:
        return 0
    return config.initial_subsidy >> halvings


class PowChain:
    """Linear PoW devnet chain with a persistent UTXO set.

    v0.31 intentionally accepts blocks that extend the current tip only. P2P fork
    tracking/highest-chainwork reorganization is a later network-layer phase.
    """

    def __init__(self, db_path: str | Path, config: PowConfig | None = None, *, create: bool = False):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self._create_schema()
        stored = self._meta_get("config")
        if stored is None:
            if not create:
                raise PowV31Error("PoW chain database is not initialized")
            self.config = config or PowConfig()
            self._meta_set("config", json.dumps(self.config.to_dict(), sort_keys=True))
            self._create_genesis()
        else:
            self.config = PowConfig.from_dict(json.loads(stored))
            if config is not None and config.to_dict() != self.config.to_dict():
                raise PowV31Error("supplied config does not match database config")

    def close(self) -> None:
        self.db.close()

    def _create_schema(self) -> None:
        self.db.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS blocks(
                height INTEGER PRIMARY KEY,
                block_hash TEXT UNIQUE NOT NULL,
                previous_hash TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                target TEXT NOT NULL,
                chainwork TEXT NOT NULL,
                block_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS transactions(
                txid TEXT PRIMARY KEY,
                block_height INTEGER NOT NULL,
                tx_index INTEGER NOT NULL,
                tx_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS utxos(
                txid TEXT NOT NULL,
                vout INTEGER NOT NULL,
                address TEXT NOT NULL,
                amount INTEGER NOT NULL,
                coinbase_height INTEGER,
                PRIMARY KEY(txid, vout)
            );
            CREATE INDEX IF NOT EXISTS utxos_address_idx ON utxos(address);
            CREATE TABLE IF NOT EXISTS mempool(
                txid TEXT PRIMARY KEY,
                fee INTEGER NOT NULL,
                received_at_ms INTEGER NOT NULL,
                tx_json TEXT NOT NULL
            );
            """
        )
        self.db.commit()

    def _meta_get(self, key: str) -> str | None:
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return None if row is None else str(row[0])

    def _meta_set(self, key: str, value: str) -> None:
        self.db.execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        self.db.commit()

    def _create_genesis(self) -> None:
        genesis_body = {
            "protocol": POW_PROTOCOL,
            "chain_id": self.config.chain_id,
            "network": self.config.network,
            "message": "Crakbit PoW research genesis",
            "config": self.config.to_dict(),
        }
        genesis_hash = sha256d_hex(canonical_json(genesis_body))
        header = {
            "version": BLOCK_VERSION,
            "chain_id": self.config.chain_id,
            "height": 0,
            "previous_hash": "0" * 64,
            "merkle_root": merkle_root([]),
            "timestamp": 1_700_000_000,
            "target": target_hex(self.config.initial_target),
            "pow_algo": self.config.pow_algo,
            "pow_seed": hashlib.sha256((self.config.chain_id + ":genesis").encode()).hexdigest(),
            "extra_nonce": 0,
            "nonce": 0,
        }
        block = {"header": header, "transactions": [], "genesis_manifest": genesis_body}
        self.db.execute(
            "INSERT INTO blocks(height,block_hash,previous_hash,timestamp,target,chainwork,block_json) VALUES(?,?,?,?,?,?,?)",
            (0, genesis_hash, "0" * 64, header["timestamp"], header["target"], "0", json.dumps(block, sort_keys=True)),
        )
        self._meta_set("genesis_hash", genesis_hash)
        self.db.commit()

    def tip(self) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM blocks ORDER BY height DESC LIMIT 1").fetchone()
        if row is None:
            raise PowV31Error("chain has no genesis")
        return {
            "height": int(row["height"]),
            "block_hash": str(row["block_hash"]),
            "timestamp": int(row["timestamp"]),
            "target": str(row["target"]),
            "chainwork": int(row["chainwork"]),
        }

    def info(self) -> dict[str, Any]:
        tip = self.tip()
        return {
            "protocol": POW_PROTOCOL,
            "chain_id": self.config.chain_id,
            "network": self.config.network,
            "pow_algo": self.config.pow_algo,
            "height": tip["height"],
            "best_block_hash": tip["block_hash"],
            "target": tip["target"],
            "difficulty": float(MAX_UINT256 / parse_target(tip["target"])),
            "chainwork": str(tip["chainwork"]),
            "mempool_size": int(self.db.execute("SELECT COUNT(*) FROM mempool").fetchone()[0]),
            "production_mainnet_ready": False,
            "production_crkbit_launched": False,
        }

    def get_block(self, height: int) -> dict[str, Any]:
        row = self.db.execute("SELECT block_hash,block_json,chainwork FROM blocks WHERE height=?", (int(height),)).fetchone()
        if row is None:
            raise PowV31Error("block not found")
        block = json.loads(row["block_json"])
        block["block_hash"] = str(row["block_hash"])
        block["chainwork"] = str(row["chainwork"])
        return block

    def get_utxos(self, address: str, *, spendable_height: int | None = None) -> list[dict[str, Any]]:
        rows = self.db.execute("SELECT txid,vout,address,amount,coinbase_height FROM utxos WHERE address=? ORDER BY amount DESC", (str(address),)).fetchall()
        height = self.tip()["height"] if spendable_height is None else int(spendable_height)
        result = []
        for row in rows:
            coinbase_height = row["coinbase_height"]
            mature = coinbase_height is None or height - int(coinbase_height) >= self.config.coinbase_maturity
            result.append({
                "txid": str(row["txid"]),
                "vout": int(row["vout"]),
                "address": str(row["address"]),
                "amount": int(row["amount"]),
                "coinbase_height": None if coinbase_height is None else int(coinbase_height),
                "mature": bool(mature),
            })
        return result

    def balance(self, address: str) -> dict[str, int]:
        height = self.tip()["height"]
        confirmed = 0
        immature = 0
        for item in self.get_utxos(address, spendable_height=height):
            if item["mature"]:
                confirmed += int(item["amount"])
            else:
                immature += int(item["amount"])
        return {"confirmed": confirmed, "immature": immature, "total": confirmed + immature}

    def _mempool_spent_outpoints(self, *, exclude_txid: str | None = None) -> set[tuple[str, int]]:
        spent: set[tuple[str, int]] = set()
        for row in self.db.execute("SELECT txid,tx_json FROM mempool"):
            if exclude_txid and str(row["txid"]) == exclude_txid:
                continue
            tx = json.loads(row["tx_json"])
            for item in tx.get("inputs", []):
                spent.add((str(item["txid"]), int(item["vout"])))
        return spent

    def _lookup_utxo(self, txid: str, vout: int) -> dict[str, Any] | None:
        row = self.db.execute("SELECT txid,vout,address,amount,coinbase_height FROM utxos WHERE txid=? AND vout=?", (txid, int(vout))).fetchone()
        if row is None:
            return None
        return {
            "txid": str(row["txid"]),
            "vout": int(row["vout"]),
            "address": str(row["address"]),
            "amount": int(row["amount"]),
            "coinbase_height": None if row["coinbase_height"] is None else int(row["coinbase_height"]),
        }

    def validate_transaction(self, tx: dict[str, Any], *, spend_height: int, mempool_policy: bool = False) -> tuple[int, list[dict[str, Any]]]:
        if int(tx.get("version", 0)) != TX_VERSION or is_coinbase(tx):
            raise PowV31Error("invalid regular transaction")
        inputs = list(tx.get("inputs", []))
        outputs = list(tx.get("outputs", []))
        if not inputs or not outputs:
            raise PowV31Error("transaction requires inputs and outputs")
        outpoints: set[tuple[str, int]] = set()
        prevouts: list[dict[str, Any]] = []
        input_total = 0
        mempool_spent = self._mempool_spent_outpoints() if mempool_policy else set()
        for index, item in enumerate(inputs):
            outpoint = (str(item.get("txid", "")).lower(), int(item.get("vout", -1)))
            if outpoint in outpoints:
                raise PowV31Error("duplicate transaction input")
            if mempool_policy and outpoint in mempool_spent:
                raise PowV31Error("input already spent by mempool transaction")
            outpoints.add(outpoint)
            prevout = self._lookup_utxo(*outpoint)
            if prevout is None:
                raise PowV31Error("input references missing/spent UTXO")
            if prevout["coinbase_height"] is not None and int(spend_height) - int(prevout["coinbase_height"]) < self.config.coinbase_maturity:
                raise PowV31Error("coinbase output is immature")
            public_key = str(item.get("public_key", ""))
            signature = str(item.get("signature", ""))
            if not public_key or not signature or address_from_public_key(public_key) != prevout["address"]:
                raise PowV31Error("input ownership proof is invalid")
            if not verify_signature(public_key, input_signing_payload(tx, index, prevout), signature):
                raise PowV31Error("invalid input signature")
            input_total += int(prevout["amount"])
            prevouts.append(prevout)
        output_total = 0
        for output in outputs:
            address = str(output.get("address", ""))
            amount = int(output.get("amount", 0))
            if not address.startswith("crk1") or amount <= 0:
                raise PowV31Error("invalid output")
            output_total += amount
            if output_total > 0x7FFFFFFFFFFFFFFF:
                raise PowV31Error("transaction output total overflow")
        fee = input_total - output_total
        if fee < 0:
            raise PowV31Error("transaction spends more than its inputs")
        return fee, prevouts

    def submit_transaction(self, tx: dict[str, Any]) -> dict[str, Any]:
        txid = transaction_id(tx)
        if self.db.execute("SELECT 1 FROM transactions WHERE txid=?", (txid,)).fetchone():
            raise PowV31Error("transaction already confirmed")
        if self.db.execute("SELECT 1 FROM mempool WHERE txid=?", (txid,)).fetchone():
            return {"accepted": True, "txid": txid, "already_in_mempool": True}
        fee, _ = self.validate_transaction(tx, spend_height=self.tip()["height"] + 1, mempool_policy=True)
        self.db.execute(
            "INSERT INTO mempool(txid,fee,received_at_ms,tx_json) VALUES(?,?,?,?)",
            (txid, fee, int(time.time() * 1000), json.dumps(tx, sort_keys=True)),
        )
        self.db.commit()
        return {"accepted": True, "txid": txid, "fee": fee}

    def create_payment(self, keypair: KeyPair, to_address: str, amount: int, fee: int) -> dict[str, Any]:
        amount = int(amount)
        fee = int(fee)
        if amount <= 0 or fee < 0:
            raise PowV31Error("invalid payment amount/fee")
        selected: list[dict[str, Any]] = []
        total = 0
        for utxo in self.get_utxos(keypair.address):
            if not utxo["mature"]:
                continue
            selected.append(utxo)
            total += int(utxo["amount"])
            if total >= amount + fee:
                break
        if total < amount + fee:
            raise PowV31Error("insufficient confirmed funds")
        outputs = [{"address": str(to_address), "amount": amount}]
        change = total - amount - fee
        if change:
            outputs.append({"address": keypair.address, "amount": change})
        unsigned = build_unsigned_transaction(
            [{"txid": item["txid"], "vout": item["vout"]} for item in selected],
            outputs,
        )
        return sign_transaction(unsigned, keypair, selected)

    def _expected_target(self, height: int) -> int:
        if int(height) <= 1:
            return self.config.initial_target
        parent = self.db.execute("SELECT target FROM blocks WHERE height=?", (int(height) - 1,)).fetchone()
        if parent is None:
            raise PowV31Error("missing parent block")
        previous_target = parse_target(parent["target"])
        interval = self.config.retarget_interval
        if int(height) % interval != 0:
            return previous_target
        first_height = int(height) - interval
        first = self.db.execute("SELECT timestamp FROM blocks WHERE height=?", (first_height,)).fetchone()
        last = self.db.execute("SELECT timestamp FROM blocks WHERE height=?", (int(height) - 1,)).fetchone()
        if first is None or last is None:
            return previous_target
        expected_span = interval * self.config.target_block_time_seconds
        actual_span = max(1, int(last["timestamp"]) - int(first["timestamp"]))
        actual_span = max(expected_span // 4, min(actual_span, expected_span * 4))
        return max(1, min(MAX_UINT256, (previous_target * actual_span) // expected_span))

    def _mempool_transactions(self, limit: int) -> list[dict[str, Any]]:
        rows = self.db.execute("SELECT tx_json FROM mempool ORDER BY fee DESC, received_at_ms ASC LIMIT ?", (int(limit),)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def get_block_template(self, miner_address: str, *, message: str = "Crakbit CPU miner") -> dict[str, Any]:
        if not str(miner_address).startswith("crk1"):
            raise PowV31Error("invalid miner address")
        tip = self.tip()
        height = tip["height"] + 1
        transactions = self._mempool_transactions(self.config.max_transactions_per_block - 1)
        valid_txs: list[dict[str, Any]] = []
        fees = 0
        seen: set[tuple[str, int]] = set()
        for tx in transactions:
            try:
                fee, _ = self.validate_transaction(tx, spend_height=height, mempool_policy=False)
                outpoints = {(str(i["txid"]), int(i["vout"])) for i in tx["inputs"]}
                if seen & outpoints:
                    continue
                seen |= outpoints
                fees += fee
                valid_txs.append(tx)
            except Exception:
                continue
        coinbase = build_coinbase(height, miner_address, subsidy_for_height(self.config, height) + fees, message)
        all_txs = [coinbase] + valid_txs
        txids = [transaction_id(tx) for tx in all_txs]
        target = self._expected_target(height)
        timestamp = max(now_seconds(), tip["timestamp"] + 1)
        header = {
            "version": BLOCK_VERSION,
            "chain_id": self.config.chain_id,
            "height": height,
            "previous_hash": tip["block_hash"],
            "merkle_root": merkle_root(txids),
            "timestamp": timestamp,
            "target": target_hex(target),
            "pow_algo": self.config.pow_algo,
            "pow_seed": pow_seed(self.config, height, tip["block_hash"]),
            "extra_nonce": 0,
            "nonce": 0,
        }
        return {
            "protocol": POW_PROTOCOL,
            "block": {"header": header, "transactions": all_txs},
            "height": height,
            "target": header["target"],
            "difficulty": float(MAX_UINT256 / target),
            "subsidy": subsidy_for_height(self.config, height),
            "fees": fees,
            "coinbase_value": subsidy_for_height(self.config, height) + fees,
            "transaction_count": len(all_txs),
            "pow": {
                "algo": self.config.pow_algo,
                "scrypt_n": self.config.scrypt_n,
                "scrypt_r": self.config.scrypt_r,
                "scrypt_p": self.config.scrypt_p,
            },
            "production_mainnet_ready": False,
        }

    def _validate_block_transactions(self, block: dict[str, Any]) -> tuple[int, list[tuple[str, int]], list[tuple[str, int, str, int, int | None]]]:
        height = int(block["header"]["height"])
        txs = list(block.get("transactions", []))
        if not txs or len(txs) > self.config.max_transactions_per_block:
            raise PowV31Error("invalid transaction count")
        coinbase = txs[0]
        if not is_coinbase(coinbase) or int(coinbase.get("height", -1)) != height:
            raise PowV31Error("first transaction must be height-bound coinbase")
        if any(is_coinbase(tx) for tx in txs[1:]):
            raise PowV31Error("multiple coinbase transactions")

        overlay: dict[tuple[str, int], dict[str, Any]] = {}
        for row in self.db.execute("SELECT txid,vout,address,amount,coinbase_height FROM utxos"):
            overlay[(str(row["txid"]), int(row["vout"]))] = {
                "txid": str(row["txid"]), "vout": int(row["vout"]), "address": str(row["address"]),
                "amount": int(row["amount"]), "coinbase_height": None if row["coinbase_height"] is None else int(row["coinbase_height"]),
            }
        spent: list[tuple[str, int]] = []
        created: list[tuple[str, int, str, int, int | None]] = []
        created_outpoints: set[tuple[str, int]] = set()
        fees = 0
        for tx in txs[1:]:
            if int(tx.get("version", 0)) != TX_VERSION:
                raise PowV31Error("unsupported transaction version")
            input_total = 0
            used: set[tuple[str, int]] = set()
            for index, item in enumerate(tx.get("inputs", [])):
                outpoint = (str(item.get("txid", "")).lower(), int(item.get("vout", -1)))
                if outpoint in used or outpoint not in overlay:
                    raise PowV31Error("block transaction spends missing/duplicate UTXO")
                used.add(outpoint)
                prevout = overlay[outpoint]
                if prevout["coinbase_height"] is not None and height - int(prevout["coinbase_height"]) < self.config.coinbase_maturity:
                    raise PowV31Error("block spends immature coinbase")
                public_key = str(item.get("public_key", ""))
                signature = str(item.get("signature", ""))
                if address_from_public_key(public_key) != prevout["address"] or not verify_signature(public_key, input_signing_payload(tx, index, prevout), signature):
                    raise PowV31Error("block transaction signature invalid")
                input_total += int(prevout["amount"])
            if not used:
                raise PowV31Error("regular transaction has no inputs")
            output_total = 0
            txid = transaction_id(tx)
            for vout, output in enumerate(tx.get("outputs", [])):
                amount = int(output.get("amount", 0))
                address = str(output.get("address", ""))
                if amount <= 0 or not address.startswith("crk1"):
                    raise PowV31Error("block transaction output invalid")
                output_total += amount
                outpoint = (txid, vout)
                overlay[outpoint] = {"txid": txid, "vout": vout, "address": address, "amount": amount, "coinbase_height": None}
                created.append((txid, vout, address, amount, None))
                created_outpoints.add(outpoint)
            if output_total > input_total:
                raise PowV31Error("block transaction creates value")
            fees += input_total - output_total
            for outpoint in used:
                del overlay[outpoint]
                if outpoint in created_outpoints:
                    created = [entry for entry in created if (entry[0], entry[1]) != outpoint]
                    created_outpoints.remove(outpoint)
                else:
                    spent.append(outpoint)

        coinbase_outputs = list(coinbase.get("outputs", []))
        if not coinbase_outputs:
            raise PowV31Error("coinbase has no output")
        coinbase_total = 0
        coinbase_txid = transaction_id(coinbase)
        for vout, output in enumerate(coinbase_outputs):
            amount = int(output.get("amount", 0))
            address = str(output.get("address", ""))
            if amount < 0 or not address.startswith("crk1"):
                raise PowV31Error("invalid coinbase output")
            coinbase_total += amount
            created.append((coinbase_txid, vout, address, amount, height))
        allowed = subsidy_for_height(self.config, height) + fees
        if coinbase_total != allowed:
            raise PowV31Error(f"coinbase value mismatch: got {coinbase_total}, expected {allowed}")
        return fees, spent, created

    def submit_block(self, block: dict[str, Any]) -> dict[str, Any]:
        header = block.get("header", {})
        tip = self.tip()
        height = int(header.get("height", -1))
        if int(header.get("version", 0)) != BLOCK_VERSION or str(header.get("chain_id")) != self.config.chain_id:
            raise PowV31Error("invalid block version/chain")
        if height != tip["height"] + 1 or str(header.get("previous_hash")) != tip["block_hash"]:
            raise PowV31Error("v0.31 accepts only blocks extending the current tip")
        expected_target = self._expected_target(height)
        if parse_target(header.get("target", "")) != expected_target:
            raise PowV31Error("unexpected difficulty target")
        expected_seed = pow_seed(self.config, height, tip["block_hash"])
        if str(header.get("pow_seed")) != expected_seed or str(header.get("pow_algo")) != self.config.pow_algo:
            raise PowV31Error("unexpected PoW seed/algorithm")
        timestamp = int(header.get("timestamp", 0))
        if timestamp <= tip["timestamp"] or timestamp > now_seconds() + self.config.max_future_seconds:
            raise PowV31Error("invalid block timestamp")
        nonce = int(header.get("nonce", -1))
        extra_nonce = int(header.get("extra_nonce", -1))
        if nonce < 0 or nonce > 0xFFFFFFFFFFFFFFFF or extra_nonce < 0 or extra_nonce > 0xFFFFFFFFFFFFFFFF:
            raise PowV31Error("invalid nonce")
        txs = list(block.get("transactions", []))
        txids = [transaction_id(tx) for tx in txs]
        if str(header.get("merkle_root")) != merkle_root(txids):
            raise PowV31Error("merkle root mismatch")
        if not verify_pow(block, self.config):
            raise PowV31Error("insufficient proof of work")
        fees, spent, created = self._validate_block_transactions(block)
        digest = block_hash(block, self.config)
        chainwork = tip["chainwork"] + work_for_target(expected_target)

        try:
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute(
                "INSERT INTO blocks(height,block_hash,previous_hash,timestamp,target,chainwork,block_json) VALUES(?,?,?,?,?,?,?)",
                (height, digest, tip["block_hash"], timestamp, target_hex(expected_target), str(chainwork), json.dumps(block, sort_keys=True)),
            )
            for index, tx in enumerate(txs):
                txid = txids[index]
                self.db.execute("INSERT INTO transactions(txid,block_height,tx_index,tx_json) VALUES(?,?,?,?)", (txid, height, index, json.dumps(tx, sort_keys=True)))
            for txid, vout in spent:
                self.db.execute("DELETE FROM utxos WHERE txid=? AND vout=?", (txid, vout))
            for txid, vout, address, amount, coinbase_height in created:
                self.db.execute("INSERT INTO utxos(txid,vout,address,amount,coinbase_height) VALUES(?,?,?,?,?)", (txid, vout, address, amount, coinbase_height))
            for txid in txids[1:]:
                self.db.execute("DELETE FROM mempool WHERE txid=?", (txid,))
            stale = []
            for row in self.db.execute("SELECT txid,tx_json FROM mempool"):
                tx = json.loads(row["tx_json"])
                if any(self._lookup_utxo(str(i["txid"]), int(i["vout"])) is None for i in tx.get("inputs", [])):
                    stale.append(str(row["txid"]))
            for txid in stale:
                self.db.execute("DELETE FROM mempool WHERE txid=?", (txid,))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return {
            "accepted": True,
            "height": height,
            "block_hash": digest,
            "chainwork": str(chainwork),
            "fees": fees,
            "transaction_count": len(txs),
            "production_mainnet_ready": False,
        }
