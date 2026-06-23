"""Funciones de procesamiento Modbus para SAJ AS1 - v2.8.5 FINAL.

ARQUITECTURA PROFESIONAL
========================
Funciones especializadas para convertir registros Modbus a valores reales.
Basado ESTRICTAMENTE en el manual oficial SAJ AS1:
- AS1Main_control_board_and_display_board_communication_protocol.pdf
- Section 4.3: Realtime Data register definition

MAGNIFICATIONS (Escalas según manual):
- 0: Sin escala (valor directo)
- -1: Dividir por 10 (voltaje, temperatura)
- -2: Dividir por 100 (corriente, SOC, SOH, energía)

TIPOS DE DATOS (según manual):
- Int16: Con signo (-32768 a 32767)
- UInt16: Sin signo (0 a 65535)
- UInt32: 2 registros (0 a 4294967295)
"""
from __future__ import annotations

from typing import List


def read_int16(registers: List[int], index: int) -> int:
    """Lee valor Int16 con signo desde registros.
    
    Según manual AS1: Type Int16
    
    Args:
        registers: Lista de registros Modbus
        index: Índice del registro a leer
    
    Returns:
        Valor con signo (-32768 a 32767)
    
    Example:
        >>> read_int16([32768], 0)
        -32768
        >>> read_int16([100], 0)
        100
    """
    val = registers[index]
    return val if val < 32768 else val - 65536


def read_uint16(registers: List[int], index: int) -> int:
    """Lee valor UInt16 sin signo desde registros.
    
    Según manual AS1: Type UInt16
    
    Args:
        registers: Lista de registros Modbus
        index: Índice del registro a leer
    
    Returns:
        Valor sin signo (0 a 65535)
    
    Example:
        >>> read_uint16([32768], 0)
        32768
        >>> read_uint16([100], 0)
        100
    """
    return registers[index]


def read_uint32(registers: List[int], index: int) -> int:
    """Lee valor UInt32 (2 registros) sin signo.
    
    Según manual AS1: Type UInt32
    
    Args:
        registers: Lista de registros Modbus
        index: Índice del primer registro (alto)
    
    Returns:
        Valor sin signo de 32 bits
    
    Example:
        >>> read_uint32([1, 0], 0)
        65536
        >>> read_uint32([0, 100], 0)
        100
    """
    high = registers[index]
    low = registers[index + 1]
    return (high << 16) | low


def read_temperature(registers: List[int], index: int) -> float:
    """Lee temperatura con escala -1 (dividir por 10).
    
    Según manual AS1:
    - 0x4010 (SinkTempC): Int16, magnification -1, °C
    - 0xA010 (Bat1Temperature): Int16, magnification -1, °C
    
    Args:
        registers: Lista de registros Modbus
        index: Índice del registro de temperatura
    
    Returns:
        Temperatura en °C con 1 decimal
    
    Example:
        >>> read_temperature([235], 0)
        23.5
        >>> read_temperature([65436], 0)  # -100 raw
        -10.0
    """
    raw = read_int16(registers, index)
    return round(raw / 10.0, 1)


def read_voltage(registers: List[int], index: int) -> float:
    """Lee voltaje con escala -1 (dividir por 10).
    
    Según manual AS1:
    - 0x4069 (BatVolt): UInt16, magnification -1, V
    - 0xA00E (Bat1Voltage): UInt16, magnification -1, V
    
    Args:
        registers: Lista de registros Modbus
        index: Índice del registro de voltaje
    
    Returns:
        Voltaje en V con 1 decimal
    
    Example:
        >>> read_voltage([512], 0)
        51.2
        >>> read_voltage([140], 0)
        14.0
    """
    raw = read_uint16(registers, index)
    return round(raw / 10.0, 1)


def read_current(registers: List[int], index: int) -> float:
    """Lee corriente con escala -2 (dividir por 100).
    
    Según manual AS1:
    - 0x406A (BatCurr): Int16, magnification -2, A
    - 0xA00F (Bat1Current): Int16, magnification -2, A
    
    Args:
        registers: Lista de registros Modbus
        index: Índice del registro de corriente
    
    Returns:
        Corriente en A con 2 decimales
    
    Example:
        >>> read_current([150], 0)
        1.5
        >>> read_current([65486], 0)  # -50 raw
        -0.5
    """
    raw = read_int16(registers, index)
    return round(raw / 100.0, 2)


