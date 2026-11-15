"""Register decoding helpers for the SAJ AS1 Modbus protocol.

Scaling follows the AS1 main control board protocol (section 4.3, realtime
data). Magnification ``-1`` divides by 10, ``-2`` by 100 and ``-3`` by 1000.
"""

from __future__ import annotations

from .const import WEEKDAYS_ALL


def read_int16(registers: list[int], index: int) -> int:
    """Return a signed 16-bit value."""
    value = registers[index]
    return value if value < 0x8000 else value - 0x10000


def read_uint16(registers: list[int], index: int) -> int:
    """Return an unsigned 16-bit value."""
    return registers[index]


def read_uint32(registers: list[int], index: int) -> int:
    """Return an unsigned 32-bit value stored high word first."""
    return (registers[index] << 16) | registers[index + 1]


def read_temperature(registers: list[int], index: int) -> float:
    """Return a temperature in °C (Int16, magnification -1)."""
    return round(read_int16(registers, index) / 10.0, 1)


def read_voltage(registers: list[int], index: int) -> float:
    """Return a voltage in V (UInt16, magnification -1)."""
    return round(read_uint16(registers, index) / 10.0, 1)


def read_current(registers: list[int], index: int) -> float:
    """Return a current in A (Int16, magnification -2)."""
    return round(read_int16(registers, index) / 100.0, 2)


def read_percentage(registers: list[int], index: int) -> float:
    """Return a percentage such as SOC or SOH (UInt16, magnification -2)."""
    return round(read_uint16(registers, index) / 100.0, 2)


def read_power(registers: list[int], index: int) -> int:
    """Return a signed power in W (Int16, magnification 0)."""
    return read_int16(registers, index)


def read_energy(registers: list[int], index: int) -> float:
    """Return an accumulated energy in kWh (UInt32, magnification -2)."""
    return round(read_uint32(registers, index) / 100.0, 2)


def extract_byte_low(value: int) -> int:
    """Return the low byte of a 16-bit register (slot power percentage)."""
    return value & 0xFF


def extract_byte_high(value: int) -> int:
    """Return the high byte of a 16-bit register (slot weekday mask)."""
    return (value >> 8) & 0xFF


def percentage_from_register(value: int) -> int:
    """Return the slot power percentage stored in the low byte, as reported.

    A value of 0 is a valid reading and is no longer shown as 100 %.
    """
    return min(extract_byte_low(value), 100)


def validate_percentage(value: int) -> int:
    """Clamp a slot power percentage to the writable 1-100 range."""
    return min(max(value, 1), 100)


def inject_days_weekdays(percentage: int, days: int = WEEKDAYS_ALL) -> int:
    """Combine a weekday mask (high byte) and a power percentage (low byte).

    The current weekday mask is kept so that days configured in the SAJ app are
    not overwritten. An empty mask would leave the slot inactive, so it falls
    back to every day of the week.
    """
    days &= 0xFF
    if days == 0:
        days = WEEKDAYS_ALL
    return (days << 8) | (percentage & 0xFF)
