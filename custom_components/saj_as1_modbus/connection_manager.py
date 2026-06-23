"""Gestión de conexión Modbus TCP para SAJ AS1."""

from __future__ import annotations

import asyncio
import logging
import time

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException, ModbusIOException
from pymodbus.pdu import ExceptionResponse

from homeassistant.core import HomeAssistant

from .exceptions import (
    MaxRetriesExceededError,
    ModbusReadError,
    ModbusWriteError,
    ReconnectionNeededError,
)

_LOGGER = logging.getLogger(__name__)

CONNECTION_CACHE_TTL = 60.0
HEALTH_CHECK_INTERVAL = 30.0
MAX_RETRIES = 3
INITIAL_BACKOFF = 0.5
MAX_BACKOFF = 4.0


class ConnectionCache:
    """Caché TTL pequeña para un cliente Modbus conectado."""

    def __init__(self, cache_ttl: float = CONNECTION_CACHE_TTL) -> None:
        """Inicializar la caché."""
        self._cached_client: AsyncModbusTcpClient | None = None
        self._cache_expiry = 0.0
        self._cache_ttl = cache_ttl
        self._last_health_check = 0.0

    def get_cached_client(self) -> AsyncModbusTcpClient | None:
        """Devolver un cliente conectado cacheado si sigue sano."""
        now = time.monotonic()
        if self._cached_client is None or now >= self._cache_expiry:
            return None

        if not self._cached_client.connected:
            self.invalidate()
            return None

        if now - self._last_health_check > HEALTH_CHECK_INTERVAL:
            if not self._cached_client.connected:
                _LOGGER.debug("La comprobación de salud Modbus ha fallado")
                return None
            self._last_health_check = now

        return self._cached_client

    def set_cached_client(self, client: AsyncModbusTcpClient) -> None:
        """Guardar un cliente conectado."""
        self._cached_client = client
        self._cache_expiry = time.monotonic() + self._cache_ttl
        self._last_health_check = time.monotonic()

    def invalidate(self) -> None:
        """Invalidar el estado de conexión cacheado."""
        self._cached_client = None
        self._cache_expiry = 0.0
        self._last_health_check = 0.0


