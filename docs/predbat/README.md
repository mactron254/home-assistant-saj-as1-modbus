# SAJ AS1 compatibility specification for PredBat

This editable master specification supports a future SAJ AS1 PredBat project.
The integration is unofficial, is not supported by SAJ, and uses Modbus TCP/IP
only. Test every write on real hardware before enabling automatic control.

## Current status

- Home Assistant schedule entities: implemented for release target `v1.1.0`.
- Local unit and strict typing tests: implemented.
- GitHub HACS, Hassfest, CodeQL, and full CI: pending feature PR.
- PredBat Monitor/read-only test: pending on the target Home Assistant instance.
- Five-minute 10% sign test: pending on real hardware.
- Automatic control and release `v1.1.0`: blocked until hardware tests pass.
- PredBat upstream contribution: draft only after local hardware proof.

The copy-ready configuration is
[`apps-saj-as1.yaml`](apps-saj-as1.yaml). Entity IDs may receive a suffix if
an older entity with the same ID exists; confirm them in Home Assistant.

## PredBat reference audit

| Item | Value |
|---|---|
| Repository | `https://github.com/springfall2008/batpred` |
| Documentation | `https://springfall2008.github.io/batpred/` |
| Pinned commit | `18a56d174c44d3689263c773d44020bcb63b5161` |
| Audit date | 2026-07-12 |
| Local working tree | `docs/internal/predbat-upstream/` (Git-ignored) |

The complete upstream working tree was downloaded at the pinned commit. It is
not versioned here because PredBat has its own license. The audit covered all
public Markdown files in upstream `docs/`, root `apps.yaml`, `License.md`,
and relevant implementation in `apps/predbat/config.py` and
`apps/predbat/inverter.py`. Key references:

- `docs/inverter-setup.md`: custom inverter flow and capability flags.
- `docs/apps-yaml.md`: HA entities, signs, schedules, rates, SoC, services.
- `docs/caution.md`: write volume and inverter safety.
- `apps/predbat/inverter.py`: real mode and service behavior.
- `apps/predbat/config.py`: built-in inverter definitions.

Re-audit the upstream diff before moving to a newer commit.

## Architecture

`connection_manager.py` owns serialized Modbus TCP connections.
`coordinator.py` owns conservative polling, AIO3 pacing, caches, grouped reads,
read-modify-write, retries, and write ordering. `modbus_processing.py` owns
time, mask, power, energy, and percentage conversion. Platform files expose HA
entities only.

Existing power, energy, SoC, temperature, mode, and rate entities are reused.
Only four minute-precision `time` entities and two first-slot `switch`
entities were added.

## Existing input mapping

| PredBat key | Home Assistant entity |
|---|---|
| `load_today` | `sensor.garaje_saj_as1_inverter_consumo_casa_diario` |
| `import_today` | `sensor.garaje_saj_as1_inverter_energia_importada_diaria` |
| `export_today` | `sensor.garaje_saj_as1_inverter_energia_exportada_diaria` |
| `pv_today` | `sensor.saj_inversor_r5_energia_hoy` |
| `battery_power` | `sensor.saj_as1_battery_power` |
| `grid_power` | `sensor.saj_as1_grid_power` |
| `load_power` | `sensor.saj_as1_inverter_potencia_casa` |
| `pv_power` | `sensor.saj_as1_inverter_potencia_solar_total` |
| `soc_percent` | `sensor.saj_as1_inverter_nivel_de_bateria_soc` |
| `soc_max` | `sensor.saj_as1_inverter_bateria_capacidad_real` |
| `battery_temperature` | `sensor.saj_as1_inverter_bateria_temperatura` |
| `charge_rate_percent` | `number.saj_as1_first_charge_power_pct` |
| `discharge_rate_percent` | `number.saj_as1_first_discharge_power_pct` |

Do not use the usable-kWh helpers or `sensor.predbat_saj_as1_monitor_0_*` as
inputs. They are helpers/outputs. Combining them with `battery_min_soc: 15`
subtracts the reserve twice.

## New schedule controls

| Entity | Register | Meaning |
|---|---:|---|
| `time.saj_as1_first_charge_start_time` | `0x3606` | Charge start |
| `time.saj_as1_first_charge_end_time` | `0x3607` | Charge end |
| `time.saj_as1_first_discharge_start_time` | `0x361B` | Discharge start |
| `time.saj_as1_first_discharge_end_time` | `0x361C` | Discharge end |
| `switch.saj_as1_first_charge_schedule_enabled` | bit 0, `0x3604` | Enable charge slot |
| `switch.saj_as1_first_discharge_schedule_enabled` | bit 0, `0x3605` | Enable discharge slot |

Times are `HH:MM:00` with minute precision. Configuration reads use blocks
`0x3604-0x3608` and `0x361B-0x361D`. Switch writes read the complete mask,
change bit 0, preserve every other bit, and reject the write if the mask cannot
be read. Equal values do not trigger another write.

## Signs

PredBat expects battery power positive for discharge and negative for charge.
`sensor.saj_as1_battery_power` follows this convention, so start with
`battery_power_invert: false`.

PredBat expects grid power negative for import and positive for export.
`sensor.saj_as1_grid_power` is positive for import, so use
`grid_power_invert: true`.

