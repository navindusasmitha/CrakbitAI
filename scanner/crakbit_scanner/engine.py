from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .models import Finding
from .rules import RULES, Rule


DEFAULT_EXTENSIONS = frozenset({ext for rule in RULES for ext in rule.extensions})
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "target", "__pycache__"}
MAX_FILE_BYTES = 1_000_000


def _iter_files(target: Path) -> Iterable[Path]:
    if target.is_file():
        yield target
        return

    for path in target.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in DEFAULT_EXTENSIONS:
            continue
        yield path


def _safe_evidence(line: str, rule: Rule) -> str:
    if rule.redact_evidence:
        return "[REDACTED: possible secret]"
    cleaned = line.strip()
    return cleaned[:180] + ("…" if len(cleaned) > 180 else "")


def scan_path(path: str | Path) -> list[Finding]:
    target = Path(path).expanduser().resolve()
    if not target.exists():
        raise FileNotFoundError(f"Path does not exist: {target}")

    findings: list[Finding] = []

    for file_path in _iter_files(target):
        try:
            if file_path.stat().st_size > MAX_FILE_BYTES:
                continue
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        extension = file_path.suffix.lower()
        for line_number, line in enumerate(text.splitlines(), start=1):
            for rule in RULES:
                if extension not in rule.extensions:
                    continue
                if not rule.pattern.search(line):
                    continue

                try:
                    display_path = str(file_path.relative_to(target if target.is_dir() else target.parent))
                except ValueError:
                    display_path = str(file_path)

                findings.append(
                    Finding(
                        rule_id=rule.rule_id,
                        title=rule.title,
                        severity=rule.severity,
                        confidence=rule.confidence,
                        file=display_path,
                        line=line_number,
                        description=rule.description,
                        remediation=rule.remediation,
                        evidence=_safe_evidence(line, rule),
                    )
                )

    return findings
