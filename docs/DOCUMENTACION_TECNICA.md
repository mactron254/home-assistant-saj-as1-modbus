# Documentación técnica - SAJ AS1 Modbus

## Objetivo

Esta integración permite leer y escribir registros del inversor SAJ AS1 mediante
Modbus TCP desde Home Assistant. Esta optimizada para estabilidad, claridad de
mantenimiento y publicacion como integracion comunitaria no oficial.

## Arquitectura

La integración vive en `custom_components/saj_as1_modbus/` y se divide en capas:

| Capa | Archivo | Responsabilidad |
| --- | --- | --- |
| Entrada | `__init__.py` | Crear coordinador, guardar `runtime_data`, cargar plataformas y migrar entradas |
| Configuración | `config_flow.py` | Validar IP, puerto e ID de dispositivo antes de crear la entrada |
| Modbus | `connection_manager.py` | Gestionar cliente PyModbus, reconexión, lock de I/O y `device_id` |
| Coordinación | `coordinator.py` | Agrupar lecturas por frecuencia, caché y disponibilidad |
| Procesamiento | `modbus_processing.py` | Convertir registros crudos a valores reales |
| Entidades | `sensor.py`, `number.py`, `select.py`, `binary_sensor.py` | Exponer valores en Home Assistant |
| Diagnóstico | `diagnostics.py` | Generar diagnóstico no sensible |
| Servicios | `services.yaml`, `__init__.py` | Registrar `saj_as1_modbus.set_profile` para automatizaciones |
| Iconos | `icons.json` | Definir iconos traducibles por `translation_key` |

## PyModbus

La integración usa `pymodbus==3.11.2` porque Home Assistant 2026.5.4 ya fija
esa versión. Mantener el mismo pin evita conflictos de resolución de
dependencias al cargar integraciones personalizadas.

Para Home Assistant 2026.6.x se mantiene el mismo pin hasta comprobar la versión
real incluida por la instalación. Si Home Assistant actualiza PyModbus, el cambio
de dependencia debe hacerse en una tarea separada y con prueba real de carga.

Reglas aplicadas:

- Todas las llamadas usan `device_id`.
- No se usa `slave=`.
- `client.close()` se llama sin `await`.
- La autoreconexión interna de PyModbus está desactivada con
  `reconnect_delay=0`; la integración controla cierres y reintentos.
- Lecturas y escrituras pasan por `ModbusConnectionManager`.
- Un único lock de I/O evita tramas Modbus concurrentes.

## Direccionamiento

No se aplica offset `-1` dentro de esta integración. Las direcciones usadas son
las direcciones del protocolo SAJ AS1.

El offset mencionado en pruebas anteriores corresponde a configuraciones YAML de
Home Assistant Modbus, no a las llamadas directas de PyModbus en esta
integración.

## Frecuencias

### HIGH - 30 segundos

Lectura de valores de alta variación:

- `0x406D`: potencia de batería.
- `0x406F`: SOC.
- `0x4099-0x40A5`: bloque de potencias.

### MEDIUM - 60 segundos

Lectura de estado y configuración:

- `0x4004`: modo de funcionamiento.
- `0x400F`: contador de errores.
- `0x4010`: temperatura del disipador.
- `0xA000-0xA011`: bloque BMS.

### CONFIG - 300 segundos

Lectura de configuración de usuario y límites:

- `0x3371`: modo de usuario.
- `0x3608`: porcentaje de carga.
- `0x361D`: porcentaje de descarga.

Estos registros se tratan como sensibles para el AIO3 por WiFi. Se leen más
despacio que MEDIUM para reducir errores puntuales como excepciones Modbus en
`0x3371`. Las escrituras desde Home Assistant actualizan la caché de inmediato,
así que la UI no depende de esperar al siguiente ciclo CONFIG.

### LOW - 300 segundos

Lectura de contadores acumulados:

- `0x40C5`: energía solar total.
- `0x40CD`: energía total cargada en batería.
- `0x40D5`: energía total descargada de batería.
- `0x40E5`: energía casa total.
- `0x40FD`: energía exportada a red total.
- `0x410D`: energía importada de red total.

Estas energías se leen en una única solicitud contigua desde `0x40C5` con 74
registros. Así se cubre el rango `0x40C5-0x410E` y se evita hacer seis lecturas
separadas para contadores que cambian despacio.

## Escrituras

### Modo de usuario

Registro `0x3371`.

Valores:

