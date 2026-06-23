"""Custom exceptions for the SAJ AS1 Modbus integration."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN


class SAJModbusException(Exception):
    """Base exception for SAJ Modbus errors."""


class ReconnectionNeededError(SAJModbusException):
    """Raised when the Modbus client needs a reconnect."""


class ModbusReadError(SAJModbusException):
    """Raised when a Modbus read fails."""


class ModbusWriteError(SAJModbusException):
    """Raised when a Modbus write fails."""


class MaxRetriesExceededError(SAJModbusException):
    """Raised when all Modbus connection retries are exhausted."""


class SAJWriteFailedError(HomeAssistantError):
    """Raised when Home Assistant cannot write a value to the inverter."""

    def __init__(self, address: int) -> None:
        """Initialize a translated write failure."""
        super().__init__(
            translation_domain=DOMAIN,
            translation_key="write_failed",
            translation_placeholders={"address": f"0x{address:04X}"},
        )
