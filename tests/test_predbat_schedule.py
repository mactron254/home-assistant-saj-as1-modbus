"""PredBat schedule behavior tests."""

from __future__ import annotations

import asyncio
from datetime import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

from custom_components.saj_as1_modbus import coordinator as coordinator_module
from custom_components.saj_as1_modbus.const import (
    FIRST_SCHEDULE_BIT,
    REGISTER_CHARGE_END_TIME,
    REGISTER_CHARGE_POWER_PCT,
    REGISTER_CHARGE_SCHEDULE_ENABLE,
    REGISTER_CHARGE_START_TIME,
    REGISTER_DISCHARGE_END_TIME,
    REGISTER_DISCHARGE_POWER_PCT,
    REGISTER_DISCHARGE_SCHEDULE_ENABLE,
    REGISTER_DISCHARGE_START_TIME,
    REGISTER_USER_MODE,
)
from custom_components.saj_as1_modbus.coordinator import SAJModbusCoordinator
from custom_components.saj_as1_modbus.exceptions import ModbusReadError
from custom_components.saj_as1_modbus.time import SAJTime, TIME_DESCRIPTIONS


class FakeConnection:
    """Minimal connection used by schedule helper tests."""

    def __init__(self, values: list[list[int] | Exception]) -> None:
        self.values = list(values)
        self.reads: list[tuple[int, int]] = []
        self.close_count = 0

    async def close(self) -> None:
        """Record a close request."""
        self.close_count += 1

    async def read_registers(self, address: int, count: int) -> list[int]:
        """Return or raise the next configured result."""
        self.reads.append((address, count))
        result = self.values.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def test_config_reads_documented_schedule_blocks() -> None:
    """Configuration polling reads both contiguous first-slot blocks."""
    calls: list[tuple[int, str, int]] = []

    async def no_op() -> None:
        return None

    async def user_mode() -> int:
        return 1

    async def read_block(address: int, label: str, count: int = 1) -> list[int]:
        calls.append((address, label, count))
        if address == 0x3604:
            return [0b101, 0b110, 0x061E, 0x071F, 0x7F50]
        return [0x1200, 0x173B, 0x7F64]

    coordinator = SimpleNamespace(
        _schedule_masks={},
        _wait_for_write_priority=no_op,
        _delay_between_blocks=no_op,
        _read_user_mode_with_retry=user_mode,
        _read_sensitive_register=read_block,
    )
    data = asyncio.run(
        SAJModbusCoordinator._read_config(coordinator)  # type: ignore[arg-type]
    )

    assert calls == [
        (0x3604, "Charge schedule block", 5),
        (0x361B, "Discharge schedule block", 3),
    ]
    assert data["first_charge_schedule_enabled"] is True
    assert data["first_discharge_schedule_enabled"] is False
    assert data["first_charge_start_time"] == time(6, 30)
    assert data["first_charge_end_time"] == time(7, 31)
    assert data["first_discharge_start_time"] == time(18, 0)
    assert data["first_discharge_end_time"] == time(23, 59)
    assert data["first_charge_power_pct"] == 80
    assert data["first_discharge_power_pct"] == 100


