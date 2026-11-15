"""Connection robustness tests (cancellation, stale values, partial failures)."""

from __future__ import annotations

from datetime import timedelta
import json
import logging
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.config_entries import ConfigEntryState, SOURCE_USER
from homeassistant.const import STATE_UNAVAILABLE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.saj_as1_modbus import coordinator as coordinator_module
from custom_components.saj_as1_modbus.const import DOMAIN
from custom_components.saj_as1_modbus.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.saj_as1_modbus.exceptions import SAJWriteFailedError

from .conftest import ENTRY_DATA, HOST, FakeDevice
from .test_init import entity_id, setup_entry, state


async def _next_cycle(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float = 31
) -> None:
    """Advance time so the coordinator runs its next poll cycle."""
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


def _energy_registers(device: FakeDevice, value: int) -> None:
    """Set every lifetime energy counter to the same raw value."""
    for address in (0x40C5, 0x40CD, 0x40D5, 0x40E5, 0x40FD, 0x410D):
        device.registers[address] = value >> 16
        device.registers[address + 1] = value & 0xFFFF


async def test_timed_out_cycle_stops_talking_to_the_stick(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """A cycle cut by the timeout does not go on reading the next blocks.

    PyModbus turns the cancellation into a Modbus error; before, the grid L1
    read swallowed it and the cycle went on to read the BMS block.
    """
    await setup_entry(hass, mock_config_entry)
    coordinator = mock_config_entry.runtime_data.coordinator
    mock_modbus.hang_addresses.add(0x4031)
    coordinator._last_high_update = 0.0  # noqa: SLF001 - make the buckets due
    coordinator._last_medium_update = 0.0  # noqa: SLF001
    mock_modbus.reads.clear()

    with patch.object(coordinator_module, "POLL_CYCLE_TIMEOUT", 0.2):
        await coordinator.async_refresh()

    assert 0x4031 in mock_modbus.reads
    assert 0xA000 not in mock_modbus.reads[mock_modbus.reads.index(0x4031) :]
    assert coordinator.consecutive_failures == 1
    assert not coordinator.connection.connected


async def test_write_does_not_revive_a_failing_coordinator(
    hass: HomeAssistant,
    mock_modbus: FakeDevice,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A successful write keeps entities unavailable while reads fail."""
    await setup_entry(hass, mock_config_entry)
    mock_modbus.reject_block(0x4000, 0x200, code=4)
    for _ in range(3):
        await _next_cycle(hass, freezer)
    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "total_pv_power")
        == STATE_UNAVAILABLE
    )

    # Entity actions skip unavailable entities, the integration action does not.
    await hass.services.async_call(
        DOMAIN, "set_profile", {"user_mode": "self_use"}, blocking=True
    )

    assert mock_modbus.writes == [(0x3371, 1)]
    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "total_pv_power")
        == STATE_UNAVAILABLE
    )


async def test_one_failing_block_is_not_a_lost_connection(
    hass: HomeAssistant,
    mock_modbus: FakeDevice,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A block that keeps failing does not mark the inverter as unreachable."""
    await setup_entry(hass, mock_config_entry)
    mock_modbus.reject_block(0x40C5, 74, code=4)

    for _ in range(6):
        await _next_cycle(hass, freezer, 301)

    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "total_pv_energy")
        == STATE_UNAVAILABLE
    )
    assert state(hass, mock_config_entry, Platform.SENSOR, "total_pv_power") == "1500"
    assert state(hass, mock_config_entry, Platform.BINARY_SENSOR, "is_connected") == "on"
    assert (
        ir.async_get(hass).async_get_issue(
            DOMAIN, f"connection_unavailable_{mock_config_entry.entry_id}"
        )
        is None
    )


