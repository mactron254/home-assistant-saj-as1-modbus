# Troubleshooting

## Connection unavailable

Check:

- AIO3 online.
- Home Assistant can reach the AIO3 IP.
- TCP port, usually `502`.
- Modbus device ID, usually `1`.
- No other client is hammering the same Modbus endpoint.

## Entity unavailable

Check logs filtered by:

```text
saj_as1_modbus
```

Bucket failures are tracked in diagnostics. Short failures should keep last valid values; repeated failures mark affected keys unavailable.

## Write failures

Supported writes are limited to:

- `REGISTER_USER_MODE`
- `REGISTER_CHARGE_POWER_PCT`
- `REGISTER_DISCHARGE_POWER_PCT`
- `saj_as1_modbus.set_profile`

Relevant files:

- `custom_components/saj_as1_modbus/coordinator.py`
- `custom_components/saj_as1_modbus/services.yaml`
- `custom_components/saj_as1_modbus/__init__.py`

Do not add new write registers without manual hardware validation.

## HACS icon missing

Confirm this file exists:

```text
custom_components/saj_as1_modbus/brand/icon.png
```

Manual installs may still not show the icon in every Home Assistant view.
