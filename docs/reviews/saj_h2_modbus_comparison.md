# Comparativa tecnica: stanus74/home-assistant-saj-h2-modbus vs SAJ AS1 Modbus

Fecha: 2026-06-11

Fuente revisada:

- Repositorio publico: https://github.com/stanus74/home-assistant-saj-h2-modbus
- Copia local temporal revisada: `%TEMP%\saj_h2_modbus_review`

## Resumen ejecutivo

La integracion SAJ H2 de `stanus74` es una integracion HACS madura, con mucha
superficie funcional y una arquitectura orientada a exponer casi todo el mapa
Modbus H2. Es util como referencia de patrones, pero no conviene copiarla de
forma directa para AS1 con AIO3 por WiFi.

Para AS1, el objetivo correcto ahora sigue siendo estabilidad: menos llamadas,
cadencias internas conservadoras, escrituras serializadas, diagnostico claro y
entidades estrictamente utiles. La H2 usa caminos rapidos de 10 s y 1 s via MQTT
que pueden tener sentido en H2, pero no son una buena base inicial para un AIO3
WiFi sensible.

## Lo que tiene H2

- Estructura estandar de custom integration:
  `custom_components/saj_h2_modbus/`.
- Soporte HACS con `hacs.json`.
- Config Flow y Options Flow amplios.
- Mas de 390 registros expuestos.
- Lecturas por grupos Modbus y decodificacion mediante mapas.
- `DataUpdateCoordinator` centralizado en `hub.py`.
- Gestion de conexion con cache, reconexion coordinada y circuit breaker.
- Lecturas rapidas:
  - coordinator normal configurable, minimo 60 s.
  - fast polling 10 s.
  - ultra-fast 1 s via MQTT.
- Escrituras avanzadas para modos, carga, descarga, limites, export limit y
  passive mode.
- Cola de comandos para escrituras.
- Bloqueos separados para lectura, escritura y read-modify-write.
- Sensores fast sin `state_class` para reducir impacto en recorder.
- Publicacion MQTT opcional.
- Custom Lovelace card en `www/`.

## Diferencias importantes frente a AS1

| Area | H2 | AS1 actual | Decision recomendada |
| --- | --- | --- | --- |
| Layout | `custom_components/saj_h2_modbus` | ya movido a `custom_components/saj_as1_modbus` | Mantener |
| Datos runtime | `hass.data` | `ConfigEntry.runtime_data` | Mantener AS1 |
| PyModbus unit | unidad fija `1` en utilidades | `device_id` configurable | Mantener AS1 |
| Polling usuario | intervalo configurable | intervalos internos | Mantener AS1 |
| Fast polling | 10 s y 1 s MQTT | no implementado | No copiar ahora |
| MQTT | dependencia `mqtt` | sin MQTT | No copiar ahora |
| Decodificacion | tablas extensas | mapas pequenos y helpers puros | Mantener simple hasta crecer |
| Escrituras | cola amplia de comandos | lote seguro para perfil basico | Ampliar solo si hay mas writes |
| RMW locks | si, para registros compartidos | no generalizado | Anadir solo si AS1 usa bitmasks/slots |
| Diagnostico | orientado a datos H2 | duracion, exitos y fallos por grupo | Mantener y mejorar AS1 |

## Ideas aprovechables para AS1

1. Mantener layout estandar

La estructura `custom_components/<domain>/` es correcta para instalacion,
revision y empaquetado. Ya se ha aplicado en AS1.

2. Circuit breaker si los logs vuelven a degradarse

H2 incorpora un circuit breaker y coordinacion global de reconexion. AS1 ya
tiene cierres, reintentos y bloqueo de I/O. No hace falta introducir otro nivel
todavia, pero es una mejora candidata si aparecen rachas largas de EOF,
`Not connected` o reconexiones simultaneas.

3. Cola de comandos si crecen las escrituras

