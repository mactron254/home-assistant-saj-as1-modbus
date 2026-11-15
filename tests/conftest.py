"""Shared pytest fixtures for the SAJ AS1 Modbus integration."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
import sys
from typing import Any
from unittest.mock import patch

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pytest_homeassistant_custom_component.common import (  # noqa: E402
    MockConfigEntry,
)

from custom_components.saj_as1_modbus import coordinator as coordinator_module  # noqa: E402
from custom_components.saj_as1_modbus import (  # noqa: E402
    connection_manager as connection_module,
)
from custom_components.saj_as1_modbus.const import (  # noqa: E402
    CONF_DEVICE_ID,
    DOMAIN,
)

HOST = "192.168.1.50"
PORT = 502
DEVICE_ID = 1
UNIQUE_ID = f"{HOST}:{PORT}:{DEVICE_ID}"
ENTRY_DATA = {"host": HOST, "port": PORT, CONF_DEVICE_ID: DEVICE_ID}


def _int16(value: int) -> int:
    """Encode a signed value as an unsigned 16-bit register."""
    return value & 0xFFFF


def default_registers() -> dict[int, int]:
    """Return a realistic AS1 register map."""
    registers: dict[int, int] = {
        0x4004: 1,  # working mode: self use
        0x400F: 0,  # error count
        0x4010: 345,  # heat sink 34.5 °C
        0x4031: 2301,  # grid voltage 230.1 V
        0x4032: 150,  # grid current 1.50 A
        0x4033: 5000,  # grid frequency 50.00 Hz
        0x406D: _int16(-500),  # battery power register (charging 500 W)
        0x406F: 7550,  # SOC 75.5 %
        0x3371: 2,  # user mode: time of use
        0x3608: 0x1F32,  # Monday-Friday, 50 %
        0x361D: 0x7F64,  # every day, 100 %
    }
    power_block = [0] * 13
    power_block[1] = 200  # grid import
    power_block[2] = 0  # grid export
    power_block[4] = 0  # battery discharge
    power_block[7] = 800  # house load
    power_block[12] = 1500  # PV
    for offset, value in enumerate(power_block):
        registers[0x4099 + offset] = value

    bms = [0] * 18
    bms[0] = 1  # number of batteries
    bms[13] = 9800  # SOH 98 %
    bms[14] = 512  # 51.2 V
    bms[15] = _int16(-1000)  # -10.00 A
    bms[16] = 250  # 25.0 °C
    bms[17] = 120  # cycles
    for offset, value in enumerate(bms):
        registers[0xA000 + offset] = value

    for index, address in enumerate((0x40C5, 0x40CD, 0x40D5, 0x40E5, 0x40FD, 0x410D)):
        total = 123456 + index * 1000  # 1234.56 kWh, 1244.56 kWh, ...
        registers[address] = total >> 16
        registers[address + 1] = total & 0xFFFF

    return registers


class FakeResponse:
    """Minimal PyModbus response."""

    def __init__(
        self, registers: list[int] | None = None, exception_code: int | None = None
    ) -> None:
        """Initialize the response."""
        self.registers = registers
        self.exception_code = exception_code

    def isError(self) -> bool:  # noqa: N802 - PyModbus API
        """Return whether this is an exception response."""
        return self.exception_code is not None


class FakeDevice:
    """In-memory SAJ AS1 that hands out fake PyModbus clients."""

    def __init__(self) -> None:
        """Initialize the fake device."""
        self.registers = default_registers()
        self.reachable = True
        self.io_error: Exception | None = None
        self.rejected_ranges: list[tuple[int, int, int]] = []
        self.writes: list[tuple[int, int]] = []
        self.clients: list[FakeClient] = []

    def __call__(self, **kwargs: Any) -> FakeClient:
        """Act as the AsyncModbusTcpClient constructor."""
        client = FakeClient(self, kwargs)
        self.clients.append(client)
        return client

    def reject_block(self, start: int, count: int, code: int = 2) -> None:
        """Answer reads touching a register range with an exception code."""
        self.rejected_ranges.append((start, start + count, code))


class FakeClient:
    """Fake AsyncModbusTcpClient bound to a FakeDevice."""

    def __init__(self, device: FakeDevice, kwargs: dict[str, Any]) -> None:
        """Initialize the client."""
        self.device = device
        self.kwargs = kwargs
        self.connected = False

    async def connect(self) -> bool:
        """Open the fake session."""
        self.connected = self.device.reachable
        return self.connected

    def close(self) -> None:
        """Close the fake session."""
        self.connected = False

    async def read_holding_registers(
        self, address: int, count: int, device_id: int
    ) -> FakeResponse:
        """Serve registers from the device map."""
        if self.device.io_error is not None:
            raise self.device.io_error
        for start, end, code in self.device.rejected_ranges:
            if address < end and start < address + count:
                return FakeResponse(exception_code=code)
        return FakeResponse(
            [self.device.registers.get(address + i, 0) for i in range(count)]
        )

    async def write_register(
        self, address: int, value: int, device_id: int
    ) -> FakeResponse:
        """Store a written register."""
        if self.device.io_error is not None:
            raise self.device.io_error
        self.device.writes.append((address, value))
        self.device.registers[address] = value
        return FakeResponse([value])


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading the custom integration in every test."""


@pytest.fixture(autouse=True)
def no_aio3_delays() -> Generator[None]:
    """Remove the AIO3 pacing delays so tests run fast."""
    delays = {
        "AIOT_DELAY_MS": 0,
        "AIO3_PRE_WRITE_DELAY": 0,
        "AIO3_WRITE_SETTLE_DELAY": 0,
        "AIO3_RECOVERY_DELAY": 0,
        "AIO3_SENSITIVE_RETRY_DELAY": 0,
        "AIO3_WRITE_BATCH_DELAY": 0,
        "AIO3_BATCH_INTER_WRITE_DELAY": 0,
        "AIO3_WRITE_RETRY_DELAY": 0,
    }
    patches = [patch.object(coordinator_module, name, value) for name, value in delays.items()]
    patches.append(patch.object(connection_module, "INITIAL_BACKOFF", 0))
    patches.append(patch.object(connection_module, "FAST_WRITE_RETRY_DELAY", 0))
    for item in patches:
        item.start()
    yield
    for item in patches:
        item.stop()


@pytest.fixture
def mock_modbus() -> Generator[FakeDevice]:
    """Replace the PyModbus TCP client with an in-memory AS1."""
    device = FakeDevice()
    with patch.object(connection_module, "AsyncModbusTcpClient", device):
        yield device


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry for the default endpoint."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"SAJ AS1 ({HOST})",
        data=dict(ENTRY_DATA),
        unique_id=UNIQUE_ID,
        version=2,
    )
