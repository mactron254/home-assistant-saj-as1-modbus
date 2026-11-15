"""Diagnostics support for SAJ AS1 Modbus."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .models import SAJConfigEntry

TO_REDACT = {CONF_HOST, "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: SAJConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator

    return async_redact_data(
        {
            "entry": {
                "unique_id": entry.unique_id,
                "version": entry.version,
                "data": dict(entry.data),
            },
            "connection": {
                "connected": coordinator.connection.connected,
                "coordinator_connected": coordinator.is_connected,
                "consecutive_failures": coordinator.consecutive_failures,
                "last_error_type": coordinator.last_error_type,
                "unavailable_keys": sorted(coordinator.unavailable_keys),
            },
            "polling": coordinator.diagnostic_polling(),
            "data": dict(coordinator.data or {}),
        },
        TO_REDACT,
    )
