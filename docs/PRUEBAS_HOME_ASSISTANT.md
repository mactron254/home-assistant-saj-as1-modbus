# Pruebas en Home Assistant - SAJ AS1 Modbus

Esta guía describe qué archivos copiar a Home Assistant y qué pruebas realizar
antes de dar por validada la integración `saj_as1_modbus`.

La prueba debe hacerse en Home Assistant OS con el SAJ AS1 real accesible por
Modbus TCP.

## 1. Archivos que Debes Copiar

Crea esta carpeta en Home Assistant:

```text
/config/custom_components/saj_as1_modbus/
```

Copia dentro estos archivos obligatorios desde:

```text
C:\Users\marco\Documents\Integracion AS1\custom_components\saj_as1_modbus
```

Archivos obligatorios:

```text
__init__.py
manifest.json
config_flow.py
const.py
connection_manager.py
coordinator.py
entity.py
exceptions.py
modbus_processing.py
models.py
sensor.py
number.py
select.py
binary_sensor.py
diagnostics.py
strings.json
services.yaml
icons.json
translations/es.json
```

El repositorio también incluye este asset opcional para empaquetado/HACS:

```text
brands/saj_as1_modbus/icon.png
```

No va dentro de `/config/custom_components/saj_as1_modbus/`. En una instalación
manual, Home Assistant puede no mostrar logos locales aunque el asset exista en
el repositorio.

La estructura final en Home Assistant debe quedar así:

```text
/config/custom_components/saj_as1_modbus/
  __init__.py
  manifest.json
  config_flow.py
  const.py
  connection_manager.py
  coordinator.py
  entity.py
  exceptions.py
  modbus_processing.py
  models.py
  sensor.py
  number.py
  select.py
  binary_sensor.py
  diagnostics.py
  strings.json
  services.yaml
  icons.json
  translations/
    es.json
```

Opcionalmente puedes copiar estos archivos solo como documentación:

```text
README.md
docs/DOCUMENTACION_TECNICA.md
docs/PRUEBAS_HOME_ASSISTANT.md
docs/INCIDENCIAS_SOLUCIONES.md
docs/AUDITORIA_PLATINO_PERSONAL.md
docs/AI_CONTEXT.md
docs/REFERENCES.md
quality_scale.yaml
```

No copies estos archivos ni carpetas a Home Assistant:

```text
.venv/
.codex_deps/
.pytest_cache/
tests/
pyproject.toml
*.pdf
Documentacion pymodbus *.md
INFORME_TECNICO_COMPLETO.md
host_controller_display_panel_protocol.md
```

## 2. Prueba de Instalación

1. Haz copia de seguridad de cualquier versión anterior:

   ```text
   /config/custom_components/saj_as1_modbus/
   ```

2. Copia la nueva carpeta `saj_as1_modbus`.
3. Reinicia Home Assistant completo.
4. Ve a **Ajustes > Sistema > Registros**.
5. Filtra los registros por:

   ```text
   saj_as1_modbus
   pymodbus
   custom_components
   ```

Resultado esperado:

- No aparece error de carga de `manifest.json`.
- No aparece error de importación Python.
- Home Assistant instala o carga `pymodbus==3.11.2` sin conflicto de requisitos.
- En Home Assistant 2026.6.x no aparecen avisos de deprecación relacionados con
  `show_advanced_options`, config entry listeners con reload ni servicios
  registrados solo por entrada.
- No aparece un bucle continuo de `received eof` / `Connection lost comm` en los
  registros de PyModbus.
- La integración aparece como **SAJ AS1 Modbus** al añadir integración.

## 3. Prueba de Configuración

1. Ve a **Ajustes > Dispositivos y servicios > Añadir integración**.
2. Busca **SAJ AS1 Modbus**.
3. Introduce:

| Campo | Valor esperado |
| --- | --- |
| Dirección IP | IP del endpoint Modbus TCP del SAJ AS1 |
| Puerto Modbus | Normalmente `502` |
| ID de dispositivo | Normalmente `1` |

Resultado esperado:

- El formulario aparece en español.
- Si los datos son correctos, se crea una entrada `SAJ AS1 (<ip>)`.
- Si pones una IP o puerto incorrecto, aparece `No se puede conectar con el inversor SAJ AS1.`
- Si intentas añadir la misma IP, puerto e ID de dispositivo, Home Assistant aborta por duplicado.

## 4. Pruebas Funcionales de Entidades

En el dispositivo **SAJ AS1 Inverter**, comprueba que se crean aproximadamente:

| Tipo | Cantidad esperada |
| --- | ---: |
| Sensores | 27 |
| Números de configuración | 2 |
| Selector | 1 |
| Sensor binario | 1 |

Comprueba que los nombres aparecen en español, por ejemplo:

