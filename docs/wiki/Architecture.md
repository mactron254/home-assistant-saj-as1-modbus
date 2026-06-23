# Architecture

This is an AI-generated project. Code, documentation, review, tests, and maintenance workflows were generated or reviewed with AI.

## Runtime layers

| Area | File | Purpose |
| --- | --- | --- |
| Setup/services | `custom_components/saj_as1_modbus/__init__.py` | Setup, unload, service registration, profile service dispatch |
| Config flow | `custom_components/saj_as1_modbus/config_flow.py` | UI setup, reconfigure flow, connection test before saving |
| Constants/map | `custom_components/saj_as1_modbus/const.py` | Domain, versions, polling intervals, register addresses, bucket keys |
| Modbus I/O | `custom_components/saj_as1_modbus/connection_manager.py` | TCP client, read/write locks, close/reconnect behavior |
| Coordinator | `custom_components/saj_as1_modbus/coordinator.py` | Polling buckets, cache, circuit breaker, write batching, derived values |
| Conversion | `custom_components/saj_as1_modbus/modbus_processing.py` | UInt16, Int16, UInt32, scaling helpers |
| Entities | `sensor.py`, `number.py`, `select.py`, `binary_sensor.py` | Home Assistant entity descriptions and values |
| Diagnostics | `custom_components/saj_as1_modbus/diagnostics.py` | Redacted diagnostics |
| Translations/icons | `strings.json`, `translations/es.json`, `icons.json` | UI names, errors, icon translations |

## Polling buckets

Buckets are fixed in `const.py`:

- `HIGH`: 30 s, live powers and SOC.
- `MEDIUM`: 60 s, operating state, BMS, temperature, grid L1.
- `CONFIG`: 300 s, user mode and writable percentages.
- `LOW`: 300 s, accumulated energy counters.

Do not expose polling intervals in the config flow. Home Assistant integrations should control their own polling cadence.

## AIO3 stability rules

- Keep Modbus blocks small enough for the AIO3 WiFi bridge.
- Do not add broad register scans.
- Keep write operations serialized.
- Close the Modbus client between sensitive operations when existing code already does this.
- Prefer adding one documented register to an existing bucket over creating a new fast bucket.
