# Installation

## HACS custom repository

1. Open HACS.
2. Add custom repository:

   ```text
   https://github.com/mactron254/home-assistant-saj-as1-modbus
   ```

3. Select category `Integration`.
4. Install **SAJ AS1 Modbus**.
5. Restart Home Assistant.
6. Add integration from **Settings > Devices & services**.

## Manual install

Copy:

```text
custom_components/saj_as1_modbus/
```

into Home Assistant `custom_components/`, then restart Home Assistant.

Manual installs may not always show brand icons.

## Requirements

- Home Assistant with custom integrations.
- SAJ AS1 reachable over Modbus TCP/IP.
- Port, usually `502`.
- Device ID, usually `1`.
