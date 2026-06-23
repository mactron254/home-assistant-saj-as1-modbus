"""Select platform for SAJ AS1 Modbus."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import REGISTER_USER_MODE, USER_MODE_OPTIONS, USER_MODES
from .coordinator import SAJModbusCoordinator
from .entity import SAJEntity
from .exceptions import SAJWriteFailedError

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class SAJSelectEntityDescription(SelectEntityDescription):
    """Description for a writable SAJ select."""

    register: int


SELECT_DESCRIPTIONS: tuple[SAJSelectEntityDescription, ...] = (
    SAJSelectEntityDescription(
        key="user_mode",
        translation_key="user_mode",
        options=USER_MODE_OPTIONS,
        entity_category=EntityCategory.CONFIG,
        register=REGISTER_USER_MODE,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SAJ AS1 select entities."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        SAJSelect(coordinator, description) for description in SELECT_DESCRIPTIONS
    )


class SAJSelect(SAJEntity, SelectEntity):
    """Writable SAJ AS1 select entity."""

    entity_description: SAJSelectEntityDescription

    def __init__(
        self,
        coordinator: SAJModbusCoordinator,
        description: SAJSelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        return USER_MODES.get(value)

    async def async_select_option(self, option: str) -> None:
        """Select a new user mode."""
        for key, name in USER_MODES.items():
            if name == option:
                ok = await self.coordinator.async_write_register(
                    self.entity_description.register,
                    key,
                )
                if not ok:
                    raise SAJWriteFailedError(self.entity_description.register)
                return
