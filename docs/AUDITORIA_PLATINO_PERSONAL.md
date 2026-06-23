# Auditoria de calidad - SAJ AS1 Modbus

## Resultado

La integracion se audita contra la escala de calidad de Home Assistant con
alcance de integracion personalizada publica. El objetivo es experiencia y
estabilidad de nivel alto para HACS custom repository. No es una integracion
oficial de Home Assistant Core ni un producto soportado por SAJ.

El estado estructurado esta en `quality_scale.yaml`.

## Compatibilidad Home Assistant 2026.6

- Se mantiene `pymodbus==3.11.2` hasta confirmar la dependencia exacta que trae
  Home Assistant 2026.6.x en la instalacion real.
- La deprecacion de Home Assistant 2026.6 sobre mezclar listeners de config
  entry con metodos de reload no afecta al codigo actual: no se registra
  `entry.async_on_unload(...)` para reconfiguracion.
- La deprecacion de `show_advanced_options` no afecta: el config flow no usa
  modo avanzado ni oculta parametros.
- Los cambios frontend 2026.6 no afectan: la integracion no define custom cards
  ni componentes frontend propios.

## Reglas cubiertas

- Configuracion por UI con prueba de conexion previa.
- Entrada unica por `host:port:device_id`.
- `ConfigEntry.runtime_data`.
- `ConfigEntryNotReady` en setup si la primera lectura no puede completarse.
- Descarga/unload de plataformas y cierre Modbus.
- Entidades con `unique_id`, `has_entity_name`, device info y traducciones.
- Categorias, device classes, state classes y entidades ruidosas deshabilitadas.
- Diagnostico no sensible y repair issue cuando la conexion cae.
- Logs una vez al caer y una vez al recuperar.
- Servicio `saj_as1_modbus.set_profile` registrado en `async_setup`.
- Excepciones de servicio traducibles.
- Iconos centralizados en `icons.json`.
- Polling interno fijo HIGH/MEDIUM/LOW, sin `scan_interval` de usuario.

## Exenciones

- Brands: cubierto mediante `brands/saj_as1_modbus/icon.png`.
- Codeowner publico: cubierto mediante `@mactron254`.
- Reauth: Modbus TCP local no usa credenciales.
- Discovery y discovery update: el AIO3 se configura por IP/puerto.
- Dynamic/stale devices: una entrada representa un unico inversor.
- `inject-websession`: PyModbus TCP no usa aiohttp.

## Pendiente para considerar "platino cerrado"

- Ejecutar una suite con `homeassistant` test harness real, no solo tests
  estaticos/locales.
- Alcanzar `pytest --cov` >95% sobre los modulos de la integracion.
- Ejecutar `mypy --strict` con dependencias/stubs reales de Home Assistant.
- Validar en Home Assistant 2026.6.x real:
  - Arranque sin errores.
  - Formulario en espanol.
  - Lecturas HIGH/MEDIUM/LOW.
  - Diagnostico descargable.
  - Reparacion al desconectar.
  - Servicio `set_profile` con escritura confirmada.

## Criterio operativo

Si en HA real no hay errores de carga, no hay bucles Modbus, los acumulados no se
reinician y el servicio de perfil confirma escrituras sin saturar el AIO3, la
integracion se considera lista para publicacion inicial como repositorio HACS
custom.
