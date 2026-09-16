from __future__ import annotations

import time

import httpx

from . import secure_node as secure_node_module
from .models import Block, PhaseVote, Transaction, ViewChange
from .secure_node import SecureNode
from .secure_node_v10 import create_app as create_v10_app
from .transport_security import TransportSecurityConfig


class HardenedTransportNode(SecureNode):
    """v0.11 transport-hardened validator wrapper.

    Consensus behavior remains inherited from the research devnet. This layer adds
    operator-managed outbound mTLS trust, optional leaf-certificate pinning and keeps
    the existing Ed25519 request signatures/challenge-response identity checks.
    """

    def __init__(self, genesis_path: str, key_path: str, data_dir: str):
        super().__init__(genesis_path, key_path, data_dir)
        self.transport_security = TransportSecurityConfig.from_env()
        if self.transport_security.require_mtls:
            insecure = [
                peer.peer_url
                for peer in self.genesis.validators
                if peer.address != self.key.address and not peer.peer_url.lower().startswith("https://")
            ]
            if insecure:
                raise ValueError(
                    "CRAKBIT_REQUIRE_MTLS=1 but genesis contains non-HTTPS peer URLs: "
                    + ", ".join(insecure)
                )

    def _verify_peer_transport(self, peer) -> None:
        if peer.address == self.key.address:
            return
        self.transport_security.verify_peer_certificate(peer.address, peer.peer_url)

    async def _request_view_change(
        self,
        peer,
        height: int,
        from_round: int,
        to_round: int,
    ) -> ViewChange | None:
        if peer.address == self.key.address:
            return None
        try:
            self._verify_peer_transport(peer)
            async with self.transport_security.async_client(timeout=3.0) as client:
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
        peer,
        block: Block,
        phase: str,
    ) -> PhaseVote | None:
        if peer.address == self.key.address:
            return None
        endpoint = "prevote" if phase == "prevote" else "precommit"
        path = f"/internal/{endpoint}"
        try:
            self._verify_peer_transport(peer)
            async with self.transport_security.async_client(timeout=3.0) as client:
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
        async with self.transport_security.async_client(timeout=3.0) as client:
            for peer in self.genesis.validators:
                if peer.address == self.key.address:
                    continue
                try:
                    self._verify_peer_transport(peer)
                    await self._post_internal(
                        client,
                        peer,
                        "/internal/block",
                        {"block": block.to_dict()},
                    )
                except Exception:
                    pass

    async def broadcast_transaction(self, tx: Transaction) -> None:
        async with self.transport_security.async_client(timeout=2.0) as client:
            for peer in self.genesis.validators:
                if peer.address == self.key.address:
                    continue
                try:
                    self._verify_peer_transport(peer)
                    await self._post_internal(
                        client,
                        peer,
                        "/internal/transaction",
                        {"transaction": tx.to_dict()},
                    )
                except Exception:
                    pass

    async def refresh_peer_health(self) -> None:
        now = int(time.time() * 1000)
        async with self.transport_security.async_client(timeout=2.5) as client:
            for peer in self.genesis.validators:
                if peer.address == self.key.address:
                    self.peer_health[peer.address] = {
                        "name": peer.name,
                        "address": peer.address,
                        "healthy": True,
                        "authenticated_identity": True,
                        "transport_verified": True,
                        "height": self.ledger.height,
                        "round": self.current_round,
                        "last_seen_ms": now,
                        "local": True,
                    }
                    continue
                try:
                    fingerprint = self.transport_security.verify_peer_certificate(
                        peer.address, peer.peer_url
                    )
                    await self.authenticate_peer(client, peer)
                    response = await client.get(self._peer_url(peer, "/status"))
                    response.raise_for_status()
                    status = response.json()
                    self.peer_health[peer.address] = {
                        "name": peer.name,
                        "address": peer.address,
                        "healthy": True,
                        "authenticated_identity": True,
                        "transport_verified": True,
                        "certificate_pin_verified": fingerprint is not None,
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
                        "transport_verified": False,
                        "height": previous.get("height"),
                        "round": previous.get("round"),
                        "last_seen_ms": previous.get("last_seen_ms"),
                        "local": False,
                        "error": type(exc).__name__,
                    }


def create_app():
    """Create the v0.11 API while preserving v0.10 RPC/resource hardening."""

    original_node_class = secure_node_module.SecureNode
    secure_node_module.SecureNode = HardenedTransportNode
    try:
        app = create_v10_app()
    finally:
        secure_node_module.SecureNode = original_node_class

    app.title = "Crakbit Chain Devnet"
    app.version = "0.11.0a1"
    node = app.state.node

    @app.get("/transport/status")
    def transport_status() -> dict:
        return {
            "chain_id": node.genesis.chain_id,
            "validator": node.key.address,
            "ed25519_request_auth": True,
            "challenge_response_identity": True,
            **node.transport_security.status(),
            "production_ready": False,
        }

    return app


app = create_app()
