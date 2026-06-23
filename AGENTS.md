# Agent Instructions

This repository contains an unofficial Home Assistant custom integration for SAJ AS1 over Modbus TCP/IP.

## Hard rules

- Answer user-facing work in Spanish when working in this repository.
- If JavaScript tooling is ever added, use `pnpm` version 11 or newer.
- Keep Python code, comments, docstrings, identifiers, and commit messages in English.
- Keep public docs in English first, with Spanish, German, and French README summaries.
- Do not claim official SAJ support.
- Do not add direct Modbus RTU/RS485 support unless it is implemented, tested, and documented.
- Do not expose polling interval options in config flow or options flow.
- Do not add undocumented write registers.

## Validation

Before publishing changes, run:

```powershell
.\.venv\Scripts\pytest.exe tests --rootdir=tests
mypy --strict --ignore-missing-imports --explicit-package-bases custom_components\saj_as1_modbus tests
```

Check `docs/AI_CONTEXT.md` before changing Modbus behavior.
