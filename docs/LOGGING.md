# Logging

## Normal logging

The integration should not spam logs during normal operation.

Expected behavior:

- Short failures keep last valid data.
- Repeated bucket failures mark affected entities unavailable.
- Warnings are emitted on threshold crossing and recovery, not every poll.

## Debugging

Filter by:

```text
saj_as1_modbus
```

Avoid sharing logs publicly without redacting:

- IP addresses.
- Serial numbers.
- Home Assistant tokens.
- Full local network details.

## Diagnostics

Home Assistant diagnostics include connection state, failure counters, bucket timing, and circuit breaker state. The integration redacts the configured host.
