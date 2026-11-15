# Services

## `saj_as1_modbus.set_profile`

Use this service to apply user mode and charge/discharge percentages in one sequence.

```yaml
action: saj_as1_modbus.set_profile
data:
  charge_power_pct: 50
  discharge_power_pct: 50
  user_mode: "time_of_use"
```

## Fields

| Field | Required | Description |
| --- | --- | --- |
| `config_entry_id` | no | Required only when multiple SAJ AS1 entries exist |
| `charge_power_pct` | no | First charge power percentage (1-100) |
| `discharge_power_pct` | no | First discharge power percentage (1-100) |
| `user_mode` | no | `self_use`, `time_of_use`, `backup` or `manual` |

At least one profile value must be provided.

The Spanish labels used before 2.0.0 (`Autoconsumo`, `Horario de Uso`,
`Reserva`, `Manual`) are still accepted and logged once as deprecated.

Charge and discharge writes keep the weekday mask (high byte) last read from
the register, so days set in the SAJ app are preserved. A slot without any day
is written for every day of the week.

## Safety

The service writes Modbus registers. Test manually before automation.
