from __future__ import annotations

import hashlib
import json
import re
import tomllib
from importlib import metadata
from pathlib import Path
from typing import Any


SBOM_FORMAT = "CycloneDX"
SBOM_SPEC_VERSION = "1.5"


class SbomError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dependency_name(spec: str) -> str:
    match = re.match(r"^\s*([A-Za-z0-9_.-]+)", spec)
    if not match:
        raise SbomError(f"unable to parse dependency: {spec}")
    return match.group(1)


def _installed_version(name: str) -> str | None:
    candidates = {name, name.replace("_", "-"), name.replace("-", "_")}
    for candidate in candidates:
        try:
            return metadata.version(candidate)
        except metadata.PackageNotFoundError:
            continue
    return None


def _parse_go_requirements(path: Path) -> list[tuple[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    result: list[tuple[str, str]] = []
    in_block = False
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if line == "require (":
            in_block = True
            continue
        if in_block and line == ")":
            in_block = False
            continue
        if line.startswith("require "):
            line = line[len("require ") :].strip()
        elif not in_block:
            continue
        parts = line.split()
        if len(parts) >= 2:
            result.append((parts[0], parts[1]))
    return sorted(set(result))


def build_sbom(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    blockchain = root / "blockchain"
    if not blockchain.is_dir() and (root / "pyproject.toml").is_file():
        blockchain = root
        root = root.parent
    pyproject = blockchain / "pyproject.toml"
    go_mod = blockchain / "cometbft-app" / "go.mod"
    go_sum = blockchain / "cometbft-app" / "go.sum"
    if not pyproject.is_file() or not go_mod.is_file():
        raise SbomError("expected blockchain/pyproject.toml and blockchain/cometbft-app/go.mod")

    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]
    components: list[dict[str, Any]] = []
    for spec in project.get("dependencies", []):
        name = _dependency_name(str(spec))
        resolved = _installed_version(name)
        component: dict[str, Any] = {
            "type": "library",
            "name": name,
            "properties": [{"name": "crakbit.constraint", "value": str(spec)}],
        }
        if resolved:
            component["version"] = resolved
        components.append(component)

    for module, version in _parse_go_requirements(go_mod):
        components.append(
            {
                "type": "library",
                "name": module,
                "version": version,
                "properties": [{"name": "crakbit.ecosystem", "value": "go"}],
            }
        )

    components.sort(key=lambda item: (item["name"], item.get("version", "")))
    inputs = [pyproject, go_mod]
    if go_sum.is_file():
        inputs.append(go_sum)
    return {
        "bomFormat": SBOM_FORMAT,
        "specVersion": SBOM_SPEC_VERSION,
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": str(project.get("name", "crakbit-chain")),
                "version": str(project.get("version", "")),
            },
            "properties": [
                {
                    "name": "crakbit.scope",
                    "value": "direct Python runtime dependencies plus direct Go module requirements",
                },
                {
                    "name": "crakbit.transitive_completeness",
                    "value": "false",
                },
            ],
        },
        "components": components,
        "properties": [
            {
                "name": f"crakbit.input_sha256.{path.relative_to(blockchain).as_posix()}",
                "value": _sha256(path),
            }
            for path in inputs
        ],
    }


def save_sbom(sbom: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise SbomError(f"SBOM already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(sbom, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return target
