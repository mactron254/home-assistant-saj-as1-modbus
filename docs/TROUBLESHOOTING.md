# Troubleshooting

## Cannot connect

- Confirm the AIO3 or Modbus TCP endpoint is online.
- Confirm Home Assistant can reach the IP address.
- Confirm port, usually `502`.
- Confirm device ID, usually `1`.
- Stop other aggressive Modbus clients temporarily.

## Entities unavailable

- Check Home Assistant logs filtered by `saj_as1_modbus`.
- Check WiFi signal and network stability.
- Wait for recovery; the integration keeps last valid values during short failures.
- If failures continue, restart the AIO3 or Home Assistant after checking network state.

## Writes fail

- Confirm the integration entry is loaded.
- Try one value at a time.
- Avoid repeated rapid service calls.
- Check whether the SAJ app or another Modbus client is changing the same mode.

## Brand icon does not show

HACS-compatible installs use `custom_components/saj_as1_modbus/brand/icon.png`. Manual installs may not always show local brand icons in every Home Assistant UI view.
