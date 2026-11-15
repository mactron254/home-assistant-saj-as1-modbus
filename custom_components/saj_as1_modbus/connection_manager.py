"""Modbus TCP connection handling for the SAJ AS1."""

from __future__ import annotations

import asyncio
import logging

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse

from .const import MODBUS_TIMEOUT, REGISTER_WORKING_MODE
from .exceptions import (
    ConnectFailedError,
    ModbusReadError,
    ModbusReadRejectedError,
    ModbusWriteError,
    ModbusWriteRejectedError,
    ReconnectionNeededError,
)

_LOGGER = logging.getLogger(__name__)

CONNECT_ATTEMPTS = 3
INITIAL_BACKOFF = 0.5
MAX_BACKOFF = 4.0
# Extra time on top of the PyModbus connect timeout before the attempt is
# abandoned. PyModbus bounds connect() itself, this only guards against a
# connect that never returns (SYN blackhole of a crashed WiFi stick).
CONNECT_TIMEOUT_MARGIN = 2.0
FAST_WRITE_RETRY_DELAY = 0.5

# Exception codes that are returned again on every retry.
DETERMINISTIC_EXCEPTION_CODES = frozenset({1, 2, 3})

# Exception codes that do not depend on the session. They are kept in the
# error text so diagnostics show why a block was rejected.
EXCEPTION_CODE_NAMES = {
    1: "illegal function",
    2: "illegal data address",
    3: "illegal data value",
    4: "server device failure",
    6: "server device busy",
    10: "gateway path unavailable",
    11: "gateway target failed to respond",
}


def _raise_if_cancelling() -> None:
    """Re-raise a cancellation that PyModbus turned into a Modbus error.

    PyModbus reports a cancelled request as ``ModbusIOException``. Treating it
    as a communication failure would retry and keep the cancelled poll cycle
    (or an unloaded entry) talking to the stick.
    """
    task = asyncio.current_task()
    if task is not None and task.cancelling():
        raise asyncio.CancelledError


def _exception_code(response: object) -> int | None:
    """Return the exception code of a Modbus error response, if any."""
    code = getattr(response, "exception_code", None)
    return code if isinstance(code, int) else None