def test_schedule_enable_preserves_mask_and_skips_idempotent_write() -> None:
    """Switch changes preserve other slots and do not repeat equal writes."""
    writes: list[dict[int, int]] = []
    cache_updates: list[tuple[int, int]] = []

    async def run_case(original: int, enabled: bool) -> bool:
        connection = FakeConnection([[original]])

        async def read_mask(
            address: int,
            label: str,
            count: int = 1,
        ) -> list[int]:
            return await connection.read_registers(address, count)

        async def apply(values: dict[int, int]) -> dict[int, bool]:
            writes.append(values)
            return {address: True for address in values}

        coordinator = SimpleNamespace(
            _pending_writes=0,
            _write_requested=False,
            _write_lock=asyncio.Lock(),
            _schedule_masks={},
            connection=connection,
            last_error_type=None,
            _read_sensitive_register=read_mask,
            _apply_write_batch=apply,
            _update_write_cache=lambda address, value: cache_updates.append(
                (address, value)
            ),
        )
        return await SAJModbusCoordinator.async_set_schedule_enabled(
            coordinator,  # type: ignore[arg-type]
            REGISTER_CHARGE_SCHEDULE_ENABLE,
            enabled,
        )

    old_delay: Any = getattr(coordinator_module, "AIO3_PRE_WRITE_DELAY")
    setattr(coordinator_module, "AIO3_PRE_WRITE_DELAY", 0)
    try:
        assert asyncio.run(run_case(0b10101010, True)) is True
        assert writes == [{REGISTER_CHARGE_SCHEDULE_ENABLE: 0b10101011}]
        writes.clear()
        assert asyncio.run(run_case(0b10101011, True)) is True
        assert writes == []
        assert cache_updates[-1] == (
            REGISTER_CHARGE_SCHEDULE_ENABLE,
            0b10101011,
        )
    finally:
        setattr(coordinator_module, "AIO3_PRE_WRITE_DELAY", old_delay)


def test_schedule_enable_rejects_write_when_mask_read_fails() -> None:
    """A switch write is rejected if the complete original mask is unknown."""
    wrote = False
    connection = FakeConnection([])

    async def read_mask(address: int, label: str, count: int = 1) -> list[int]:
        raise ModbusReadError("mask unavailable")

    async def apply(values: dict[int, int]) -> dict[int, bool]:
        nonlocal wrote
        wrote = True
        return {}

    coordinator = SimpleNamespace(
        _pending_writes=0,
        _write_requested=False,
        _write_lock=asyncio.Lock(),
        connection=connection,
        last_error_type=None,
        _read_sensitive_register=read_mask,
        _apply_write_batch=apply,
    )
    old_delay: Any = getattr(coordinator_module, "AIO3_PRE_WRITE_DELAY")
    setattr(coordinator_module, "AIO3_PRE_WRITE_DELAY", 0)
    try:
        result = asyncio.run(
            SAJModbusCoordinator.async_set_schedule_enabled(
                coordinator,  # type: ignore[arg-type]
                REGISTER_CHARGE_SCHEDULE_ENABLE,
                True,
            )
        )
    finally:
        setattr(coordinator_module, "AIO3_PRE_WRITE_DELAY", old_delay)

    assert result is False
    assert wrote is False


def test_sensitive_block_retries_after_aio3_failure() -> None:
    """Sensitive block reads close and retry after a transient AIO3 error."""
    connection = FakeConnection(
        [ModbusReadError("temporary"), [1, 2, 3, 4, 5]]
    )
    coordinator = SimpleNamespace(connection=connection)
    old_delay: Any = getattr(coordinator_module, "AIO3_SENSITIVE_RETRY_DELAY")
    setattr(coordinator_module, "AIO3_SENSITIVE_RETRY_DELAY", 0)
    try:
        result = asyncio.run(
            SAJModbusCoordinator._read_sensitive_register(
                coordinator,  # type: ignore[arg-type]
                0x3604,
                "Charge schedule block",
                5,
            )
        )
    finally:
        setattr(coordinator_module, "AIO3_SENSITIVE_RETRY_DELAY", old_delay)

    assert result == [1, 2, 3, 4, 5]
    assert connection.reads == [(0x3604, 5), (0x3604, 5)]
    assert connection.close_count == 1


def test_schedule_cache_decodes_time() -> None:
    """Successful writes update the time entity without another poll."""
    updated: dict[str, Any] = {}
    coordinator = SimpleNamespace(
        data={},
        _config_cache={},
        _schedule_masks={},
        unavailable_keys={"first_charge_end_time"},
        _last_user_mode=None,
        async_set_updated_data=lambda data: updated.update(data),
    )

    SAJModbusCoordinator._update_write_cache(
        coordinator,  # type: ignore[arg-type]
        REGISTER_CHARGE_END_TIME,
        0x173B,
    )

    assert coordinator._config_cache["first_charge_end_time"] == time(23, 59)
    assert updated["first_charge_end_time"] == time(23, 59)
    assert "first_charge_end_time" not in coordinator.unavailable_keys


