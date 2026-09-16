from __future__ import annotations

import asyncio
import os
import secrets
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from .crypto import canonical_json
from .genesis import Validator
from .models import Block, PhaseVote, Transaction, ViewChange
from .node import BlockEnvelope, Node, TxEnvelope, ViewChangeRequest
from .peer_auth import (
    PeerAuthError,
    PeerAuthenticator,
    build_hello_payload,
    sign_peer_request,
    verify_hello_response,
)
from .snapshots import sign_snapshot
from .storage import LedgerError


class PeerHelloRequest(BaseModel):
    challenge: str


class SecureNode(Node):
    """v0.6 wrapper around the v0.5 consensus node.

    Consensus semantics remain inherited from v0.5. This layer authenticates validator
    HTTP requests with Ed25519 request signatures, adds a signed identity handshake,
    exposes signed snapshots, and supports a deployment mode that refuses non-HTTPS
    validator peer URLs.
    """

    def __init__(self, genesis_path: str, key_path: str, data_dir: str):
        super().__init__(genesis_path, key_path, data_dir)
        self.peer_authenticator = PeerAuthenticator(self.genesis)
        self.require_peer_tls = os.environ.get("CRAKBIT_REQUIRE_PEER_TLS", "0") == "1"
        if self.require_peer_tls:
            insecure = [
                peer.peer_url
                for peer in self.genesis.validators
                if peer.address != self.key.address and not peer.peer_url.lower().startswith("https://")
            ]
            if insecure:
                raise ValueError(
                    "CRAKBIT_REQUIRE_PEER_TLS=1 but genesis contains non-HTTPS peer URLs: "
                    + ", ".join(insecure)
                )

    def _peer_url(self, peer: Validator, path: str) -> str:
        base = peer.peer_url.rstrip("/")
        if self.require_peer_tls and not base.lower().startswith("https://"):
            raise LedgerError("peer TLS enforcement rejected a non-HTTPS validator URL")
        return f"{base}{path}"

    async def _post_internal(
        self,
        client: httpx.AsyncClient,
        peer: Validator,
        path: str,
        payload: dict[str, Any],
    ) -> httpx.Response:
        body = canonical_json(payload)
        headers = {
            "Content-Type": "application/json",
            **sign_peer_request(
                self.key,
                method="POST",
                path=path,
                body=body,
            ),
        }
        return await client.post(
            self._peer_url(peer, path),
            content=body,
            headers=headers,
        )

    async def authenticate_peer(self, client: httpx.AsyncClient, peer: Validator) -> dict:
        challenge = secrets.token_hex(24)
        response = await self._post_internal(
            client,
            peer,
            "/internal/hello",
            {"challenge": challenge},
        )
        response.raise_for_status()
        return verify_hello_response(
            peer,
            response.json(),
            chain_id=self.genesis.chain_id,
            challenge=challenge,
        )

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
                response = await self._post_internal(
                    client,
                    peer,
                    "/internal/view-change-request",
                    {"height": height, "from_round": from_round, "to_round": to_round},
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

    async def _request_phase_vote(
        self,
        peer: Validator,
        block: Block,
        phase: str,
    ) -> PhaseVote | None:
        if peer.address == self.key.address:
            return None
        endpoint = "prevote" if phase == "prevote" else "precommit"
        path = f"/internal/{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await self._post_internal(
                    client,
                    peer,
                    path,
                    {"block": block.to_dict()},
                )
                response.raise_for_status()
                vote = PhaseVote.from_dict(response.json()["vote"])
                self.validate_peer_phase_vote(vote, block, phase)
                return vote
        except Exception:
            return None

    async def broadcast_block(self, block: Block) -> None:
        async with httpx.AsyncClient(timeout=3.0) as client:
            for peer in self.genesis.validators:
                if peer.address == self.key.address:
                    continue
                try:
                    await self._post_internal(
                        client,
                        peer,
                        "/internal/block",
                        {"block": block.to_dict()},
                    )
                except Exception:
                    pass

    async def broadcast_transaction(self, tx: Transaction) -> None:
        async with httpx.AsyncClient(timeout=2.0) as client:
            for peer in self.genesis.validators:
                if peer.address == self.key.address:
                    continue
                try:
                    await self._post_internal(
                        client,
                        peer,
                        "/internal/transaction",
                        {"transaction": tx.to_dict()},
                    )
                except Exception:
                    pass

    async def refresh_peer_health(self) -> None:
        now = int(__import__("time").time() * 1000)
        async with httpx.AsyncClient(timeout=2.5) as client:
            for peer in self.genesis.validators:
                if peer.address == self.key.address:
                    self.peer_health[peer.address] = {
                        "name": peer.name,
                        "address": peer.address,
                        "healthy": True,
                        "authenticated_identity": True,
                        "height": self.ledger.height,
                        "round": self.current_round,
                        "last_seen_ms": now,
                        "local": True,
                    }
                    continue
                try:
                    await self.authenticate_peer(client, peer)
                    response = await client.get(f"{peer.peer_url.rstrip('/')}/status")
                    response.raise_for_status()
                    status = response.json()
                    self.peer_health[peer.address] = {
                        "name": peer.name,
                        "address": peer.address,
                        "healthy": True,
                        "authenticated_identity": True,
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
                        "authenticated_identity": False,
                        "height": previous.get("height"),
                        "round": previous.get("round"),
                        "last_seen_ms": previous.get("last_seen_ms"),
                        "local": False,
                        "error": type(exc).__name__,
                    }


