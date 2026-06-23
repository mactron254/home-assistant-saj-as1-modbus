# SAJ AS1 Modbus Wiki

This wiki documents the public Home Assistant custom integration for SAJ AS1 over Modbus TCP/IP.

> Unofficial community integration. Not affiliated with, endorsed, approved, or supported by SAJ.

## Pages

- [Architecture](Architecture.md)
- [Modbus Register Guide](Modbus-Register-Guide.md)
- [Adding a Modbus Sensor](Adding-Modbus-Sensor.md)
- [Release and HACS](Release-HACS.md)
- [Troubleshooting](Troubleshooting.md)

## Repository layout

- Runtime integration: `custom_components/saj_as1_modbus/`
- Tests: `tests/`
- Public docs: `docs/`
- Modbus/manual references: `docs/reference/`
- Wiki source: `docs/wiki/`

## Transport scope

This project supports Modbus TCP/IP only. It does not implement direct Modbus RTU/RS485.
