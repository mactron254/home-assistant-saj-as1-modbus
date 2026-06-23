"""Binary sensor platform for SAJ AS1 Modbus."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SAJModbusCoordinator
from .entity import SAJEntity

PARALLEL_UPDATES = 1

BINARY_SENSOR_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="is_connected",
        translation_key="is_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SAJ AS1 binary sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        SAJBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class SAJBinarySensor(SAJEntity, BinarySensorEntity):
    """SAJ AS1 binary sensor."""

    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator: SAJModbusCoordinator,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return whether the inverter connection is healthy."""
        return bool(self.coordinator.is_connected)