| Valor | Modo |
| --- | --- |
| `1` | Autoconsumo |
| `2` | Horario de uso |
| `3` | Reserva |
| `4` | Manual |

### Potencia de carga y descarga

Registros:

- `0x3608`: primera franja de carga.
- `0x361D`: primera franja de descarga.

Formato:

- Byte alto: días de la semana.
- Byte bajo: porcentaje.

La integración fuerza el byte alto a `0x7F`, que activa lunes a domingo.

### Servicio de perfil

El servicio `saj_as1_modbus.set_profile` permite aplicar carga, descarga y modo
en una sola llamada de automatización. Se registra en `async_setup`, no en
`async_setup_entry`, para que Home Assistant pueda validar acciones aunque una
entrada concreta no esté cargada.

El orden de escritura replica el comportamiento más estable observado en
Elekeeper:

```text
0x3608 -> 0x361D -> 0x3371
```

Los fallos del servicio usan excepciones traducibles.

## Disponibilidad

Cada grupo de lectura tiene contador de fallos:

- HIGH.
- MEDIUM.
- CONFIG.
- LOW.

Si un grupo falla menos de `MAX_FAILURES_BEFORE_UNAVAILABLE`, se conservan los
últimos valores válidos. Si supera el umbral, las entidades del grupo pasan a no
disponibles. Esto evita publicar ceros falsos en contadores o potencias.

El coordinador también guarda duración de la última actualización, lecturas
correctas por grupo y último éxito por grupo. En diagnóstico se expone como edad
en segundos para poder distinguir entre fallo real, lentitud del stick Modbus y
un grupo que simplemente todavía no tocaba refrescar.

El diagnóstico también expone por grupo:

- Duración de la última lectura.
- Último error conocido.
- Número de registros esperados.
- Tamaño de caché.
- Claves no disponibles.

Tras varios fallos globales consecutivos, el coordinador abre un circuit breaker
breve. Durante ese cooldown no fuerza más I/O Modbus y reutiliza los últimos
datos válidos si existen. Esto reduce presión sobre el AIO3 cuando el bridge WiFi
queda en mal estado.

## Migración

Las versiones anteriores podían tener `scan_interval` en `data` u `options`.
La migración elimina esa clave porque el intervalo ahora es interno.

La integración mantiene `unique_id` por entidad basado en:

```text
entry_id + clave de entidad
```

Esto evita recrear entidades existentes en Home Assistant.

## Traducciones

Los textos visibles están en español en:

- `strings.json`.
- `translations/es.json`.

Las entidades usan `translation_key`, por lo que Home Assistant toma el nombre
traducido desde los JSON.

Los iconos de contexto están en `icons.json`; no se definen como `icon=` en las
descripciones Python.

## Compatibilidad Home Assistant 2026.6

- No se usa `show_advanced_options`.
- No se registran listeners de config entry junto con métodos de reload.
- No hay frontend propio ni custom cards afectados por cambios de componentes.
- La reconfiguración usa el flujo de UI existente y no expone `scan_interval`.

## Reparaciones

Cuando la conexión queda no disponible, el coordinador crea una incidencia de
reparación con clave:

```text
connection_unavailable
```

Cuando la conexión se recupera, la incidencia se elimina.

## Validaciones recomendadas en Home Assistant

1. Reiniciar Home Assistant tras copiar la integración.
2. Crear la integración desde la UI.
3. Confirmar que los nombres aparecen en español.
4. Confirmar que las energías acumuladas no aparecen como `unknown` tras la
   primera lectura LOW.
5. Cambiar modo de usuario desde el `select`.
6. Cambiar potencia de carga y descarga desde las entidades `number`.
7. Revisar logs si aparece una reparación de conexión.

La guía operativa completa de copia, pruebas manuales, fallo/recuperación y
evidencias está en `docs/PRUEBAS_HOME_ASSISTANT.md`.
El historial de errores reales y correcciones aplicadas está en
`docs/INCIDENCIAS_SOLUCIONES.md`.
La memoria publica para futuras sesiones de IA esta en
`docs/AI_CONTEXT.md`.
La auditoria de calidad esta en `docs/AUDITORIA_PLATINO_PERSONAL.md` y
`quality_scale.yaml`.

## Regla práctica de mantenimiento

Si una lectura funciona desde el protocolo SAJ AS1, debe quedar documentada en:

1. `const.py`, si es un registro usado por el código.
2. `coordinator.py`, si participa en una lectura.
3. `README.md` o este documento, si afecta a una entidad visible.
4. `tests/`, si es una conversión o dirección crítica.
