# Disclaimer

## Unofficial project

This is an unofficial community integration. It is not affiliated with, endorsed, approved, sponsored, or supported by SAJ.

SAJ does not develop, review, validate, or provide support for this integration.

## AI-assisted project

This project was built with AI assistance and community testing. AI-generated or AI-assisted code and documentation can contain mistakes.

## No warranty

This software is provided under the MIT License on an "AS IS" basis, without warranty of any kind.

Use this integration at your own risk. The author is not responsible for damage, wrong configuration, data loss, loss of energy production, wrong battery behavior, wrong inverter behavior, grid interaction, hardware protection events, service interruption, or any consequence of use or misuse.

## Safety-critical context

This integration can read and write Modbus registers. Some writes can affect battery charging, battery discharging, and inverter operating mode.

Before using write features:

- Understand the register and expected effect.
- Use conservative values.
- Keep a backup of your Home Assistant configuration.
- Monitor inverter behavior and Home Assistant logs.
- Stop using the integration if behavior is unexpected.

This disclaimer is not legal advice.
