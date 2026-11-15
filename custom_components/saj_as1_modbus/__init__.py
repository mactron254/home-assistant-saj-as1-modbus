"""SAJ AS1 Modbus integration."""

from __future__ import annotations

import logging
from typing import Any, cast

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import (
    config_validation as cv,
    issue_registry as ir,
    service,
)
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_CHARGE_POWER_PCT,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_DISCHARGE_POWER_PCT,
    ATTR_USER_MODE,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    LEGACY_USER_MODE_OPTIONS,
    SERVICE_SET_PROFILE,
    USER_MODE_OPTIONS,
    USER_MODES,
)
from .coordinator import SAJModbusCoordinator, connection_issue_id
from .models import SAJConfigEntry, SAJRuntimeData

_LOGGER = logging.getLogger(__name__)

CURRENT_ENTRY_VERSION = 2

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BINARY_SENSOR,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_legacy_option_warned = False

# Home Assistant 2026.9+ aliases voluptuous to probatio; typed as Any so the
# schema type checks against both validation engines.
SET_PROFILE_SCHEMA: Any = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(ATTR_CHARGE_POWER_PCT): vol.All(
            vol.Coerce(int),
            vol.Range(min=1, max=100),
        ),
        vol.Optional(ATTR_DISCHARGE_POWER_PCT): vol.All(
            vol.Coerce(int),
            vol.Range(min=1, max=100),
        ),
        vol.Optional(ATTR_USER_MODE): vol.In(
            [*USER_MODE_OPTIONS, *LEGACY_USER_MODE_OPTIONS]
        ),
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration-wide SAJ AS1 actions."""
    _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SAJConfigEntry) -> bool:
    """Set up SAJ AS1 Modbus from a config entry."""
    coordinator = SAJModbusCoordinator(hass, entry)
    entry.runtime_data = SAJRuntimeData(coordinator=coordinator)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await coordinator.connection.close()
        raise

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SAJConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.coordinator.connection.close()
        ir.async_delete_issue(hass, DOMAIN, connection_issue_id(entry.entry_id))
    return unload_ok


def _async_register_services(hass: HomeAssistant) -> None:
    """Register the automation actions of the integration."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_PROFILE):
        return

    async def async_handle_set_profile(call: ServiceCall) -> None:
        """Apply a user profile in a single action call."""
        if not any(
            key in call.data
            for key in (
                ATTR_CHARGE_POWER_PCT,
                ATTR_DISCHARGE_POWER_PCT,
                ATTR_USER_MODE,
            )
        ):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="profile_requires_value",
            )

        entry = _async_get_service_entry(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        ok = await entry.runtime_data.coordinator.async_set_profile(
            charge_power_pct=call.data.get(ATTR_CHARGE_POWER_PCT),
            discharge_power_pct=call.data.get(ATTR_DISCHARGE_POWER_PCT),
            user_mode=_service_user_mode_value(call.data.get(ATTR_USER_MODE)),
        )
        if not ok:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="profile_write_failed",
            )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PROFILE,
        async_handle_set_profile,
        schema=SET_PROFILE_SCHEMA,
    )


@callback
def _async_get_service_entry(
    hass: HomeAssistant, entry_id: str | None
) -> SAJConfigEntry:
    """Return the loaded entry an action call targets.

    Without an explicit entry the single loaded inverter is used. Home
    Assistant 2026.5 has no built-in fallback for that case, so it is kept here.
    """
    if entry_id is not None:
        return cast(
            SAJConfigEntry, service.async_get_config_entry(hass, DOMAIN, entry_id)
        )

    loaded = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]
    if not loaded:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="entry_not_loaded"
        )
    if len(loaded) > 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="entry_required"
        )
    return cast(SAJConfigEntry, loaded[0])


def _service_user_mode_value(option: str | None) -> int | None:
    """Convert a user mode option (or a legacy Spanish label) to its value."""
    global _legacy_option_warned  # noqa: PLW0603

    if option is None:
        return None
    if option in LEGACY_USER_MODE_OPTIONS:
        if not _legacy_option_warned:
            _legacy_option_warned = True
            _LOGGER.warning(
                "The %s.%s option '%s' is deprecated, use '%s' instead",
                DOMAIN,
                SERVICE_SET_PROFILE,
                option,
                LEGACY_USER_MODE_OPTIONS[option],
            )
        option = LEGACY_USER_MODE_OPTIONS[option]
    for value, name in USER_MODES.items():
        if name == option:
            return value
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="invalid_user_mode",
        translation_placeholders={"mode": option},
    )


async def async_migrate_entry(hass: HomeAssistant, entry: SAJConfigEntry) -> bool:
    """Migrate legacy config entries."""
    if entry.version > CURRENT_ENTRY_VERSION:
        # The entry was created by a newer version of the integration.
        return False

    data = dict(entry.data)
    options = dict(entry.options)
    changed = False

    if CONF_SCAN_INTERVAL in data:
        data.pop(CONF_SCAN_INTERVAL)
        changed = True
    if CONF_SCAN_INTERVAL in options:
        options.pop(CONF_SCAN_INTERVAL)
        changed = True

    if changed or entry.version < CURRENT_ENTRY_VERSION:
        hass.config_entries.async_update_entry(
            entry,
            data=data,
            options=options,
            version=CURRENT_ENTRY_VERSION,
        )

    return True
