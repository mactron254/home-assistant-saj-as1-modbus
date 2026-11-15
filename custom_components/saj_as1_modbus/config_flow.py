"""Config flow for SAJ AS1 Modbus."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
import homeassistant.helpers.config_validation as cv

from .connection_manager import ModbusConnectionManager
from .const import (
    CONF_DEVICE_ID,
    DEFAULT_DEVICE_ID,
    DEFAULT_PORT,
    DOMAIN,
    MODBUS_TIMEOUT,
)
from .exceptions import SAJModbusException

_LOGGER = logging.getLogger(__name__)

CONNECTION_ERRORS = (SAJModbusException, OSError, TimeoutError)


def _unique_id(host: str, port: int, device_id: int) -> str:
    """Build a stable unique id for one inverter endpoint."""
    return f"{host.lower()}:{port}:{device_id}"


def _entry_title(host: str) -> str:
    """Return the default title of an entry."""
    return f"SAJ AS1 ({host})"


def _schema(defaults: dict[str, Any] | None = None) -> Any:
    """Return the connection form schema.

    Home Assistant 2026.9+ validates with probatio and aliases ``voluptuous``
    to it, while 2026.5 still uses voluptuous. The return type is left open so
    both type check.
    """
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): vol.All(
                cv.string,
                vol.Strip,
                vol.Length(min=1),
            ),
            vol.Required(
                CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=1, max=65535),
            ),
            vol.Optional(
                CONF_DEVICE_ID,
                default=defaults.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=247)),
        }
    )


async def _async_test_connection(host: str, port: int, device_id: int) -> None:
    """Validate that the inverter answers before saving the entry."""
    manager = ModbusConnectionManager(
        host=host,
        port=port,
        device_id=device_id,
        timeout=MODBUS_TIMEOUT,
        # One attempt so the form answers in seconds when the host is down.
        connect_attempts=1,
    )
    try:
        await manager.test_connection()
    finally:
        await manager.close()


class SAJConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SAJ AS1 Modbus."""

    VERSION = 2

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host: str = user_input[CONF_HOST]
            port: int = user_input[CONF_PORT]
            device_id: int = user_input[CONF_DEVICE_ID]

            await self.async_set_unique_id(_unique_id(host, port, device_id))
            self._abort_if_unique_id_configured()

            try:
                await _async_test_connection(host, port, device_id)
            except CONNECTION_ERRORS:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error while testing the SAJ AS1")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=_entry_title(host),
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
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the connection from the UI."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host: str = user_input[CONF_HOST]
            port: int = user_input[CONF_PORT]
            device_id: int = user_input[CONF_DEVICE_ID]
            unique_id = _unique_id(host, port, device_id)

            if unique_id != entry.unique_id:
                # Another entry may already poll this endpoint.
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

            try:
                await _async_test_connection(host, port, device_id)
            except CONNECTION_ERRORS:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error while testing the SAJ AS1")
                errors["base"] = "unknown"
            else:
                title = entry.title
                if title == _entry_title(entry.data[CONF_HOST]):
                    title = _entry_title(host)
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=unique_id,
                    title=title,
                    data_updates={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_DEVICE_ID: device_id,
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(user_input or dict(entry.data)),
            errors=errors,
        )
