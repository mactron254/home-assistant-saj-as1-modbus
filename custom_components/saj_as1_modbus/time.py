"""Time platform for SAJ AS1 Modbus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    REGISTER_CHARGE_END_TIME,
    REGISTER_CHARGE_START_TIME,
    REGISTER_DISCHARGE_END_TIME,
    REGISTER_DISCHARGE_START_TIME,
)
from .coordinator import SAJModbusCoordinator
from .entity import SAJEntity
from .exceptions import SAJWriteFailedError
from .modbus_processing import encode_schedule_time

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class SAJTimeEntityDescription(TimeEntityDescription):
    """Describe a writable SAJ schedule time."""

    register: int


TIME_DESCRIPTIONS: tuple[SAJTimeEntityDescription, ...] = (
    SAJTimeEntityDescription(
        key="first_charge_start_time",
        translation_key="first_charge_start_time",
        entity_category=EntityCategory.CONFIG,
        register=REGISTER_CHARGE_START_TIME,
    ),
    SAJTimeEntityDescription(
        key="first_charge_end_time",
        translation_key="first_charge_end_time",
        entity_category=EntityCategory.CONFIG,
        register=REGISTER_CHARGE_END_TIME,
    ),
    SAJTimeEntityDescription(
        key="first_discharge_start_time",
        translation_key="first_discharge_start_time",
        entity_category=EntityCategory.CONFIG,
        register=REGISTER_DISCHARGE_START_TIME,
    ),
    SAJTimeEntityDescription(
        key="first_discharge_end_time",
        translation_key="first_discharge_end_time",
        entity_category=EntityCategory.CONFIG,
        register=REGISTER_DISCHARGE_END_TIME,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SAJ AS1 time entities."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        SAJTime(coordinator, description) for description in TIME_DESCRIPTIONS
    )


class SAJTime(SAJEntity, TimeEntity):
    """Expose a minute-precision SAJ schedule time."""

    entity_description: SAJTimeEntityDescription

    def __init__(
        self,
        coordinator: SAJModbusCoordinator,
        description: SAJTimeEntityDescription,
    ) -> None:
        """Initialize the time entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> time | None:
        """Return the current schedule time."""
        value = self.coordinator.data.get(self.entity_description.key)
        return value if isinstance(value, time) else None

    async def async_set_value(self, value: time) -> None:
        """Write a minute-precision schedule time."""
        normalized = value.replace(second=0, microsecond=0)
        if self.native_value == normalized:
            return
        ok = await self.coordinator.async_write_register(
            self.entity_description.register,
            encode_schedule_time(normalized),
        )
        if not ok:
            raise SAJWriteFailedError(self.entity_description.register)
