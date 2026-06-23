"""Config flow for SAJ AS1 Modbus."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
import homeassistant.helpers.config_validation as cv

from .connection_manager import ModbusConnectionManager
from .const import CONF_DEVICE_ID, DEFAULT_DEVICE_ID, DOMAIN, MODBUS_TIMEOUT

_LOGGER = logging.getLogger(__name__)


def _unique_id(host: str, port: int, device_id: int) -> str:
    """Build a stable unique id for one inverter endpoint."""
    return f"{host.lower()}:{port}:{device_id}"


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the config form schema."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): vol.All(
                cv.string,
                vol.Length(min=1),
            ),
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, 502)): vol.All(
                vol.Coerce(int),
                vol.Range(min=1, max=65535),
            ),
            vol.Optional(
                CONF_DEVICE_ID,
                default=defaults.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=247)),
        }
    )


class SAJConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SAJ AS1 Modbus."""

    VERSION = 2

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            device_id = user_input[CONF_DEVICE_ID]

            await self.async_set_unique_id(_unique_id(host, port, device_id))
            self._abort_if_unique_id_configured()

            try:
                await self._async_test_connection(host, port, device_id)
            except Exception as err:
                _LOGGER.debug("SAJ AS1 config flow connection test failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"SAJ AS1 ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_DEVICE_ID: device_id,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration from the UI."""
        entry = self._get_reconfigure_entry()
        defaults = dict(entry.data)
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            device_id = user_input[CONF_DEVICE_ID]

            try:
                await self._async_test_connection(host, port, device_id)
            except Exception as err:
                _LOGGER.debug("SAJ AS1 reconfigure connection test failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(_unique_id(host, port, device_id))
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_DEVICE_ID: device_id,
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(user_input or defaults),
            errors=errors,
        )

    async def _async_test_connection(
        self,
        host: str,
        port: int,
        device_id: int,
    ) -> None:
        """Validate that the inverter answers before saving the entry."""
        manager = ModbusConnectionManager(
            hass=self.hass,
            host=host,
            port=port,
            device_id=device_id,
            timeout=MODBUS_TIMEOUT,
        )
        try:
            await manager.test_connection()
        finally:
            await manager.close()
