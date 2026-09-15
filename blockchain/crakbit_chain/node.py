from __future__ import annotations

import asyncio
import os
from pathlib import Path
from threading import Lock

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .crypto import KeyPair
from .genesis import Genesis
from .models import Block, Transaction, merkle_root, now_ms
from .storage import Ledger, LedgerError


class TxEnvelope(BaseModel):
    transaction: dict


class BlockEnvelope(BaseModel):
    block: dict


class Node:
    def __init__(self, genesis_path: str, key_path: str, data_dir: str):
        self.genesis = Genesis.load(genesis_path)
        self.key = KeyPair.load(key_path)
        validator = self.genesis.validator_by_address(self.key.address)
        if validator is None or validator.public_key != self.key.public_key_b64:
            raise ValueError("node key is not a configured genesis validator")
        self.validator = validator
        self.ledger = Ledger(Path(data_dir) / "chain.sqlite3", self.genesis)
        self.mempool: dict[str, Transaction] = {}
        self.lock = Lock()

    def submit_transaction(self, tx: Transaction) -> str:
        self.ledger.validate_transaction(tx)
        with self.lock:
            if any(item.sender == tx.sender for item in self.mempool.values()):
                raise LedgerError("sender already has a pending transaction")
            self.mempool[tx.txid] = tx
        return tx.txid

    def _select_transactions(self, limit: int = 1000) -> list[Transaction]:
        with self.lock:
            txs = list(self.mempool.values())[:limit]
        valid: list[Transaction] = []
        for tx in txs:
            try:
                self.ledger.validate_transaction(tx)
                valid.append(tx)
            except LedgerError:
                with self.lock:
                    self.mempool.pop(tx.txid, None)
        return valid

    def build_block(self) -> Block:
        height = self.ledger.height + 1
        expected = self.genesis.proposer_for_height(height)
        if expected.address != self.key.address:
            raise LedgerError("this validator is not proposer for next height")
        txs = self._select_transactions()
        state_root = self.ledger.simulate_state_root(txs, self.key.address)
        block = Block(
            chain_id=self.genesis.chain_id,
            height=height,
            previous_hash=self.ledger.last_hash,
            timestamp=now_ms(),
            proposer=self.key.address,
            proposer_public_key=self.key.public_key_b64,
            transactions=txs,
            tx_root=merkle_root([tx.txid for tx in txs]),
            state_root=state_root,
        )
        block.signature = self.key.sign(block.signing_bytes())
        return block

    def accept_block(self, block: Block) -> None:
        self.ledger.apply_block(block)
        with self.lock:
            for tx in block.transactions:
                self.mempool.pop(tx.txid, None)

    async def broadcast_block(self, block: Block) -> None:
        async with httpx.AsyncClient(timeout=3.0) as client:
            for peer in self.genesis.validators:
                if peer.address == self.key.address:
                    continue
                try:
                    await client.post(
                        f"{peer.peer_url.rstrip('/')}/internal/block",
                        json={"block": block.to_dict()},
                    )
                except Exception:
                    pass

    async def sync_once(self) -> None:
        peers = [p for p in self.genesis.validators if p.address != self.key.address]
        async with httpx.AsyncClient(timeout=3.0) as client:
            for peer in peers:
                try:
                    status = (await client.get(f"{peer.peer_url.rstrip('/')}/status")).json()
                    remote_height = int(status["height"])
                    while self.ledger.height < remote_height:
                        next_height = self.ledger.height + 1
                        response = await client.get(f"{peer.peer_url.rstrip('/')}/blocks/{next_height}")
                        if response.status_code != 200:
                            break
                        self.accept_block(Block.from_dict(response.json()))
                    if self.ledger.height >= remote_height:
                        return
                except Exception:
                    continue

    async def consensus_loop(self) -> None:
        while True:
            try:
                await self.sync_once()
                next_height = self.ledger.height + 1
                expected = self.genesis.proposer_for_height(next_height)
                if expected.address == self.key.address:
                    block = self.build_block()
                    self.accept_block(block)
                    await self.broadcast_block(block)
            except Exception:
                pass
            await asyncio.sleep(self.genesis.block_time_ms / 1000)


def create_app() -> FastAPI:
    genesis_path = os.environ.get("CRAKBIT_GENESIS", "runtime/genesis.json")
    key_path = os.environ.get("CRAKBIT_VALIDATOR_KEY", "runtime/validator.json")
    data_dir = os.environ.get("CRAKBIT_DATA_DIR", "runtime/data")
    node = Node(genesis_path, key_path, data_dir)

    app = FastAPI(title="Crakbit Chain Devnet", version="0.1.0a1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.state.node = node

    @app.on_event("startup")
    async def startup() -> None:
        app.state.consensus_task = asyncio.create_task(node.consensus_loop())

    @app.on_event("shutdown")
    async def shutdown() -> None:
        app.state.consensus_task.cancel()

    @app.get("/status")
    def status() -> dict:
        return {
            "chain_id": node.genesis.chain_id,
            "network": node.genesis.network_name,
            "symbol": node.genesis.symbol,
            "height": node.ledger.height,
            "last_hash": node.ledger.last_hash,
            "validator": node.key.address,
            "mempool": len(node.mempool),
            "genesis_fingerprint": node.genesis.fingerprint(),
        }

    @app.get("/balance/{address}")
    def balance(address: str) -> dict:
        return node.ledger.account(address)

    @app.get("/blocks/{height}")
    def block(height: int) -> dict:
        result = node.ledger.get_block(height)
        if result is None:
            raise HTTPException(404, "block not found")
        return result

    @app.get("/transactions/{txid}")
    def transaction(txid: str) -> dict:
        result = node.ledger.get_transaction(txid)
        if result is None:
            raise HTTPException(404, "transaction not found")
        return result

    @app.post("/transactions")
    async def submit(envelope: TxEnvelope) -> dict:
        try:
            tx = Transaction.from_dict(envelope.transaction)
            txid = node.submit_transaction(tx)
        except (KeyError, ValueError, LedgerError) as exc:
            raise HTTPException(400, str(exc)) from exc
        async with httpx.AsyncClient(timeout=2.0) as client:
            for peer in node.genesis.validators:
                if peer.address == node.key.address:
                    continue
                try:
                    await client.post(
                        f"{peer.peer_url.rstrip('/')}/internal/transaction",
                        json={"transaction": tx.to_dict()},
                    )
                except Exception:
                    pass
        return {"accepted": True, "txid": txid}

    @app.post("/internal/transaction")
    def peer_submit(envelope: TxEnvelope) -> dict:
        try:
            txid = node.submit_transaction(Transaction.from_dict(envelope.transaction))
            return {"accepted": True, "txid": txid}
        except LedgerError as exc:
            if "pending transaction" in str(exc):
                return {"accepted": True, "duplicate": True}
            raise HTTPException(400, str(exc)) from exc

    @app.post("/internal/block")
    def receive_block(envelope: BlockEnvelope) -> dict:
        try:
            incoming = Block.from_dict(envelope.block)
            if incoming.height <= node.ledger.height:
                return {"accepted": True, "duplicate": True}
            node.accept_block(incoming)
            return {"accepted": True, "height": incoming.height}
        except (ValueError, LedgerError) as exc:
            raise HTTPException(400, str(exc)) from exc

    return app


app = create_app()
