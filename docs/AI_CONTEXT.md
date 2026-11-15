# AI Context

This file is for future AI agents and maintainers.

## AI-generated disclosure

This project was built, documented, reviewed, tested, and maintained using AI-generated workflows. Future changes must preserve the public "AI-generated project" disclosure in README files, `DISCLAIMER.md`, and wiki documentation.

## Project identity

- Integration: `SAJ AS1 Modbus`
- Domain: `saj_as1_modbus`
- Repository target: `mactron254/home-assistant-saj-as1-modbus`
- Status: unofficial community integration, not supported by SAJ
- Transport: Modbus TCP/IP only
- Runtime Modbus dependency: the integration uses the PyModbus version bundled by Home Assistant through `after_dependencies: ["modbus"]`, and declares only a lower bound (`pymodbus>=3.11.2`). Never pin an exact version: it broke startup twice when Home Assistant moved to another PyModbus release.
- Validation engine: Home Assistant 2026.9+ validates with probatio and aliases `import voluptuous` to it. Keep importing voluptuous while 2026.5 is supported; schemas are typed `Any` so mypy passes on both.
- Compatibility target: keep API usage compatible with PyModbus 3.11.2 when Home Assistant ships it, while allowing newer Home Assistant releases such as 2026.7.1 to provide PyModbus 3.13.1.

## Architecture

- `connection_manager.py` owns Modbus TCP connection lifecycle, locking, reads, writes, and reconnect behavior.
- `coordinator.py` owns polling buckets, cache, AIO3 pacing, circuit breaker, and write batching.
- `modbus_processing.py` owns register conversion and scaling.
- Entity platforms expose Home Assistant entities only; keep protocol logic outside entity classes.
- `diagnostics.py` must redact network-sensitive data.

## Connection model (decided after reviewing saj-h2-modbus, 2026-11)

Only the connection handling was taken from the saj-h2-modbus review. Do not
add register reads or entities from it (the 0x8F00 information block was
deliberately left out).

- One session per poll cycle, closed at the end of the cycle. Do not switch to
  a persistent connection: the AIO3 stick misbehaves when the session stays
  open while Elekeeper also talks to it (see `INCIDENCIAS_SOLUCIONES.md`).
- PyModbus auto-reconnect stays disabled (`reconnect_delay=0`).
- `ConnectFailedError` (host unreachable) is never retried by the fast retry
  layers; only the coordinator slow write retry tries again.
- The whole poll cycle is bounded by `POLL_CYCLE_TIMEOUT`.
- After `STALE_DATA_MAX_FAILURES` failed cycles the coordinator raises
  `UpdateFailed`; before that it keeps the last values.
- Home Assistant 2026.9+ offers shared Modbus connections
  (`homeassistant.components.modbus.async_get_unit`). Migrating to it is a
  separate step that must be tested with the AIO3 stick first.

## Modbus constraints

- The AIO3 WiFi bridge can become unstable when hammered.
- Keep reads grouped but conservative.
- Keep sensitive config reads separate from live data.
- Keep writes serialized and patient.
- Do not add broad scans of undocumented ranges.
- Do not add L2/L3 grid sensors unless documented and tested.

## Write behavior

Supported writes:

- `0x3371` user mode.
- `0x3608` first charge power percentage.
- `0x361D` first discharge power percentage.
- Service: `saj_as1_modbus.set_profile`.

Charge/discharge percentage writes keep the weekday mask (high byte) last read from the register; an empty mask falls back to `0x7F` (every day).

## Public documentation rules

- Always include unofficial SAJ disclaimer in public entry points.
- Always state Modbus TCP/IP only.
- Do not weaken the AI-generated project disclosure.
- Keep root `README.md` in English.
- Keep `README.es.md`, `README.de.md`, and `README.fr.md` aligned for safety and install notes.

## Validation

Run:

```powershell
.\.venv\Scripts\pytest.exe tests --rootdir=tests
mypy --strict --ignore-missing-imports --explicit-package-bases custom_components\saj_as1_modbus tests
```

CI must include Python tests, HACS validation, and Hassfest.