def create_app() -> FastAPI:
    genesis_path = os.environ.get("CRAKBIT_GENESIS", "runtime/genesis.json")
    key_path = os.environ.get("CRAKBIT_VALIDATOR_KEY", "runtime/validator.json")
    data_dir = os.environ.get("CRAKBIT_DATA_DIR", "runtime/data")
    node = SecureNode(genesis_path, key_path, data_dir)

    app = FastAPI(title="Crakbit Chain Devnet", version="0.6.0a1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.state.node = node

    @app.middleware("http")
    async def validator_authentication(request: Request, call_next):
        if request.url.path.startswith("/internal/"):
            body = await request.body()
            try:
                request.state.validator = node.peer_authenticator.verify(
                    request.headers,
                    method=request.method,
                    path=request.url.path,
                    body=body,
                )
            except PeerAuthError as exc:
                return JSONResponse(
                    status_code=401,
                    content={"detail": str(exc)},
                )
        return await call_next(request)

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
            "peer_auth": "ed25519-signed-requests",
            "peer_tls_required": node.require_peer_tls,
            "uptime_seconds": node.uptime_seconds,
        }

    @app.get("/status")
    def status() -> dict:
        node._sync_round_height()
        next_height = node.ledger.height + 1
        next_proposer = node.genesis.proposer_for_height_round(next_height, node.current_round)
        healthy_peers = sum(1 for item in node.peer_health.values() if item.get("healthy"))
        authenticated_peers = sum(
            1 for item in node.peer_health.values() if item.get("authenticated_identity")
        )
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
            "authenticated_validator_views": authenticated_peers,
            "peer_auth": "ed25519-request-signatures+challenge-response",
            "peer_tls_required": node.require_peer_tls,
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
            "peer_tls_required": node.require_peer_tls,
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
            "authenticated_validator_views": sum(
                1 for item in node.peer_health.values() if item.get("authenticated_identity")
            ),
        }

    @app.get("/metrics/prometheus", response_class=PlainTextResponse)
    def prometheus_metrics() -> str:
        locked = 1 if node.ledger.consensus_lock(node.ledger.height + 1) else 0
        healthy = sum(1 for item in node.peer_health.values() if item.get("healthy"))
        authenticated = sum(
            1 for item in node.peer_health.values() if item.get("authenticated_identity")
        )
        values = {
            "crakbit_chain_height": node.ledger.height,
            "crakbit_consensus_round": node.current_round,
            "crakbit_mempool_transactions": len(node.mempool),
            "crakbit_local_prevotes_total": node.ledger.phase_vote_count("prevote"),
            "crakbit_local_precommits_total": node.ledger.phase_vote_count("precommit"),
            "crakbit_consensus_locked": locked,
            "crakbit_equivocation_evidence_total": node.ledger.evidence_count(),
            "crakbit_consensus_events_total": node.ledger.consensus_event_count(),
            "crakbit_healthy_validator_views": healthy,
            "crakbit_authenticated_validator_views": authenticated,
        }
        return "".join(f"{name} {value}\n" for name, value in values.items())

    @app.get("/snapshot/latest")
    def latest_snapshot() -> dict:
        return sign_snapshot(node.ledger, node.key)

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
        await node.broadcast_transaction(tx)
        return {"accepted": True, "txid": txid}

    @app.post("/internal/hello")
    def peer_hello(request: PeerHelloRequest) -> dict:
        if len(request.challenge) < 16 or len(request.challenge) > 256:
            raise HTTPException(400, "invalid peer hello challenge")
        return build_hello_payload(
            node.key,
            chain_id=node.genesis.chain_id,
            challenge=request.challenge,
        )

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
