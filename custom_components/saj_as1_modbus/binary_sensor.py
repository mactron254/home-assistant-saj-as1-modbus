"""Binary sensor platform for SAJ AS1 Modbus."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (  # type: ignore[attr-defined,unused-ignore]
    # Re-exported implicitly in 2026.10, explicitly again in 2026.12.
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SAJModbusCoordinator
from .entity import SAJEntity
from .models import SAJConfigEntry

# Read-only entities are updated by the coordinator.
PARALLEL_UPDATES = 0

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
    entry: SAJConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
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
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        """Stay available: a lost connection must show as off, not unavailable."""
        return True

    @property
    def is_on(self) -> bool | None:
        """Return whether the inverter connection is healthy."""
        return bool(self.coordinator.is_connected)
