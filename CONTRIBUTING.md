# Contributing

This project is a Home Assistant custom integration for SAJ AS1 over Modbus TCP/IP.

## Rules

- Keep runtime files required by Home Assistant inside `custom_components/saj_as1_modbus/`.
- Keep code, comments, internal keys, and technical identifiers in English.
- Keep user-facing documentation available in English and Spanish when behavior changes.
- Do not add configurable polling intervals.
- Do not add undocumented write registers.
- Do not add Modbus RTU/RS485 claims unless tested and documented separately.
- Prefer small changes with tests.

## Validation

Run:

```powershell
.\.venv\Scripts\pytest.exe tests --rootdir=tests
mypy --strict --ignore-missing-imports --explicit-package-bases custom_components\saj_as1_modbus tests
```

Public CI also runs HACS validation and Hassfest.
