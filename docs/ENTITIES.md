# Entities

Entity names can vary depending on Home Assistant language and entity registry history.

## Power and energy

- Total PV power.
- House/load power.
- Grid import power.
- Grid export power.
- Signed grid power.
- Total PV energy.
- Total battery charge energy.
- Total battery discharge energy.
- Total load energy.
- Total grid import energy.
- Total grid export energy.

## Grid L1

- Grid voltage L1.
- Grid current L1.
- Grid frequency L1.

L2/L3 are not exposed by this integration because the documented AS1 local protocol only provides L1/R values here.

## Battery

- Battery charging power.
- Battery discharging power.
- Signed battery power.
- Battery SOC.
- Battery SOH.
- Battery voltage.
- Battery current.
- Battery temperature.
- Battery cycles.
- Time to full.
- Time to empty.

## Status

- Working mode.
- Error count.
- Radiator temperature.
- Battery count.
- Connection state.

Some diagnostic entities are disabled by default to reduce UI noise.
