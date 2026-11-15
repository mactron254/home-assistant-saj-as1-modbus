"""Polling and write behavior tests for SAJ AS1 Modbus."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.saj_as1_modbus.const import DOMAIN
from custom_components.saj_as1_modbus.exceptions import SAJWriteFailedError

from .conftest import FakeDevice
from .test_init import entity_id, setup_entry, state


async def _next_cycle(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float = 31
) -> None:
    """Advance time so the coordinator runs its next poll cycle."""
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass)
    # Coordinator refreshes run as background tasks.
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_failed_energy_block_publishes_no_zeros(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """A rejected energy block leaves the counters unknown instead of 0 kWh."""
    mock_modbus.reject_block(0x40C5, 74, code=4)
    await setup_entry(hass, mock_config_entry)

    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "total_pv_energy")
        == STATE_UNKNOWN
    )
    assert state(hass, mock_config_entry, Platform.SENSOR, "total_pv_power") == "1500"


async def test_zero_slot_percentage_is_reported(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """A slot power of 0 % is no longer shown as 100 %."""
    mock_modbus.registers[0x361D] = 0x7F00
    await setup_entry(hass, mock_config_entry)

    assert (
        state(hass, mock_config_entry, Platform.NUMBER, "first_discharge_power_pct")
        == "0.0"
    )


async def test_entities_become_unavailable_after_outage(
    hass: HomeAssistant,
    mock_modbus: FakeDevice,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Short outages keep the last values, longer ones make entities unavailable."""
    await setup_entry(hass, mock_config_entry)
    mock_modbus.reachable = False

    for _ in range(2):
        await _next_cycle(hass, freezer)
        assert (
            state(hass, mock_config_entry, Platform.SENSOR, "total_pv_power") == "1500"
        )
    assert (
        state(hass, mock_config_entry, Platform.BINARY_SENSOR, "is_connected") == "off"
    )

    await _next_cycle(hass, freezer)
    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "total_pv_power")
        == STATE_UNAVAILABLE
    )

    mock_modbus.reachable = True
    mock_modbus.registers[0x4099 + 12] = 900
    await _next_cycle(hass, freezer, 61)
    assert state(hass, mock_config_entry, Platform.SENSOR, "total_pv_power") == "900"
    assert state(hass, mock_config_entry, Platform.BINARY_SENSOR, "is_connected") == "on"


async def test_repair_issue_only_after_long_outage(
    hass: HomeAssistant,
    mock_modbus: FakeDevice,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The repair issue is per entry, delayed and removed on recovery."""
    await setup_entry(hass, mock_config_entry)
    issue_id = f"connection_unavailable_{mock_config_entry.entry_id}"
    registry = ir.async_get(hass)
    mock_modbus.reachable = False

    await _next_cycle(hass, freezer)
    assert registry.async_get_issue(DOMAIN, issue_id) is None

    for _ in range(16):
        await _next_cycle(hass, freezer, 61)
    issue = registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_placeholders is not None
    assert issue.translation_placeholders["minutes"] == "15"

    mock_modbus.reachable = True
    await _next_cycle(hass, freezer, 61)
    assert registry.async_get_issue(DOMAIN, issue_id) is None


async def test_unload_removes_repair_issue(
    hass: HomeAssistant,
    mock_modbus: FakeDevice,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Unloading an entry removes its repair issue."""
    await setup_entry(hass, mock_config_entry)
    issue_id = f"connection_unavailable_{mock_config_entry.entry_id}"
    mock_modbus.reachable = False
    for _ in range(17):
        await _next_cycle(hass, freezer, 61)
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None


async def test_charge_power_write_keeps_weekday_mask(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """Writing a slot power keeps the weekdays configured in the SAJ app."""
    await setup_entry(hass, mock_config_entry)

    await hass.services.async_call(
        Platform.NUMBER,
        "set_value",
        {
            "entity_id": entity_id(
                hass, mock_config_entry, Platform.NUMBER, "first_charge_power_pct"
            ),
            "value": 60,
        },
        blocking=True,
    )

    assert mock_modbus.writes == [(0x3608, 0x1F3C)]
    assert (
        state(hass, mock_config_entry, Platform.NUMBER, "first_charge_power_pct")
        == "60.0"
    )


async def test_empty_weekday_mask_falls_back_to_every_day(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """A slot without days is written for every day of the week."""
    mock_modbus.registers[0x361D] = 0x0064
    await setup_entry(hass, mock_config_entry)

    await hass.services.async_call(
        Platform.NUMBER,
        "set_value",
        {
            "entity_id": entity_id(
                hass, mock_config_entry, Platform.NUMBER, "first_discharge_power_pct"
            ),
            "value": 40,
        },
        blocking=True,
    )

    assert mock_modbus.writes == [(0x361D, 0x7F28)]


async def test_select_user_mode(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """Selecting a user mode writes its register value."""
    await setup_entry(hass, mock_config_entry)
    select_id = entity_id(hass, mock_config_entry, Platform.SELECT, "user_mode")

    await hass.services.async_call(
        Platform.SELECT,
        "select_option",
        {"entity_id": select_id, "option": "self_use"},
        blocking=True,
    )

    assert mock_modbus.writes == [(0x3371, 1)]
    assert state(hass, mock_config_entry, Platform.SELECT, "user_mode") == "self_use"


async def test_set_profile_accepts_legacy_option(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """The action writes powers first, mode last, and accepts old labels."""
    await setup_entry(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN,
        "set_profile",
        {"charge_power_pct": 30, "user_mode": "Autoconsumo"},
        blocking=True,
    )

    assert mock_modbus.writes == [(0x3608, 0x1F1E), (0x3371, 1)]


async def test_set_profile_requires_a_value(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """Calling the action without any value is rejected."""
    await setup_entry(hass, mock_config_entry)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "set_profile", {}, blocking=True)


async def test_set_profile_targets_a_config_entry(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """The action can name the config entry explicitly."""
    await setup_entry(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN,
        "set_profile",
        {"config_entry_id": mock_config_entry.entry_id, "discharge_power_pct": 80},
        blocking=True,
    )

    assert mock_modbus.writes == [(0x361D, 0x7F50)]


async def test_failed_write_raises(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """A write that keeps failing is reported to the user."""
    await setup_entry(hass, mock_config_entry)
    mock_modbus.reachable = False

    with pytest.raises(SAJWriteFailedError):
        await hass.services.async_call(
            Platform.SELECT,
            "select_option",
            {
                "entity_id": entity_id(
                    hass, mock_config_entry, Platform.SELECT, "user_mode"
                ),
                "option": "backup",
            },
            blocking=True,
        )


async def test_set_profile_needs_entry_with_several_inverters(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """With two loaded inverters the action must name one."""
    await setup_entry(hass, mock_config_entry)
    second = MockConfigEntry(
        domain=DOMAIN,
        unique_id="SECOND",
        data={"host": "192.168.1.51", "port": 502, "device_id": 1},
        version=2,
    )
    await setup_entry(hass, second)

    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, "set_profile", {"charge_power_pct": 20}, blocking=True
        )
    assert err.value.translation_key == "entry_required"
