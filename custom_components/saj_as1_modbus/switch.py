"""Switch platform for SAJ AS1 Modbus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    REGISTER_CHARGE_SCHEDULE_ENABLE,
    REGISTER_DISCHARGE_SCHEDULE_ENABLE,
)
from .coordinator import SAJModbusCoordinator
from .entity import SAJEntity
from .exceptions import SAJWriteFailedError

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class SAJSwitchEntityDescription(SwitchEntityDescription):
    """Describe a writable SAJ schedule switch."""

    register: int


SWITCH_DESCRIPTIONS: tuple[SAJSwitchEntityDescription, ...] = (
    SAJSwitchEntityDescription(
        key="first_charge_schedule_enabled",
        translation_key="first_charge_schedule_enabled",
        entity_category=EntityCategory.CONFIG,
        register=REGISTER_CHARGE_SCHEDULE_ENABLE,
    ),
    SAJSwitchEntityDescription(
        key="first_discharge_schedule_enabled",
        translation_key="first_discharge_schedule_enabled",
        entity_category=EntityCategory.CONFIG,
        register=REGISTER_DISCHARGE_SCHEDULE_ENABLE,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SAJ AS1 schedule switches."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        SAJScheduleSwitch(coordinator, description)
        for description in SWITCH_DESCRIPTIONS
    )


class SAJScheduleSwitch(SAJEntity, SwitchEntity):
    """Control bit zero of an SAJ schedule-enable mask."""

    entity_description: SAJSwitchEntityDescription

    def __init__(
        self,
        coordinator: SAJModbusCoordinator,
        description: SAJSwitchEntityDescription,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return whether the first schedule is enabled."""
        value: Any = self.coordinator.data.get(self.entity_description.key)
        return value if isinstance(value, bool) else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the first schedule."""
        if self.is_on is True:
            return
        await self._async_set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the first schedule."""
        if self.is_on is False:
            return
        await self._async_set_enabled(False)

    async def _async_set_enabled(self, enabled: bool) -> None:
        """Apply one schedule-enable state."""
        ok = await self.coordinator.async_set_schedule_enabled(
            self.entity_description.register,
            enabled,
        )
        if not ok:
            raise SAJWriteFailedError(self.entity_description.register)
