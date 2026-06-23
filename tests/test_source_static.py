"""Static source checks for coordinator and PyModbus API use."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = PROJECT_ROOT / "custom_components" / "saj_as1_modbus"


def test_coordinator_has_no_duplicate_methods() -> None:
    """Python should not silently override coordinator methods."""
    tree = ast.parse((INTEGRATION_DIR / "coordinator.py").read_text(encoding="utf-8"))
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "SAJModbusCoordinator"
    )
    methods: dict[str, list[int]] = {}
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            methods.setdefault(node.name, []).append(node.lineno)

    duplicates = {name: lines for name, lines in methods.items() if len(lines) > 1}
    assert duplicates == {}


def test_pymodbus_calls_use_device_id_keyword() -> None:
    """The integration should not use the removed slave keyword."""
    checked_files = ("coordinator.py", "connection_manager.py")
    for file_name in checked_files:
        source = (INTEGRATION_DIR / file_name).read_text(encoding="utf-8")
        assert "slave=" not in source
        assert "device_id=" in source


def test_connection_close_is_not_awaited() -> None:
    """PyModbus documents close() as a synchronous method."""
    source = (INTEGRATION_DIR / "connection_manager.py").read_text(encoding="utf-8")
    assert "await client.close()" not in source
    assert "client.close()" in source


def test_pymodbus_auto_reconnect_is_disabled() -> None:
    """The integration controls reconnects to avoid PyModbus reconnect loops."""
    source = (INTEGRATION_DIR / "connection_manager.py").read_text(encoding="utf-8")
    assert "reconnect_delay=0" in source
    assert "reconnect_delay_max=0" in source


def test_aio3_sensitive_registers_use_retries_and_socket_close() -> None:
    """AIO3 WiFi sensitive registers should not hammer a stale connection."""
    coordinator_source = (INTEGRATION_DIR / "coordinator.py").read_text(encoding="utf-8")
    const_source = (INTEGRATION_DIR / "const.py").read_text(encoding="utf-8")

    assert "CONFIG_KEYS" in const_source
    assert "SCAN_INTERVAL_CONFIG" in const_source
    assert "_read_config" in coordinator_source
    assert "_config_cache" in coordinator_source
    assert "AIO3_SENSITIVE_RETRIES" in const_source
    assert "_read_sensitive_register" in coordinator_source
    assert "REGISTER_CHARGE_POWER_PCT" in coordinator_source
    assert "REGISTER_DISCHARGE_POWER_PCT" in coordinator_source
    assert "REGISTER_USER_MODE" in coordinator_source
    assert "await self.connection.close()" in coordinator_source
    assert "await self.connection.reconnect()" not in coordinator_source


def test_aio3_writes_are_serialized_and_patient() -> None:
    """Rapid HA service calls should be queued for the AIO3 WiFi bridge."""
    coordinator_source = (INTEGRATION_DIR / "coordinator.py").read_text(encoding="utf-8")
    const_source = (INTEGRATION_DIR / "const.py").read_text(encoding="utf-8")
    connection_source = (INTEGRATION_DIR / "connection_manager.py").read_text(
        encoding="utf-8"
    )

    assert "self._write_lock = asyncio.Lock()" in coordinator_source
    assert "self._write_batch_lock = asyncio.Lock()" in coordinator_source
    assert "self._write_batch_values" in coordinator_source
    assert "self._pending_writes" in coordinator_source
    assert "async with self._write_lock" in coordinator_source
    assert "_flush_write_batch" in coordinator_source
    assert "_ordered_write_addresses" in coordinator_source
    assert "_write_register_with_recovery" in coordinator_source
    assert "AIO3_WRITE_BATCH_DELAY" in const_source
    assert "AIO3_WRITE_RETRY_DELAY" in const_source
    assert "async with self._io_lock" in connection_source


def test_profile_service_exists_for_automation_batches() -> None:
    """Automations should be able to send one complete profile write."""
    init_source = (INTEGRATION_DIR / "__init__.py").read_text(encoding="utf-8")
    coordinator_source = (INTEGRATION_DIR / "coordinator.py").read_text(encoding="utf-8")
    services_source = (INTEGRATION_DIR / "services.yaml").read_text(encoding="utf-8")

    assert "SERVICE_SET_PROFILE" in init_source
    assert "hass.services.async_register" in init_source
    assert "async_set_profile" in coordinator_source
    assert "set_profile:" in services_source
    assert "charge_power_pct" in services_source
    assert "discharge_power_pct" in services_source
    assert "user_mode" in services_source


def test_low_energy_bucket_is_read_as_one_block() -> None:
    """LOW polling should not spend six Modbus transactions on accumulated data."""
    coordinator_source = (INTEGRATION_DIR / "coordinator.py").read_text(encoding="utf-8")

    assert "LOW_ENERGY_BLOCK_START" in coordinator_source
    assert "LOW_ENERGY_BLOCK_COUNT" in coordinator_source
    assert "read_registers(address, 2)" not in coordinator_source
    assert "address - LOW_ENERGY_BLOCK_START" in coordinator_source


def test_bucket_unavailable_warning_is_not_spammed() -> None:
    """Bucket outage warnings should only be emitted on the threshold crossing."""
    coordinator_source = (INTEGRATION_DIR / "coordinator.py").read_text(encoding="utf-8")

    assert "failures == MAX_FAILURES_BEFORE_UNAVAILABLE" in coordinator_source
    assert "bucket still unavailable" in coordinator_source
    assert "bucket recovered" in coordinator_source


def test_diagnostics_include_bucket_metrics_and_circuit_breaker() -> None:
    """Diagnostics should expose enough polling detail without log spam."""
    coordinator_source = (INTEGRATION_DIR / "coordinator.py").read_text(encoding="utf-8")
    diagnostics_source = (INTEGRATION_DIR / "diagnostics.py").read_text(
        encoding="utf-8"
    )
    const_source = (INTEGRATION_DIR / "const.py").read_text(encoding="utf-8")

    assert "AIO3_CIRCUIT_BREAKER_FAILURES" in const_source
    assert "AIO3_CIRCUIT_BREAKER_COOLDOWN" in const_source
    assert "def diagnostic_polling" in coordinator_source
    assert "_bucket_last_duration" in coordinator_source
    assert "_bucket_last_error" in coordinator_source
    assert "_bucket_expected_registers" in coordinator_source
    assert "circuit_breaker" in coordinator_source
    assert "coordinator.diagnostic_polling()" in diagnostics_source


def test_battery_time_sensors_are_visible_and_branded() -> None:
    """Battery time sensors should remain visible and the integration branded."""
    sensor_source = (INTEGRATION_DIR / "sensor.py").read_text(encoding="utf-8")
    strings_source = (INTEGRATION_DIR / "strings.json").read_text(encoding="utf-8")
    es_source = (INTEGRATION_DIR / "translations" / "es.json").read_text(
        encoding="utf-8"
    )
    icons_source = (INTEGRATION_DIR / "icons.json").read_text(encoding="utf-8")
    icon_path = PROJECT_ROOT / "brands" / "saj_as1_modbus" / "icon.png"
    hacs_icon_path = INTEGRATION_DIR / "brand" / "icon.png"

    for key in ("battery_time_to_full", "battery_time_to_empty"):
        sensor_block = sensor_source[
            sensor_source.index(f'key="{key}"') : sensor_source.index(
                "SensorEntityDescription(",
                sensor_source.index(f'key="{key}"') + 1,
            )
        ]
        assert "device_class=SensorDeviceClass.DURATION" in sensor_block
        assert "native_unit_of_measurement=UnitOfTime.HOURS" in sensor_block
        assert "entity_category=EntityCategory.DIAGNOSTIC" not in sensor_block
        assert key in strings_source
        assert key in es_source
        assert key in icons_source

    assert icon_path.exists()
    assert icon_path.stat().st_size > 0
    assert hacs_icon_path.exists()
    assert hacs_icon_path.stat().st_size > 0


def test_evcc_grid_l1_sensors_are_documented_without_l2_l3() -> None:
    """evcc helper sensors should expose only documented AS1 L1 grid values."""
    sensor_source = (INTEGRATION_DIR / "sensor.py").read_text(encoding="utf-8")
    strings_source = (INTEGRATION_DIR / "strings.json").read_text(encoding="utf-8")
    es_source = (INTEGRATION_DIR / "translations" / "es.json").read_text(
        encoding="utf-8"
    )
    icons_source = (INTEGRATION_DIR / "icons.json").read_text(encoding="utf-8")
    coordinator_source = (INTEGRATION_DIR / "coordinator.py").read_text(
        encoding="utf-8"
    )

    expected = {
        "grid_voltage_l1": (
            "device_class=SensorDeviceClass.VOLTAGE",
            "native_unit_of_measurement=UnitOfElectricPotential.VOLT",
        ),
        "grid_current_l1": (
            "device_class=SensorDeviceClass.CURRENT",
            "native_unit_of_measurement=UnitOfElectricCurrent.AMPERE",
        ),
        "grid_frequency_l1": (
            "device_class=SensorDeviceClass.FREQUENCY",
            "native_unit_of_measurement=UnitOfFrequency.HERTZ",
        ),
    }
    for key, required_snippets in expected.items():
        assert key in strings_source
        assert key in es_source
        assert key in icons_source
        sensor_block = sensor_source[
            sensor_source.index(f'key="{key}"') : sensor_source.index(
                "SensorEntityDescription(",
                sensor_source.index(f'key="{key}"') + 1,
            )
        ]
        for snippet in required_snippets:
            assert snippet in sensor_block

    assert "REGISTER_GRID_L1_STATUS_START" in coordinator_source
    assert "REGISTER_GRID_L1_STATUS_COUNT" in coordinator_source
    for unsupported_key in (
        "grid_voltage_l2",
        "grid_voltage_l3",
        "grid_current_l2",
        "grid_current_l3",
    ):
        assert unsupported_key not in sensor_source
