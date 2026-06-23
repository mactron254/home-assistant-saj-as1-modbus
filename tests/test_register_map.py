"""Tests for SAJ register mapping decisions."""

from custom_components.saj_as1_modbus.const import (
    CONFIG_KEYS,
    HIGH_KEYS,
    LOW_ENERGY_BLOCK_COUNT,
    LOW_ENERGY_BLOCK_START,
    LOW_ENERGY_REGISTERS,
    MEDIUM_KEYS,
    REGISTER_CHARGE_POWER_PCT,
    REGISTER_DISCHARGE_POWER_PCT,
    REGISTER_GRID_L1_STATUS_COUNT,
    REGISTER_GRID_L1_STATUS_START,
    SCAN_INTERVAL_CONFIG,
)


def test_low_energy_registers_use_protocol_addresses() -> None:
    """LOW energy sensors use documented accumulated-energy registers."""
    assert LOW_ENERGY_REGISTERS["total_pv_energy"] == 0x40C5
    assert LOW_ENERGY_REGISTERS["total_battery_charge_energy"] == 0x40CD
    assert LOW_ENERGY_REGISTERS["total_battery_discharge_energy"] == 0x40D5
    assert LOW_ENERGY_REGISTERS["total_load_energy"] == 0x40E5
    assert LOW_ENERGY_REGISTERS["total_grid_export_energy"] == 0x40FD
    assert LOW_ENERGY_REGISTERS["total_grid_import_energy"] == 0x410D


def test_low_energy_block_covers_all_energy_registers() -> None:
    """LOW energy counters can be read in one safe contiguous block."""
    assert LOW_ENERGY_BLOCK_START == 0x40C5
    assert LOW_ENERGY_BLOCK_COUNT == 74
    for address in LOW_ENERGY_REGISTERS.values():
        offset = address - LOW_ENERGY_BLOCK_START
        assert 0 <= offset
        assert offset + 1 < LOW_ENERGY_BLOCK_COUNT


def test_high_keys_include_signed_power_helpers() -> None:
    """Signed power helpers should share HIGH availability with their sources."""
    assert "grid_power_signed" in HIGH_KEYS
    assert "battery_power_signed" in HIGH_KEYS


def test_sensitive_config_registers_use_slow_bucket() -> None:
    """AIO3 WiFi user settings should not be polled with MEDIUM status data."""
    assert SCAN_INTERVAL_CONFIG == 300
    assert "user_mode" in CONFIG_KEYS
    assert "first_charge_power_pct" in CONFIG_KEYS
    assert "first_discharge_power_pct" in CONFIG_KEYS
    assert "user_mode" not in MEDIUM_KEYS
    assert "first_charge_power_pct" not in MEDIUM_KEYS
    assert "first_discharge_power_pct" not in MEDIUM_KEYS


def test_config_registers_are_documented_addresses() -> None:
    """Writable charge/discharge registers match the AS1 protocol."""
    assert REGISTER_CHARGE_POWER_PCT == 0x3608
    assert REGISTER_DISCHARGE_POWER_PCT == 0x361D


def test_grid_l1_status_uses_documented_medium_block() -> None:
    """evcc-friendly L1 voltage/current uses the documented AS1 grid registers."""
    assert REGISTER_GRID_L1_STATUS_START == 0x4031
    assert REGISTER_GRID_L1_STATUS_COUNT == 3
    assert "grid_voltage_l1" in MEDIUM_KEYS
    assert "grid_current_l1" in MEDIUM_KEYS
    assert "grid_frequency_l1" in MEDIUM_KEYS


def test_grid_l2_l3_entities_are_not_invented() -> None:
    """The AS1 protocol reference only documents R/L1 for this device."""
    unsupported_keys = {
        "grid_voltage_l2",
        "grid_voltage_l3",
        "grid_current_l2",
        "grid_current_l3",
    }
    assert unsupported_keys.isdisjoint(MEDIUM_KEYS)
    assert unsupported_keys.isdisjoint(HIGH_KEYS)