async def test_connection_state_shows_off_during_outage(
    hass: HomeAssistant,
    mock_modbus: FakeDevice,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The connection sensor reports off instead of becoming unavailable."""
    await setup_entry(hass, mock_config_entry)
    mock_modbus.reachable = False

    for _ in range(4):
        await _next_cycle(hass, freezer, 61)

    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "total_pv_power")
        == STATE_UNAVAILABLE
    )
    assert (
        state(hass, mock_config_entry, Platform.BINARY_SENSOR, "is_connected") == "off"
    )


async def test_outage_uses_one_connect_attempt_per_cycle(
    hass: HomeAssistant,
    mock_modbus: FakeDevice,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Once the inverter is down each cycle tries to connect only once."""
    await setup_entry(hass, mock_config_entry)
    mock_modbus.reachable = False

    await _next_cycle(hass, freezer)
    first = len(mock_modbus.clients)
    await _next_cycle(hass, freezer)

    assert len(mock_modbus.clients) - first == 1


async def test_circuit_breaker_warns_once_per_outage(
    hass: HomeAssistant,
    mock_modbus: FakeDevice,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A long outage logs the circuit breaker warning only once."""
    await setup_entry(hass, mock_config_entry)
    mock_modbus.reachable = False

    with caplog.at_level(logging.WARNING):
        for _ in range(12):
            await _next_cycle(hass, freezer, 61)

    warnings = [
        record
        for record in caplog.records
        if "circuit breaker open" in record.getMessage()
        and record.levelno == logging.WARNING
    ]
    assert len(warnings) == 1


async def test_setup_fails_when_no_block_answers(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """An inverter that rejects every block is not set up with empty data."""
    mock_modbus.reject_block(0x0000, 0xFFFF, code=4)
    await setup_entry(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_grid_l1_values_expire(
    hass: HomeAssistant,
    mock_modbus: FakeDevice,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Grid L1 values are not reused forever when only their block fails."""
    await setup_entry(hass, mock_config_entry)
    mock_modbus.reject_block(0x4031, 3, code=4)

    for _ in range(4):
        await _next_cycle(hass, freezer, 61)
    assert state(hass, mock_config_entry, Platform.SENSOR, "grid_voltage_l1") == "230.1"

    await _next_cycle(hass, freezer, 61)
    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "grid_voltage_l1")
        == STATE_UNAVAILABLE
    )
    assert state(hass, mock_config_entry, Platform.SENSOR, "radiator_temp") == "34.5"

    mock_modbus.rejected_ranges.clear()
    await _next_cycle(hass, freezer, 61)
    assert state(hass, mock_config_entry, Platform.SENSOR, "grid_voltage_l1") == "230.1"


async def test_derived_values_follow_their_inputs(
    hass: HomeAssistant,
    mock_modbus: FakeDevice,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Battery capacity becomes unavailable together with the battery SOH."""
    await setup_entry(hass, mock_config_entry)
    mock_modbus.reject_block(0xA000, 18, code=4)

    for _ in range(5):
        await _next_cycle(hass, freezer, 61)

    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "bat1_soh") == STATE_UNAVAILABLE
    )
    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "battery_capacity_real")
        == STATE_UNAVAILABLE
    )
    assert state(hass, mock_config_entry, Platform.SENSOR, "bat1_soc") == "75.5"


async def test_user_mode_expires(
    hass: HomeAssistant,
    mock_modbus: FakeDevice,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The last user mode is not shown forever when its register fails."""
    await setup_entry(hass, mock_config_entry)
    mock_modbus.reject_block(0x3371, 1, code=4)

    for _ in range(5):
        await _next_cycle(hass, freezer, 301)

    assert (
        state(hass, mock_config_entry, Platform.SELECT, "user_mode") == STATE_UNAVAILABLE
    )
    assert (
        state(hass, mock_config_entry, Platform.NUMBER, "first_charge_power_pct")
        == "50.0"
    )


async def test_rejected_write_is_not_retried(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """An illegal address or value answer is final."""
    await setup_entry(hass, mock_config_entry)
    mock_modbus.rejected_writes[0x3371] = 2

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

    assert mock_modbus.write_attempts == [(0x3371, 3)]


async def test_set_profile_reports_what_was_not_written(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """A partial profile names the fields that could not be written."""
    await setup_entry(hass, mock_config_entry)
    mock_modbus.rejected_writes[0x3371] = 2

    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call(
            DOMAIN,
            "set_profile",
            {"charge_power_pct": 30, "user_mode": "backup"},
            blocking=True,
        )

    assert err.value.translation_key == "profile_write_failed"
    assert err.value.translation_placeholders == {"failed": "user_mode"}
    assert mock_modbus.writes == [(0x3608, 0x1F1E)]


async def test_energy_counters_ignore_zero_readings(
    hass: HomeAssistant,
    mock_modbus: FakeDevice,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Zero readings of lifetime counters are not published."""
    await setup_entry(hass, mock_config_entry)

    _energy_registers(mock_modbus, 0)
    await _next_cycle(hass, freezer, 301)
    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "total_pv_energy") == "1234.56"
    )

    _energy_registers(mock_modbus, 200000)
    mock_modbus.registers[0x40C5] = 0
    mock_modbus.registers[0x40C6] = 0
    await _next_cycle(hass, freezer, 301)
    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "total_pv_energy") == "1234.56"
    )
    assert (
        state(hass, mock_config_entry, Platform.SENSOR, "total_load_energy") == "2000.0"
    )


async def test_config_flow_tries_to_connect_once(
    hass: HomeAssistant, mock_modbus: FakeDevice
) -> None:
    """The setup form answers after one attempt when the host is down."""
    mock_modbus.reachable = False
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], dict(ENTRY_DATA)
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert len(mock_modbus.clients) == 1


async def test_diagnostics_never_contain_the_address(
    hass: HomeAssistant,
    mock_modbus: FakeDevice,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Error texts are redacted and the raw power flows are included."""
    await setup_entry(hass, mock_config_entry)
    mock_modbus.reachable = False
    await _next_cycle(hass, freezer)

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert HOST not in json.dumps(result)
    assert result["connection"]["last_error_type"]
    assert result["raw_power_flows"]["0x409A_grid_to_load"] == 200
    assert result["raw_power_flows"]["0x40A5_total_pv_power"] == 1500
