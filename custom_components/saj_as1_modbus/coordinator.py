"""Coordinador de datos para la integración SAJ AS1 Modbus."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta
import logging
import time
from typing import Any, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .connection_manager import ModbusConnectionManager
from .const import (
    AIO3_BATCH_INTER_WRITE_DELAY,
    AIO3_CIRCUIT_BREAKER_COOLDOWN,
    AIO3_CIRCUIT_BREAKER_FAILURES,
    AIO3_PRE_WRITE_DELAY,
    AIO3_RECOVERY_DELAY,
    AIO3_SENSITIVE_RETRIES,
    AIO3_SENSITIVE_RETRY_DELAY,
    AIO3_WRITE_BATCH_DELAY,
    AIO3_WRITE_SETTLE_DELAY,
    AIO3_WRITE_RETRIES,
    AIO3_WRITE_RETRY_DELAY,
    AIOT_DELAY_MS,
    BAT_ENERGY_CAPACITY_NOMINAL,
    CONF_DEVICE_ID,
    CONFIG_KEYS,
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
    SCAN_INTERVAL_HIGH,
    SCAN_INTERVAL_CONFIG,
    SCAN_INTERVAL_LOW,
    SCAN_INTERVAL_MEDIUM,
    WORKING_MODES,
)
from .exceptions import (
    ModbusReadError,
    ModbusWriteError,
    ReconnectionNeededError,
)
from .modbus_processing import (
    extract_byte_low,
    inject_days_weekdays,
    read_current,
    read_energy,
    read_percentage,
    read_power,
    read_temperature,
    read_uint16,
    read_voltage,
    validate_percentage,
)

_LOGGER = logging.getLogger(__name__)

ReadMethod = Callable[[], Awaitable[dict[str, Any]]]


class SAJModbusCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinar todas las lecturas y escrituras Modbus del SAJ AS1."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Inicializar el coordinador."""
        self._hass = hass
        self.entry = entry
        self.host: str = entry.data[CONF_HOST]
        self.port: int = entry.data[CONF_PORT]
        self.device_id: int = entry.data.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID)

        self.connection = ModbusConnectionManager(
            hass=hass,
            host=self.host,
            port=self.port,
            device_id=self.device_id,
            timeout=MODBUS_TIMEOUT,
        )

        self._write_requested = False
        self._pending_writes = 0
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
        self._connection_issue_active = False
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

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=SCAN_INTERVAL_HIGH),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Leer datos usando las frecuencias HIGH/MEDIUM/LOW ajustadas al SAJ."""
        now = time.monotonic()
        started = now
        data = dict(self.data or {})

        try:
            if self._circuit_is_open(now):
                await self.connection.close()
                await self._set_connected_state(False)
                if data:
                    return data
                raise UpdateFailed("SAJ AS1 circuit breaker open")

            await self._refresh_bucket_if_due(
                data=data,
                now=now,
                interval=SCAN_INTERVAL_HIGH,
                last_attr="_last_high_update",
                failures_attr="_high_failures",
                cache_attr="_high_cache",
                keys=HIGH_KEYS,
                fallback=self._zero_high(),
                reader=self._read_high,
                label="HIGH",
            )
            await self._refresh_bucket_if_due(
                data=data,
                now=now,
                interval=SCAN_INTERVAL_MEDIUM,
                last_attr="_last_medium_update",
                failures_attr="_medium_failures",
                cache_attr="_medium_cache",
                keys=MEDIUM_KEYS,
                fallback=self._zero_medium(),
                reader=self._read_medium,
                label="MEDIUM",
            )
            await self._refresh_bucket_if_due(
                data=data,
                now=now,
                interval=SCAN_INTERVAL_CONFIG,
                last_attr="_last_config_update",
                failures_attr="_config_failures",
                cache_attr="_config_cache",
                keys=CONFIG_KEYS,
                fallback=self._zero_config(),
                reader=self._read_config,
                label="CONFIG",
            )
            await self._refresh_bucket_if_due(
                data=data,
                now=now,
                interval=SCAN_INTERVAL_LOW,
                last_attr="_last_low_update",
                failures_attr="_low_failures",
                cache_attr="_low_cache",
                keys=LOW_KEYS,
                fallback=self._zero_low(),
                reader=self._read_low,
                label="LOW",
            )

            self._calc_derived(data)
            self._last_update_duration = round(time.monotonic() - started, 3)
            self.consecutive_failures = 0
            self.last_error_type = None
            self._circuit_open_until = 0.0
            await self._set_connected_state(not self.unavailable_keys)
            await self.connection.close()
            return data

        except ReconnectionNeededError as err:
            self.consecutive_failures += 1
            self.last_error_type = str(err)
            self._open_circuit_if_needed()
            await self.connection.close()
            await asyncio.sleep(AIO3_RECOVERY_DELAY)
            await self._set_connected_state(False)
            if self.data:
                return self.data
            raise UpdateFailed("Modbus reconnect required") from err

        except Exception as err:
            self.consecutive_failures += 1
            self.last_error_type = str(err)
            self._open_circuit_if_needed()
            if self.consecutive_failures >= 3:
                await self._set_connected_state(False)
            await self.connection.close()
            if self.data:
                return self.data
            raise UpdateFailed(f"SAJ AS1 Modbus update failed: {err}") from err

    async def async_write_register(self, address: int, value: int) -> bool:
        """Escribir un registro y actualizar caché de forma optimista."""
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()

        self._pending_writes += 1
        self._write_requested = True
        try:
            async with self._write_batch_lock:
                self._write_batch_values[address] = value
                self._write_batch_futures.setdefault(address, []).append(future)
                if self._write_batch_task is None or self._write_batch_task.done():
                    self._write_batch_task = self._hass.async_create_task(
                        self._flush_write_batch()
                    )

            return await future

        finally:
            self._pending_writes = max(0, self._pending_writes - 1)
            self._write_requested = self._pending_writes > 0

    async def _flush_write_batch(self) -> None:
        """Aplicar escrituras pendientes como un lote estilo Elekeeper."""
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

        async with self._write_batch_lock:
            if self._write_batch_values:
                self._write_batch_task = self._hass.async_create_task(
                    self._flush_write_batch()
                )
            else:
                self._write_batch_task = None

    async def async_set_profile(
        self,
        *,
        charge_power_pct: int | None = None,
        discharge_power_pct: int | None = None,
        user_mode: int | None = None,
    ) -> bool:
        """Aplicar un perfil completo en una sola llamada de servicio."""
        batch_values: dict[int, int] = {}
        if charge_power_pct is not None:
            batch_values[REGISTER_CHARGE_POWER_PCT] = charge_power_pct
        if discharge_power_pct is not None:
            batch_values[REGISTER_DISCHARGE_POWER_PCT] = discharge_power_pct
        if user_mode is not None:
            batch_values[REGISTER_USER_MODE] = user_mode

        if not batch_values:
            return True

        self._pending_writes += 1
        self._write_requested = True
        try:
            async with self._write_lock:
                results = await self._apply_write_batch(batch_values)
            return all(results.get(address, False) for address in batch_values)
        finally:
            self._pending_writes = max(0, self._pending_writes - 1)
            self._write_requested = self._pending_writes > 0

    async def _apply_write_batch(self, batch_values: dict[int, int]) -> dict[int, bool]:
        """Escribir un lote de registros con una sola ventana de asentamiento."""
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

            if set(CONFIG_KEYS).issubset(self._config_cache):
                self._last_config_update = time.monotonic()
            await self.connection.close()
            await asyncio.sleep(AIO3_WRITE_SETTLE_DELAY)

            if any(results.values()):
                await self._set_connected_state(True)
            return results

        except Exception as err:
            self.last_error_type = str(err)
            _LOGGER.warning("SAJ AS1 write batch failed: %s", err)
            await self.connection.close()
            await asyncio.sleep(AIO3_RECOVERY_DELAY)
            return {address: False for address in batch_values}

    def _ordered_write_addresses(self, batch_values: dict[int, int]) -> list[int]:
        """Ordenar escrituras: potencias primero y modo al final."""
        preferred_order = (
            REGISTER_CHARGE_POWER_PCT,
            REGISTER_DISCHARGE_POWER_PCT,
            REGISTER_USER_MODE,
        )
        ordered = [address for address in preferred_order if address in batch_values]
        ordered.extend(address for address in batch_values if address not in ordered)
        return ordered

    @staticmethod
    def _prepare_write_value(address: int, value: int) -> tuple[int, int]:
        """Preparar valor Modbus y valor de cache para un registro."""
        if address in (REGISTER_CHARGE_POWER_PCT, REGISTER_DISCHARGE_POWER_PCT):
            cache_value = validate_percentage(value & 0xFF)
            return inject_days_weekdays(cache_value), cache_value

        return value, value

    async def _write_register_with_recovery(self, address: int, value: int) -> None:
        """Escribir con reintento lento para registros delicados del AIO3."""
        last_error: Exception | None = None
        for attempt in range(1, AIO3_WRITE_RETRIES + 1):
            try:
                await self.connection.write_register(address, value)
                return
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
        fallback: dict[str, Any],
        reader: ReadMethod,
        label: str,
    ) -> None:
        """Actualizar un grupo de lectura o reutilizar su caché."""
        cache: dict[str, Any] = getattr(self, cache_attr)
        last_update: float = getattr(self, last_attr)
        due = now - last_update >= interval or not cache

        if not due:
            data.update(cache)
            return

        started = time.monotonic()
        try:
            bucket_data = await reader()
        except ReconnectionNeededError:
            self._bucket_last_duration[label] = round(time.monotonic() - started, 3)
            raise
        except Exception as err:
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
            return

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
        data.update(cache or fallback)

    def diagnostic_polling(self) -> dict[str, Any]:
        """Devolver metricas de polling utiles para diagnostico."""
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

    def _circuit_is_open(self, now: float) -> bool:
        """Indicar si el circuito esta abierto por fallos globales recientes."""
        return now < self._circuit_open_until

    def _open_circuit_if_needed(self) -> None:
        """Abrir un cooldown breve tras fallos globales consecutivos."""
        if self.consecutive_failures < AIO3_CIRCUIT_BREAKER_FAILURES:
            return

        if self._circuit_is_open(time.monotonic()):
            return

        self._circuit_open_count += 1
        self._circuit_open_until = time.monotonic() + AIO3_CIRCUIT_BREAKER_COOLDOWN
        _LOGGER.warning(
            "SAJ AS1 circuit breaker open for %.0fs after %d failures",
            AIO3_CIRCUIT_BREAKER_COOLDOWN,
            self.consecutive_failures,
        )

    async def _read_high(self) -> dict[str, Any]:
        """Leer potencias y SOC de alta frecuencia."""
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
        """Leer estado, BMS y configuración de frecuencia media."""
        data: dict[str, Any] = {}

        await self._wait_for_write_priority()
        mode_regs = await self.connection.read_registers(REGISTER_WORKING_MODE, 1)
        working_mode = read_uint16(mode_regs, 0)
        data["working_mode"] = working_mode
        data["working_mode_name"] = WORKING_MODES.get(
            working_mode,
            f"Unknown ({working_mode})",
        )

        await self._delay_between_blocks()
        data["error_count"] = read_uint16(
            await self.connection.read_registers(REGISTER_ERROR_COUNT, 1),
            0,
        )

        await self._delay_between_blocks()
        data["radiator_temp"] = read_temperature(
            await self.connection.read_registers(REGISTER_RADIATOR_TEMP, 1),
            0,
        )

        await self._delay_between_blocks()
        data.update(await self._read_grid_l1_status())

        await self._delay_between_blocks()
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
        """Leer tension, corriente y frecuencia L1 sin romper el bucket MEDIUM."""
        try:
            regs = await self.connection.read_registers(
                REGISTER_GRID_L1_STATUS_START,
                REGISTER_GRID_L1_STATUS_COUNT,
            )
        except (ModbusReadError, ReconnectionNeededError) as err:
            _LOGGER.debug("Grid L1 status block failed: %s", err)
            current_data = self.data or {}
            fallback: dict[str, float] = {}
            for key in ("grid_voltage_l1", "grid_current_l1", "grid_frequency_l1"):
                value = current_data.get(key)
                if isinstance(value, int | float):
                    fallback[key] = float(value)
            return fallback

        return {
            "grid_voltage_l1": read_voltage(regs, 0),
            "grid_current_l1": read_current(regs, 1),
            "grid_frequency_l1": round(read_uint16(regs, 2) / 100.0, 2),
        }

    async def _read_config(self) -> dict[str, Any]:
        """Leer configuración de usuario de baja variación."""
        data: dict[str, Any] = {}

        await self._wait_for_write_priority()
        await self._delay_between_blocks()
        data["user_mode"] = await self._read_user_mode_with_retry()

        await self._delay_between_blocks()
        charge_regs = await self._read_sensitive_register(
            REGISTER_CHARGE_POWER_PCT,
            "Potencia de carga",
        )
        data["first_charge_power_pct"] = validate_percentage(
            extract_byte_low(read_uint16(charge_regs, 0))
        )

        await self._delay_between_blocks()
        discharge_regs = await self._read_sensitive_register(
            REGISTER_DISCHARGE_POWER_PCT,
            "Potencia de descarga",
        )
        data["first_discharge_power_pct"] = validate_percentage(
            extract_byte_low(read_uint16(discharge_regs, 0))
        )

        return data

    async def _read_low(self) -> dict[str, Any]:
        """Leer contadores de energía acumulada de baja frecuencia."""
        await self._wait_for_write_priority()
        regs = await self.connection.read_registers(
            LOW_ENERGY_BLOCK_START,
            LOW_ENERGY_BLOCK_COUNT,
        )
        return self._energy_data_from_block(regs)

    @staticmethod
    def _energy_data_from_block(regs: list[int]) -> dict[str, float]:
        """Extraer energías acumuladas desde el bloque LOW contiguo."""
        return {
            key: read_energy(regs, address - LOW_ENERGY_BLOCK_START)
            for key, address in LOW_ENERGY_REGISTERS.items()
        }

    async def _read_user_mode_with_retry(self) -> int | None:
        """Leer modo de usuario con reintentos acotados."""
        try:
            regs = await self._read_sensitive_register(
                REGISTER_USER_MODE,
                "Modo de usuario",
            )
            user_mode = read_uint16(regs, 0)
            self._last_user_mode = user_mode
            return user_mode
        except ModbusReadError as err:
            _LOGGER.debug("No se pudo leer el modo de usuario: %s", err)

        return self._last_user_mode

    async def _read_sensitive_register(self, address: int, label: str) -> list[int]:
        """Leer un registro sensible con reintentos para AIO3 WiFi."""
        last_error: Exception | None = None
        for attempt in range(1, AIO3_SENSITIVE_RETRIES + 1):
            try:
                return await self.connection.read_registers(address, 1)
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
        """Aplicar una escritura correcta a las cachés del coordinador."""
        key: str | None = None
        if address == REGISTER_CHARGE_POWER_PCT:
            key = "first_charge_power_pct"
            value = validate_percentage(value)
        elif address == REGISTER_DISCHARGE_POWER_PCT:
            key = "first_discharge_power_pct"
            value = validate_percentage(value)
        elif address == REGISTER_USER_MODE:
            key = "user_mode"
            self._last_user_mode = value

        if key is None:
            return

        current_data = dict(self.data or {})
        current_data[key] = value
        self._config_cache[key] = value
        self.unavailable_keys.discard(key)
        self.async_set_updated_data(current_data)

    async def _wait_for_write_priority(self) -> None:
        """Pausar nuevos bloques de lectura si hay escritura pendiente."""
        while self._write_requested:
            await asyncio.sleep(0.01)

    async def _delay_between_blocks(self) -> None:
        """Esperar entre bloques Modbus para proteger el stick AS1."""
        await asyncio.sleep(AIOT_DELAY_MS / 1000.0)

    def _calc_derived(self, data: dict[str, Any]) -> None:
        """Calcular capacidad real y tiempos derivados de batería."""
        soh = data.get("bat1_soh", 100.0)
        soc = data.get("bat1_soc", 0.0)
        battery_power = data.get("battery_power", 0)

        capacity_real_kwh = BAT_ENERGY_CAPACITY_NOMINAL * (soh / 100.0)
        data["battery_capacity_real"] = round(capacity_real_kwh, 2)

        if battery_power > 10:
            remaining_capacity = capacity_real_kwh * (100 - soc) / 100
            data["battery_time_to_full"] = round(
                remaining_capacity / (battery_power / 1000.0),
                1,
            )
        else:
            data["battery_time_to_full"] = 0.0

        if battery_power < -10:
            usable_capacity = capacity_real_kwh * soc / 100
            data["battery_time_to_empty"] = round(
                usable_capacity / (abs(battery_power) / 1000.0),
                1,
            )
        else:
            data["battery_time_to_empty"] = 0.0

    async def _set_connected_state(self, connected: bool) -> None:
        """Actualizar conexión, logs y estado de reparación."""
        previous = self.is_connected
        self.is_connected = connected
        if connected == previous and connected != self._connection_issue_active:
            return

        if connected:
            if not previous:
                _LOGGER.info("Conexión SAJ AS1 Modbus recuperada")
            self._connection_issue_active = False
            ir.async_delete_issue(self.hass, DOMAIN, ISSUE_CONNECTION_UNAVAILABLE)
            return

        if previous:
            _LOGGER.warning("Conexión SAJ AS1 Modbus no disponible")
        self._connection_issue_active = True
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            ISSUE_CONNECTION_UNAVAILABLE,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_CONNECTION_UNAVAILABLE,
            translation_placeholders={"host": self.host},
        )

    @staticmethod
    def _zero_high() -> dict[str, Any]:
        """Devolver valores fallback de alta frecuencia."""
        return {
            "battery_power": 0,
            "battery_power_signed": 0,
            "bat1_soc": 0.0,
            "grid_import_power": 0,
            "grid_export_power": 0,
            "grid_power_signed": 0,
            "battery_charging_power": 0,
            "battery_discharging_power": 0,
            "total_load_power": 0,
            "total_pv_power": 0,
        }

    @staticmethod
    def _zero_medium() -> dict[str, Any]:
        """Devolver valores fallback de frecuencia media."""
        return {
            "working_mode": 0,
            "working_mode_name": "Standby",
            "error_count": 0,
            "radiator_temp": 0.0,
            "grid_voltage_l1": 0.0,
            "grid_current_l1": 0.0,
            "grid_frequency_l1": 0.0,
            "bat_number": 0,
            "bat1_soh": 100.0,
            "bat1_voltage": 0.0,
            "bat1_current": 0.0,
            "bat1_temp": 0.0,
            "bat1_cycles": 0,
        }

    @staticmethod
    def _zero_config() -> dict[str, Any]:
        """Devolver valores fallback de configuración."""
        return {
            "user_mode": None,
            "first_charge_power_pct": 100,
            "first_discharge_power_pct": 100,
        }

    @staticmethod
    def _zero_low() -> dict[str, Any]:
        """Devolver valores fallback de baja frecuencia."""
        return {
            "total_pv_energy": 0.0,
            "total_battery_charge_energy": 0.0,
            "total_battery_discharge_energy": 0.0,
            "total_load_energy": 0.0,
            "total_grid_export_energy": 0.0,
            "total_grid_import_energy": 0.0,
        }
