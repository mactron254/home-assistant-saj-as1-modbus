"""Config flow tests for SAJ AS1 Modbus."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.saj_as1_modbus.const import DOMAIN

from .conftest import ENTRY_DATA, HOST, UNIQUE_ID, FakeDevice

OLD_HOST = "192.168.1.99"


async def _start_user_flow(hass: HomeAssistant) -> str:
    """Start the user step and return the flow id."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return result["flow_id"]


async def test_user_flow_creates_entry(
    hass: HomeAssistant, mock_modbus: FakeDevice
) -> None:
    """A reachable inverter is added with its endpoint as unique id."""
    flow_id = await _start_user_flow(hass)

    result = await hass.config_entries.flow.async_configure(flow_id, dict(ENTRY_DATA))

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"SAJ AS1 ({HOST})"
    assert result["data"] == ENTRY_DATA
    assert result["result"].unique_id == UNIQUE_ID


async def test_user_flow_recovers_from_cannot_connect(
    hass: HomeAssistant, mock_modbus: FakeDevice
) -> None:
    """An unreachable inverter shows cannot_connect and the form can be retried."""
    mock_modbus.reachable = False
    flow_id = await _start_user_flow(hass)

    result = await hass.config_entries.flow.async_configure(flow_id, dict(ENTRY_DATA))
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    mock_modbus.reachable = True
    result = await hass.config_entries.flow.async_configure(flow_id, dict(ENTRY_DATA))
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_unexpected_error(
    hass: HomeAssistant, mock_modbus: FakeDevice
) -> None:
    """Unexpected errors are reported as unknown."""
    mock_modbus.io_error = RuntimeError("boom")
    flow_id = await _start_user_flow(hass)

    result = await hass.config_entries.flow.async_configure(flow_id, dict(ENTRY_DATA))

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_user_flow_same_endpoint_aborts(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """The same endpoint cannot be added twice."""
    mock_config_entry.add_to_hass(hass)
    flow_id = await _start_user_flow(hass)

    result = await hass.config_entries.flow.async_configure(flow_id, dict(ENTRY_DATA))

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure_updates_address_unique_id_and_title(
    hass: HomeAssistant, mock_modbus: FakeDevice
) -> None:
    """Reconfiguring stores the new address and its unique id."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"SAJ AS1 ({OLD_HOST})",
        unique_id=f"{OLD_HOST}:502:1",
        data={**ENTRY_DATA, CONF_HOST: OLD_HOST},
        version=2,
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], dict(ENTRY_DATA)
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_HOST] == HOST
    assert entry.unique_id == UNIQUE_ID
    assert entry.title == f"SAJ AS1 ({HOST})"


async def test_reconfigure_to_an_endpoint_in_use_aborts(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """An entry cannot be moved onto an endpoint another entry already uses."""
    mock_config_entry.add_to_hass(hass)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{OLD_HOST}:502:1",
        data={**ENTRY_DATA, CONF_HOST: OLD_HOST},
        version=2,
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], dict(ENTRY_DATA)
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == OLD_HOST


async def test_reconfigure_cannot_connect(
    hass: HomeAssistant, mock_modbus: FakeDevice, mock_config_entry: MockConfigEntry
) -> None:
    """Reconfiguring to an unreachable address shows an error."""
    mock_config_entry.add_to_hass(hass)
    mock_modbus.reachable = False

    result = await mock_config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**ENTRY_DATA, CONF_HOST: OLD_HOST}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
