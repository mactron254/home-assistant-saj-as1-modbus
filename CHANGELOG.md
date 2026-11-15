# Changelog

## 2.0.0

Same entities and register map as 1.0.2 (no new sensors and no new register
reads). Improvements for Home Assistant 2026/2027, connection fixes and bug
fixes.

### Breaking changes

- The **User mode** select now uses the states `self_use`, `time_of_use`,
  `backup` and `manual` (shown translated in the UI, so Spanish users still see
  `Autoconsumo`, `Horario de Uso`, `Reserva` and `Manual`). Update automations
  and conditions that compare the select state or call `select.select_option`
  with the Spanish labels. The `set_profile` action still accepts the old
  labels.
- The **Working mode** sensor is now an enum sensor with the states
  `standby`, `self_use`, `peak_shaving`, `backup` and `off_grid` (translated in
  the UI). Unknown values are reported as unknown instead of `Unknown (n)`.

### Connection

- A whole poll cycle is bounded to 300 s, so a stalled connection cannot stop
  polling silently.
- An unreachable host is no longer retried by every layer (up to 12 connect
  attempts per register write before, at most 6 now).
- Write priority uses an event instead of polling every 10 ms, and pending
  writes are resolved when the entry unloads instead of hanging.
- Unchanged on purpose: one Modbus session per poll cycle, closed at the end,
  and PyModbus auto-reconnect disabled (the AIO3 stick needs both).

### Fixes

- Entities become unavailable after three consecutive failed poll cycles
  instead of showing frozen values while the inverter is offline.
- Register blocks that have never been read publish no value instead of zeros,
  so energy counters no longer create spikes in the energy dashboard.
- A slot power of 0 % is reported as 0 % instead of 100 %.
- Charge and discharge writes keep the weekday mask configured in the SAJ app
  (an empty mask still falls back to every day).
- Reconfiguring the connection updates the unique id and the default title,
  and refuses an address another entry already uses.
- The connection repair issue is raised per inverter, only after 15 minutes
  without an answer, and removed when the entry unloads.
- English translations were missing, and two Spanish entity names
  (`Potencia de red neta`, `Potencia de batería neta`) were missing.

### Improvements

- Real battery capacity uses the energy storage device class and the number
  of batteries. Time to full/empty is unknown when it does not apply.
- `pymodbus>=3.11.2` is declared as a lower bound, still sharing the version
  bundled with Home Assistant.
- Current Home Assistant APIs: typed config entry, `config_entry` passed to
  the coordinator, `AddConfigEntryEntitiesCallback`, translated update errors,
  config entry selector in the `set_profile` action.
- Tests run on the Home Assistant test harness against 2026.5.0 and 2026.10.4,
  plus a non-blocking job on the latest harness.

Existing entity ids are kept by the entity registry. New installations get
entity ids generated from the English names.

## 1.0.2

- Fix Home Assistant 2026.7.1 startup by removing the hard PyModbus runtime pin.
- Use the PyModbus version bundled by Home Assistant through the core `modbus` integration dependency.
- Keep PyModbus 3.11.2-compatible API usage while validating development tests against Home Assistant 2026.7.1 and PyModbus 3.13.1.
- Document Codex/AI contribution attribution as 99% and owner validation/publishing as 1%.

## 1.0.1

- Clarify that the project code, documentation, review, tests, guides, and maintenance workflow are AI-generated/reviewed, not merely AI-assisted.

## 1.0.0

- Initial public HACS custom repository release.
- Add Home Assistant custom integration for SAJ AS1 over Modbus TCP/IP.
- Add HACS metadata, brand assets, MIT license, disclaimer, safety guide, and multilingual README files.
- Add public documentation, Modbus references, maintainer AI context, and wiki source documentation.
- Add GitHub Actions validation for Python tests, mypy, HACS, and Hassfest.

## Pre-public history

Earlier `3.x` tags were created during first publication setup and CI validation. Public versioning starts at `1.0.0`.
