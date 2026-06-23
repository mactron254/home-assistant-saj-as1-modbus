"""Tests for pure Modbus conversion helpers."""

from custom_components.saj_as1_modbus.modbus_processing import (
    extract_byte_high,
    extract_byte_low,
    inject_days_weekdays,
    read_current,
    read_energy,
    read_int16,
    read_percentage,
    read_temperature,
    read_uint16,
    read_uint32,
    read_voltage,
    validate_percentage,
)


def test_signed_and_unsigned_register_reads() -> None:
    """Register helpers convert raw words correctly."""
    assert read_int16([0x0001], 0) == 1
    assert read_int16([0x8000], 0) == -32768
    assert read_int16([0xFFFF], 0) == -1
    assert read_uint16([0xFFFF], 0) == 65535
    assert read_uint32([0x0001, 0x0000], 0) == 65536


def test_scaled_values() -> None:
    """Scaled helpers match the SAJ protocol magnification rules."""
    assert read_temperature([235], 0) == 23.5
    assert read_temperature([65436], 0) == -10.0
    assert read_voltage([512], 0) == 51.2
    assert read_voltage([2411], 0) == 241.1
    assert read_current([194], 0) == 1.94
    assert read_current([65486], 0) == -0.5
    assert read_uint16([4997], 0) / 100.0 == 49.97
    assert read_percentage([9832], 0) == 98.32
    assert read_energy([0, 12345], 0) == 123.45


def test_weekday_power_byte_helpers() -> None:
    """Charge and discharge power writes preserve the weekday mask."""
    value = inject_days_weekdays(50)
    assert value == 0x7F32
    assert extract_byte_high(value) == 0x7F
    assert extract_byte_low(value) == 50


def test_percentage_validation() -> None:
    """Power percentage writes stay in the AS1-supported range."""
    assert validate_percentage(1) == 1
    assert validate_percentage(50) == 50
    assert validate_percentage(0) == 100
    assert validate_percentage(150) == 100
