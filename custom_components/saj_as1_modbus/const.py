"""Constants for the SAJ AS1 Modbus integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "saj_as1_modbus"
MANUFACTURER: Final = "SAJ Electric"
MODEL: Final = "AS1"

CONF_DEVICE_ID: Final = "device_id"
CONF_SCAN_INTERVAL: Final = "scan_interval"  # Legacy key removed during migration.

DEFAULT_DEVICE_ID: Final = 1
DEFAULT_PORT: Final = 502
MODBUS_TIMEOUT: Final = 10

SCAN_INTERVAL_HIGH: Final = 30
SCAN_INTERVAL_MEDIUM: Final = 60
SCAN_INTERVAL_CONFIG: Final = 300
SCAN_INTERVAL_LOW: Final = 300
AIOT_DELAY_MS: Final = 300

# Upper bound for one complete poll cycle. DataUpdateCoordinator does not
# impose a timeout of its own, so a stalled await would otherwise stop polling
# silently until the entry is reloaded. Generous on purpose: a cycle that waits
# for a slow write batch must not be cut short.
POLL_CYCLE_TIMEOUT: Final = 300.0

AIO3_PRE_WRITE_DELAY: Final = 1.0
AIO3_WRITE_SETTLE_DELAY: Final = 5.0
AIO3_RECOVERY_DELAY: Final = 8.0
AIO3_SENSITIVE_RETRIES: Final = 3
AIO3_SENSITIVE_RETRY_DELAY: Final = 1.5
AIO3_WRITE_BATCH_DELAY: Final = 2.0
AIO3_BATCH_INTER_WRITE_DELAY: Final = 1.0
AIO3_WRITE_RETRIES: Final = 2
AIO3_WRITE_RETRY_DELAY: Final = 12.0

MAX_FAILURES_BEFORE_UNAVAILABLE: Final = 5
AIO3_CIRCUIT_BREAKER_FAILURES: Final = 3
AIO3_CIRCUIT_BREAKER_COOLDOWN: Final = 60.0

# Consecutive failed cycles during which the last good values are kept. From
# this failure on, the coordinator raises UpdateFailed and entities become
# unavailable instead of showing frozen readings.
STALE_DATA_MAX_FAILURES: Final = 3

# A repair issue is only raised when the inverter has been unreachable for this
# long, so short WiFi drops of the AIO3 stick do not create noise.
CONNECTION_ISSUE_DELAY: Final = 900.0

BAT_ENERGY_CAPACITY_NOMINAL: Final = 5.12

REGISTER_BAT_POWER: Final = 0x406D
REGISTER_BAT_SOC: Final = 0x406F
REGISTER_POWER_BLOCK_START: Final = 0x4099
REGISTER_POWER_BLOCK_COUNT: Final = 13

REGISTER_WORKING_MODE: Final = 0x4004
REGISTER_ERROR_COUNT: Final = 0x400F
REGISTER_RADIATOR_TEMP: Final = 0x4010
REGISTER_GRID_L1_STATUS_START: Final = 0x4031
REGISTER_GRID_L1_STATUS_COUNT: Final = 3
REGISTER_BMS_START: Final = 0xA000
REGISTER_BMS_COUNT: Final = 18
REGISTER_USER_MODE: Final = 0x3371
REGISTER_CHARGE_POWER_PCT: Final = 0x3608
REGISTER_DISCHARGE_POWER_PCT: Final = 0x361D

# Weekday mask written in the high byte of the slot power registers when the
# current mask is unknown or empty (0x7F = Monday to Sunday).
WEEKDAYS_ALL: Final = 0x7F

LOW_ENERGY_REGISTERS: Final = {
    "total_pv_energy": 0x40C5,
    "total_battery_charge_energy": 0x40CD,
    "total_battery_discharge_energy": 0x40D5,
    "total_load_energy": 0x40E5,
    "total_grid_export_energy": 0x40FD,
    "total_grid_import_energy": 0x410D,
}
LOW_ENERGY_BLOCK_START: Final = min(LOW_ENERGY_REGISTERS.values())
LOW_ENERGY_BLOCK_COUNT: Final = (
    max(LOW_ENERGY_REGISTERS.values()) - LOW_ENERGY_BLOCK_START + 2
)

HIGH_KEYS: Final = (
    "battery_power",
    "battery_power_signed",
    "bat1_soc",
    "grid_import_power",
    "grid_export_power",
    "grid_power_signed",
    "battery_charging_power",
    "battery_discharging_power",
    "total_load_power",
    "total_pv_power",
)

MEDIUM_KEYS: Final = (
    "working_mode",
    "working_mode_name",
    "error_count",
    "radiator_temp",
    "grid_voltage_l1",
    "grid_current_l1",
    "grid_frequency_l1",
    "bat_number",
    "bat1_soh",
    "bat1_voltage",
    "bat1_current",
    "bat1_temp",
    "bat1_cycles",
)

CONFIG_KEYS: Final = (
    "user_mode",
    "first_charge_power_pct",
    "first_discharge_power_pct",
)

LOW_KEYS: Final = tuple(LOW_ENERGY_REGISTERS)

# Working mode register values mapped to enum sensor states.
WORKING_MODES: Final = {
    0: "standby",
    1: "self_use",
    2: "peak_shaving",
    3: "backup",
    4: "off_grid",
}
WORKING_MODE_OPTIONS: Final = list(WORKING_MODES.values())

USER_MODE_SELF_USE: Final = 1
USER_MODE_TIME_OF_USE: Final = 2
USER_MODE_BACKUP: Final = 3
USER_MODE_MANUAL: Final = 4

# User mode register values mapped to select options (translated in the UI).
USER_MODES: Final = {
    USER_MODE_SELF_USE: "self_use",
    USER_MODE_TIME_OF_USE: "time_of_use",
    USER_MODE_BACKUP: "backup",
    USER_MODE_MANUAL: "manual",
}
USER_MODE_OPTIONS: Final = list(USER_MODES.values())

# Spanish option labels used before 2.0.0. The set_profile action still accepts
# them so existing automations keep working.
LEGACY_USER_MODE_OPTIONS: Final = {
    "Autoconsumo": "self_use",
    "Horario de Uso": "time_of_use",
    "Reserva": "backup",
    "Manual": "manual",
}

ISSUE_CONNECTION_UNAVAILABLE: Final = "connection_unavailable"

SERVICE_SET_PROFILE: Final = "set_profile"
ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"
ATTR_CHARGE_POWER_PCT: Final = "charge_power_pct"
ATTR_DISCHARGE_POWER_PCT: Final = "discharge_power_pct"
ATTR_USER_MODE: Final = "user_mode"
