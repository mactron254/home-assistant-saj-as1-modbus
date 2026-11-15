"""Diagnostics support for SAJ AS1 Modbus."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .models import SAJConfigEntry

REDACTED = "**REDACTED**"
TO_REDACT = {CONF_HOST, "unique_id"}


def _redact_host(value: Any, host: str) -> Any:
    """Remove the inverter address from error texts as well."""
    if isinstance(value, str):
        return value.replace(host, REDACTED)
    if isinstance(value, dict):
        return {key: _redact_host(item, host) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_host(item, host) for item in value]
    return value


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: SAJConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator

    diagnostics = async_redact_data(
        {
            "entry": {
                "unique_id": entry.unique_id,
                "version": entry.version,
                "data": dict(entry.data),
            },
            "connection": {
                "inverter_reachable": coordinator.is_connected,
                "consecutive_failures": coordinator.consecutive_failures,
                "last_error_type": coordinator.last_error_type,
                "unavailable_keys": sorted(coordinator.unavailable_keys),
                "expired_keys": sorted(coordinator.expired_keys),
            },
            "polling": coordinator.diagnostic_polling(),
            # Raw power flows (W) of the 0x4099 block, already read every cycle.
            "raw_power_flows": dict(coordinator.raw_power_flows),
            "data": dict(coordinator.data or {}),
        },
        TO_REDACT,
    )
    return _redact_host(diagnostics, coordinator.host)  # type: ignore[no-any-return]
