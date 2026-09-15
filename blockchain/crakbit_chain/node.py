from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from threading import Lock

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .crypto import KeyPair
from .genesis import Genesis, Validator
from .models import Block, PhaseVote, Transaction, ViewChange, merkle_root, now_ms
from .storage import Ledger, LedgerError


class TxEnvelope(BaseModel):
    transaction: dict


class BlockEnvelope(BaseModel):
    block: dict


class ViewChangeRequest(BaseModel):
    height: int
    from_round: int
    to_round: int


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
        self.pending_block: Block | None = None
        self.round_height = self.ledger.height + 1
        self.current_round = self.ledger.consensus_round(self.round_height)
        self.round_started_monotonic = time.monotonic()
        self.started_monotonic = time.monotonic()
        self.peer_health: dict[str, dict] = {}
        self.view_certificates: dict[tuple[int, int], list[ViewChange]] = {}

    # ------------------------------------------------------------------
    # Round / timing helpers
    # ------------------------------------------------------------------

    def _sync_round_height(self) -> None:
        next_height = self.ledger.height + 1
        if next_height != self.round_height:
            self.round_height = next_height
            self.current_round = self.ledger.consensus_round(next_height)
            self.pending_block = None
            self.round_started_monotonic = time.monotonic()

    def set_round(self, round_number: int) -> None:
        self._sync_round_height()
        if round_number < self.current_round:
            return
        if round_number != self.current_round:
            self.ledger.record_consensus_round(self.round_height, round_number)
            self.ledger.record_consensus_event(
                self.round_height,
                round_number,
                "round_change",
                details={"previous_round": self.current_round},
            )
            self.current_round = round_number
            self.pending_block = None
            self.round_started_monotonic = time.monotonic()

    @property
    def round_elapsed_ms(self) -> int:
        return int((time.monotonic() - self.round_started_monotonic) * 1000)

    @property
    def uptime_seconds(self) -> int:
        return int(time.monotonic() - self.started_monotonic)

    # ------------------------------------------------------------------
    # Transactions / proposals
    # ------------------------------------------------------------------

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

    def build_block(self, round_number: int | None = None) -> Block:
        self._sync_round_height()
        height = self.ledger.height + 1
        round_number = self.current_round if round_number is None else int(round_number)
        expected = self.genesis.proposer_for_height_round(height, round_number)
        if expected.address != self.key.address:
            raise LedgerError("this validator is not proposer for the current height/round")

        view_changes: list[ViewChange] = []
        if round_number > 0:
            view_changes = list(self.view_certificates.get((height, round_number), []))
            if len(view_changes) < self.genesis.quorum_size:
                raise LedgerError("missing quorum-certified view change for proposal round")

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
            round=round_number,
            view_changes=view_changes,
        )
        block.signature = self.key.sign(block.signing_bytes())
        self.ledger.record_consensus_event(
            block.height,
            block.round,
            "proposal_built",
            block_hash=block.block_hash,
        )
        return block

    # ------------------------------------------------------------------
    # Certified view changes
    # ------------------------------------------------------------------

    def _lock_metadata(self, height: int) -> tuple[int, str]:
        locked = self.ledger.consensus_lock(height)
        if locked is None:
            return -1, ""
        return locked

    def sign_view_change(
        self,
        height: int,
        from_round: int,
        to_round: int,
        *,
        require_timeout: bool = True,
    ) -> ViewChange:
        self._sync_round_height()
        if height != self.ledger.height + 1:
            raise LedgerError("view change targets an unexpected height")
        if from_round != self.current_round:
            raise LedgerError("view change does not match local consensus round")
        if to_round != from_round + 1:
            raise LedgerError("view change must advance exactly one round")
        if require_timeout and self.round_elapsed_ms < self.genesis.view_timeout_ms:
            raise LedgerError("view timeout has not elapsed")

        locked_round, locked_hash = self._lock_metadata(height)
        self.ledger.record_local_view_change(height, from_round, to_round)
        change = ViewChange(
            chain_id=self.genesis.chain_id,
            height=height,
            from_round=from_round,
            to_round=to_round,
            voter=self.key.address,
            public_key=self.key.public_key_b64,
            locked_round=locked_round,
            locked_block_hash=locked_hash,
        )
        change.signature = self.key.sign(change.signing_bytes())
        return change

    def validate_peer_view_change(
        self,
        change: ViewChange,
        *,
        height: int,
        from_round: int,
        to_round: int,
    ) -> None:
        if change.chain_id != self.genesis.chain_id:
            raise LedgerError("peer view-change chain_id mismatch")
        if change.height != height:
            raise LedgerError("peer view-change height mismatch")
        if change.from_round != from_round or change.to_round != to_round:
            raise LedgerError("peer view-change round mismatch")
        validator = self.genesis.validator_by_address(change.voter)
        if validator is None:
            raise LedgerError("peer view-change from unknown validator")
        if validator.public_key != change.public_key:
            raise LedgerError("peer view-change public key mismatch")
        if change.locked_round < -1 or change.locked_round >= change.to_round:
            raise LedgerError("peer view-change lock round invalid")
        if change.locked_round == -1 and change.locked_block_hash:
            raise LedgerError("unlocked peer view-change carries a block hash")
        if change.locked_round >= 0 and len(change.locked_block_hash) != 64:
            raise LedgerError("locked peer view-change lacks a valid block hash")
        if not change.verify_signature():
            raise LedgerError("invalid peer view-change signature")

    async def _request_view_change(
        self,
        peer: Validator,
        height: int,
        from_round: int,
        to_round: int,
    ) -> ViewChange | None:
        if peer.address == self.key.address:
            return None
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(
                    f"{peer.peer_url.rstrip('/')}/internal/view-change-request",
                    json={"height": height, "from_round": from_round, "to_round": to_round},
                )
                response.raise_for_status()
                change = ViewChange.from_dict(response.json()["view_change"])
                self.validate_peer_view_change(
                    change,
                    height=height,
                    from_round=from_round,
                    to_round=to_round,
                )
                return change
        except Exception:
            return None

    async def collect_view_change_certificate(self, target_round: int) -> bool:
        self._sync_round_height()
        height = self.ledger.height + 1
        from_round = self.current_round
        if target_round != from_round + 1:
            raise LedgerError("target view must be the next round")

        changes: dict[str, ViewChange] = {}
        self_change = self.sign_view_change(height, from_round, target_round, require_timeout=True)
        changes[self_change.voter] = self_change
        results = await asyncio.gather(
            *(
                self._request_view_change(peer, height, from_round, target_round)
                for peer in self.genesis.validators
            ),
            return_exceptions=False,
        )
        for change in results:
            if change is not None:
                changes[change.voter] = change
        if len(changes) < self.genesis.quorum_size:
            return False

        certificate = list(changes.values())
        for change in certificate:
            self.validate_peer_view_change(
                change,
                height=height,
                from_round=from_round,
                to_round=target_round,
            )
        self.view_certificates[(height, target_round)] = certificate
        self.ledger.record_consensus_event(
            height,
            target_round,
            "view_change_certificate",
            details={"votes": len(certificate)},
        )
        self.set_round(target_round)
        return True

    # ------------------------------------------------------------------
    # v0.5 prevote / precommit pipeline
    # ------------------------------------------------------------------

    def _prepare_vote_round(self, block: Block) -> None:
        self._sync_round_height()
        self.ledger.validate_block_proposal(block)
        if block.round < self.current_round:
            raise LedgerError("validator refuses to vote for a stale consensus round")
        if block.round > self.current_round + 1:
            raise LedgerError("validator refuses an excessive consensus-round jump")
        if block.round > self.current_round:
            self.view_certificates[(block.height, block.round)] = list(block.view_changes)
            self.set_round(block.round)

        evidence = self.ledger.record_seen_proposal(block)
        if evidence is not None:
            raise LedgerError("validator detected conflicting signed proposals from the same proposer")

    def _enforce_lock(self, block: Block) -> None:
        locked = self.ledger.consensus_lock(block.height)
        if locked is None:
            return
        locked_round, locked_hash = locked
        if locked_hash != block.block_hash:
            raise LedgerError(
                f"cross-round consensus lock prevents conflicting vote; locked at round {locked_round}"
            )

    def _sign_phase_vote(self, block: Block, phase: str) -> PhaseVote:
        self._prepare_vote_round(block)
        self._enforce_lock(block)
        if phase == "precommit":
            self.ledger.validate_prevote_certificate(block)

        existing_hash = self.ledger.phase_vote_hash(block.height, block.round, phase)
        if existing_hash is not None and existing_hash != block.block_hash:
            raise LedgerError(f"validator refuses to double-{phase} at the same height and round")

        vote = PhaseVote(
            chain_id=block.chain_id,
            height=block.height,
            round=block.round,
            phase=phase,
            block_hash=block.block_hash,
            voter=self.key.address,
            public_key=self.key.public_key_b64,
        )
        vote.signature = self.key.sign(vote.signing_bytes())
        self.ledger.record_phase_vote(block.height, block.round, phase, block.block_hash)
        if phase == "precommit":
            self.ledger.set_consensus_lock(block.height, block.round, block.block_hash)
        return vote

    def sign_prevote(self, block: Block) -> PhaseVote:
        return self._sign_phase_vote(block, "prevote")

    def sign_precommit(self, block: Block) -> PhaseVote:
        return self._sign_phase_vote(block, "precommit")

    def validate_peer_phase_vote(self, vote: PhaseVote, block: Block, phase: str) -> None:
        if vote.phase != phase:
            raise LedgerError("peer consensus vote phase mismatch")
        if vote.chain_id != block.chain_id:
            raise LedgerError("peer consensus vote chain_id mismatch")
        if vote.height != block.height or vote.round != block.round:
            raise LedgerError("peer consensus vote height/round mismatch")
        if vote.block_hash != block.block_hash:
            raise LedgerError("peer consensus vote block hash mismatch")
        validator = self.genesis.validator_by_address(vote.voter)
        if validator is None:
            raise LedgerError("peer consensus vote from unknown validator")
        if validator.public_key != vote.public_key:
            raise LedgerError("peer consensus vote public key mismatch")
        if not vote.verify_signature():
            raise LedgerError("invalid peer consensus vote signature")

    async def _request_phase_vote(self, peer: Validator, block: Block, phase: str) -> PhaseVote | None:
        if peer.address == self.key.address:
            return None
        endpoint = "prevote" if phase == "prevote" else "precommit"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(
                    f"{peer.peer_url.rstrip('/')}/internal/{endpoint}",
                    json={"block": block.to_dict()},
                )
                response.raise_for_status()
                vote = PhaseVote.from_dict(response.json()["vote"])
                self.validate_peer_phase_vote(vote, block, phase)
                return vote
        except Exception:
            return None

    async def collect_prevotes(self, block: Block) -> bool:
        votes: dict[str, PhaseVote] = {}
        self_vote = self.sign_prevote(block)
        votes[self_vote.voter] = self_vote
        results = await asyncio.gather(
            *(self._request_phase_vote(peer, block, "prevote") for peer in self.genesis.validators),
            return_exceptions=False,
        )
        for vote in results:
            if vote is not None:
                votes[vote.voter] = vote
        if len(votes) < self.genesis.quorum_size:
            return False
        block.prevote_votes = list(votes.values())
        self.ledger.validate_prevote_certificate(block)
        self.ledger.record_consensus_event(
            block.height,
            block.round,
            "prevote_certificate",
            phase="prevote",
            block_hash=block.block_hash,
            details={"votes": len(block.prevote_votes)},
        )
        return True

    async def collect_precommits(self, block: Block) -> bool:
        self.ledger.validate_prevote_certificate(block)
        votes: dict[str, PhaseVote] = {}
        self_vote = self.sign_precommit(block)
        votes[self_vote.voter] = self_vote
        results = await asyncio.gather(
            *(self._request_phase_vote(peer, block, "precommit") for peer in self.genesis.validators),
            return_exceptions=False,
        )
        for vote in results:
            if vote is not None:
                votes[vote.voter] = vote
        if len(votes) < self.genesis.quorum_size:
            return False
        block.precommit_votes = list(votes.values())
        self.ledger.validate_precommit_certificate(block)
        self.ledger.record_consensus_event(
            block.height,
            block.round,
            "precommit_certificate",
            phase="precommit",
            block_hash=block.block_hash,
            details={"votes": len(block.precommit_votes)},
        )
        return True

    # ------------------------------------------------------------------
    # Finalization / networking / monitoring
    # ------------------------------------------------------------------

    def accept_block(self, block: Block) -> None:
        self.ledger.apply_block(block)
        self.ledger.prune_consensus_state(block.height)
        with self.lock:
            for tx in block.transactions:
                self.mempool.pop(tx.txid, None)
        self.pending_block = None
        self.view_certificates = {
            key: value for key, value in self.view_certificates.items() if key[0] > block.height
        }
        self._sync_round_height()

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
                        self._sync_round_height()
                        return
                except Exception:
                    continue

    async def refresh_peer_health(self) -> None:
        now = now_ms()
        async with httpx.AsyncClient(timeout=2.0) as client:
            for peer in self.genesis.validators:
                if peer.address == self.key.address:
                    self.peer_health[peer.address] = {
                        "name": peer.name,
                        "address": peer.address,
                        "healthy": True,
                        "height": self.ledger.height,
                        "round": self.current_round,
                        "last_seen_ms": now,
                        "local": True,
                    }
                    continue
                try:
                    response = await client.get(f"{peer.peer_url.rstrip('/')}/status")
                    response.raise_for_status()
                    status = response.json()
                    self.peer_health[peer.address] = {
                        "name": peer.name,
                        "address": peer.address,
                        "healthy": True,
                        "height": int(status.get("height", 0)),
                        "round": int(status.get("consensus_round", 0)),
                        "last_seen_ms": now,
                        "local": False,
                    }
                except Exception as exc:
                    previous = self.peer_health.get(peer.address, {})
                    self.peer_health[peer.address] = {
                        "name": peer.name,
                        "address": peer.address,
                        "healthy": False,
                        "height": previous.get("height"),
                        "round": previous.get("round"),
                        "last_seen_ms": previous.get("last_seen_ms"),
                        "local": False,
                        "error": type(exc).__name__,
                    }

    async def consensus_loop(self) -> None:
        while True:
            try:
                await self.sync_once()
                self._sync_round_height()
                next_height = self.ledger.height + 1
                expected = self.genesis.proposer_for_height_round(next_height, self.current_round)

                if expected.address == self.key.address:
                    if (
                        self.pending_block is None
                        or self.pending_block.height != next_height
                        or self.pending_block.round != self.current_round
                    ):
                        self.pending_block = self.build_block(self.current_round)

                    candidate = self.pending_block
                    if not candidate.prevote_votes:
                        await self.collect_prevotes(candidate)
                    if candidate.prevote_votes and not candidate.precommit_votes:
                        await self.collect_precommits(candidate)
                    if candidate.prevote_votes and candidate.precommit_votes:
                        finalized = candidate
                        self.accept_block(finalized)
                        await self.broadcast_block(finalized)

                await self.refresh_peer_health()

                if self.round_elapsed_ms >= self.genesis.view_timeout_ms:
                    await self.collect_view_change_certificate(self.current_round + 1)
            except Exception:
                pass
            await asyncio.sleep(self.genesis.block_time_ms / 1000)


