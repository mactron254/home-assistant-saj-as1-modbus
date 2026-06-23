# SAJ AS1 Modbus for Home Assistant

> **Unofficial community integration. Not affiliated with, endorsed, approved, or supported by SAJ.**
>
> This project was built with AI assistance and community testing. Use it at your own risk. The author provides no warranty and is not responsible for damage, wrong configuration, data loss, inverter behavior, battery behavior, grid interaction, or any other consequence of use or misuse.

[Español](README.es.md) | [Deutsch](README.de.md) | [Français](README.fr.md)

SAJ AS1 Modbus is a Home Assistant custom integration for reading and controlling a SAJ AS1 system over **Modbus TCP/IP only**.

It is designed for local polling through an AIO3/Modbus TCP endpoint. It does **not** support direct Modbus RTU/RS485 connections.

## Status

- Initial public target: HACS custom repository.
- Repository: `mactron254/home-assistant-saj-as1-modbus`.
- Integration domain: `saj_as1_modbus`.
- Current release target: `v3.1.0`.

## Features

- UI config flow and reconfigure flow.
- Local Modbus TCP polling with conservative timing for AIO3 WiFi.
- Power, energy, battery, grid L1, status, diagnostics, and connection entities.
- Battery charge/discharge time sensors shown as normal sensors.
- Controlled write support for user mode and first charge/discharge power percentages.
- One automation service: `saj_as1_modbus.set_profile`.
- Diagnostics with sensitive IP redaction.
- Repair issue when Modbus communication remains unavailable.
- HACS-compatible brand icon in `custom_components/saj_as1_modbus/brand/icon.png`.

## Requirements

- Home Assistant with custom integrations enabled.
- SAJ AS1 reachable through a Modbus TCP/IP endpoint, usually port `502`.
- Modbus device ID, usually `1`.
- Only one aggressive Modbus client should poll the same AIO3 at a time.

## Installation With HACS Custom Repository

1. Open HACS in Home Assistant.
2. Open custom repositories.
3. Add:

   ```text
   https://github.com/mactron254/home-assistant-saj-as1-modbus
   ```

4. Select category `Integration`.
5. Install **SAJ AS1 Modbus**.
6. Restart Home Assistant.
7. Go to **Settings > Devices & services > Add integration**.
8. Search for **SAJ AS1 Modbus**.

## Manual Installation

1. Copy this folder into Home Assistant:

   ```text
   custom_components/saj_as1_modbus/
   ```

2. Restart Home Assistant.
3. Add the integration from the UI.

Manual installs may not always show brand icons in every Home Assistant view. HACS-compatible installs handle this better.

## Configuration

| Field | Description | Typical value |
| --- | --- | --- |
| Host | IP or hostname of the Modbus TCP endpoint | AIO3 IP address |
| Port | TCP port used by Modbus | `502` |
| Device ID | Logical Modbus device ID | `1` |

Polling cadence is internal and intentionally not exposed as a user option.

## Main Entities

- Solar power.
- House/load power.
- Grid import/export power.
- Signed grid power.
- Grid voltage/current/frequency L1.
- Battery charge/discharge power.
- Signed battery power.
- Battery SOC, SOH, voltage, current, temperature, cycles.
- Time to battery full and empty.
- Accumulated solar, battery, house, and grid energy.
- Working mode, error count, connection state, and diagnostics.

Some noisy or low-use diagnostic entities are disabled by default.

## Automation Service

Use one service call for profile changes:

```yaml
service: saj_as1_modbus.set_profile
data:
  charge_power_pct: 50
  discharge_power_pct: 50
  user_mode: "Time of Use"
```

The integration writes charge/discharge power first and user mode last.

## evcc Notes

Use Home Assistant entities with evcc `template: homeassistant`.

Recommended grid mapping:

```yaml
power: sensor.saj_as1_modbus_grid_power_signed
voltageL1: sensor.saj_as1_modbus_grid_voltage_l1
currentL1: sensor.saj_as1_modbus_grid_current_l1
```

Do not configure L2/L3 from this integration. The documented local AS1 protocol exposes only L1/R values for these grid measurements.

## Documentation

- [Installation](docs/INSTALLATION.md)
- [Configuration](docs/CONFIGURATION.md)
- [Entities](docs/ENTITIES.md)
- [Services](docs/SERVICES.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Logging](docs/LOGGING.md)
- [Safety](SAFETY.md)
- [Disclaimer](DISCLAIMER.md)
- [References](docs/REFERENCES.md)
- [AI context for future maintainers](docs/AI_CONTEXT.md)

## Development

```powershell
.\.venv\Scripts\pytest.exe tests --rootdir=tests
mypy --strict --ignore-missing-imports --explicit-package-bases custom_components\saj_as1_modbus tests
```

Public CI runs Python tests, HACS validation, and Hassfest.

If JavaScript tooling is ever added, use `pnpm` version 11 or newer.

## License

MIT. See [LICENSE](LICENSE).