Confirm both with 10% charge and discharge tests for five minutes. Change only
the corresponding invert flag if the measured sign contradicts this conclusion.

## Modes and `has_fox_inverter_mode`

| SAJ option | Intended use |
|---|---|
| `Autoconsumo` | Normal and every stopped PredBat state |
| `Horario de Uso` | Active PredBat charge/discharge schedule |
| `Reserva` | User-controlled backup; PredBat never selects it |
| `Manual` | Maintenance; PredBat never selects it |

Keep `has_fox_inverter_mode: false`. It is not a generic schedule-control flag.
At the pinned commit PredBat hard-codes `SelfUse` when it is true. SAJ exposes
`Autoconsumo` and requires `Horario de Uso` for active schedules. Enabling
the Fox flag would fail polling or undo TOU. Also omit the real SAJ entity from
`inverter_mode`; the non-Fox path may try `Eco` or `Timed Export`. The four
SAJ service sequences control mode explicitly.

## SoC policy

The physical range remains 15-100%. PredBat reads current SoC and stops action
itself. Use `battery_min_soc: 15`, `has_target_soc: false`, and
`has_reserve_soc: false`. Never expose or access physical SoC configuration
registers `0x3373` or `0x3374`.

## Register policy

| Register/block | Access | Rule |
|---|---|---|
| `0x3371` | R/W | User mode |
| `0x3604-0x3608` | R; selected R/W | Masks, charge time/rate |
| `0x361B-0x361D` | R; selected R/W | Discharge time/rate |
| `0x3373`, `0x3374` | Prohibited | Never read or write |
| Slots 2-7 | Preserved | Slot 1 writes never clear them |

Power percentage writes keep the existing all-week day mask. No undocumented
write register is allowed.

## Fixed configuration

Use 3000 W for `battery_rate_max`, `inverter_limit`,
`inverter_limit_charge`, and `inverter_limit_discharge`. Use
`charge_time_format: "HH:MM:SS"`, `charge_time_entity_is_option: false`,
`can_span_midnight: false`, and `write_and_poll_sleep: 10`. Freeze, pause,
idle time, and balancing remain disabled.

## Transitions

Do not use `repeat: true`. PredBat already calls each service once per state.

### Start charge

1. Turn off discharge.
2. PredBat confirms charge time and percentage via configured entities.
3. Enable charge.
4. Select `Horario de Uso`.

### Stop charge

1. Disable charge.
2. Select `Autoconsumo`.

### Start discharge

1. Turn off charge.
2. PredBat confirms discharge time and percentage via configured entities.
3. Enable discharge.
4. Select `Horario de Uso`.

### Stop discharge

1. Disable discharge.
2. Select `Autoconsumo`.

Charge-to-discharge must finish charge stop first. On failure the slot end time
limits action. Rollback: turn off both first-slot switches, select
`Autoconsumo`, then confirm self-consumption power behavior.

## Validation

1. Install/reload `v1.1.0` while PredBat remains Monitor/read-only.
2. Confirm four times, two switches, two rate numbers, and mode select.
3. Merge `apps-saj-as1.yaml` into the existing application entry.
4. Observe one tariff cycle read-only; there must be no Modbus writes.
5. Run 10% charge and discharge for five minutes; confirm signs.
6. Test Autoconsumo -> charge TOU -> Autoconsumo.
7. Test Autoconsumo -> discharge TOU -> Autoconsumo.
8. Test early target, charge-to-discharge, HA restart with active slot, partial
   Modbus error, and rollback.
9. Only then disable read-only and monitor the first automatic day.

## Troubleshooting

- Switch write fails: fix Modbus; never bypass the missing-mask rejection.
- Other slots change: stop immediately; complete mask preservation failed.
- Time rejected: use valid 24-hour time; seconds store as zero.
- `SelfUse`/`Eco`/`Timed Export` error: keep Fox/GE flags false, omit
  `inverter_mode`, and use SAJ services.
- Battery crosses 15%: disable PredBat, roll back, check `battery_min_soc`.
- Wrong grid sign: change only `grid_power_invert`.
- Wrong battery sign: change only `battery_power_invert`.
- AIO3 instability: retain 10-second write/poll delay; avoid repeated services.

## Future project

1. Start at the pinned commit or re-audit a newer one.
2. Copy `apps-saj-as1.yaml` and adjust only actual entity IDs.
3. Keep this integration as the sole writer of documented SAJ registers.
4. Attach anonymized hardware evidence to a draft PredBat PR.
5. Do not release `v1.1.0` before hardware sign-off.

## Installation-specific data (editable)

| Field | Value |
|---|---|
| Home Assistant version | `TODO` |
| PredBat commit | `18a56d174c44d3689263c773d44020bcb63b5161` |
| Integration | `1.1.0 candidate` |
| SAJ/AIO3 firmware | `TODO` |
| Battery | `1 module / 4.81 kWh observed` |
| Physical SoC | `15-100%` |
| Battery/grid sign | `TODO after 10% test` |
| Charge/discharge result | `TODO` |
| Rollback tested | `TODO` |

## Continuation

See [`CONTINUATION.md`](CONTINUATION.md) for the new-chat state and pending work.