def read_percentage(registers: List[int], index: int) -> float:
    """Lee porcentaje con escala -2 (dividir por 100).
    
    Según manual AS1:
    - 0x406F (BatEnergyPercent): UInt16, magnification -2, %
    - 0xA00C (Bat1SOC): UInt16, magnification -2, %
    - 0xA00D (Bat1SOH): UInt16, magnification -2, %
    
    Args:
        registers: Lista de registros Modbus
        index: Índice del registro de porcentaje
    
    Returns:
        Porcentaje con 2 decimales (0.00 a 100.00)
    
    Example:
        >>> read_percentage([8700], 0)
        87.0
        >>> read_percentage([9832], 0)
        98.32
    """
    raw = read_uint16(registers, index)
    return round(raw / 100.0, 2)


def read_power(registers: List[int], index: int) -> int:
    """Lee potencia con signo (sin escala).
    
    Según manual AS1 (magnification 0):
    - 0x4099 (PVConsumpWatt): Int16, W
    - 0x409A (GridConsumpWatt): Int16, W
    - 0x409B (GridFeedInPVWatt): Int16, W
    - 0x409D (BatConsumpWatt): Int16, W
    - 0x40A0 (SysTotalLoadWatt): Int16, W
    - 0x40A5 (TotalPVPower): Int16, W
    - 0x406D (BatPower): Int16, W
    
    Args:
        registers: Lista de registros Modbus
        index: Índice del registro de potencia
    
    Returns:
        Potencia en W (puede ser negativa)
    
    Example:
        >>> read_power([1500], 0)
        1500
        >>> read_power([64036], 0)  # -1500 raw
        -1500
    """
    return read_int16(registers, index)


def read_power_unsigned(registers: List[int], index: int) -> int:
    """Lee potencia sin signo (sin escala).
    
    Usado para valores que siempre son positivos según manual AS1.
    
    Args:
        registers: Lista de registros Modbus
        index: Índice del registro de potencia
    
    Returns:
        Potencia en W (siempre positiva)
    
    Example:
        >>> read_power_unsigned([3500], 0)
        3500
    """
    return read_uint16(registers, index)


def read_energy(registers: List[int], index: int) -> float:
    """Lee energía de 32 bits con escala -2 (dividir por 100).
    
    Según manual AS1 (magnification -2):
    - 0x40BF-0x40C0 (Today_PVEnergy): UInt32, kWh
    - 0x40C5-0x40C6 (Total_PVEnergy): UInt32, kWh
    - 0x40C7-0x40C8 (Today_BatChgEnergy): UInt32, kWh
    - Y muchos más registros de energía
    
    Args:
        registers: Lista de registros Modbus
        index: Índice del primer registro (alto)
    
    Returns:
        Energía en kWh con 2 decimales
    
    Example:
        >>> read_energy([0, 12345], 0)
        123.45
        >>> read_energy([1, 0], 0)
        655.36
    """
    raw = read_uint32(registers, index)
    return round(raw / 100.0, 2)


def extract_byte_low(value: int) -> int:
    """Extrae byte bajo (8 bits inferiores) de un registro de 16 bits.
    
    Usado para extraer porcentajes de registros compartidos (0x3608, 0x361D).
    
    Args:
        value: Valor de 16 bits
    
    Returns:
        Byte bajo (0-255)
    
    Example:
        >>> extract_byte_low(0x7F32)
        50
        >>> extract_byte_low(0x0064)
        100
    """
    return value & 0xFF


def extract_byte_high(value: int) -> int:
    """Extrae byte alto (8 bits superiores) de un registro de 16 bits.
    
    Usado para extraer días de la semana de registros compartidos.
    
    Args:
        value: Valor de 16 bits
    
    Returns:
        Byte alto (0-255)
    
    Example:
        >>> extract_byte_high(0x7F32)
        127
        >>> extract_byte_high(0x0064)
        0
    """
    return (value >> 8) & 0xFF


def inject_days_weekdays(percentage: int) -> int:
    """Inyecta días Lunes-Domingo (0x7F) en byte alto.
    
    DNA AS1 INNEGOCIABLE:
    Según manual AS1, registros 0x3608 y 0x361D:
    - Byte alto = días semana (0x7F = 0111 1111 = Lunes a Domingo)
    - Byte bajo = porcentaje de potencia (0-100)
    
    Args:
        percentage: Porcentaje de potencia (0-100)
    
    Returns:
        Valor de 16 bits con días inyectados
    
    Example:
        >>> hex(inject_days_weekdays(50))
        '0x7f32'
        >>> hex(inject_days_weekdays(100))
        '0x7f64'
    """
    return (0x7F << 8) | (percentage & 0xFF)


def validate_percentage(value: int) -> int:
    """Valida y corrige porcentaje al rango 1-100.
    
    Args:
        value: Valor de porcentaje
    
    Returns:
        Porcentaje válido (1-100, o 100 si 0)
    
    Example:
        >>> validate_percentage(50)
        50
        >>> validate_percentage(0)
        100
        >>> validate_percentage(150)
        100
    """
    if value <= 0:
        return 100
    if value > 100:
        return 100
    return value
