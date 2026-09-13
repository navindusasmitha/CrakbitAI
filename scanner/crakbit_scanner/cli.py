from __future__ import annotations

import argparse
import json
from collections import Counter

from .engine import scan_path


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}


def _print_human(findings) -> None:
    counts = Counter(item.severity for item in findings)
    print("CRAKBIT SECURITY SCAN")
    print("=" * 24)
    print(f"Findings: {len(findings)}")

    for severity in ("critical", "high", "medium", "low", "informational"):
        if counts[severity]:
            print(f"{severity.title()}: {counts[severity]}")

    if not findings:
        print("\nNo findings from the current rule set.")
        print("This does not prove the code is secure.")
        return

    for finding in sorted(
        findings,
        key=lambda item: (SEVERITY_ORDER.get(item.severity, 99), item.file, item.line),
    ):
        print(f"\n[{finding.severity.upper()}] {finding.rule_id} — {finding.title}")
        print(f"Location: {finding.file}:{finding.line}")
        print(f"Confidence: {finding.confidence}")
        print(f"Why: {finding.description}")
        print(f"Fix: {finding.remediation}")
        if finding.evidence:
            print(f"Evidence: {finding.evidence}")

    print("\nNote: Automated analysis can produce false positives and false negatives.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crakbit AI defensive static-security scanner (early alpha)"
    )
    parser.add_argument("path", help="File or directory to scan")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output JSON")
    args = parser.parse_args()

    try:
        findings = scan_path(args.path)
    except FileNotFoundError as exc:
        parser.error(str(exc))

    if args.as_json:
        print(json.dumps([item.to_dict() for item in findings], indent=2))
    else:
        _print_human(findings)

    return 1 if any(item.severity in {"critical", "high"} for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
