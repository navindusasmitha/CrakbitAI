from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


REPRO_FORMAT = "crakbit-reproducible-build-report/1"


class ReproducibleBuildError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compare_build_outputs(
    *,
    left_root: str | Path,
    right_root: str | Path,
    relative_files: Iterable[str],
) -> dict[str, Any]:
    left = Path(left_root)
    right = Path(right_root)
    names = sorted({str(item).replace("\\", "/").lstrip("/") for item in relative_files if str(item).strip()})
    if not names:
        raise ReproducibleBuildError("at least one relative artifact path is required")

    artifacts: list[dict[str, Any]] = []
    all_match = True
    for name in names:
        if ".." in Path(name).parts:
            raise ReproducibleBuildError(f"artifact path must stay within build root: {name}")
        left_path = left / name
        right_path = right / name
        if not left_path.is_file() or not right_path.is_file():
            raise ReproducibleBuildError(f"artifact missing from one or both build roots: {name}")
        left_hash = _sha256(left_path)
        right_hash = _sha256(right_path)
        left_size = left_path.stat().st_size
        right_size = right_path.stat().st_size
        matches = left_hash == right_hash and left_size == right_size
        all_match = all_match and matches
        artifacts.append(
            {
                "path": name,
                "left_sha256": left_hash,
                "right_sha256": right_hash,
                "left_size": left_size,
                "right_size": right_size,
                "matches": matches,
            }
        )

    return {
        "format": REPRO_FORMAT,
        "reproducible": all_match,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "note": "Matching hashes show identical supplied artifacts; they do not by themselves prove independent build-environment diversity.",
        "production_mainnet_ready": False,
    }


def save_repro_report(report: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise ReproducibleBuildError(f"reproducibility report already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return target
