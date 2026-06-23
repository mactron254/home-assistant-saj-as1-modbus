# Configuration

## Fields

| Field | Description | Default |
| --- | --- | --- |
| Host | Modbus TCP/IP endpoint IP or hostname | none |
| Port | Modbus TCP port | `502` |
| Device ID | Modbus device ID | `1` |

The integration tests the connection before saving.

## Polling

Polling intervals are internal. They are not user configurable.

Current buckets:

| Bucket | Cadence | Purpose |
| --- | --- | --- |
| HIGH | 30 seconds | Live power and SOC |
| MEDIUM | 60 seconds | Mode, errors, BMS, temperature, grid L1 |
| CONFIG | 300 seconds | User mode and configurable limits |
| LOW | 300 seconds | Accumulated energy |

This protects the AIO3 WiFi bridge from unnecessary load.
