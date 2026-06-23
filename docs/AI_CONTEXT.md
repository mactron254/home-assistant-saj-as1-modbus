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
- Runtime Modbus dependency: `pymodbus==3.11.2`

## Architecture

- `connection_manager.py` owns Modbus TCP connection lifecycle, locking, reads, writes, and reconnect behavior.
- `coordinator.py` owns polling buckets, cache, AIO3 pacing, circuit breaker, and write batching.
- `modbus_processing.py` owns register conversion and scaling.
- Entity platforms expose Home Assistant entities only; keep protocol logic outside entity classes.
- `diagnostics.py` must redact network-sensitive data.

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

Charge/discharge percentage writes include the weekday high byte behavior already implemented by the integration.

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