def create_app() -> FastAPI:
    genesis_path = os.environ.get("CRAKBIT_GENESIS", "runtime/genesis.json")
    key_path = os.environ.get("CRAKBIT_VALIDATOR_KEY", "runtime/validator.json")
    data_dir = os.environ.get("CRAKBIT_DATA_DIR", "runtime/data")
    node = Node(genesis_path, key_path, data_dir)

    app = FastAPI(title="Crakbit Chain Devnet", version="0.5.0a1")
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

    @app.get("/health")
    def health() -> dict:
        return {
            "ok": True,
            "validator": node.key.address,
            "height": node.ledger.height,
            "round": node.current_round,
            "uptime_seconds": node.uptime_seconds,
        }

    @app.get("/status")
    def status() -> dict:
        node._sync_round_height()
        next_height = node.ledger.height + 1
        next_proposer = node.genesis.proposer_for_height_round(next_height, node.current_round)
        healthy_peers = sum(1 for item in node.peer_health.values() if item.get("healthy"))
        certificate = node.view_certificates.get((next_height, node.current_round), [])
        consensus_lock = node.ledger.consensus_lock(next_height)
        candidate = node.pending_block
        return {
            "chain_id": node.genesis.chain_id,
            "network": node.genesis.network_name,
            "symbol": node.genesis.symbol,
            "height": node.ledger.height,
            "finalized_height": node.ledger.height,
            "last_hash": node.ledger.last_hash,
            "validator": node.key.address,
            "validator_count": len(node.genesis.validators),
            "commit_quorum": node.genesis.quorum_size,
            "consensus": "certified-view-change+prevote+precommit+durable-lock",
            "consensus_round": node.current_round,
            "round_elapsed_ms": node.round_elapsed_ms,
            "view_timeout_ms": node.genesis.view_timeout_ms,
            "view_certificate_votes": len(certificate),
            "next_proposer": {"name": next_proposer.name, "address": next_proposer.address},
            "local_lock": (
                {"round": consensus_lock[0], "block_hash": consensus_lock[1]}
                if consensus_lock is not None
                else None
            ),
            "candidate_prevotes": len(candidate.prevote_votes) if candidate else 0,
            "candidate_precommits": len(candidate.precommit_votes) if candidate else 0,
            "mempool": len(node.mempool),
            "pending_proposal": candidate.block_hash if candidate else None,
            "persistent_phase_votes": node.ledger.phase_vote_count(),
            "persistent_view_changes": node.ledger.local_view_change_count(),
            "consensus_events": node.ledger.consensus_event_count(),
            "equivocation_evidence": node.ledger.evidence_count(),
            "healthy_validator_views": healthy_peers,
            "uptime_seconds": node.uptime_seconds,
            "genesis_fingerprint": node.genesis.fingerprint(),
        }

    @app.get("/validators")
    def validators() -> dict:
        next_height = node.ledger.height + 1
        proposer = node.genesis.proposer_for_height_round(next_height, node.current_round)
        return {
            "quorum": node.genesis.quorum_size,
            "round": node.current_round,
            "current_proposer": proposer.address,
            "validators": [
                {"name": v.name, "address": v.address, "peer_url": v.peer_url}
                for v in node.genesis.validators
            ],
        }

    @app.get("/peers")
    def peers() -> dict:
        return {"updated_from_consensus_loop": True, "peers": list(node.peer_health.values())}

    @app.get("/evidence")
    def evidence(limit: int = 100) -> dict:
        return {"count": node.ledger.evidence_count(), "items": node.ledger.list_evidence(limit)}

    @app.get("/consensus/events")
    def consensus_events(limit: int = 100) -> dict:
        return {
            "count": node.ledger.consensus_event_count(),
            "items": node.ledger.list_consensus_events(limit),
        }

    @app.get("/metrics")
    def metrics() -> dict:
        locked = node.ledger.consensus_lock(node.ledger.height + 1)
        return {
            "height": node.ledger.height,
            "round": node.current_round,
            "mempool": len(node.mempool),
            "local_prevotes": node.ledger.phase_vote_count("prevote"),
            "local_precommits": node.ledger.phase_vote_count("precommit"),
            "locked": locked is not None,
            "evidence": node.ledger.evidence_count(),
            "events": node.ledger.consensus_event_count(),
            "healthy_validator_views": sum(
                1 for item in node.peer_health.values() if item.get("healthy")
            ),
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

    @app.post("/internal/view-change-request")
    def view_change_request(request: ViewChangeRequest) -> dict:
        try:
            change = node.sign_view_change(
                request.height,
                request.from_round,
                request.to_round,
                require_timeout=True,
            )
            return {"accepted": True, "view_change": change.to_dict()}
        except (KeyError, ValueError, LedgerError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/internal/prevote")
    def prevote(envelope: BlockEnvelope) -> dict:
        try:
            incoming = Block.from_dict(envelope.block)
            vote = node.sign_prevote(incoming)
            return {"accepted": True, "vote": vote.to_dict()}
        except (KeyError, ValueError, LedgerError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/internal/precommit")
    def precommit(envelope: BlockEnvelope) -> dict:
        try:
            incoming = Block.from_dict(envelope.block)
            vote = node.sign_precommit(incoming)
            return {"accepted": True, "vote": vote.to_dict()}
        except (KeyError, ValueError, LedgerError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/internal/proposal")
    def legacy_proposal_alias(envelope: BlockEnvelope) -> dict:
        """Compatibility alias: v0.5 proposal voting maps to the prevote phase."""
        try:
            incoming = Block.from_dict(envelope.block)
            vote = node.sign_prevote(incoming)
            return {"accepted": True, "vote": vote.to_dict(), "phase": "prevote"}
        except (KeyError, ValueError, LedgerError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/internal/block")
    def receive_block(envelope: BlockEnvelope) -> dict:
        try:
            incoming = Block.from_dict(envelope.block)
            if incoming.height <= node.ledger.height:
                return {"accepted": True, "duplicate": True}
            node.accept_block(incoming)
            return {"accepted": True, "height": incoming.height, "round": incoming.round}
        except (KeyError, ValueError, LedgerError) as exc:
            raise HTTPException(400, str(exc)) from exc

    return app


app = create_app()
