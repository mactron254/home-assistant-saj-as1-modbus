# References

## Home Assistant

- Integration manifest: https://developers.home-assistant.io/docs/creating_integration_manifest/
- Integration quality scale rules: https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/
- Diagnostics platform: https://developers.home-assistant.io/docs/core/platform/diagnostics/

## HACS

- Publishing general requirements: https://hacs.xyz/docs/publish/start/
- Integration requirements: https://hacs.xyz/docs/publish/integration/
- GitHub Action validation: https://hacs.xyz/docs/publish/action/

## Modbus and dependencies

- PyModbus: https://pymodbus.readthedocs.io/
- Local pinned runtime dependency: `pymodbus==3.11.2`
- Local AS1 protocol reference: `docs/reference/AS1Main control board and display board communication protocol (1).pdf`
- Local protocol markdown extraction: `docs/reference/host_controller_display_panel_protocol.md`
- Local PyModbus documentation snapshots:
  - `docs/reference/Documentacion pymodbus 3.11.2.md`
  - `docs/reference/Documentacion pymodbus 3.13.0.md`

Only use these files for implementation reference. If a copied vendor/manual document has distribution limits, replace it with a public link or a short citation before broader redistribution.

## Community references

- SAJ H2 Modbus integration reference: https://github.com/stanus74/home-assistant-saj-h2-modbus
- evcc Home Assistant template documentation: https://docs.evcc.io/
- EMHASS project: https://github.com/davidusb-geek/emhass
