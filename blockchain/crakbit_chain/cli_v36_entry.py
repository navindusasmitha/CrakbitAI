from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import cli_v36
from .pow_handoff_v36 import PowHandoffV36Error, build_review_handoff, load_json, verify_review_handoff


def _save(path: str | Path, value: dict, overwrite: bool) -> None:
    target = Path(path)
    if target.exists() and not overwrite:
        raise ValueError(f"file exists: {target}; pass --overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="crakchain pow-handoff-v36-build")
    parser.add_argument("--key", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--package-version", default="0.36.0a1")
    parser.add_argument("--chain-id", required=True)
    parser.add_argument("--genesis-hash", required=True)
    parser.add_argument("--v35-freeze", required=True)
    parser.add_argument("--campaign-summary", required=True)
    parser.add_argument("--undo-rehearsal", required=True)
    parser.add_argument("--activation-proposal", default=None)
    parser.add_argument("--notes", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    value = build_review_handoff(
        key_path=args.key,
        source_commit=args.source_commit,
        package_version=args.package_version,
        chain_id=args.chain_id,
        genesis_hash=args.genesis_hash,
        v35_freeze=load_json(args.v35_freeze),
        campaign_summary=load_json(args.campaign_summary),
        undo_rehearsal=load_json(args.undo_rehearsal),
        activation_proposal=None if args.activation_proposal is None else load_json(args.activation_proposal),
        notes=args.notes,
    )
    _save(args.output, value, args.overwrite)
    print(json.dumps({
        "saved": args.output,
        "handoff_id": value["manifest"]["handoff_id"],
        "external_review_handoff_ready": value["manifest"]["external_review_handoff_ready"],
        "independent_security_review_completed": False,
        "production_mainnet_ready": False,
    }, indent=2))
    return 0 if value["manifest"]["external_review_handoff_ready"] else 2


def _verify(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="crakchain pow-handoff-v36-verify")
    parser.add_argument("--record", required=True)
    args = parser.parse_args(argv)
    value = verify_review_handoff(load_json(args.record))
    print(json.dumps(value, indent=2))
    return 0 if value["external_review_handoff_ready"] else 2


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "pow-handoff-v36-build":
        try:
            return _build(sys.argv[2:])
        except (PowHandoffV36Error, ValueError, OSError) as exc:
            print(json.dumps({"error": str(exc), "production_mainnet_ready": False}), file=sys.stderr)
            return 2
    if len(sys.argv) > 1 and sys.argv[1] == "pow-handoff-v36-verify":
        try:
            return _verify(sys.argv[2:])
        except (PowHandoffV36Error, ValueError, OSError) as exc:
            print(json.dumps({"error": str(exc), "production_mainnet_ready": False}), file=sys.stderr)
            return 2
    return cli_v36.main()


if __name__ == "__main__":
    raise SystemExit(main())
