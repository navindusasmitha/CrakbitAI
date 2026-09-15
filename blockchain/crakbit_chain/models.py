from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .crypto import address_from_public_key, canonical_json, sha256_hex, verify_signature

ATOMIC_UNITS = 100_000_000
CONSENSUS_PHASES = {"prevote", "precommit"}


def merkle_root(items: list[str]) -> str:
    if not items:
        return sha256_hex(b"")
    layer = [bytes.fromhex(item) for item in items]
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [bytes.fromhex(sha256_hex(layer[i] + layer[i + 1])) for i in range(0, len(layer), 2)]
    return layer[0].hex()


@dataclass
class Transaction:
    chain_id: str
    sender: str
    recipient: str
    amount: int
    fee: int
    nonce: int
    public_key: str
    memo: str = ""
    signature: str = ""

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": int(self.amount),
            "fee": int(self.fee),
            "nonce": int(self.nonce),
            "public_key": self.public_key,
            "memo": self.memo,
        }

    def signing_bytes(self) -> bytes:
        return canonical_json(self.unsigned_dict())

    @property
    def txid(self) -> str:
        return sha256_hex(canonical_json(self.to_dict()))

    def verify_signature(self) -> bool:
        if self.sender != address_from_public_key(self.public_key):
            return False
        return bool(self.signature) and verify_signature(self.public_key, self.signing_bytes(), self.signature)

    def to_dict(self) -> dict[str, Any]:
        data = self.unsigned_dict()
        data["signature"] = self.signature
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transaction":
        return cls(
            chain_id=str(data["chain_id"]),
            sender=str(data["sender"]),
            recipient=str(data["recipient"]),
            amount=int(data["amount"]),
            fee=int(data.get("fee", 0)),
            nonce=int(data["nonce"]),
            public_key=str(data["public_key"]),
            memo=str(data.get("memo", "")),
            signature=str(data.get("signature", "")),
        )


@dataclass
class CommitVote:
    """Legacy v0.2-v0.4 commit vote kept for parsing old devnet fixtures."""

    chain_id: str
    height: int
    round: int
    block_hash: str
    voter: str
    public_key: str
    signature: str = ""

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "height": int(self.height),
            "round": int(self.round),
            "block_hash": self.block_hash,
            "voter": self.voter,
            "public_key": self.public_key,
        }

    def signing_bytes(self) -> bytes:
        return canonical_json(self.unsigned_dict())

    def verify_signature(self) -> bool:
        if self.voter != address_from_public_key(self.public_key):
            return False
        return bool(self.signature) and verify_signature(self.public_key, self.signing_bytes(), self.signature)

    def to_dict(self) -> dict[str, Any]:
        data = self.unsigned_dict()
        data["signature"] = self.signature
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CommitVote":
        return cls(
            chain_id=str(data["chain_id"]),
            height=int(data["height"]),
            round=int(data.get("round", 0)),
            block_hash=str(data["block_hash"]),
            voter=str(data["voter"]),
            public_key=str(data["public_key"]),
            signature=str(data.get("signature", "")),
        )


@dataclass
class PhaseVote:
    """Signed v0.5 consensus vote for the prevote or precommit phase."""

    chain_id: str
    height: int
    round: int
    phase: str
    block_hash: str
    voter: str
    public_key: str
    signature: str = ""

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "height": int(self.height),
            "round": int(self.round),
            "phase": self.phase,
            "block_hash": self.block_hash,
            "voter": self.voter,
            "public_key": self.public_key,
        }

    def signing_bytes(self) -> bytes:
        return canonical_json(self.unsigned_dict())

    def verify_signature(self) -> bool:
        if self.phase not in CONSENSUS_PHASES:
            return False
        if self.voter != address_from_public_key(self.public_key):
            return False
        return bool(self.signature) and verify_signature(self.public_key, self.signing_bytes(), self.signature)

    def to_dict(self) -> dict[str, Any]:
        data = self.unsigned_dict()
        data["signature"] = self.signature
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PhaseVote":
        phase = str(data["phase"])
        if phase not in CONSENSUS_PHASES:
            raise ValueError("invalid consensus vote phase")
        return cls(
            chain_id=str(data["chain_id"]),
            height=int(data["height"]),
            round=int(data.get("round", 0)),
            phase=phase,
            block_hash=str(data["block_hash"]),
            voter=str(data["voter"]),
            public_key=str(data["public_key"]),
            signature=str(data.get("signature", "")),
        )


