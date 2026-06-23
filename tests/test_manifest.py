"""Manifest-level checks for the custom integration."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = PROJECT_ROOT / "custom_components" / "saj_as1_modbus"


def test_manifest_pins_home_assistant_pymodbus_version() -> None:
    """The integration uses the PyModbus version bundled by Home Assistant."""
    manifest = json.loads((INTEGRATION_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert "pymodbus==3.11.2" in manifest["requirements"]
    assert manifest["config_flow"] is True
    assert manifest["iot_class"] == "local_polling"
    assert manifest["documentation"] == (
        "https://github.com/mactron254/home-assistant-saj-as1-modbus"
    )
    assert manifest["issue_tracker"] == (
        "https://github.com/mactron254/home-assistant-saj-as1-modbus/issues"
    )
    assert manifest["codeowners"] == ["@mactron254"]
    assert manifest["version"] == "3.1.0"
    assert "pymodbus" not in manifest.get("loggers", [])


def test_scan_interval_is_not_user_configurable() -> None:
    """Polling cadence is internal, not exposed in config/options flows."""
    assert (
        "scan_interval"
        not in (INTEGRATION_DIR / "config_flow.py").read_text(encoding="utf-8")
    )
