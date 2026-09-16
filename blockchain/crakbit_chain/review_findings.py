from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .crypto import canonical_json, sha256_hex


MATRIX_FORMAT = "crakbit-review-remediation-matrix/1"
SEVERITIES = {"info", "low", "medium", "high", "critical"}
STATUSES = {"open", "accepted", "remediated", "not_applicable"}


class ReviewFindingsError(ValueError):
    pass


def _valid_commit(value: str) -> bool:
    value = str(value).strip().lower()
    return len(value) in {40, 64} and all(ch in "0123456789abcdef" for ch in value)


def _normalize_finding(raw: dict[str, Any], source_name: str) -> dict[str, Any]:
    finding_id = str(raw.get("id", "")).strip()
    title = str(raw.get("title", "")).strip()
    severity = str(raw.get("severity", "")).strip().lower()
    status = str(raw.get("status", "open")).strip().lower()
    if not finding_id or not title:
        raise ReviewFindingsError(f"finding in {source_name} requires id and title")
    if severity not in SEVERITIES:
        raise ReviewFindingsError(f"finding {finding_id} has unsupported severity: {severity}")
    if status not in STATUSES:
        raise ReviewFindingsError(f"finding {finding_id} has unsupported status: {status}")
    regression_tests = sorted({str(item).strip() for item in raw.get("regression_tests", []) if str(item).strip()})
    evidence = sorted({str(item).strip() for item in raw.get("evidence", []) if str(item).strip()})
    return {
        "id": finding_id,
        "title": title,
        "severity": severity,
        "status": status,
        "regression_tests": regression_tests,
        "evidence": evidence,
        "source": source_name,
    }


def _load_findings(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        raise ReviewFindingsError(f"finding file not found: {source}")
    data = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("findings")
    if not isinstance(data, list):
        raise ReviewFindingsError(f"finding file must contain a list or {{'findings': [...]}}: {source}")
    return [_normalize_finding(item, source.name) for item in data if isinstance(item, dict)]


def build_remediation_matrix(
    *,
    source_commit: str,
    finding_paths: Iterable[str | Path],
) -> dict[str, Any]:
    commit = str(source_commit).strip().lower()
    if not _valid_commit(commit):
        raise ReviewFindingsError("source_commit must be an exact hexadecimal Git commit SHA")

    findings: list[dict[str, Any]] = []
    seen: set[str] = set()
    source_files: list[dict[str, Any]] = []
    for raw_path in finding_paths:
        path = Path(raw_path)
        if not path.is_file():
            raise ReviewFindingsError(f"finding file not found: {path}")
        payload = path.read_bytes()
        source_files.append({"name": path.name, "sha256": sha256_hex(payload), "size": len(payload)})
        for finding in _load_findings(path):
            if finding["id"] in seen:
                raise ReviewFindingsError(f"duplicate finding id: {finding['id']}")
            seen.add(finding["id"])
            findings.append(finding)

    findings.sort(key=lambda item: (item["severity"], item["id"]))
    counts = Counter(item["severity"] for item in findings)
    status_counts = Counter(item["status"] for item in findings)
    blockers = [
        item["id"]
        for item in findings
        if item["severity"] in {"high", "critical"}
        and item["status"] not in {"remediated", "not_applicable"}
    ]
    missing_regression = [
        item["id"]
        for item in findings
        if item["severity"] in {"high", "critical"}
        and item["status"] == "remediated"
        and not item["regression_tests"]
    ]

    matrix = {
        "format": MATRIX_FORMAT,
        "source_commit": commit,
        "source_files": sorted(source_files, key=lambda item: item["name"]),
        "findings": findings,
        "summary": {
            "total": len(findings),
            "severity_counts": {name: int(counts.get(name, 0)) for name in sorted(SEVERITIES)},
            "status_counts": {name: int(status_counts.get(name, 0)) for name in sorted(STATUSES)},
            "high_critical_blockers": sorted(blockers),
            "high_critical_missing_regression_tests": sorted(missing_regression),
            "high_critical_release_gate_clear": not blockers and not missing_regression,
            "production_mainnet_ready": False,
        },
    }
    matrix["matrix_sha256"] = sha256_hex(canonical_json(matrix))
    return matrix


def verify_remediation_matrix(matrix: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(matrix, dict) or matrix.get("format") != MATRIX_FORMAT:
        raise ReviewFindingsError("unsupported remediation matrix format")
    provided = str(matrix.get("matrix_sha256", ""))
    unsigned = dict(matrix)
    unsigned.pop("matrix_sha256", None)
    expected = sha256_hex(canonical_json(unsigned))
    if provided != expected:
        raise ReviewFindingsError("remediation matrix hash mismatch")
    if not _valid_commit(str(matrix.get("source_commit", ""))):
        raise ReviewFindingsError("remediation matrix source commit is invalid")

    summary = matrix.get("summary")
    if not isinstance(summary, dict):
        raise ReviewFindingsError("remediation matrix summary is missing")
    blockers = list(summary.get("high_critical_blockers", []))
    missing = list(summary.get("high_critical_missing_regression_tests", []))
    return {
        "valid": True,
        "source_commit": matrix["source_commit"],
        "finding_count": len(matrix.get("findings", [])),
        "high_critical_release_gate_clear": not blockers and not missing,
        "high_critical_blockers": blockers,
        "high_critical_missing_regression_tests": missing,
        "production_mainnet_ready": False,
    }


def save_remediation_matrix(matrix: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise ReviewFindingsError(f"remediation matrix already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    return target
