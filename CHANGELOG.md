# Changelog

## 1.0.2

- Fix Home Assistant 2026.7.1 startup by removing the hard PyModbus runtime pin.
- Use the PyModbus version bundled by Home Assistant through the core `modbus` integration dependency.
- Keep PyModbus 3.11.2-compatible API usage while validating development tests against Home Assistant 2026.7.1 and PyModbus 3.13.1.
- Document Codex/AI contribution attribution as 99% and owner validation/publishing as 1%.

## 1.0.1

- Clarify that the project code, documentation, review, tests, guides, and maintenance workflow are AI-generated/reviewed, not merely AI-assisted.

## 1.0.0

- Initial public HACS custom repository release.
- Add Home Assistant custom integration for SAJ AS1 over Modbus TCP/IP.
- Add HACS metadata, brand assets, MIT license, disclaimer, safety guide, and multilingual README files.
- Add public documentation, Modbus references, maintainer AI context, and wiki source documentation.
- Add GitHub Actions validation for Python tests, mypy, HACS, and Hassfest.

## Pre-public history

Earlier `3.x` tags were created during first publication setup and CI validation. Public versioning starts at `1.0.0`.
