"""Data update coordinator for the SAJ AS1 Modbus integration."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta
import logging
import time
from typing import Any, cast

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .connection_manager import CONNECT_ATTEMPTS, ModbusConnectionManager
from .const import (
    AIO3_BATCH_INTER_WRITE_DELAY,
    AIO3_CIRCUIT_BREAKER_COOLDOWN,
    AIO3_CIRCUIT_BREAKER_FAILURES,
    AIO3_PRE_WRITE_DELAY,
    AIO3_RECOVERY_DELAY,
    AIO3_SENSITIVE_RETRIES,
    AIO3_SENSITIVE_RETRY_DELAY,
    AIO3_WRITE_BATCH_DELAY,
    AIO3_WRITE_RETRIES,
    AIO3_WRITE_RETRY_DELAY,
    AIO3_WRITE_SETTLE_DELAY,
    AIOT_DELAY_MS,
    BAT_ENERGY_CAPACITY_NOMINAL,
    CONF_DEVICE_ID,
    CONFIG_KEYS,
    CONNECTION_ISSUE_DELAY,
    DEFAULT_DEVICE_ID,
    DOMAIN,
    HIGH_KEYS,
    ISSUE_CONNECTION_UNAVAILABLE,
    LOW_ENERGY_BLOCK_COUNT,
    LOW_ENERGY_BLOCK_START,
    LOW_ENERGY_REGISTERS,
    LOW_KEYS,
    MAX_FAILURES_BEFORE_UNAVAILABLE,
    MEDIUM_KEYS,
    MODBUS_TIMEOUT,
    POLL_CYCLE_TIMEOUT,
    REGISTER_BAT_POWER,
    REGISTER_BAT_SOC,
    REGISTER_BMS_COUNT,
    REGISTER_BMS_START,
    REGISTER_CHARGE_POWER_PCT,
    REGISTER_DISCHARGE_POWER_PCT,
    REGISTER_ERROR_COUNT,
    REGISTER_GRID_L1_STATUS_COUNT,
    REGISTER_GRID_L1_STATUS_START,
    REGISTER_POWER_BLOCK_COUNT,
    REGISTER_POWER_BLOCK_START,
    REGISTER_RADIATOR_TEMP,
    REGISTER_USER_MODE,
    REGISTER_WORKING_MODE,
    SCAN_INTERVAL_CONFIG,
    SCAN_INTERVAL_HIGH,
    SCAN_INTERVAL_LOW,
    SCAN_INTERVAL_MEDIUM,
    STALE_DATA_MAX_FAILURES,
    WEEKDAYS_ALL,
    WORKING_MODES,
)
from .exceptions import (
    ConnectFailedError,
    ModbusReadError,
    ModbusReadRejectedError,
    ModbusWriteError,
    ModbusWriteRejectedError,
    ReconnectionNeededError,
    SAJModbusException,
)
from .modbus_processing import (
    extract_byte_high,
    inject_days_weekdays,
    percentage_from_register,
    read_current,
    read_energy,
    read_percentage,
    read_power,
    read_temperature,
    read_uint16,
    read_voltage,
    validate_percentage,
)
from .models import SAJConfigEntry

_LOGGER = logging.getLogger(__name__)

ReadMethod = Callable[[], Awaitable[dict[str, Any]]]

SLOT_POWER_REGISTERS = (REGISTER_CHARGE_POWER_PCT, REGISTER_DISCHARGE_POWER_PCT)

GRID_L1_KEYS = ("grid_voltage_l1", "grid_current_l1", "grid_frequency_l1")

# Derived values are only available while every value they are built from is.
DERIVED_INPUTS: dict[str, tuple[str, ...]] = {
    "battery_capacity_real": ("bat1_soh",),
    "battery_time_to_full": ("bat1_soh", "bat1_soc", "battery_power"),
    "battery_time_to_empty": ("bat1_soh", "bat1_soc", "battery_power"),
}

# Raw power flow registers of the HIGH power block (offset from 0x4099), kept
# for diagnostics so the grid and battery mapping can be checked on hardware.
RAW_POWER_FLOWS = {
    "0x4099_pv_to_load": 0,
    "0x409A_grid_to_load": 1,
    "0x409B_pv_to_grid": 2,
    "0x409C_battery_to_grid": 3,
    "0x409D_battery_to_load": 4,
    "0x409E_pv_to_battery": 5,
    "0x409F_grid_to_battery": 6,
    "0x40A0_total_load": 7,
    "0x40A1_ct_grid_power": 8,
    "0x40A2_ct_grid_power_va": 9,
    "0x40A3_ct_pv_power": 10,
    "0x40A4_ct_pv_power_va": 11,
    "0x40A5_total_pv_power": 12,
}


def connection_issue_id(entry_id: str) -> str:
    """Return the repair issue id used for one config entry."""
    return f"{ISSUE_CONNECTION_UNAVAILABLE}_{entry_id}"


class SAJModbusCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate every Modbus read and write of one SAJ AS1."""

    config_entry: SAJConfigEntry

    def __init__(self, hass: HomeAssistant, entry: SAJConfigEntry) -> None:
        """Initialize the coordinator."""
        self.host: str = entry.data[CONF_HOST]
        self.port: int = entry.data[CONF_PORT]
        self.device_id: int = entry.data.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID)

        self.connection = ModbusConnectionManager(
            host=self.host,
            port=self.port,
            device_id=self.device_id,
            timeout=MODBUS_TIMEOUT,
        )

        self._pending_writes = 0
        self._writes_idle = asyncio.Event()
        self._writes_idle.set()
        self._write_lock = asyncio.Lock()
        self._write_batch_lock = asyncio.Lock()
        self._write_batch_values: dict[int, int] = {}
        self._write_batch_futures: dict[int, list[asyncio.Future[bool]]] = {}
        self._write_batch_task: asyncio.Task[None] | None = None
        self._last_high_update = 0.0
        self._last_medium_update = 0.0
        self._last_config_update = 0.0
        self._last_low_update = 0.0
        self._high_failures = 0
        self._medium_failures = 0
        self._config_failures = 0
        self._low_failures = 0
        self._high_cache: dict[str, Any] = {}
        self._medium_cache: dict[str, Any] = {}
        self._config_cache: dict[str, Any] = {}
        self._low_cache: dict[str, Any] = {}
        self._last_user_mode: int | None = None
        # Weekday mask (high byte) last read from each slot power register.
        self._slot_days: dict[int, int | None] = dict.fromkeys(SLOT_POWER_REGISTERS)
        self._connection_issue_active = False
        self._disconnected_since: float | None = None
        self._circuit_warned = False
        self._grid_l1_failures = 0
        self._user_mode_failures = 0
        self._last_update_duration = 0.0
        self._circuit_open_until = 0.0
        self._circuit_open_count = 0
        self._bucket_read_counts = {"HIGH": 0, "MEDIUM": 0, "CONFIG": 0, "LOW": 0}
        self._bucket_last_success = {
            "HIGH": 0.0,
            "MEDIUM": 0.0,
            "CONFIG": 0.0,
            "LOW": 0.0,
        }
        self._bucket_last_duration = {
            "HIGH": 0.0,
            "MEDIUM": 0.0,
            "CONFIG": 0.0,
            "LOW": 0.0,
        }
        self._bucket_last_error: dict[str, str | None] = {
            "HIGH": None,
            "MEDIUM": None,
            "CONFIG": None,
            "LOW": None,
        }
        self._bucket_expected_registers = {
            "HIGH": 15,
            "MEDIUM": 24,
            "CONFIG": 3,
            "LOW": LOW_ENERGY_BLOCK_COUNT,
        }

        self.is_connected = False
        self.consecutive_failures = 0
        self.last_error_type: str | None = None
        self.unavailable_keys: set[str] = set()
        # Keys whose last value is too old to show although their bucket works.
        self.expired_keys: set[str] = set()
        self.raw_power_flows: dict[str, int] = {}

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=timedelta(seconds=SCAN_INTERVAL_HIGH),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Read the HIGH/MEDIUM/CONFIG/LOW buckets that are due."""
        now = time.monotonic()
        if self._circuit_is_open(now):
            await self.connection.close()
            self._set_connected_state(False)
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="circuit_open")

        # While the inverter is known to be down, one connect attempt per
        # cycle is enough; three only add load and log lines.
        self.connection.connect_attempts = (
            1 if self.consecutive_failures else CONNECT_ATTEMPTS
        )
        data = dict(self.data or {})
        try:
            async with asyncio.timeout(POLL_CYCLE_TIMEOUT):
                due, refreshed = await self._refresh_buckets(data, now)
            if due and not refreshed:
                raise ModbusReadError("No register block could be read")
        except asyncio.CancelledError:
            await self.connection.close()
            raise
        except ReconnectionNeededError as err:
            await self.connection.close()
            await asyncio.sleep(AIO3_RECOVERY_DELAY)
            return self._cycle_failed(err, connection_lost=True)
        except TimeoutError as err:
            await self.connection.close()
            _LOGGER.warning(
                "SAJ AS1 poll cycle exceeded %.0fs and was aborted",
                POLL_CYCLE_TIMEOUT,
            )
            return self._cycle_failed(err, connection_lost=True)
        except Exception as err:
            await self.connection.close()
            return self._cycle_failed(err, connection_lost=False)

        self._calc_derived(data)
        self._last_update_duration = round(time.monotonic() - now, 3)
        self.consecutive_failures = 0
        self.last_error_type = None
        self._circuit_open_until = 0.0
        self._circuit_warned = False
        self._set_connected_state(True)
        await self.connection.close()
        return data

    async def _refresh_buckets(
        self, data: dict[str, Any], now: float
    ) -> tuple[int, int]:
        """Refresh every bucket whose interval has elapsed.

        Return how many buckets were due and how many of them were read.
        """
        results = [
            await self._refresh_bucket_if_due(
                data=data,
                now=now,
                interval=SCAN_INTERVAL_HIGH,
                last_attr="_last_high_update",
                failures_attr="_high_failures",
                cache_attr="_high_cache",
                keys=HIGH_KEYS,
                reader=self._read_high,
                label="HIGH",
            ),
            await self._refresh_bucket_if_due(
                data=data,
                now=now,
                interval=SCAN_INTERVAL_MEDIUM,
                last_attr="_last_medium_update",
                failures_attr="_medium_failures",
                cache_attr="_medium_cache",
                keys=MEDIUM_KEYS,
                reader=self._read_medium,
                label="MEDIUM",
            ),
            await self._refresh_bucket_if_due(
                data=data,
                now=now,
                interval=SCAN_INTERVAL_CONFIG,
                last_attr="_last_config_update",
                failures_attr="_config_failures",
                cache_attr="_config_cache",
                keys=CONFIG_KEYS,
                reader=self._read_config,
                label="CONFIG",
            ),
            await self._refresh_bucket_if_due(
                data=data,
                now=now,
                interval=SCAN_INTERVAL_LOW,
                last_attr="_last_low_update",
                failures_attr="_low_failures",
                cache_attr="_low_cache",
                keys=LOW_KEYS,
                reader=self._read_low,
                label="LOW",
            ),
        ]
        due = [result for result in results if result is not None]
        return len(due), sum(due)

    def _cycle_failed(self, err: Exception, *, connection_lost: bool) -> dict[str, Any]:
        """Keep the last values through short outages, then fail the update.

        Returning stale data forever would leave power sensors frozen while the
        inverter is offline, so from STALE_DATA_MAX_FAILURES consecutive failed
        cycles on the entities become unavailable.
        """
        self.consecutive_failures += 1
        self.last_error_type = str(err) or type(err).__name__
        self._open_circuit_if_needed()
        if connection_lost or self.consecutive_failures >= STALE_DATA_MAX_FAILURES:
            self._set_connected_state(False)

        if self.data and self.consecutive_failures < STALE_DATA_MAX_FAILURES:
            _LOGGER.debug(
                "SAJ AS1 update failed (%d/%d), keeping the last values: %s",
                self.consecutive_failures,
                STALE_DATA_MAX_FAILURES,
                self.last_error_type,
            )
            return self.data

        raise UpdateFailed(
            translation_domain=DOMAIN,
            translation_key="update_failed",
            translation_placeholders={"error": self.last_error_type},
        ) from err

    async def async_write_register(self, address: int, value: int) -> bool:
        """Queue a register write and update the cache once it succeeds."""
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()

        self._begin_write()
        try:
            async with self._write_batch_lock:
                self._write_batch_values[address] = value
                self._write_batch_futures.setdefault(address, []).append(future)
                if self._write_batch_task is None or self._write_batch_task.done():
                    self._write_batch_task = self._create_write_batch_task()

            return await future

        finally:
            self._end_write()

    def _create_write_batch_task(self) -> asyncio.Task[None]:
        """Start a write batch tied to the config entry lifetime."""
        return self.config_entry.async_create_background_task(
            self.hass,
            self._flush_write_batch(),
            f"{DOMAIN}_write_batch_{self.config_entry.entry_id}",
        )

    async def _flush_write_batch(self) -> None:
        """Apply queued writes as one batch, like the Elekeeper app does."""
        batch_futures: dict[int, list[asyncio.Future[bool]]] = {}
        try:
            await asyncio.sleep(AIO3_WRITE_BATCH_DELAY)

            async with self._write_lock:
                async with self._write_batch_lock:
                    batch_values = dict(self._write_batch_values)
                    batch_futures = {
                        address: list(futures)
                        for address, futures in self._write_batch_futures.items()
                    }
                    self._write_batch_values.clear()
                    self._write_batch_futures.clear()

                results = await self._apply_write_batch(batch_values)

                for address, futures in batch_futures.items():
                    result = results.get(address, False)
                    for future in futures:
                        if not future.done():
                            future.set_result(result)
        except asyncio.CancelledError:
            # Unloading cancels the batch. Resolve every caller so no service
            # call or entity action waits forever.
            pending = [*batch_futures.values(), *self._write_batch_futures.values()]
            for futures in pending:
                for future in futures:
                    if not future.done():
                        future.set_result(False)
            self._write_batch_values.clear()
            self._write_batch_futures.clear()
            raise

        async with self._write_batch_lock:
            if self._write_batch_values:
                self._write_batch_task = self._create_write_batch_task()
            else:
                self._write_batch_task = None

    async def async_set_profile(
        self,
        *,
        charge_power_pct: int | None = None,
        discharge_power_pct: int | None = None,
        user_mode: int | None = None,
    ) -> dict[int, bool]:
        """Apply a complete profile in a single action call.

        Return whether each requested register was written.
        """
        batch_values: dict[int, int] = {}
        if charge_power_pct is not None:
            batch_values[REGISTER_CHARGE_POWER_PCT] = charge_power_pct
        if discharge_power_pct is not None:
            batch_values[REGISTER_DISCHARGE_POWER_PCT] = discharge_power_pct
        if user_mode is not None:
            batch_values[REGISTER_USER_MODE] = user_mode

        if not batch_values:
            return {}

        self._begin_write()
        try:
            async with self._write_lock:
                results = await self._apply_write_batch(batch_values)
            return {address: results.get(address, False) for address in batch_values}
        finally:
            self._end_write()

    async def _apply_write_batch(self, batch_values: dict[int, int]) -> dict[int, bool]:
        """Write a batch of registers with a single settle window."""
        if not batch_values:
            return {}

        results: dict[int, bool] = {}
        ordered_addresses = self._ordered_write_addresses(batch_values)
        try:
            await self.connection.close()
            await asyncio.sleep(AIO3_PRE_WRITE_DELAY)

            for index, address in enumerate(ordered_addresses):
                write_value, cache_value = self._prepare_write_value(
                    address,
                    batch_values[address],
                )
                try:
                    await self._write_register_with_recovery(address, write_value)
                except (ModbusWriteError, ReconnectionNeededError) as err:
                    self.last_error_type = str(err)
                    _LOGGER.warning(
                        "SAJ AS1 write failed at 0x%04X: %s",
                        address,
                        err,
                    )
                    results[address] = False
                    continue

                self._update_write_cache(address, cache_value)
                results[address] = True
                if index < len(ordered_addresses) - 1:
                    await self.connection.close()
                    await asyncio.sleep(AIO3_BATCH_INTER_WRITE_DELAY)

            if any(results.values()) and set(CONFIG_KEYS).issubset(
                self._config_cache
            ):
                self._last_config_update = time.monotonic()
            await self.connection.close()
            await asyncio.sleep(AIO3_WRITE_SETTLE_DELAY)

            if any(results.values()):
                self._set_connected_state(True)
            return results

        except Exception as err:
            self.last_error_type = str(err)
            _LOGGER.warning("SAJ AS1 write batch failed: %s", err)
            await self.connection.close()
            await asyncio.sleep(AIO3_RECOVERY_DELAY)
            return dict.fromkeys(batch_values, False)

    def _ordered_write_addresses(self, batch_values: dict[int, int]) -> list[int]:
        """Order writes: power percentages first, user mode last."""
        preferred_order = (
            REGISTER_CHARGE_POWER_PCT,
            REGISTER_DISCHARGE_POWER_PCT,
            REGISTER_USER_MODE,
        )
        ordered = [address for address in preferred_order if address in batch_values]
        ordered.extend(address for address in batch_values if address not in ordered)
        return ordered

    def _prepare_write_value(self, address: int, value: int) -> tuple[int, int]:
        """Return the Modbus value to write and the value to cache."""
        if address in SLOT_POWER_REGISTERS:
            percentage = validate_percentage(value & 0xFF)
            days = self._slot_days.get(address)
            return (
                inject_days_weekdays(
                    percentage, WEEKDAYS_ALL if days is None else days
                ),
                percentage,
            )

        return value, value

    async def _write_register_with_recovery(self, address: int, value: int) -> None:
        """Write with a slow retry for the sensitive AIO3 registers."""
        last_error: Exception | None = None
        for attempt in range(1, AIO3_WRITE_RETRIES + 1):
            try:
                await self.connection.write_register(address, value)
                return
            except ModbusWriteRejectedError:
                raise
            except (ModbusWriteError, ReconnectionNeededError) as err:
                last_error = err
                await self.connection.close()
                if attempt < AIO3_WRITE_RETRIES:
                    _LOGGER.debug(
                        "SAJ AS1 write attempt %d/%d failed at 0x%04X: %s",
                        attempt,
                        AIO3_WRITE_RETRIES,
                        address,
                        err,
                    )
                    await asyncio.sleep(AIO3_WRITE_RETRY_DELAY)

        raise ModbusWriteError(
            f"Write failed at 0x{address:04X} after "
            f"{AIO3_WRITE_RETRIES} attempts: {last_error}"
        )

    async def _refresh_bucket_if_due(
        self,
        *,
        data: dict[str, Any],
        now: float,
        interval: int,
        last_attr: str,
        failures_attr: str,
        cache_attr: str,
        keys: tuple[str, ...],
        reader: ReadMethod,
        label: str,
    ) -> bool | None:
        """Refresh one bucket or reuse its cache.

        Return None when the bucket was not due, otherwise whether it was read.

        A bucket that has never been read successfully publishes nothing, so
        its entities stay unknown instead of reporting zeros. A zero would be
        recorded as a meter reset by the energy dashboard.
        """
        cache: dict[str, Any] = getattr(self, cache_attr)
        last_update: float = getattr(self, last_attr)
        due = now - last_update >= interval or not cache

        if not due:
            data.update(cache)
            return None

        started = time.monotonic()
        try:
            bucket_data = await reader()
        except ReconnectionNeededError:
            self._bucket_last_duration[label] = round(time.monotonic() - started, 3)
            raise
        except Exception as err:
            if not isinstance(err, SAJModbusException) and (
                self._bucket_last_error[label] != str(err)
            ):
                _LOGGER.warning(
                    "Unexpected error in the %s bucket: %s", label, err, exc_info=True
                )
            else:
                _LOGGER.debug("%s bucket failed: %s", label, err)
            self._bucket_last_error[label] = str(err)
            bucket_data = {}

        self._bucket_last_duration[label] = round(time.monotonic() - started, 3)
        if bucket_data:
            was_unavailable = bool(self.unavailable_keys.intersection(keys))
            cache = bucket_data.copy()
            setattr(self, cache_attr, cache)
            setattr(self, failures_attr, 0)
            setattr(self, last_attr, now)
            self._bucket_read_counts[label] += 1
            self._bucket_last_success[label] = now
            self._bucket_last_error[label] = None
            self.unavailable_keys.difference_update(keys)
            if was_unavailable:
                _LOGGER.info("%s bucket recovered", label)
            data.update(cache)
            return True

        failures = getattr(self, failures_attr) + 1
        setattr(self, failures_attr, failures)
        if failures >= MAX_FAILURES_BEFORE_UNAVAILABLE:
            self.unavailable_keys.update(keys)
            if failures == MAX_FAILURES_BEFORE_UNAVAILABLE:
                _LOGGER.warning(
                    "%s bucket unavailable after %d failures",
                    label,
                    failures,
                )
            else:
                _LOGGER.debug(
                    "%s bucket still unavailable after %d failures",
                    label,
                    failures,
                )
        data.update(cache)
        return False

    def diagnostic_polling(self) -> dict[str, Any]:
        """Return polling metrics for diagnostics."""
        now = time.monotonic()
        bucket_specs = {
            "HIGH": {
                "failures": self._high_failures,
                "cache": self._high_cache,
                "keys": HIGH_KEYS,
            },
            "MEDIUM": {
                "failures": self._medium_failures,
                "cache": self._medium_cache,
                "keys": MEDIUM_KEYS,
            },
            "CONFIG": {
                "failures": self._config_failures,
                "cache": self._config_cache,
                "keys": CONFIG_KEYS,
            },
            "LOW": {
                "failures": self._low_failures,
                "cache": self._low_cache,
                "keys": LOW_KEYS,
            },
        }

        buckets: dict[str, dict[str, Any]] = {}
        for label, spec in bucket_specs.items():
            last_success = self._bucket_last_success[label]
            keys = cast(tuple[str, ...], spec["keys"])
            buckets[label] = {
                "failures": spec["failures"],
                "read_count": self._bucket_read_counts[label],
                "expected_registers": self._bucket_expected_registers[label],
                "last_duration": self._bucket_last_duration[label],
                "last_error": self._bucket_last_error[label],
                "last_success_age": (
                    None if last_success <= 0 else round(now - last_success, 1)
                ),
                "cache_size": len(cast(dict[str, Any], spec["cache"])),
                "unavailable_keys": sorted(set(keys).intersection(self.unavailable_keys)),
            }

        return {
            "last_update_duration": self._last_update_duration,
            "buckets": buckets,
            "circuit_breaker": {
                "open": self._circuit_is_open(now),
                "open_count": self._circuit_open_count,
                "remaining_cooldown": (
                    0.0
                    if not self._circuit_is_open(now)
                    else round(self._circuit_open_until - now, 1)
                ),
            },
        }

    def is_key_available(self, key: str) -> bool:
        """Return whether the value of a data key can be shown."""
        blocked = self.unavailable_keys | self.expired_keys
        if key in blocked:
            return False
        return blocked.isdisjoint(DERIVED_INPUTS.get(key, ()))

    def _circuit_is_open(self, now: float) -> bool:
        """Return whether the cooldown after repeated failures is active."""
        return now < self._circuit_open_until

    def _open_circuit_if_needed(self) -> None:
        """Open a short cooldown after consecutive global failures."""
        if self.consecutive_failures < AIO3_CIRCUIT_BREAKER_FAILURES:
            return

        if self._circuit_is_open(time.monotonic()):
            return

        self._circuit_open_count += 1
        self._circuit_open_until = time.monotonic() + AIO3_CIRCUIT_BREAKER_COOLDOWN
        log = _LOGGER.debug if self._circuit_warned else _LOGGER.warning
        self._circuit_warned = True
        log(
            "SAJ AS1 circuit breaker open for %.0fs after %d failures",
            AIO3_CIRCUIT_BREAKER_COOLDOWN,
            self.consecutive_failures,
        )

    async def _read_high(self) -> dict[str, Any]:
        """Read power values and SOC (high frequency)."""
        await self._wait_for_write_priority()
        bat_power_regs = await self.connection.read_registers(REGISTER_BAT_POWER, 1)
        battery_power = read_power(bat_power_regs, 0) * -1

        await self._delay_between_blocks()
        await self._wait_for_write_priority()
        soc_regs = await self.connection.read_registers(REGISTER_BAT_SOC, 1)

        await self._delay_between_blocks()
        await self._wait_for_write_priority()
        power_regs = await self.connection.read_registers(
            REGISTER_POWER_BLOCK_START,
            REGISTER_POWER_BLOCK_COUNT,
        )

        self.raw_power_flows = {
            name: read_power(power_regs, offset)
            for name, offset in RAW_POWER_FLOWS.items()
        }
        grid_import = read_power(power_regs, 1)
        grid_export = read_power(power_regs, 2)
        battery_discharge = read_power(power_regs, 4)
        total_load = read_power(power_regs, 7)
        total_pv = read_power(power_regs, 12)
        grid_import_power = max(0, grid_import)
        grid_export_power = max(0, grid_export)
        battery_charging_power = max(0, battery_power)
        battery_discharging_power = max(0, battery_discharge)

        return {
            "battery_power": battery_power,
            "battery_power_signed": battery_discharging_power - battery_charging_power,
            "bat1_soc": read_percentage(soc_regs, 0),
            "grid_import_power": grid_import_power,
            "grid_export_power": grid_export_power,
            "grid_power_signed": grid_import_power - grid_export_power,
            "battery_charging_power": battery_charging_power,
            "battery_discharging_power": battery_discharging_power,
            "total_load_power": max(0, total_load),
            "total_pv_power": max(0, total_pv),
        }

    async def _read_medium(self) -> dict[str, Any]:
        """Read status, BMS and grid L1 values (medium frequency)."""
        data: dict[str, Any] = {}

        await self._wait_for_write_priority()
        mode_regs = await self.connection.read_registers(REGISTER_WORKING_MODE, 1)
        working_mode = read_uint16(mode_regs, 0)
        data["working_mode"] = working_mode
        data["working_mode_name"] = WORKING_MODES.get(working_mode)
        if data["working_mode_name"] is None:
            _LOGGER.debug("Unknown SAJ AS1 working mode value: %s", working_mode)

        await self._delay_between_blocks()
        await self._wait_for_write_priority()
        data["error_count"] = read_uint16(
            await self.connection.read_registers(REGISTER_ERROR_COUNT, 1),
            0,
        )

        await self._delay_between_blocks()
        await self._wait_for_write_priority()
        data["radiator_temp"] = read_temperature(
            await self.connection.read_registers(REGISTER_RADIATOR_TEMP, 1),
            0,
        )

        await self._delay_between_blocks()
        await self._wait_for_write_priority()
        data.update(await self._read_grid_l1_status())

        await self._delay_between_blocks()
        await self._wait_for_write_priority()
        bms_regs = await self.connection.read_registers(
            REGISTER_BMS_START,
            REGISTER_BMS_COUNT,
        )
        data.update(
            {
                "bat_number": read_uint16(bms_regs, 0),
                "bat1_soh": read_percentage(bms_regs, 13),
                "bat1_voltage": read_voltage(bms_regs, 14),
                "bat1_current": read_current(bms_regs, 15),
                "bat1_temp": read_temperature(bms_regs, 16),
                "bat1_cycles": read_uint16(bms_regs, 17),
            }
        )

        return data

    async def _read_grid_l1_status(self) -> dict[str, float]:
        """Read L1 voltage, current and frequency without failing MEDIUM."""
        try:
            regs = await self.connection.read_registers(
                REGISTER_GRID_L1_STATUS_START,
                REGISTER_GRID_L1_STATUS_COUNT,
            )
        except ConnectFailedError:
            raise
        except (ModbusReadError, ReconnectionNeededError) as err:
            self._grid_l1_failures += 1
            _LOGGER.debug("Grid L1 status block failed: %s", err)
            if self._grid_l1_failures >= MAX_FAILURES_BEFORE_UNAVAILABLE:
                # Too old to show: the entities become unavailable.
                self.expired_keys.update(GRID_L1_KEYS)
                return {}
            current_data = self.data or {}
            fallback: dict[str, float] = {}
            for key in GRID_L1_KEYS:
                value = current_data.get(key)
                if isinstance(value, int | float):
                    fallback[key] = float(value)
            return fallback

        self._grid_l1_failures = 0
        self.expired_keys.difference_update(GRID_L1_KEYS)
        return {
            "grid_voltage_l1": read_voltage(regs, 0),
            "grid_current_l1": read_current(regs, 1),
            "grid_frequency_l1": round(read_uint16(regs, 2) / 100.0, 2),
        }

    async def _read_config(self) -> dict[str, Any]:
        """Read the user configuration registers (slow)."""
        data: dict[str, Any] = {}

        await self._wait_for_write_priority()
        await self._delay_between_blocks()
        data["user_mode"] = await self._read_user_mode_with_retry()

        for address, key, label in (
            (REGISTER_CHARGE_POWER_PCT, "first_charge_power_pct", "Charge power"),
            (
                REGISTER_DISCHARGE_POWER_PCT,
                "first_discharge_power_pct",
                "Discharge power",
            ),
        ):
            await self._delay_between_blocks()
            await self._wait_for_write_priority()
            raw = read_uint16(await self._read_sensitive_register(address, label), 0)
            self._slot_days[address] = extract_byte_high(raw)
            data[key] = percentage_from_register(raw)

        return data

    async def _read_low(self) -> dict[str, Any]:
        """Read accumulated energy counters (slow)."""
        await self._wait_for_write_priority()
        regs = await self.connection.read_registers(
            LOW_ENERGY_BLOCK_START,
            LOW_ENERGY_BLOCK_COUNT,
        )
        energies = self._energy_data_from_block(regs)
        if not any(energies.values()):
            # A running installation never has every lifetime counter at 0;
            # publishing it would be recorded as a meter reset.
            raise ModbusReadError("Energy counters read as all zeros")
        for key, value in energies.items():
            previous = self._low_cache.get(key)
            if value == 0 and isinstance(previous, int | float) and previous > 0:
                _LOGGER.debug("Ignoring a 0 kWh reading of %s", key)
                energies[key] = previous
        return energies

    @staticmethod
    def _energy_data_from_block(regs: list[int]) -> dict[str, float]:
        """Extract accumulated energies from the contiguous LOW block."""
        return {
            key: read_energy(regs, address - LOW_ENERGY_BLOCK_START)
            for key, address in LOW_ENERGY_REGISTERS.items()
        }

    async def _read_user_mode_with_retry(self) -> int | None:
        """Read the user mode, falling back to the last known value."""
        try:
            regs = await self._read_sensitive_register(REGISTER_USER_MODE, "User mode")
            user_mode = read_uint16(regs, 0)
            self._last_user_mode = user_mode
            self._user_mode_failures = 0
            self.expired_keys.discard("user_mode")
            return user_mode
        except ModbusReadError as err:
            self._user_mode_failures += 1
            _LOGGER.debug("User mode could not be read: %s", err)
            if self._user_mode_failures >= MAX_FAILURES_BEFORE_UNAVAILABLE:
                self.expired_keys.add("user_mode")

        return self._last_user_mode

    async def _read_sensitive_register(self, address: int, label: str) -> list[int]:
        """Read a sensitive AIO3 register, retrying a broken session.

        An unreachable host is not retried: each retry would run the whole
        connect sequence again.
        """
        last_error: Exception | None = None
        for attempt in range(1, AIO3_SENSITIVE_RETRIES + 1):
            try:
                return await self.connection.read_registers(address, 1)
            except (ConnectFailedError, ModbusReadRejectedError):
                raise
            except (ModbusReadError, ReconnectionNeededError) as err:
                last_error = err
                _LOGGER.debug(
                    "%s read attempt %d/%d failed: %s",
                    label,
                    attempt,
                    AIO3_SENSITIVE_RETRIES,
                    err,
                )
                await self.connection.close()
                if attempt < AIO3_SENSITIVE_RETRIES:
                    await asyncio.sleep(AIO3_SENSITIVE_RETRY_DELAY)

        raise ModbusReadError(
            f"{label} read failed after {AIO3_SENSITIVE_RETRIES} attempts: {last_error}"
        )

    def _update_write_cache(self, address: int, value: int) -> None:
        """Apply a successful write to the coordinator caches."""
        key: str | None = None
        if address == REGISTER_CHARGE_POWER_PCT:
            key = "first_charge_power_pct"
        elif address == REGISTER_DISCHARGE_POWER_PCT:
            key = "first_discharge_power_pct"
        elif address == REGISTER_USER_MODE:
            key = "user_mode"
            self._last_user_mode = value

        if key is None:
            return

        current_data = dict(self.data or {})
        current_data[key] = value
        self._config_cache[key] = value
        self.unavailable_keys.discard(key)
        self.expired_keys.discard(key)
        # Not async_set_updated_data: it would postpone the next poll and mark
        # the coordinator as successful although reads may be failing.
        self.data = current_data
        self.async_update_listeners()

    def _begin_write(self) -> None:
        """Register a pending write so new read blocks wait for it."""
        self._pending_writes += 1
        self._writes_idle.clear()

    def _end_write(self) -> None:
        """Release a pending write and wake the readers when none is left."""
        self._pending_writes = max(0, self._pending_writes - 1)
        if self._pending_writes == 0:
            self._writes_idle.set()

    async def _wait_for_write_priority(self) -> None:
        """Pause new read blocks while a write is pending."""
        await self._writes_idle.wait()

    async def _delay_between_blocks(self) -> None:
        """Wait between Modbus blocks to protect the AIO3 stick."""
        await asyncio.sleep(AIOT_DELAY_MS / 1000.0)

    @staticmethod
    def _calc_derived(data: dict[str, Any]) -> None:
        """Calculate real battery capacity and charge/discharge times.

        Values that cannot be calculated are None, so the sensors show unknown
        instead of a misleading 0.
        """
        soh = data.get("bat1_soh")
        soc = data.get("bat1_soc")
        battery_power = data.get("battery_power")
        bat_number = data.get("bat_number")
        modules = bat_number if isinstance(bat_number, int) and bat_number > 0 else 1

        capacity_real_kwh: float | None = None
        if isinstance(soh, int | float):
            capacity_real_kwh = BAT_ENERGY_CAPACITY_NOMINAL * modules * soh / 100.0
        data["battery_capacity_real"] = (
            None if capacity_real_kwh is None else round(capacity_real_kwh, 2)
        )

        data["battery_time_to_full"] = None
        data["battery_time_to_empty"] = None
        if (
            capacity_real_kwh is None
            or not isinstance(soc, int | float)
            or not isinstance(battery_power, int | float)
        ):
            return

        if battery_power > 10:
            remaining_capacity = capacity_real_kwh * (100 - soc) / 100
            data["battery_time_to_full"] = round(
                remaining_capacity / (battery_power / 1000.0), 1
            )
        elif battery_power < -10:
            usable_capacity = capacity_real_kwh * soc / 100
            data["battery_time_to_empty"] = round(
                usable_capacity / (abs(battery_power) / 1000.0), 1
            )

    @callback
    def _set_connected_state(self, connected: bool) -> None:
        """Track the connection state and raise a repair after long outages."""
        previous = self.is_connected
        self.is_connected = connected
        issue_id = connection_issue_id(self.config_entry.entry_id)

        if connected:
            if self._disconnected_since is not None:
                _LOGGER.info("SAJ AS1 Modbus connection restored")
            self._disconnected_since = None
            if self._connection_issue_active:
                self._connection_issue_active = False
                ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            return

        now = time.monotonic()
        if self._disconnected_since is None:
            self._disconnected_since = now
            if previous:
                _LOGGER.warning("SAJ AS1 Modbus connection unavailable")

        if (
            not self._connection_issue_active
            and now - self._disconnected_since >= CONNECTION_ISSUE_DELAY
        ):
            self._connection_issue_active = True
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key=ISSUE_CONNECTION_UNAVAILABLE,
                translation_placeholders={
                    "name": self.config_entry.title,
                    "host": self.host,
                    "port": str(self.port),
                    "minutes": str(int(CONNECTION_ISSUE_DELAY // 60)),
                },
            )
