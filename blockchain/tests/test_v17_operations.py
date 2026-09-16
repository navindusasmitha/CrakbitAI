from __future__ import annotations

import pytest

from crakbit_chain.fault_campaign import campaign_plan, parse_campaign


def test_fault_campaign_is_dry_run_by_default_and_preserves_argv():
    spec = {
        "name": "local validator recovery",
        "steps": [
            {
                "name": "restart-validator-2",
                "command": ["docker", "stop", "validator-2"],
                "recovery_command": ["docker", "start", "validator-2"],
                "settle_seconds": 0,
                "recovery_seconds": 0,
            }
        ],
    }
    plan = campaign_plan(spec)
    assert plan["safe_default"] == "dry-run"
    assert plan["steps"][0]["command"] == ["docker", "stop", "validator-2"]
    assert plan["steps"][0]["recovery_command"] == ["docker", "start", "validator-2"]


def test_fault_campaign_requires_recovery_command():
    with pytest.raises(ValueError):
        parse_campaign({"steps": [{"name": "unsafe", "command": ["false"]}]})
