from __future__ import annotations

from . import cli_v26
from .remediation_gate_v26 import build_remediation_gate


def main() -> int:
    # v0.26 permits the final candidate commit to differ from the initially
    # reviewed commit, but requires high/critical retests against the exact
    # candidate commit being re-frozen.
    cli_v26.build_remediation_gate = build_remediation_gate
    return int(cli_v26.main())


if __name__ == "__main__":
    raise SystemExit(main())
