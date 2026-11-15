"""Tests of the Modbus session handling against a fake PyModbus client."""

from __future__ import annotations

from pymodbus.exceptions import ModbusIOException
import pytest

from custom_components.saj_as1_modbus.connection_manager import ModbusConnectionManager
from custom_components.saj_as1_modbus.exceptions import (
    ConnectFailedError,
    ModbusReadError,
    ModbusReadRejectedError,
    ModbusWriteError,
    ModbusWriteRejectedError,
    ReconnectionNeededError,
)

from .conftest import DEVICE_ID, HOST, PORT, FakeDevice


def _manager(connect_attempts: int = 3) -> ModbusConnectionManager:
    """Return a manager for the default endpoint."""
    return ModbusConnectionManager(
        host=HOST, port=PORT, device_id=DEVICE_ID, connect_attempts=connect_attempts
    )


async def test_properties_and_session_lifecycle(mock_modbus: FakeDevice) -> None:
    """The session opens on demand and closes on request."""
    manager = _manager()
    assert (manager.host, manager.port, manager.device_id) == (HOST, PORT, DEVICE_ID)
    assert not manager.connected

    assert await manager.read_registers(0x406F, 1) == [7550]
    assert manager.connected
    assert await manager.read_registers(0x4004, 1) == [1]
    assert len(mock_modbus.clients) == 1

    await manager.close()
    assert not manager.connected


async def test_connect_retries_then_fails(mock_modbus: FakeDevice) -> None:
    """An unreachable host is tried a bounded number of times."""
    mock_modbus.connect_error = OSError("host unreachable")

    with pytest.raises(ConnectFailedError, match="after 3 attempts"):
        await _manager().read_registers(0x406F, 1)
    assert len(mock_modbus.clients) == 3


async def test_broken_session_is_discarded(mock_modbus: FakeDevice) -> None:
    """An I/O error closes the session so the next read reconnects."""
    manager = _manager()
    await manager.read_registers(0x406F, 1)
    mock_modbus.io_error = ModbusIOException("eof")  # type: ignore[no-untyped-call]

    with pytest.raises(ReconnectionNeededError):
        await manager.read_registers(0x406F, 1)
    assert not manager.connected

    mock_modbus.io_error = None
    assert await manager.read_registers(0x406F, 1) == [7550]
    assert len(mock_modbus.clients) == 2


async def test_rejected_and_short_reads(mock_modbus: FakeDevice) -> None:
    """Exception responses and short answers are reported as read errors."""
    manager = _manager()
    mock_modbus.reject_block(0x4004, 1, code=2)
    with pytest.raises(ModbusReadRejectedError, match="illegal data address"):
        await manager.read_registers(0x4004, 1)

    mock_modbus.rejected_ranges.clear()
    mock_modbus.reject_block(0x4004, 1, code=6)
    with pytest.raises(ModbusReadError, match="busy") as err:
        await manager.read_registers(0x4004, 1)
    assert not isinstance(err.value, ModbusReadRejectedError)

    mock_modbus.rejected_ranges.clear()
    mock_modbus.short_reads = True
    with pytest.raises(ModbusReadError, match="too few registers"):
        await manager.read_registers(0x4099, 13)


async def test_write_retries_a_broken_session_once(mock_modbus: FakeDevice) -> None:
    """A write that hits a dead session is retried once on a new one."""
    mock_modbus.fail_writes = 1

    await _manager().write_register(0x3371, 1)

    assert mock_modbus.write_attempts == [(0x3371, 1), (0x3371, 1)]
    assert mock_modbus.writes == [(0x3371, 1)]


async def test_write_errors(mock_modbus: FakeDevice) -> None:
    """Busy answers are retried once, illegal values are not retried."""
    manager = _manager()
    mock_modbus.rejected_writes[0x3371] = 6
    with pytest.raises(ModbusWriteError, match="busy"):
        await manager.write_register(0x3371, 1)
    assert len(mock_modbus.write_attempts) == 2

    mock_modbus.write_attempts.clear()
    mock_modbus.rejected_writes[0x3371] = 3
    with pytest.raises(ModbusWriteRejectedError):
        await manager.write_register(0x3371, 9)
    assert len(mock_modbus.write_attempts) == 1

    mock_modbus.rejected_writes.clear()
    mock_modbus.fail_writes = 2
    with pytest.raises(ReconnectionNeededError):
        await manager.write_register(0x3371, 1)


async def test_close_ignores_transport_errors(mock_modbus: FakeDevice) -> None:
    """A transport that fails while closing does not raise."""
    manager = _manager()
    await manager.read_registers(0x406F, 1)
    mock_modbus.close_error = RuntimeError("transport already gone")

    await manager.close()

    assert not manager.connected