AS1 ya serializa y agrupa `charge_power_pct`, `discharge_power_pct` y
`user_mode`. Si luego se anaden franjas horarias, limite de exportacion o modo
pasivo, convendra evolucionar a una cola formal parecida a `charge_control.py`.

4. Locks read-modify-write para registros compartidos

H2 protege registros donde varios campos comparten una palabra. En AS1 ahora se
inyecta `0x7F` y el porcentaje en registros concretos. Si se empiezan a editar
dias, horas o mascaras parciales, sera obligatorio anadir RMW locks por
registro.

5. Cache TTL para datos estaticos

H2 cachea informacion estatica del inversor durante 1 hora. Para AS1 podria
aplicarse a datos de version, serial, modelo o configuracion poco cambiante si
se exponen en el futuro.

6. Sensores rapidos sin recorder

H2 crea sensores fast sin `state_class`. Para AS1 solo tendria sentido si se
necesita visualizacion casi en vivo y se confirma que AIO3 aguanta. No debe ser
parte de la fase actual.

## Ideas a evitar ahora

1. `scan_interval` configurable

Aunque H2 lo expone, para AS1 es mejor mantener cadencias internas. El AIO3 WiFi
no debe quedar a merced de una configuracion agresiva desde UI.

2. Ultra-fast 1 s

El polling de 1 s por MQTT no encaja con el objetivo actual de estabilidad. Es
una fuente probable de ruido, saturacion y datos innecesarios en HA.

3. Dependencia MQTT temprana

MQTT complica instalacion, permisos y soporte. No aporta valor para las mejoras
actuales de rendimiento y estabilidad.

4. Copiar el mapa masivo de entidades

Exponer demasiadas entidades reduce experiencia de uso. AS1 debe priorizar
entidades utiles, diagnostico y deshabilitar por defecto lo secundario.

5. Hardcodear unidad Modbus

H2 usa unidad `1` en varias utilidades. AS1 debe conservar `device_id`
configurable y usar `device_id=` en PyModbus.

## Plan de mejoras AS1 derivado de la comparativa

### Prioridad 1: estabilidad y experiencia

- Mantener grupos HIGH/MEDIUM/CONFIG/LOW.
- No bajar HIGH por debajo de 30 s mientras se use AIO3 WiFi.
- Mantener CONFIG en 300 s para `0x3371`, `0x3608`, `0x361D`.
- Revisar logs reales tras cada cambio y medir duracion por grupo.
- Mejorar diagnostico con ultimo error por grupo y numero de registros leidos.
- Documentar claramente que no se debe usar otro cliente Modbus agresivo a la
  vez.

### Prioridad 2: arquitectura

- Evaluar circuit breaker ligero si hay fallos repetidos consecutivos.
- Extraer politica de grupos de lectura a una tabla declarativa solo si crece el
  mapa de registros.
- Mantener helpers puros de `modbus_processing.py` para tests rapidos.
- Mantener `runtime_data`, no volver a `hass.data`.

### Prioridad 3: escrituras futuras

- Si se anaden mas registros de control, crear una cola formal de comandos.
- Anadir read-modify-write locks antes de editar campos parciales dentro de una
  misma palabra.
- Evitar escrituras paralelas desde entidades independientes; preferir servicios
  atomicos tipo `set_profile`.

### Prioridad 4: integraciones externas futuras

- EMHASS y EVCC deben ir despues de cerrar estabilidad.
- Para EMHASS, priorizar sensores netos y servicio atomico de perfil.
- Para EVCC, priorizar nombres/semantica clara de potencia PV, carga casa, red
  neta y bateria neta.

## Conclusion

La H2 confirma que las decisiones actuales de AS1 son razonables para AIO3 WiFi:
lecturas agrupadas pero conservadoras, escrituras serializadas, sin intervalos
configurables por usuario y sin MQTT rapido por ahora.

La mejora mas valiosa a corto plazo no es anadir mas funciones, sino cerrar un
paquete estable: estructura correcta, tests actualizados, diagnostico mas util y
documentacion operativa alineada con la carpeta real de Home Assistant.
