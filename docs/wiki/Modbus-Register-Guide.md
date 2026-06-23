# Modbus Register Guide

## Reference files

- `docs/reference/AS1Main control board and display board communication protocol (1).pdf`
- `docs/reference/host_controller_display_panel_protocol.md`
- `docs/reference/Documentacion pymodbus 3.11.2.md`
- `docs/reference/Documentacion pymodbus 3.13.0.md`

## Address convention

Use protocol hexadecimal addresses directly. Do not apply `-1` offset for PyModbus in this integration.

Example:

- Protocol register `0x4031` is used in code as `0x4031`.
- Do not convert it to `0x4030`.

## Data types

Conversion helpers live in `custom_components/saj_as1_modbus/modbus_processing.py`.

| Protocol type | Helper | Notes |
| --- | --- | --- |
| `UInt16` | `read_uint16(registers, index)` | Unsigned 16-bit |
| `Int16` | `read_int16(registers, index)` | Signed 16-bit |
| `UInt32` | `read_uint32(registers, index)` | Two registers, high word first |
| voltage x0.1 | `read_voltage(registers, index)` | Returns volts |
| current x0.01 | `read_current(registers, index)` | Returns amperes |
| temperature x0.1 | `read_temperature(registers, index)` | Returns Celsius |
| percentage x0.01 | `read_percentage(registers, index)` | Returns percent |
| energy x0.01 | `read_energy(registers, index)` | Returns kWh |

## Existing register groups

`custom_components/saj_as1_modbus/const.py` defines:

- `REGISTER_POWER_BLOCK_START` / `REGISTER_POWER_BLOCK_COUNT`
- `REGISTER_GRID_L1_STATUS_START` / `REGISTER_GRID_L1_STATUS_COUNT`
- `REGISTER_BMS_START` / `REGISTER_BMS_COUNT`
- `LOW_ENERGY_REGISTERS`
- `REGISTER_USER_MODE`
- `REGISTER_CHARGE_POWER_PCT`
- `REGISTER_DISCHARGE_POWER_PCT`

If the new register is inside an existing block, read it from that block. Do not add a separate Modbus request.

## Write-register rule

Do not add write support unless:

- Register is documented.
- Behavior is understood.
- Manual test is safe.
- `SAFETY.md` and tests are updated.
- Writes remain serialized through coordinator methods.
