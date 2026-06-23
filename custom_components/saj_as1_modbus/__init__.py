"""SAJ AS1 Modbus integration."""

from __future__ import annotations

from typing import cast

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_CHARGE_POWER_PCT,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_DISCHARGE_POWER_PCT,
    ATTR_USER_MODE,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    SERVICE_SET_PROFILE,
    USER_MODE_OPTIONS,
    USER_MODES,
)
from .coordinator import SAJModbusCoordinator
from .models import SAJRuntimeData

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BINARY_SENSOR,
]

SET_PROFILE_SCHEMA = vol.Schema(
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
        vol.Optional(ATTR_USER_MODE): vol.In(USER_MODE_OPTIONS),
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration-wide SAJ AS1 services."""
    _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SAJ AS1 Modbus from a config entry."""
    coordinator = SAJModbusCoordinator(hass, entry)
    entry.runtime_data = SAJRuntimeData(coordinator=coordinator)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await coordinator.connection.close()
        raise
    except Exception as err:
        await coordinator.connection.close()
        raise ConfigEntryNotReady(
            "El inversor SAJ AS1 no está disponible durante la configuración."
        ) from err

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.coordinator.connection.close()
    return bool(unload_ok)


def _async_register_services(hass: HomeAssistant) -> None:
    """Registrar servicios propios de automatización."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_PROFILE):
        return

    async def async_handle_set_profile(call: ServiceCall) -> None:
        """Aplicar un perfil de usuario en una sola llamada."""
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

        coordinator = _get_service_coordinator(
            hass,
            cast(str | None, call.data.get(ATTR_CONFIG_ENTRY_ID)),
        )
        ok = await coordinator.async_set_profile(
            charge_power_pct=cast(int | None, call.data.get(ATTR_CHARGE_POWER_PCT)),
            discharge_power_pct=cast(
                int | None,
                call.data.get(ATTR_DISCHARGE_POWER_PCT),
            ),
            user_mode=_service_user_mode_value(
                cast(str | None, call.data.get(ATTR_USER_MODE))
            ),
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


def _get_service_coordinator(
    hass: HomeAssistant,
    entry_id: str | None,
) -> SAJModbusCoordinator:
    """Obtener el coordinador que debe ejecutar un servicio."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if entry_id is not None:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="entry_not_found",
                translation_placeholders={"entry_id": entry_id},
            )
        return _loaded_entry_coordinator(entry)

    if len(entries) != 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_required",
        )

    return _loaded_entry_coordinator(entries[0])


def _loaded_entry_coordinator(entry: ConfigEntry) -> SAJModbusCoordinator:
    """Devolver el coordinador si la entrada está cargada."""
    if entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_loaded",
            translation_placeholders={"entry_id": entry.entry_id},
        )
    return cast(SAJRuntimeData, entry.runtime_data).coordinator


def _service_user_mode_value(option: str | None) -> int | None:
    """Convertir el texto del modo de usuario a valor Modbus."""
    if option is None:
        return None
    for value, name in USER_MODES.items():
        if name == option:
            return value
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="invalid_user_mode",
        translation_placeholders={"mode": option},
    )


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate legacy config entries."""
    data = dict(entry.data)
    options = dict(entry.options)
    changed = False

    if CONF_SCAN_INTERVAL in data:
        data.pop(CONF_SCAN_INTERVAL)
        changed = True
    if CONF_SCAN_INTERVAL in options:
        options.pop(CONF_SCAN_INTERVAL)
        changed = True

    if changed or entry.version < 2:
        hass.config_entries.async_update_entry(
            entry,
            data=data,
            options=options,
            version=2,
        )

    return True
