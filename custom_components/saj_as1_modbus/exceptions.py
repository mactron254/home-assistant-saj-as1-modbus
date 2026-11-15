"""Custom exceptions for the SAJ AS1 Modbus integration."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN


class SAJModbusException(Exception):
    """Base exception for SAJ Modbus errors."""


class ReconnectionNeededError(SAJModbusException):
    """Raised when the Modbus session broke and a new connection is needed."""


class ConnectFailedError(ReconnectionNeededError):
    """Raised when no TCP connection could be opened after all attempts.

    Callers that retry a broken session (EOF, no response) must not retry this
    one: every retry would run the full connect sequence against a host that is
    already known to be unreachable.
    """


class ModbusReadError(SAJModbusException):
    """Raised when the device answers a read with an error or no data."""


class ModbusWriteError(SAJModbusException):
    """Raised when a Modbus write fails."""


class SAJWriteFailedError(HomeAssistantError):
    """Raised when Home Assistant cannot write a value to the inverter."""

    def __init__(self, address: int) -> None:
        """Initialize a translated write failure."""
        super().__init__(
            translation_domain=DOMAIN,
            translation_key="write_failed",
            translation_placeholders={"address": f"0x{address:04X}"},
        )
