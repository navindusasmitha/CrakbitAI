from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import Block
from .storage import Ledger


class FinalizedBlockExecution(Protocol):
    """Minimal boundary a future reviewed consensus core can call into."""

    def validate_finalized_block(self, block: Block) -> None: ...
    def apply_finalized_block(self, block: Block) -> None: ...
    def status(self) -> dict: ...


@dataclass
class LedgerExecutionAdapter:
    ledger: Ledger

    def validate_finalized_block(self, block: Block) -> None:
        self.ledger.validate_block_proposal(block)
        self.ledger.validate_prevote_certificate(block)
        self.ledger.validate_precommit_certificate(block)

    def apply_finalized_block(self, block: Block) -> None:
        self.ledger.apply_block(block)

    def status(self) -> dict:
        return {
            "adapter": "sqlite-ledger-execution-v1",
            "height": self.ledger.height,
            "last_hash": self.ledger.last_hash,
            "consensus_owns_execution": False,
            "reviewed_bft_core_integrated": False,
            "migration_boundary_ready": True,
        }