- Potencia solar total.
- Potencia casa.
- Potencia importada de red.
- Potencia exportada de red.
- Potencia de red neta.
- Potencia de batería neta.
- Energía importada de red total.
- Energía exportada de red total.
- Estado de carga batería.
- Tiempo hasta carga completa.
- Tiempo hasta descarga completa.
- Modo de usuario.
- Estado de conexión.
- Los iconos de entidades aparecen correctamente desde `icons.json`.

Los sensores de tiempo de batería deben aparecer como entidades normales. Si no
aparecen tras actualizar desde una versión anterior, revisa **Ajustes >
Dispositivos y servicios > Entidades** y confirma que no quedaron ocultos o
deshabilitados manualmente.

Comprueba unidades y clases:

| Tipo de dato | Unidad esperada |
| --- | --- |
| Potencias | `W` |
| Energías | `kWh` |
| Batería | `%` |
| Temperaturas | `°C` |
| Tiempo estimado | `h` |

Tiempos mínimos antes de validar valores:

- Espera al menos 2 minutos para lecturas HIGH y MEDIUM.
- Espera al menos 6 minutos para lecturas CONFIG, LOW y energías acumuladas.

Las energías acumuladas que deben venir de registros acumulados, no de potencia
instantánea, son:

- Energía casa total.
- Energía importada de red total.
- Energía exportada de red total.

## 5. Pruebas de Escritura

Haz estas pruebas solo si es seguro cambiar temporalmente los parámetros del
inversor. Anota siempre el valor original antes de modificarlo.

1. Cambia **Potencia de carga primera franja** a un valor seguro, por ejemplo `50`.
2. Comprueba que Home Assistant conserva el valor y no muestra error.
3. Cambia **Potencia de descarga primera franja** a un valor seguro.
4. Cambia **Modo de usuario** entre opciones conocidas:
   - Autoconsumo.
   - Horario de Uso.
   - Reserva.
   - Manual.
5. Verifica en la app o pantalla del SAJ si el cambio se refleja.
6. Restaura los valores originales.

Resultado esperado:

- No aparece error de escritura.
- La entidad actualiza el valor.
- Para carga y descarga, la integración escribe el byte alto `0x7F`; por ejemplo:

  ```text
  50 % -> 0x7F32
  ```

## 6. Pruebas de Fallo y Recuperación

1. Con la integración funcionando, desconecta temporalmente la red Modbus o
   bloquea el endpoint.
2. Espera varios ciclos de actualización.
3. Comprueba:
   - Algunas entidades pasan a no disponible.
   - El sensor **Estado de conexión** pasa a desconectado.
   - Aparece una reparación de conexión en Home Assistant.
4. Restaura la conexión.
5. Espera uno o dos ciclos.
6. Comprueba:
   - Las entidades vuelven a tener valor.
   - La reparación desaparece.
   - Los acumulados no se han puesto a cero.

## 7. Diagnóstico y Evidencias

Antes de dar la prueba por validada, guarda:

- Captura de la página del dispositivo con entidades.
- Captura del formulario en español.
- Captura de registros sin errores.
- Descarga de diagnóstico desde la entrada de integración.
- Valores reales de:
  - Potencia solar total.
  - Potencia casa.
  - Potencia importada de red.
  - Potencia exportada de red.
  - Potencia de red neta.
  - Potencia de batería neta.
  - Estado de carga batería.
  - Energía casa total.
  - Energía importada de red total.
  - Energía exportada de red total.
  - Estado de conexión.
- Resultado de una escritura pequeña de prueba, si decides probar escrituras.

El diagnóstico debe ocultar la dirección IP y mostrar datos útiles como puerto,
ID de dispositivo, estado de conexión, último error, claves no disponibles y
contadores de fallos HIGH, MEDIUM y LOW. También debe mostrar duración de la
última actualización, lecturas correctas por grupo y segundos desde el último
éxito por grupo.
Si aparece algún fallo aislado en `0x3371`, revisa que el grupo CONFIG se
recupere y no arrastre a los sensores HIGH/MEDIUM.

## 8. Criterios de Aceptación

La prueba se considera correcta si:

- Home Assistant carga la integración sin errores.
- El formulario y las entidades aparecen en español.
- La entrada se crea solo cuando el AS1 responde por Modbus TCP.
- Las entidades principales publican valores coherentes.
- Las energías acumuladas no se resetean a cero durante fallos de comunicación.
- Las escrituras seguras funcionan y se pueden restaurar.
- La integración genera reparación al caer la conexión y la limpia al recuperar.
- El diagnóstico no expone datos sensibles.

## 9. Supuestos de Prueba

- Home Assistant está configurado en español.
- El SAJ AS1 responde por Modbus TCP.
- El puerto habitual es `502`.
- El `device_id` habitual es `1`.
- La integracion es comunitaria no oficial, publicada como HACS custom repository.
- No se aplica offset `-1`; se usan las direcciones hexadecimales del protocolo.
