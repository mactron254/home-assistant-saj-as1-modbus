# Safety Guide

## Scope

This integration is for SAJ AS1 over Modbus TCP/IP only. It is not for direct Modbus RTU/RS485.

## Read operations

Read operations are conservative and grouped to avoid overloading an AIO3 WiFi bridge. Avoid running multiple aggressive Modbus clients against the same device.

## Write operations

Write operations can change inverter behavior. Supported writes are limited to:

- User mode.
- First charge power percentage.
- First discharge power percentage.
- Combined profile service `saj_as1_modbus.set_profile`.

Do not test unknown registers on a production system. Do not automate writes until manual tests are stable.

## Before enabling automations

- Confirm current mode and battery behavior from Home Assistant and the SAJ app.
- Test with low-risk percentages.
- Check logs for Modbus write errors.
- Keep manual control available.
- Disable automations immediately if behavior differs from expected behavior.

## Logs

For debugging, filter Home Assistant logs by:

```text
saj_as1_modbus
```

Avoid publishing logs with IP addresses, serial numbers, tokens, or personal network data.
