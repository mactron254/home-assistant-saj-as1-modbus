"""Behavior tests for coordinator helper methods."""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any

from custom_components.saj_as1_modbus.const import (
    AIO3_CIRCUIT_BREAKER_COOLDOWN,
    AIO3_CIRCUIT_BREAKER_FAILURES,
    CONFIG_KEYS,
    HIGH_KEYS,
    LOW_ENERGY_BLOCK_COUNT,
)
from custom_components.saj_as1_modbus.coordinator import SAJModbusCoordinator


def _fake_coordinator() -> SimpleNamespace:
    now = time.monotonic()
    coordinator = SimpleNamespace(
        _last_update_duration=1.25,
        _circuit_open_until=0.0,
        _circuit_open_count=0,
        _high_failures=0,
        _medium_failures=1,
        _config_failures=2,
        _low_failures=3,
        _high_cache={"bat1_soc": 75.0},
        _medium_cache={},
        _config_cache={"user_mode": 2},
        _low_cache={},
        _bucket_read_counts={"HIGH": 4, "MEDIUM": 3, "CONFIG": 2, "LOW": 1},
        _bucket_last_success={
            "HIGH": now - 10,
            "MEDIUM": 0.0,
            "CONFIG": now - 30,
            "LOW": 0.0,
        },
        _bucket_last_duration={
            "HIGH": 0.4,
            "MEDIUM": 0.5,
            "CONFIG": 0.6,
            "LOW": 0.7,
        },
        _bucket_last_error={
            "HIGH": None,
            "MEDIUM": "medium failed",
            "CONFIG": None,
            "LOW": "low failed",
        },
        _bucket_expected_registers={
            "HIGH": 15,
            "MEDIUM": 24,
            "CONFIG": 3,
            "LOW": LOW_ENERGY_BLOCK_COUNT,
        },
        unavailable_keys={HIGH_KEYS[0], CONFIG_KEYS[0]},
    )
    coordinator._circuit_is_open = lambda value: value < coordinator._circuit_open_until
    return coordinator


def test_diagnostic_polling_returns_bucket_metrics() -> None:
    """Diagnostics helper should expose grouped polling health."""
    coordinator = _fake_coordinator()

    result = SAJModbusCoordinator.diagnostic_polling(coordinator)  # type: ignore[arg-type]

    assert result["last_update_duration"] == 1.25
    assert result["buckets"]["HIGH"]["read_count"] == 4
    assert result["buckets"]["HIGH"]["cache_size"] == 1
    assert result["buckets"]["HIGH"]["last_success_age"] is not None
    assert result["buckets"]["LOW"]["expected_registers"] == LOW_ENERGY_BLOCK_COUNT
    assert result["buckets"]["LOW"]["last_error"] == "low failed"
    assert result["buckets"]["CONFIG"]["unavailable_keys"] == [CONFIG_KEYS[0]]
    assert result["circuit_breaker"]["open"] is False


def test_open_circuit_sets_cooldown_once() -> None:
    """Circuit breaker should open after consecutive global failures."""
    coordinator = SimpleNamespace(
        consecutive_failures=AIO3_CIRCUIT_BREAKER_FAILURES,
        _circuit_open_until=0.0,
        _circuit_open_count=0,
    )
    coordinator._circuit_is_open = lambda value: value < coordinator._circuit_open_until

    SAJModbusCoordinator._open_circuit_if_needed(coordinator)  # type: ignore[arg-type]
    first_open_until = coordinator._circuit_open_until

    assert coordinator._circuit_open_count == 1
    assert first_open_until > time.monotonic()
    assert first_open_until <= time.monotonic() + AIO3_CIRCUIT_BREAKER_COOLDOWN

    SAJModbusCoordinator._open_circuit_if_needed(coordinator)  # type: ignore[arg-type]

    assert coordinator._circuit_open_count == 1
    assert coordinator._circuit_open_until == first_open_until
