from __future__ import annotations

from . import cli_v27
from . import mainnet_candidate_v27 as core
from .mainnet_candidate_gate_v27 import build_candidate_identity


def main() -> int:
    # Harden both the direct CLI command and the final-gate internal identity
    # recomputation with exact cross-artifact source/genesis/review bindings.
    cli_v27.build_candidate_identity = build_candidate_identity
    core.build_candidate_identity = build_candidate_identity
    return int(cli_v27.main())


if __name__ == "__main__":
    raise SystemExit(main())
