from pathlib import Path

from crakbit_scanner.engine import scan_path


def test_detects_python_eval(tmp_path: Path):
    sample = tmp_path / "sample.py"
    sample.write_text("value = eval(user_input)\n", encoding="utf-8")

    findings = scan_path(tmp_path)

    assert any(item.rule_id == "CRAK-PY-002" for item in findings)


def test_redacts_possible_secret(tmp_path: Path):
    sample = tmp_path / "config.py"
    sample.write_text('api_key = "EXAMPLE_NOT_A_REAL_SECRET"\n', encoding="utf-8")

    findings = scan_path(tmp_path)
    secret = next(item for item in findings if item.rule_id == "CRAK-SEC-001")

    assert secret.evidence == "[REDACTED: possible secret]"
    assert "EXAMPLE_NOT_A_REAL_SECRET" not in secret.evidence
