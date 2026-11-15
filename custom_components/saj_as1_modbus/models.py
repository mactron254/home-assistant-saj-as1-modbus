"""Internal models for the SAJ AS1 Modbus integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .coordinator import SAJModbusCoordinator


@dataclass(slots=True)
class SAJRuntimeData:
    """Runtime data stored on the config entry."""

    coordinator: SAJModbusCoordinator


type SAJConfigEntry = ConfigEntry[SAJRuntimeData]