class ModbusConnectionManager:
    """Own the single Modbus TCP session to one AS1 endpoint.

    The AIO3 WiFi stick tolerates one client at a time and becomes unstable
    when PyModbus reconnects on its own, so the session is opened on demand,
    every operation is serialized, PyModbus auto-reconnect is disabled and the
    coordinator closes the session at the end of every poll cycle.
    """

    def __init__(
        self,
        host: str,
        port: int,
        device_id: int,
        timeout: float = MODBUS_TIMEOUT,
        connect_attempts: int = CONNECT_ATTEMPTS,
    ) -> None:
        """Initialize the connection manager."""
        self.connect_attempts = connect_attempts
        self._host = host
        self._port = port
        self._device_id = device_id
        self._timeout = timeout
        self._client: AsyncModbusTcpClient | None = None
        self._connection_lock = asyncio.Lock()
        self._io_lock = asyncio.Lock()

    @property
    def host(self) -> str:
        """Return the configured host."""
        return self._host

    @property
    def port(self) -> int:
        """Return the configured port."""
        return self._port

    @property
    def device_id(self) -> int:
        """Return the configured Modbus device id."""
        return self._device_id

    @property
    def connected(self) -> bool:
        """Return whether a session is currently open."""
        return self._client is not None and self._client.connected

    async def read_registers(self, address: int, count: int) -> list[int]:
        """Read holding registers from the configured device id."""
        client = await self._get_client()
        async with self._io_lock:
            try:
                if not client.connected:
                    raise ReconnectionNeededError("Modbus session is not connected")
                result = await client.read_holding_registers(
                    address=address,
                    count=count,
                    device_id=self._device_id,
                )
            except (ModbusException, OSError, ReconnectionNeededError) as err:
                self._discard_client_unlocked()
                _raise_if_cancelling()
                raise ReconnectionNeededError(
                    f"Read failed at 0x{address:04X}: {err}"
                ) from err

            if self._response_is_error(result):
                self._discard_client_unlocked()
                error_class = (
                    ModbusReadRejectedError
                    if _exception_code(result) in DETERMINISTIC_EXCEPTION_CODES
                    else ModbusReadError
                )
                raise error_class(
                    f"Read rejected at 0x{address:04X}{self._describe_error(result)}"
                )

            registers = getattr(result, "registers", None)
            if registers is None or len(registers) < count:
                self._discard_client_unlocked()
                raise ModbusReadError(
                    f"Read returned too few registers at 0x{address:04X}"
                )
            return list(registers[:count])

    async def write_register(self, address: int, value: int) -> None:
        """Write one holding register, retrying once on a broken session.

        A connection that cannot be opened at all, or a deterministic
        rejection (codes 1-3), is not retried here; the coordinator owns the
        slow retry policy.
        """
        error: Exception | None = None
        for attempt in range(2):
            client = await self._get_client()
            async with self._io_lock:
                try:
                    if not client.connected:
                        raise ReconnectionNeededError("Modbus session is not connected")
                    result = await client.write_register(
                        address=address,
                        value=value,
                        device_id=self._device_id,
                    )
                except (ModbusException, OSError, ReconnectionNeededError) as err:
                    self._discard_client_unlocked()
                    _raise_if_cancelling()
                    error = ReconnectionNeededError(
                        f"Write failed at 0x{address:04X}: {err}"
                    )
                else:
                    if not self._response_is_error(result):
                        return
                    self._discard_client_unlocked()
                    if _exception_code(result) in DETERMINISTIC_EXCEPTION_CODES:
                        raise ModbusWriteRejectedError(
                            f"Write rejected at 0x{address:04X}"
                            f"{self._describe_error(result)}"
                        )
                    error = ModbusWriteError(
                        f"Write rejected at 0x{address:04X}"
                        f"{self._describe_error(result)}"
                    )
            if attempt == 0:
                await asyncio.sleep(FAST_WRITE_RETRY_DELAY)

        assert error is not None
        raise error

    async def test_connection(self) -> None:
        """Open a session and check that the inverter answers a known register."""
        await self.read_registers(REGISTER_WORKING_MODE, 1)

    async def close(self) -> None:
        """Close the current session, waiting for an in-flight operation."""
        async with self._io_lock:
            self._discard_client_unlocked()

    async def _get_client(self) -> AsyncModbusTcpClient:
        """Return a connected client, opening a new session if needed."""
        client = self._client
        if client is not None and client.connected:
            return client

        async with self._connection_lock:
            if self._client is not None and self._client.connected:
                return self._client
            self._client = await self._connect_with_retries()
            return self._client

    async def _connect_with_retries(self) -> AsyncModbusTcpClient:
        """Open a session with a short, bounded exponential backoff."""
        last_error: Exception | None = None
        attempts = max(1, self.connect_attempts)
        for attempt in range(1, attempts + 1):
            client = AsyncModbusTcpClient(
                host=self._host,
                port=self._port,
                reconnect_delay=0,
                reconnect_delay_max=0,
                timeout=self._timeout,
                retries=1,
            )
            connected = False
            try:
                async with asyncio.timeout(self._timeout + CONNECT_TIMEOUT_MARGIN):
                    connected = await client.connect()
            except (TimeoutError, OSError, ModbusException) as err:
                last_error = err

            if connected or client.connected:
                return client

            self._close_quietly(client)
            if attempt < attempts:
                backoff = min(INITIAL_BACKOFF * 2 ** (attempt - 1), MAX_BACKOFF)
                _LOGGER.debug(
                    "Modbus connection attempt %d/%d to %s:%d failed, retrying in %.1fs",
                    attempt,
                    attempts,
                    self._host,
                    self._port,
                    backoff,
                )
                await asyncio.sleep(backoff)

        detail = f": {last_error}" if last_error else ""
        raise ConnectFailedError(
            f"Unable to connect to {self._host}:{self._port} "
            f"after {attempts} attempts{detail}"
        )

    def _discard_client_unlocked(self) -> None:
        """Close and forget the current client. The I/O lock must be held."""
        client, self._client = self._client, None
        if client is not None:
            self._close_quietly(client)

    @staticmethod
    def _close_quietly(client: AsyncModbusTcpClient) -> None:
        """Close a client, ignoring errors from an already broken transport."""
        try:
            client.close()
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Error while closing the Modbus client: %s", err)

    @staticmethod
    def _response_is_error(response: object) -> bool:
        """Return whether a PyModbus response is an error response."""
        is_error = getattr(response, "isError", None)
        return isinstance(response, ExceptionResponse) or (
            callable(is_error) and bool(is_error())
        )

    @staticmethod
    def _describe_error(response: object) -> str:
        """Return a short description of a Modbus exception response."""
        code = _exception_code(response)
        if code is None:
            return ""
        name = EXCEPTION_CODE_NAMES.get(code, "device specific")
        return f" (exception code {code}: {name})"
