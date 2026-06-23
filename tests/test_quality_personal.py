"""Quality-scale guardrails for the personal SAJ AS1 integration."""

from __future__ import annotations

import ast
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = PROJECT_ROOT / "custom_components" / "saj_as1_modbus"

TEXT_FILES = (
    "custom_components/saj_as1_modbus/__init__.py",
    "custom_components/saj_as1_modbus/connection_manager.py",
    "custom_components/saj_as1_modbus/services.yaml",
    "custom_components/saj_as1_modbus/strings.json",
    "custom_components/saj_as1_modbus/translations/es.json",
    "README.md",
    "docs/DOCUMENTACION_TECNICA.md",
    "docs/PRUEBAS_HOME_ASSISTANT.md",
    "docs/INCIDENCIAS_SOLUCIONES.md",
    "docs/AUDITORIA_PLATINO_PERSONAL.md",
    "docs/AI_CONTEXT.md",
)


def test_service_is_registered_in_async_setup() -> None:
    """Integration-wide services should not depend on a loaded entry."""
    source = (INTEGRATION_DIR / "__init__.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    async_setup = next(
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_setup"
    )
    setup_entry = next(
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_setup_entry"
    )

    assert "_async_register_services(hass)" in ast.unparse(async_setup)
    assert "_async_register_services(hass)" not in ast.unparse(setup_entry)


def test_service_errors_are_translatable() -> None:
    """Service failures should be visible in Spanish in Home Assistant."""
    strings = json.loads((INTEGRATION_DIR / "strings.json").read_text(encoding="utf-8"))
    es_strings = json.loads(
        (INTEGRATION_DIR / "translations" / "es.json").read_text(encoding="utf-8")
    )
    expected = {
        "write_failed",
        "profile_requires_value",
        "profile_write_failed",
        "entry_required",
        "entry_not_found",
        "entry_not_loaded",
        "invalid_user_mode",
    }

    assert expected <= set(strings["exceptions"])
    assert expected <= set(es_strings["exceptions"])

    init_source = (INTEGRATION_DIR / "__init__.py").read_text(encoding="utf-8")
    for key in expected - {"write_failed"}:
        assert f'translation_key="{key}"' in init_source


def test_home_assistant_2026_6_config_flow_guardrails() -> None:
    """Avoid APIs deprecated around Home Assistant 2026.6 config flows."""
    config_flow_source = (INTEGRATION_DIR / "config_flow.py").read_text(encoding="utf-8")
    init_source = (INTEGRATION_DIR / "__init__.py").read_text(encoding="utf-8")

    assert "show_advanced_options" not in config_flow_source
    assert "async_on_unload" not in init_source
    assert "async_update_listener" not in init_source
    assert "async_update_reload_and_abort" in config_flow_source


def test_icon_translations_are_used_instead_of_static_icons() -> None:
    """Entity icons should be centralized in icons.json."""
    icons = json.loads((INTEGRATION_DIR / "icons.json").read_text(encoding="utf-8"))
    entity_icons = icons["entity"]

    assert "sensor" in entity_icons
    assert "number" in entity_icons
    assert "select" in entity_icons
    assert "binary_sensor" in entity_icons
    assert entity_icons["sensor"]["total_pv_power"]["default"]
    assert entity_icons["number"]["first_charge_power_pct"]["default"]

    for file_name in ("sensor.py", "number.py", "select.py", "binary_sensor.py"):
        source = (INTEGRATION_DIR / file_name).read_text(encoding="utf-8")
        assert "icon=" not in source


def test_personal_quality_audit_documents_exist() -> None:
    """Future sessions should have a durable context and audit trail."""
    quality = (PROJECT_ROOT / "quality_scale.yaml").read_text(encoding="utf-8")
    audit = (PROJECT_ROOT / "docs" / "AUDITORIA_PLATINO_PERSONAL.md").read_text(
        encoding="utf-8"
    )
    context = (PROJECT_ROOT / "docs" / "AI_CONTEXT.md").read_text(
        encoding="utf-8"
    )

    assert "action-setup: done" in quality
    assert "brands: done" in quality
    assert "integration-owner: done" in quality
    assert "icon-translations: done" in quality
    assert "inject-websession" in quality
    assert "Home Assistant 2026.6" in audit
    assert "pymodbus==3.11.2" in context
    assert "saj_as1_modbus.set_profile" in context


def test_text_files_do_not_contain_literal_mojibake() -> None:
    """Spanish UI/documentation files should not contain common mojibake."""
    forbidden = ("Ã", "Â", "�")
    offenders: dict[str, list[str]] = {}

    for file_name in TEXT_FILES:
        text = (PROJECT_ROOT / file_name).read_text(encoding="utf-8")
        hits = [marker for marker in forbidden if marker in text]
        if hits:
            offenders[file_name] = hits

    assert offenders == {}
