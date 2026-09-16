from __future__ import annotations

import json

import pytest

from crakbit_chain.transport_security import (
    TransportSecurityConfig,
    TransportSecurityError,
    load_pin_map,
)


def test_transport_config_allows_default_plain_devnet():
    config = TransportSecurityConfig()
    config.validate()
    assert config.mtls_configured is False
    assert config.status()["require_mtls"] is False


def test_transport_config_rejects_partial_mtls_files(tmp_path):
    ca = tmp_path / "ca.pem"
    ca.write_text("not-a-real-ca", encoding="utf-8")
    config = TransportSecurityConfig(ca_file=str(ca))
    with pytest.raises(TransportSecurityError, match="requires CRAKBIT_MTLS_CA"):
        config.validate()


def test_peer_pin_map_normalizes_colons_and_case(tmp_path):
    pin_file = tmp_path / "pins.json"
    raw = "AA:" + ":".join(["bb"] * 31)
    pin_file.write_text(json.dumps({"crk1validator": raw}), encoding="utf-8")
    pins = load_pin_map(pin_file)
    assert pins["crk1validator"] == "aa" + ("bb" * 31)
    assert len(pins["crk1validator"]) == 64


def test_peer_pin_map_rejects_invalid_fingerprint(tmp_path):
    pin_file = tmp_path / "pins.json"
    pin_file.write_text(json.dumps({"crk1validator": "xyz"}), encoding="utf-8")
    with pytest.raises(TransportSecurityError, match="invalid SHA-256"):
        load_pin_map(pin_file)


def test_required_peer_pins_need_nonempty_map(tmp_path):
    pin_file = tmp_path / "pins.json"
    pin_file.write_text("{}", encoding="utf-8")
    config = TransportSecurityConfig(require_peer_pins=True, pin_file=str(pin_file))
    with pytest.raises(TransportSecurityError, match="pin map is empty"):
        config.validate()


def test_require_mtls_rejects_http_peer_url():
    config = TransportSecurityConfig(require_mtls=True)
    # URL policy can be tested independently of file validation.
    with pytest.raises(TransportSecurityError, match="requires HTTPS"):
        config.validate_peer_url("http://validator.example:9101")
