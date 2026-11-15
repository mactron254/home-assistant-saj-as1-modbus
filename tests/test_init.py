"""Setup, entity and device tests for SAJ AS1 Modbus."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.saj_as1_modbus.const import DOMAIN
from custom_components.saj_as1_modbus.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import ENTRY_DATA, UNIQUE_ID, FakeDevice


def entry_state(entry: MockConfigEntry) -> ConfigEntryState:
    """Return the current entry state (avoids mypy narrowing across awaits)."""
    state: ConfigEntryState = entry.state
    return state


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add and set up a config entry."""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def entity_id(hass: HomeAssistant, entry: MockConfigEntry, platform: str, key: str) -> str:
    """Return the entity id of one of the entry's entities."""
    result = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}_{key}"
    )
    assert result is not None, key
    return result


def state(hass: HomeAssistant, entry: MockConfigEntry, platform: str, key: str) -> str:
    """Return the state of one of the entry's entities."""
    current = hass.states.get(entity_id(hass, entry, platform, key))
    assert current is not None, key
    return current.state


async def test_setup_and_unload(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """The entry loads, publishes decoded values and unloads cleanly."""
    await setup_entry(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    assert state(hass, mock_config_entry, Platform.SENSOR, "total_pv_power") == "1500"
    assert state(hass, mock_config_entry, Platform.SENSOR, "grid_power_signed") == "200"
    assert state(hass, mock_config_entry, Platform.SENSOR, "bat1_soc") == "75.5"
    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "total_pv_energy") == "1234.56"
    )
    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "working_mode_name")
        == "self_use"
    )
    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "battery_capacity_real")
        == "5.02"
    )
    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "battery_time_to_full") == "2.5"
    )
    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "battery_time_to_empty")
        == STATE_UNKNOWN
    )
    assert state(hass, mock_config_entry, Platform.SELECT, "user_mode") == "time_of_use"
    assert (
        state(hass, mock_config_entry, Platform.NUMBER, "first_charge_power_pct")
        == "50.0"
    )
    assert state(hass, mock_config_entry, Platform.BINARY_SENSOR, "is_connected") == "on"

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert entry_state(mock_config_entry) is ConfigEntryState.NOT_LOADED


async def test_entity_ids_use_english_names(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """Entity ids are generated from the English translations."""
    await setup_entry(hass, mock_config_entry)

    assert (
        entity_id(hass, mock_config_entry, Platform.SENSOR, "total_pv_power")
        == "sensor.saj_as1_inverter_total_pv_power"
    )
    assert (
        entity_id(hass, mock_config_entry, Platform.SELECT, "user_mode")
        == "select.saj_as1_inverter_user_mode"
    )


async def test_device_info_is_unchanged(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """All entities belong to one device with the same info as before."""
    await setup_entry(hass, mock_config_entry)

    devices = dr.async_entries_for_config_entry(
        dr.async_get(hass), mock_config_entry.entry_id
    )
    assert len(devices) == 1
    device = devices[0]
    assert device.identifiers == {(DOMAIN, mock_config_entry.entry_id)}
    assert device.name == "SAJ AS1 Inverter"
    assert device.manufacturer == "SAJ Electric"
    assert device.model == "AS1"
    assert mock_config_entry.unique_id == UNIQUE_ID


async def test_setup_retries_when_unreachable(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """An unreachable inverter puts the entry in setup retry."""
    mock_modbus.reachable = False
    await setup_entry(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_migration_rejects_future_versions(
    hass: HomeAssistant, mock_modbus: FakeDevice
) -> None:
    """Entries created by a newer version are not downgraded."""
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=UNIQUE_ID, data=dict(ENTRY_DATA), version=3
    )
    await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.MIGRATION_ERROR


async def test_migration_removes_scan_interval(
    hass: HomeAssistant, mock_modbus: FakeDevice
) -> None:
    """Version 1 entries lose the user configurable scan interval."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=UNIQUE_ID,
        data={**ENTRY_DATA, "scan_interval": 10},
        options={"scan_interval": 10},
        version=1,
    )
    await setup_entry(hass, entry)

    assert entry.version == 2
    assert "scan_interval" not in entry.data
    assert "scan_interval" not in entry.options


async def test_diagnostics_redact_host(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """Diagnostics never expose the inverter address."""
    await setup_entry(hass, mock_config_entry)

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert result["entry"]["data"]["host"] == "**REDACTED**"
    assert result["entry"]["unique_id"] == "**REDACTED**"
    assert result["data"]["total_pv_power"] == 1500
    assert result["polling"]["buckets"]["HIGH"]["read_count"] == 1


async def test_action_description_loads(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """services.yaml parses and the action is described."""
    from homeassistant.helpers.service import async_get_all_descriptions

    await setup_entry(hass, mock_config_entry)
    descriptions = await async_get_all_descriptions(hass)

    fields = descriptions[DOMAIN]["set_profile"]["fields"]
    assert set(fields) == {
        "config_entry_id",
        "charge_power_pct",
        "discharge_power_pct",
        "user_mode",
    }
    assert fields["user_mode"]["selector"]["select"]["translation_key"] == "user_mode"
