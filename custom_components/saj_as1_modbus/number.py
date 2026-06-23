"""Number platform for SAJ AS1 Modbus."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import REGISTER_CHARGE_POWER_PCT, REGISTER_DISCHARGE_POWER_PCT
from .coordinator import SAJModbusCoordinator
from .entity import SAJEntity
from .exceptions import SAJWriteFailedError

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class SAJNumberEntityDescription(NumberEntityDescription):
    """Description for a writable SAJ number."""

    register: int


NUMBER_DESCRIPTIONS: tuple[SAJNumberEntityDescription, ...] = (
    SAJNumberEntityDescription(
        key="first_charge_power_pct",
        translation_key="first_charge_power_pct",
        native_min_value=1,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.CONFIG,
        register=REGISTER_CHARGE_POWER_PCT,
    ),
    SAJNumberEntityDescription(
        key="first_discharge_power_pct",
        translation_key="first_discharge_power_pct",
        native_min_value=1,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.CONFIG,
        register=REGISTER_DISCHARGE_POWER_PCT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SAJ AS1 number entities."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        SAJNumber(coordinator, description) for description in NUMBER_DESCRIPTIONS
    )


class SAJNumber(SAJEntity, NumberEntity):
    """Writable SAJ AS1 number entity."""

    entity_description: SAJNumberEntityDescription

    def __init__(
        self,
        coordinator: SAJModbusCoordinator,
        description: SAJNumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        value = self.coordinator.data.get(self.entity_description.key)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Write a new value to the inverter."""
        ok = await self.coordinator.async_write_register(
            self.entity_description.register,
            int(value),
        )
        if not ok:
            raise SAJWriteFailedError(self.entity_description.register)
