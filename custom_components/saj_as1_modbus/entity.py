"""Ayudantes compartidos de entidades para SAJ AS1 Modbus."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SAJModbusCoordinator


class SAJEntity(CoordinatorEntity[SAJModbusCoordinator]):
    """Clase base para entidades SAJ AS1."""

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Devolver información de dispositivo para agrupar entidades."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name="SAJ AS1 Inverter",
            manufacturer="SAJ Electric",
            model="AS1",
        )

    @property
    def available(self) -> bool:
        """Devolver disponibilidad según coordinador y salud del registro."""
        key = self.entity_description.key
        return super().available and key not in self.coordinator.unavailable_keys
