"""Modelos internos para la integración SAJ AS1 Modbus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .coordinator import SAJModbusCoordinator


@dataclass(frozen=True, slots=True)
class SAJRegisterDescription:
    """Descripción de un registro Modbus usado por la integración."""

    key: str
    address: int
    count: int = 1


@dataclass(slots=True)
class SAJRuntimeData:
    """Datos runtime guardados en la entrada de Home Assistant."""

    coordinator: "SAJModbusCoordinator"
