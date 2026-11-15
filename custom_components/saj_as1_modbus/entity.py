"""Shared entity helpers for SAJ AS1 Modbus."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import SAJModbusCoordinator


class SAJEntity(CoordinatorEntity[SAJModbusCoordinator]):
    """Base class for SAJ AS1 entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SAJModbusCoordinator, key: str) -> None:
        """Initialize the entity and its device."""
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="SAJ AS1 Inverter",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def available(self) -> bool:
        """Return availability from the coordinator and the bucket health."""
        key = self.entity_description.key
        return super().available and key not in self.coordinator.unavailable_keys