class ModbusConnectionManager:
    """Gestor de conexión e I/O Modbus de una sola trama cada vez."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        device_id: int,
        timeout: int = 10,
    ) -> None:
        """Inicializar el gestor de conexión."""
        self.hass = hass
        self._host = host
        self._port = port
        self._device_id = device_id
        self._timeout = timeout
        self._client: AsyncModbusTcpClient | None = None
        self._connection_lock = asyncio.Lock()
        self._io_lock = asyncio.Lock()
        self._reconnecting = False
        self._connection_cache = ConnectionCache()

    @property
    def host(self) -> str:
        """Devolver el host configurado."""
        return self._host

    @property
    def port(self) -> int:
        """Devolver el puerto configurado."""
        return self._port

    @property
    def device_id(self) -> int:
        """Devolver el ID de dispositivo Modbus configurado."""
        return self._device_id

    @property
    def connected(self) -> bool:
        """Indicar si el cliente actual está conectado."""
        return self._client is not None and self._client.connected

    async def get_client(self) -> AsyncModbusTcpClient:
        """Devolver un cliente conectado, reconectando si hace falta."""
        cached_client = self._connection_cache.get_cached_client()
        if cached_client is not None:
            return cached_client

        async with self._connection_lock:
            cached_client = self._connection_cache.get_cached_client()
            if cached_client is not None:
                return cached_client

            try:
                self._client = await self._connect_with_retries()
            except MaxRetriesExceededError as err:
                raise ReconnectionNeededError(str(err)) from err
            self._connection_cache.set_cached_client(self._client)
            return self._client

    async def read_registers(self, address: int, count: int) -> list[int]:
        """Leer registros holding del ID de dispositivo configurado."""
        try:
            result = await self._read_registers_once(address, count)
        except ModbusException as err:
            self._discard_client()
            raise ReconnectionNeededError(str(err)) from err

        if self._response_is_error(result):
            self._discard_client()
            raise ModbusReadError(f"Read failed at 0x{address:04X}")

        registers = getattr(result, "registers", None)
        if registers is None:
            self._discard_client()
            raise ModbusReadError(f"Read returned no registers at 0x{address:04X}")
        return list(registers)

    async def write_register(self, address: int, value: int) -> None:
        """Escribir un registro holding en el ID de dispositivo configurado."""
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                result = await self._write_register_once(address, value)
            except (ModbusException, ReconnectionNeededError) as err:
                last_error = err
                self._discard_client()
                if attempt == 0:
                    await asyncio.sleep(INITIAL_BACKOFF)
                    continue
                raise ReconnectionNeededError(str(err)) from err

            if self._response_is_error(result):
                last_error = ModbusWriteError(f"Write failed at 0x{address:04X}")
                self._discard_client()
                if attempt == 0:
                    await asyncio.sleep(INITIAL_BACKOFF)
                    continue
                raise last_error
            return

        raise ModbusWriteError(f"Write failed at 0x{address:04X}: {last_error}")

    async def _read_registers_once(self, address: int, count: int) -> object:
        """Ejecutar una lectura Modbus con el cliente actual."""
        client = await self.get_client()
        async with self._io_lock:
            if not client.connected:
                self._discard_client()
                raise ReconnectionNeededError("Cliente Modbus no conectado")
            return await client.read_holding_registers(
                address=address,
                count=count,
                device_id=self._device_id,
            )

    async def _write_register_once(self, address: int, value: int) -> object:
        """Ejecutar una escritura Modbus con el cliente actual."""
        client = await self.get_client()
        async with self._io_lock:
            if not client.connected:
                self._discard_client()
                raise ReconnectionNeededError("Cliente Modbus no conectado")
            return await client.write_register(
                address=address,
                value=value,
                device_id=self._device_id,
            )

    async def test_connection(self) -> None:
        """Abrir la conexión y validar que el dispositivo responde."""
        await self.read_registers(0x4004, 1)

    async def reconnect(self) -> bool:
        """Forzar una reconexión."""
        if self._reconnecting:
            return False

        async with self._connection_lock:
            if self._reconnecting:
                return False

            self._reconnecting = True
            try:
                self._connection_cache.invalidate()
                await self.close()
                self._client = await self._connect_with_retries()
                self._connection_cache.set_cached_client(self._client)
                _LOGGER.info("Reconectado a SAJ AS1 en %s:%d", self._host, self._port)
                return True
            except Exception as err:
                _LOGGER.warning("La reconexión con SAJ AS1 ha fallado: %s", err)
                return False
            finally:
                self._reconnecting = False

    async def close(self) -> None:
        """Cerrar el cliente actual si existe."""
        async with self._io_lock:
            self._close_unlocked()

    def _close_unlocked(self) -> None:
        """Cerrar el cliente actual con la exclusión de I/O ya adquirida."""
        self._connection_cache.invalidate()
        if self._client is None:
            return

        client = self._client
        self._client = None
        try:
            client.close()
        except Exception as err:
            _LOGGER.debug("Error al cerrar el cliente Modbus: %s", err)

    def update_config(
        self,
        host: str,
        port: int,
        device_id: int,
        timeout: int = 10,
    ) -> None:
        """Actualizar parámetros de conexión e invalidar el cliente actual."""
        if (
            host == self._host
            and port == self._port
            and device_id == self._device_id
            and timeout == self._timeout
        ):
            return

        self._host = host
        self._port = port
        self._device_id = device_id
        self._timeout = timeout
        self._connection_cache.invalidate()
        if self._client is not None:
            self.hass.async_create_task(self.close())

    async def _connect_with_retries(self) -> AsyncModbusTcpClient:
        """Conectar con reintentos exponenciales acotados."""
        last_exception: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if self._client is None:
                    self._client = AsyncModbusTcpClient(
                        host=self._host,
                        port=self._port,
                        reconnect_delay=0,
                        reconnect_delay_max=0,
                        timeout=self._timeout,
                        retries=1,
                    )

                connected = await self._client.connect()
                if connected or self._client.connected:
                    return self._client

                raise ConnectionError(f"Unable to connect to {self._host}:{self._port}")

            except (ConnectionError, ModbusIOException, ModbusException) as err:
                last_exception = err
                self._discard_client()
                if attempt >= MAX_RETRIES:
                    break

                backoff = min(INITIAL_BACKOFF * 2 ** (attempt - 1), MAX_BACKOFF)
                _LOGGER.debug(
                    "Modbus connection attempt %d/%d failed, retrying in %.1fs: %s",
                    attempt,
                    MAX_RETRIES,
                    backoff,
                    err,
                )
                await asyncio.sleep(backoff)

        raise MaxRetriesExceededError(
            f"Failed to connect after {MAX_RETRIES} attempts: {last_exception}"
        )

    def _discard_client(self) -> None:
        """Cerrar y descartar un cliente tras un intento de conexión fallido."""
        if self._client is None:
            self._connection_cache.invalidate()
            return
        try:
            self._client.close()
        except Exception:
            pass
        self._client = None
        self._connection_cache.invalidate()

    @staticmethod
    def _response_is_error(response: object) -> bool:
        """Indicar si una respuesta de PyModbus representa un error."""
        is_error = getattr(response, "isError", None)
        return isinstance(response, ExceptionResponse) or (
            callable(is_error) and is_error()
        )
