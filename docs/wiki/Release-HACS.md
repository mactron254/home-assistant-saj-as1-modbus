# Release and HACS

## Versioning

Public versioning starts at `1.0.0`.

When releasing:

1. Update `custom_components/saj_as1_modbus/manifest.json`.
2. Update `custom_components/saj_as1_modbus/const.py` `INTEGRATION_VERSION`.
3. Update `CHANGELOG.md`.
4. Update tests expecting the manifest version.
5. Run local validation.
6. Commit, push, tag, and create a GitHub release.

## Required local validation

```powershell
.\.venv\Scripts\pytest.exe tests --rootdir=tests
.\.venv\Scripts\mypy.exe --strict --ignore-missing-imports --explicit-package-bases custom_components\saj_as1_modbus tests
```

## Required GitHub checks

Workflow: `.github/workflows/validate.yml`

Jobs:

- Python tests.
- mypy.
- HACS validation.
- Hassfest.

## HACS custom repository URL

```text
https://github.com/mactron254/home-assistant-saj-as1-modbus
```

Category:

```text
Integration
```

## Brand asset

HACS expects:

```text
custom_components/saj_as1_modbus/brand/icon.png
```

The legacy local copy also remains at:

```text
brands/saj_as1_modbus/icon.png
```
