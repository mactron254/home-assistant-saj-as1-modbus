# PredBat SAJ AS1 continuation

## Goal

Finish the unofficial SAJ AS1 Modbus TCP/IP compatibility layer for PredBat
without touching physical SoC registers.

## Implemented

- Four first-slot time entities and two read-modify-write switches.
- Block reads `0x3604-0x3608` and `0x361B-0x361D`.
- Minute precision, idempotence, caches, and AIO3 retries.
- Test proving `0x3373/0x3374` are absent from Python operations.
- Copy-ready `apps-saj-as1.yaml`.
- `has_fox_inverter_mode: false` because PredBat hard-codes `SelfUse`.
- Upstream pinned to `18a56d174c44d3689263c773d44020bcb63b5161`.

## Pending

1. Full pytest, strict mypy, HACS, Hassfest, CodeQL.
2. Five-minute charge/discharge sign tests at 10%.
3. Mode, early-stop, restart, partial-failure, and rollback tests.
4. Keep feature PR draft until hardware proof.
5. Squash merge and publish `v1.1.0` only after proof.
6. Open upstream PredBat draft only after real testing.

## Safety invariants

- SoC remains 15-100%; never access `0x3373/0x3374`.
- Never clear schedule slots 2-7.
- Fox and GivEnergy mode behavior stays disabled.
- Normal is `Autoconsumo`; active schedule is `Horario de Uso`.
- Rollback disables both switches then selects `Autoconsumo`.
