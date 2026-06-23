# Services

## `saj_as1_modbus.set_profile`

Use this service to apply user mode and charge/discharge percentages in one sequence.

```yaml
service: saj_as1_modbus.set_profile
data:
  charge_power_pct: 50
  discharge_power_pct: 50
  user_mode: "Time of Use"
```

## Fields

| Field | Required | Description |
| --- | --- | --- |
| `config_entry_id` | no | Required only when multiple SAJ AS1 entries exist |
| `charge_power_pct` | no | First charge power percentage |
| `discharge_power_pct` | no | First discharge power percentage |
| `user_mode` | no | Target user mode |

At least one profile value must be provided.

## Safety

The service writes Modbus registers. Test manually before automation.
