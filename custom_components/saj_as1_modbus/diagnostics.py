"""Soporte de diagnóstico para SAJ AS1 Modbus."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_ID

TO_REDACT = {CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Devolver diagnóstico de una entrada de configuración."""
    coordinator = entry.runtime_data.coordinator
    entry_data = async_redact_data(dict(entry.data), TO_REDACT)

    return {
        "entry": {
            CONF_HOST: entry_data.get(CONF_HOST),
            CONF_PORT: entry.data.get(CONF_PORT),
            CONF_DEVICE_ID: entry.data.get(CONF_DEVICE_ID),
        },
        "connection": {
            "connected": coordinator.connection.connected,
            "coordinator_connected": coordinator.is_connected,
            "consecutive_failures": coordinator.consecutive_failures,
            "last_error_type": coordinator.last_error_type,
            "unavailable_keys": sorted(coordinator.unavailable_keys),
        },
        "polling": coordinator.diagnostic_polling(),
    }
