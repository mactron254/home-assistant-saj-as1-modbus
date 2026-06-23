# Adding a Modbus Sensor

This page shows the minimum safe path for adding a new read-only Modbus sensor.

## 1. Confirm protocol data

Find the register in:

- `docs/reference/AS1Main control board and display board communication protocol (1).pdf`
- `docs/reference/host_controller_display_panel_protocol.md`

Record:

- Register address.
- Size in words.
- Data type.
- Scale/magnification.
- Unit.
- Whether it belongs to an existing block.

## 2. Add constants

Edit `custom_components/saj_as1_modbus/const.py`.

For a single new MEDIUM register:

```python
REGISTER_EXAMPLE_VALUE: Final = 0x4011
```

Add the entity key to the right bucket:

```python
MEDIUM_KEYS: Final = (
    ...
    "example_value",
)
```

For LOW accumulated energy, add to `LOW_ENERGY_REGISTERS` instead of adding a new request:

```python
LOW_ENERGY_REGISTERS: Final = {
    ...
    "example_total_energy": 0x4111,
}
```

## 3. Read and convert value

Edit `custom_components/saj_as1_modbus/coordinator.py`.

If the register is in an existing block, use the correct offset:

```python
data["example_value"] = read_voltage(existing_regs, offset)
```

If a new request is unavoidable, add it to the slowest safe bucket:

```python
data["example_value"] = read_voltage(
    await self.connection.read_registers(REGISTER_EXAMPLE_VALUE, 1),
    0,
)
```

Avoid adding new requests to `HIGH` unless the value is genuinely live and needed every 30 seconds.

## 4. Add entity description

Edit `custom_components/saj_as1_modbus/sensor.py`.

Example voltage sensor:

```python
SensorEntityDescription(
    key="example_value",
    translation_key="example_value",
    native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    device_class=SensorDeviceClass.VOLTAGE,
    state_class=SensorStateClass.MEASUREMENT,
    entity_category=EntityCategory.DIAGNOSTIC,
),
```

Use `EntityCategory.DIAGNOSTIC` for values that are useful for troubleshooting but not daily dashboards.

## 5. Add translations

Edit:

- `custom_components/saj_as1_modbus/strings.json`
- `custom_components/saj_as1_modbus/translations/es.json`
- `custom_components/saj_as1_modbus/icons.json`

Add the same `translation_key` in all files.

## 6. Add tests

Update or add tests in:

- `tests/test_register_map.py`
- `tests/test_source_static.py`
- `tests/test_modbus_processing.py` if conversion changes.

Minimum test expectations:

- Register address is exact.
- Key exists in the correct bucket.
- Entity description has unit, device class, state class.
- Translation and icon keys exist.
- Unsupported invented phases/values are not added.

## 7. Validate

Run:

```powershell
.\.venv\Scripts\pytest.exe tests --rootdir=tests
.\.venv\Scripts\mypy.exe --strict --ignore-missing-imports --explicit-package-bases custom_components\saj_as1_modbus tests
```

Then test in Home Assistant with real AIO3 hardware.