@dataclass
class ViewChange:
    """Signed validator message requesting a move to a later consensus round."""

    chain_id: str
    height: int
    from_round: int
    to_round: int
    voter: str
    public_key: str
    locked_round: int = -1
    locked_block_hash: str = ""
    signature: str = ""

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "height": int(self.height),
            "from_round": int(self.from_round),
            "to_round": int(self.to_round),
            "voter": self.voter,
            "public_key": self.public_key,
            "locked_round": int(self.locked_round),
            "locked_block_hash": self.locked_block_hash,
        }

    def signing_bytes(self) -> bytes:
        return canonical_json(self.unsigned_dict())

    def verify_signature(self) -> bool:
        if self.voter != address_from_public_key(self.public_key):
            return False
        return bool(self.signature) and verify_signature(self.public_key, self.signing_bytes(), self.signature)

    def to_dict(self) -> dict[str, Any]:
        data = self.unsigned_dict()
        data["signature"] = self.signature
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ViewChange":
        return cls(
            chain_id=str(data["chain_id"]),
            height=int(data["height"]),
            from_round=int(data["from_round"]),
            to_round=int(data["to_round"]),
            voter=str(data["voter"]),
            public_key=str(data["public_key"]),
            locked_round=int(data.get("locked_round", -1)),
            locked_block_hash=str(data.get("locked_block_hash", "")),
            signature=str(data.get("signature", "")),
        )


@dataclass
class Block:
    chain_id: str
    height: int
    previous_hash: str
    timestamp: int
    proposer: str
    proposer_public_key: str
    transactions: list[Transaction] = field(default_factory=list)
    tx_root: str = ""
    state_root: str = ""
    round: int = 0
    signature: str = ""
    commit_votes: list[CommitVote] = field(default_factory=list)
    view_changes: list[ViewChange] = field(default_factory=list)
    prevote_votes: list[PhaseVote] = field(default_factory=list)
    precommit_votes: list[PhaseVote] = field(default_factory=list)

    def unsigned_dict(self) -> dict[str, Any]:
        txids = [tx.txid for tx in self.transactions]
        return {
            "chain_id": self.chain_id,
            "height": int(self.height),
            "previous_hash": self.previous_hash,
            "timestamp": int(self.timestamp),
            "proposer": self.proposer,
            "proposer_public_key": self.proposer_public_key,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "tx_root": self.tx_root or merkle_root(txids),
            "state_root": self.state_root,
            "round": int(self.round),
        }

    def signing_bytes(self) -> bytes:
        return canonical_json(self.unsigned_dict())

    @property
    def block_hash(self) -> str:
        payload = self.unsigned_dict()
        payload["signature"] = self.signature
        return sha256_hex(canonical_json(payload))

    def verify_signature(self) -> bool:
        if self.proposer != address_from_public_key(self.proposer_public_key):
            return False
        return bool(self.signature) and verify_signature(
            self.proposer_public_key, self.signing_bytes(), self.signature
        )

    def to_dict(self) -> dict[str, Any]:
        data = self.unsigned_dict()
        data["signature"] = self.signature
        data["hash"] = self.block_hash
        data["commit_votes"] = [vote.to_dict() for vote in self.commit_votes]
        data["view_changes"] = [change.to_dict() for change in self.view_changes]
        data["prevote_votes"] = [vote.to_dict() for vote in self.prevote_votes]
        data["precommit_votes"] = [vote.to_dict() for vote in self.precommit_votes]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Block":
        return cls(
            chain_id=str(data["chain_id"]),
            height=int(data["height"]),
            previous_hash=str(data["previous_hash"]),
            timestamp=int(data["timestamp"]),
            proposer=str(data["proposer"]),
            proposer_public_key=str(data["proposer_public_key"]),
            transactions=[Transaction.from_dict(item) for item in data.get("transactions", [])],
            tx_root=str(data.get("tx_root", "")),
            state_root=str(data.get("state_root", "")),
            round=int(data.get("round", 0)),
            signature=str(data.get("signature", "")),
            commit_votes=[CommitVote.from_dict(item) for item in data.get("commit_votes", [])],
            view_changes=[ViewChange.from_dict(item) for item in data.get("view_changes", [])],
            prevote_votes=[PhaseVote.from_dict(item) for item in data.get("prevote_votes", [])],
            precommit_votes=[PhaseVote.from_dict(item) for item in data.get("precommit_votes", [])],
        )


def now_ms() -> int:
    return int(time.time() * 1000)
