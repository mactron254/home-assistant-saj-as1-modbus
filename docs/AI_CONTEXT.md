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
- Runtime Modbus dependency: the integration uses the PyModbus version bundled by Home Assistant through `after_dependencies: ["modbus"]`.
- Compatibility target: keep API usage compatible with PyModbus 3.11.2 when Home Assistant ships it, while allowing newer Home Assistant releases such as 2026.7.1 to provide PyModbus 3.13.1.

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
- Bit 0 of `0x3604` first charge schedule enable.
- Bit 0 of `0x3605` first discharge schedule enable.
- `0x3606` and `0x3607` first charge start/end time.
- `0x3608` first charge power percentage.
- `0x361B` and `0x361C` first discharge start/end time.
- `0x361D` first discharge power percentage.
- Service: `saj_as1_modbus.set_profile`.

Read configuration in blocks `0x3604-0x3608` and `0x361B-0x361D`.
Time uses hour in the high byte and minute in the low byte. Enable writes must
read the full original mask, change bit 0, preserve all other bits, and fail
closed when the mask cannot be read. Write times/rates before enable masks and
user mode last. Equal schedule values must not be written again.

Charge/discharge percentage writes keep the existing weekday high byte.

PredBat must never read or write physical SoC registers `0x3373` or `0x3374`.
Do not expose target SoC, reserve SoC, or charge-limit entities. Keep
`has_fox_inverter_mode: false` because PredBat hard-codes `SelfUse`; use
explicit services for `Autoconsumo` and `Horario de Uso`.

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
