from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .crypto import canonical_json, sha256_hex


@dataclass(frozen=True)
class Validator:
    address: str
    public_key: str
    name: str
    peer_url: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Validator":
        return cls(str(data["address"]), str(data["public_key"]), str(data["name"]), str(data["peer_url"]))


@dataclass(frozen=True)
class Genesis:
    chain_id: str
    network_name: str
    symbol: str
    decimals: int
    max_supply: int
    block_time_ms: int
    min_fee: int
    validators: tuple[Validator, ...]
    allocations: dict[str, int]

    @classmethod
    def load(cls, path: str | Path) -> "Genesis":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        validators = tuple(Validator.from_dict(item) for item in data["validators"])
        allocations = {str(k): int(v) for k, v in data.get("allocations", {}).items()}
        max_supply = int(data["max_supply"])
        if sum(allocations.values()) > max_supply:
            raise ValueError("genesis allocations exceed max supply")
        if not validators:
            raise ValueError("genesis requires at least one validator")
        addresses = [v.address for v in validators]
        if len(set(addresses)) != len(addresses):
            raise ValueError("genesis validator addresses must be unique")
        return cls(
            chain_id=str(data["chain_id"]),
            network_name=str(data["network_name"]),
            symbol=str(data["symbol"]),
            decimals=int(data["decimals"]),
            max_supply=max_supply,
            block_time_ms=int(data.get("block_time_ms", 5000)),
            min_fee=int(data.get("min_fee", 1000)),
            validators=validators,
            allocations=allocations,
        )

    def proposer_for_height(self, height: int) -> Validator:
        return self.validators[(height - 1) % len(self.validators)]

    def validator_by_address(self, address: str) -> Validator | None:
        return next((v for v in self.validators if v.address == address), None)

    @property
    def quorum_size(self) -> int:
        """Return the >2/3 commit threshold for the configured validator set."""
        return (2 * len(self.validators)) // 3 + 1

    def fingerprint(self) -> str:
        return sha256_hex(canonical_json({
            "chain_id": self.chain_id,
            "validators": [v.__dict__ for v in self.validators],
            "allocations": self.allocations,
            "max_supply": self.max_supply,
        }))