def test_no_soc_configuration_register_is_accessed() -> None:
    """PredBat controls schedules but never physical SOC configuration."""
    integration = Path(__file__).resolve().parents[1] / "custom_components"
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in integration.rglob("*.py")
    )
    assert "0x3373" not in source
    assert "0x3374" not in source
    assert FIRST_SCHEDULE_BIT == 0x01


def test_predbat_template_mode_transitions() -> None:
    """PredBat services switch slots safely and restore self-consumption."""
    template_path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "predbat"
        / "apps-saj-as1.yaml"
    )
    config: dict[str, Any] = yaml.safe_load(
        template_path.read_text(encoding="utf-8")
    )
    app = config["pred_bat"]

    assert app["inverter"]["has_fox_inverter_mode"] is False
    assert app["inverter"]["has_target_soc"] is False
    assert app["inverter"]["has_reserve_soc"] is False
    assert app["grid_power_invert"] == [True]
    assert app["battery_power_invert"] == [False]

    charge_start = app["charge_start_service"]
    assert [step["service"] for step in charge_start] == [
        "switch.turn_off",
        "switch.turn_on",
        "select.select_option",
    ]
    assert charge_start[-1]["option"] == "Horario de Uso"

    discharge_start = app["discharge_start_service"]
    assert [step["service"] for step in discharge_start] == [
        "switch.turn_off",
        "switch.turn_on",
        "select.select_option",
    ]
    assert discharge_start[-1]["option"] == "Horario de Uso"

    for stop_name in ("charge_stop_service", "discharge_stop_service"):
        stop = app[stop_name]
        assert [step["service"] for step in stop] == [
            "switch.turn_off",
            "select.select_option",
        ]
        assert stop[-1]["option"] == "Autoconsumo"

    assert "repeat" not in template_path.read_text(encoding="utf-8")


def test_schedule_write_order() -> None:
    """Times and rates are written before enables, with mode last."""
    batch = {
        REGISTER_USER_MODE: 2,
        REGISTER_DISCHARGE_SCHEDULE_ENABLE: 1,
        REGISTER_CHARGE_SCHEDULE_ENABLE: 1,
        REGISTER_DISCHARGE_POWER_PCT: 100,
        REGISTER_CHARGE_POWER_PCT: 50,
        REGISTER_DISCHARGE_END_TIME: 0x1700,
        REGISTER_DISCHARGE_START_TIME: 0x1600,
        REGISTER_CHARGE_END_TIME: 0x0700,
        REGISTER_CHARGE_START_TIME: 0x0600,
    }
    ordered = SAJModbusCoordinator._ordered_write_addresses(
        SimpleNamespace(),  # type: ignore[arg-type]
        batch,
    )
    assert ordered == [
        REGISTER_CHARGE_START_TIME,
        REGISTER_CHARGE_END_TIME,
        REGISTER_DISCHARGE_START_TIME,
        REGISTER_DISCHARGE_END_TIME,
        REGISTER_CHARGE_POWER_PCT,
        REGISTER_DISCHARGE_POWER_PCT,
        REGISTER_CHARGE_SCHEDULE_ENABLE,
        REGISTER_DISCHARGE_SCHEDULE_ENABLE,
        REGISTER_USER_MODE,
    ]


def test_time_entity_skips_equal_minute_value() -> None:
    """A time write is idempotent after seconds are normalized."""
    writes: list[tuple[int, int]] = []

    async def write_register(address: int, value: int) -> bool:
        writes.append((address, value))
        return True

    entity = object.__new__(SAJTime)
    untyped_entity: Any = entity
    untyped_entity.coordinator = SimpleNamespace(
        data={"first_charge_start_time": time(6, 30)},
        async_write_register=write_register,
    )
    untyped_entity.entity_description = TIME_DESCRIPTIONS[0]

    asyncio.run(entity.async_set_value(time(6, 30, 45)))

    assert writes == []
