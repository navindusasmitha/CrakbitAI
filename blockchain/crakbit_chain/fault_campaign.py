from __future__ import annotations

import json
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .testnet_health import check_inventory


CAMPAIGN_FORMAT = "crakbit-testnet-fault-campaign/1"
MAX_CAPTURE_CHARS = 16_000


@dataclass(frozen=True)
class CampaignStep:
    name: str
    command: list[str]
    recovery_command: list[str]
    settle_seconds: float = 2.0
    recovery_seconds: float = 2.0


def _command(value: Any) -> list[str]:
    if isinstance(value, list) and value and all(isinstance(item, str) and item for item in value):
        return list(value)
    if isinstance(value, str) and value.strip():
        return shlex.split(value, posix=True)
    raise ValueError("campaign command must be a non-empty string or list of arguments")


def parse_campaign(spec: dict[str, Any]) -> list[CampaignStep]:
    raw_steps = spec.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("campaign must contain a non-empty steps list")
    steps: list[CampaignStep] = []
    names: set[str] = set()
    for index, raw in enumerate(raw_steps):
        if not isinstance(raw, dict):
            raise ValueError("each campaign step must be an object")
        name = str(raw.get("name") or f"step-{index + 1}").strip()
        if not name or name in names:
            raise ValueError("campaign step names must be unique and non-empty")
        names.add(name)
        command = _command(raw.get("command"))
        recovery = _command(raw.get("recovery_command"))
        settle = float(raw.get("settle_seconds", 2))
        recovery_seconds = float(raw.get("recovery_seconds", 2))
        if settle < 0 or settle > 3600 or recovery_seconds < 0 or recovery_seconds > 3600:
            raise ValueError("campaign settle/recovery waits must be between 0 and 3600 seconds")
        steps.append(
            CampaignStep(
                name=name,
                command=command,
                recovery_command=recovery,
                settle_seconds=settle,
                recovery_seconds=recovery_seconds,
            )
        )
    return steps


def campaign_plan(spec: dict[str, Any]) -> dict[str, Any]:
    steps = parse_campaign(spec)
    return {
        "format": CAMPAIGN_FORMAT,
        "name": str(spec.get("name", "Crakbit fault campaign")),
        "safe_default": "dry-run",
        "steps": [
            {
                "name": step.name,
                "command": step.command,
                "recovery_command": step.recovery_command,
                "settle_seconds": step.settle_seconds,
                "recovery_seconds": step.recovery_seconds,
            }
            for step in steps
        ],
    }


def _run_command(command: list[str], *, timeout_seconds: float) -> dict[str, Any]:
    started = time.time()
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout[-MAX_CAPTURE_CHARS:],
            "stderr": completed.stderr[-MAX_CAPTURE_CHARS:],
            "duration_ms": int((time.time() - started) * 1000),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": None,
            "stdout": str(exc.stdout or "")[-MAX_CAPTURE_CHARS:],
            "stderr": str(exc.stderr or "")[-MAX_CAPTURE_CHARS:],
            "duration_ms": int((time.time() - started) * 1000),
            "timed_out": True,
        }


def run_campaign(
    *,
    inventory: dict[str, Any],
    spec: dict[str, Any],
    execute: bool = False,
    health_timeout_seconds: float = 5.0,
    max_height_spread: int = 2,
    command_timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    steps = parse_campaign(spec)
    evidence: dict[str, Any] = {
        "format": CAMPAIGN_FORMAT,
        "name": str(spec.get("name", "Crakbit fault campaign")),
        "started_at_ms": int(time.time() * 1000),
        "execute": bool(execute),
        "production_mainnet_evidence": False,
        "baseline": check_inventory(
            inventory,
            timeout_seconds=health_timeout_seconds,
            max_height_spread=max_height_spread,
        ),
        "steps": [],
    }
    if not execute:
        evidence["plan"] = campaign_plan(spec)
        evidence["completed_at_ms"] = int(time.time() * 1000)
        return evidence

    for step in steps:
        item: dict[str, Any] = {
            "name": step.name,
            "command": step.command,
            "recovery_command": step.recovery_command,
            "before": check_inventory(
                inventory,
                timeout_seconds=health_timeout_seconds,
                max_height_spread=max_height_spread,
            ),
        }
        item["fault_command"] = _run_command(step.command, timeout_seconds=command_timeout_seconds)
        if step.settle_seconds:
            time.sleep(step.settle_seconds)
        item["during"] = check_inventory(
            inventory,
            timeout_seconds=health_timeout_seconds,
            max_height_spread=max_height_spread,
        )
        # Recovery is attempted even when the fault command fails, because operator cleanup is
        # more important than treating the campaign as an all-or-nothing test.
        item["recovery_command_result"] = _run_command(
            step.recovery_command,
            timeout_seconds=command_timeout_seconds,
        )
        if step.recovery_seconds:
            time.sleep(step.recovery_seconds)
        item["after"] = check_inventory(
            inventory,
            timeout_seconds=health_timeout_seconds,
            max_height_spread=max_height_spread,
        )
        item["recovered_healthy"] = bool(item["after"].get("healthy"))
        evidence["steps"].append(item)

    evidence["final"] = check_inventory(
        inventory,
        timeout_seconds=health_timeout_seconds,
        max_height_spread=max_height_spread,
    )
    evidence["completed_at_ms"] = int(time.time() * 1000)
    evidence["all_steps_recovered"] = all(
        bool(item.get("recovered_healthy")) for item in evidence["steps"]
    )
    return evidence


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(payload: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> Path:
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"evidence output already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return target
