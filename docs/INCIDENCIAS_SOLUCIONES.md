# Incidencias y soluciones - SAJ AS1 Modbus

Este documento registra cada problema encontrado en pruebas reales de Home
Assistant y la solución aplicada. Sirve como memoria técnica para futuras
sesiones.

## 2026-06-03 - Conflicto de PyModbus al abrir el flujo de configuración

### Síntoma

Home Assistant no puede abrir el flujo de configuración de la integración y
registra errores similares a:

```text
Unable to install package pymodbus==3.13.0
Because you require pymodbus==3.13.0 and pymodbus==3.11.2,
we can conclude that your requirements are unsatisfiable.
```

También puede aparecer:

```text
homeassistant.requirements.RequirementsNotFound:
Requirements for saj_as1_modbus not found: ['pymodbus==3.13.0'].
```

### Causa

Home Assistant 2026.5.4 ya fija `pymodbus==3.11.2`. La integración personalizada
pedía `pymodbus==3.13.0` en `manifest.json`, y el resolver de dependencias de
Home Assistant no puede instalar dos versiones incompatibles del mismo paquete.

### Solución Aplicada

- Cambiar `manifest.json` de `pymodbus==3.13.0` a `pymodbus==3.11.2`.
- Subir la versión de la integración a `3.0.1`.
- Mantener el uso de `device_id=` y `client.close()` sin `await`, porque la
  documentación local de PyModbus 3.11.2 confirma que ambas APIs existen.
- Actualizar README, documentación técnica, guía de pruebas y tests.

### Archivos modificados

```text
manifest.json
README.md
DOCUMENTACION_TECNICA.md
PRUEBAS_HOME_ASSISTANT.md
tests/test_manifest.py
INCIDENCIAS_SOLUCIONES.md
```

### Verificación Esperada en Home Assistant

1. Copiar de nuevo la integración a:

   ```text
   /config/custom_components/saj_as1_modbus/
   ```

2. Reiniciar Home Assistant completo.
3. Abrir **Ajustes > Dispositivos y servicios > Añadir integración**.
4. Buscar **SAJ AS1 Modbus**.

Resultado esperado:

- Ya no aparece el conflicto `pymodbus==3.13.0` contra `pymodbus==3.11.2`.
- El flujo de configuración se abre.
- Si el inversor responde por Modbus TCP, la entrada se puede crear.

### Regla para futuras actualizaciones

Antes de cambiar el pin de una dependencia ya usada por Home Assistant, comprobar
la versión que trae la instalación real. En integraciones custom publicas,
priorizar compatibilidad con la versión de Home Assistant instalada sobre usar
la versión más nueva de una librería.

## 2026-06-03 - Bucle de reconexión PyModbus y escrituras `Not connected`

### Síntoma

Tras un tiempo estable, Home Assistant registra:

```text
Conexión SAJ AS1 Modbus no disponible
```

Después, algunas escrituras fallan con:

```text
SAJ AS1 write failed at 0x3608:
Modbus Error: [Connection] Not connected[AsyncModbusTcpClient 192.168.50.119:502]
```

El log de depuración muestra muchas líneas seguidas de PyModbus:

```text
-> transport: received eof
Connection lost comm due to None
Wait comm 100.0 ms before reconnecting.
```

### Causa

PyModbus mantenía activa su autoreconexión interna con `reconnect_delay=0.1`.
Cuando el stick Modbus/TCP cerraba la conexión o devolvía una respuesta de error,
el cliente quedaba en un estado inestable y empezaba a reconectar en bucle.

Además, la caché de conexión podía devolver un cliente cacheado sin comprobar en
cada uso si seguía conectado.

### Solución Aplicada

- Desactivar la autoreconexión interna de PyModbus con `reconnect_delay=0` y
  `reconnect_delay_max=0`.
- Reducir los reintentos internos de petición de PyModbus a `retries=1`.
- Comprobar siempre `client.connected` antes de devolver un cliente cacheado.
- Cerrar e invalidar el cliente ante excepciones Modbus, respuestas de error o
  respuestas sin registros.
- Reintentar una escritura una vez con cliente nuevo antes de devolver
  `write_failed`.
- Subir la versión de la integración a `3.0.2`.

### Archivos modificados

```text
connection_manager.py
tests/test_source_static.py
manifest.json
INCIDENCIAS_SOLUCIONES.md
```

### Verificación Esperada en Home Assistant

1. Copiar de nuevo la integración y reiniciar Home Assistant completo.
2. Activar depuración temporal de `saj_as1_modbus` y `pymodbus`.
3. Esperar varios ciclos de lectura.
4. Cambiar **Modo de usuario** y **Potencia de carga primera franja**.

Resultado esperado:

- No aparece un bucle continuo de `received eof`.
- Si el stick cierra una conexión puntual, la integración crea una conexión
  nueva en el siguiente intento.
- Las escrituras ya no fallan por cliente cacheado `Not connected`.

## 2026-06-03 - AIO3 WiFi se bloquea tras cambios desde Elekeeper o modo de bateria

### Sintoma

La integracion funciona estable despues de reiniciar Home Assistant, pero se
desconecta al cabo de uno o dos ciclos tras:

- Cambiar parametros desde la app oficial Elekeeper.
- Cambiar el modo de bateria desde la integracion, por ejemplo de
  **Horario de Uso** a **Autoconsumo** y de vuelta a **Horario de Uso**.

Despues del fallo, eliminar y volver a anadir la integracion puede devolver:

```text
No se puede conectar con el inversor SAJ AS1.
```

Hasta reiniciar Home Assistant completo. En los logs se observa que el AIO3 abre
la conexion TCP, pero cierra inmediatamente con `received eof` antes de responder
a una lectura Modbus.

### Causa

El AIO3 por WiFi parece quedar temporalmente ocupado o en una sesion Modbus
fragil cuando otro cliente modifica parametros o cuando se escriben registros de
configuracion sensibles. Los registros mas delicados observados son:

```text
0x3371 - Modo de usuario
0x3608 - Potencia de carga primera franja
0x361D - Potencia de descarga primera franja
```

Una reconexion inmediata podia ser contraproducente: el socket TCP llegaba a
abrirse, pero la primera trama Modbus posterior recibia EOF. Por eso el log podia
parecer recuperado aunque el transporte siguiera sin estar realmente usable.

### Solucion Aplicada

- Aumentar la pausa entre bloques Modbus de `100 ms` a `300 ms`.
- Antes de escribir, cerrar cualquier sesion abierta y esperar brevemente.
- Despues de una escritura correcta, cerrar la sesion Modbus y esperar `3 s`
  antes de continuar.
- Si una escritura falla, cerrar la sesion y esperar `8 s` de recuperacion.
- Tras un `ReconnectionNeededError` durante lecturas, cerrar y esperar en lugar
  de llamar a una reconexion proactiva inmediata.
- Leer `0x3371`, `0x3608` y `0x361D` con hasta tres intentos; entre intentos se
  cierra el cliente y se espera `1.5 s`.
- Cerrar la sesion Modbus al terminar un ciclo de lectura correcto para que el
  AIO3 no conserve una conexion larga cuando tambien puede intervenir Elekeeper.
- Subir la version de la integracion a `3.0.3`.

### Archivos modificados

```text
const.py
coordinator.py
manifest.json
tests/test_source_static.py
INCIDENCIAS_SOLUCIONES.md
```

### Verificacion Esperada en Home Assistant

1. Copiar de nuevo la integracion y reiniciar Home Assistant completo.
2. Esperar dos ciclos de lectura sin tocar Elekeeper.
3. Cambiar un modo desde Elekeeper y esperar al menos tres minutos.
4. Cambiar desde la integracion entre **Autoconsumo** y **Horario de Uso**.
5. Revisar los logs filtrando por:

   ```text
   saj_as1_modbus
   pymodbus
   ```

Resultado esperado:

- Puede aparecer algun EOF puntual si el AIO3 esta ocupado, pero no debe quedar
  en bucle permanente hasta reiniciar Home Assistant.
- La integracion debe recuperar valores por si sola en los siguientes ciclos.
- El flujo de configuracion debe poder conectar de nuevo sin reiniciar Home
  Assistant, siempre que el AIO3 vuelva a aceptar Modbus TCP.

## 2026-06-03 - Rafagas de escrituras bloquean temporalmente el AIO3

### Sintoma

Con la version `3.0.3` la integracion ya no queda bloqueada hasta reiniciar Home
Assistant, pero al cambiar varios valores seguidos desde la UI, por ejemplo:

```text
Potencia de carga
Potencia de descarga
Autoconsumo / Horario de Uso
```

el AIO3 puede quedarse ocupado durante unos segundos. El log muestra que una
escritura responde correctamente y otra entra demasiado cerca, especialmente en
el registro:

```text
0x3371 - Modo de usuario
```

Ejemplos observados:

```text
WriteSingleRegisterResponse address=0x3608
SAJ AS1 write failed at 0x3371
WriteSingleRegisterResponse address=0x361D
```

Tambien se observa que `0x3371` puede devolver una excepcion Modbus y aceptar la
misma escritura unos segundos despues.

### Causa

Home Assistant puede lanzar varias llamadas de servicio casi consecutivas. La
integracion pausaba lecturas mientras habia una escritura activa, pero no
serializaba la escritura completa como una cola. Eso permitia que cambios de
carga, descarga y modo se pisaran en el AIO3 antes de que el adaptador WiFi
terminara de aplicar el cambio anterior.

Ademas, `connection.close()` podia ejecutarse mientras otra operacion Modbus
acababa de entrar en PyModbus, lo que aumentaba el riesgo de `Cancel send` o
`No response received`.

### Solucion Aplicada

- Anadir un contador de escrituras pendientes y un `asyncio.Lock()` exclusivo
  para serializar las escrituras completas.
- Mantener `_write_requested=True` mientras haya escrituras pendientes, no solo
  durante la escritura actualmente activa.
- Subir la pausa previa a escritura a `1 s`.
- Subir la pausa posterior a escritura a `5 s`.
- Anadir reintento lento de escritura: dos intentos de coordinador separados por
  `12 s`, ademas del reintento rapido interno del gestor Modbus.
- Al escribir correctamente, retrasar la siguiente lectura MEDIUM porque los
  valores de modo/carga/descarga ya se actualizan de forma optimista en cache.
- Proteger `connection.close()` con el mismo bloqueo de I/O que lecturas y
  escrituras, para no cerrar un socket mientras PyModbus esta usando una trama.
- Subir la version de la integracion a `3.0.4`.

### Archivos modificados

```text
const.py
coordinator.py
connection_manager.py
manifest.json
tests/test_source_static.py
INCIDENCIAS_SOLUCIONES.md
```

### Verificacion Esperada en Home Assistant

1. Copiar la version `3.0.4` y reiniciar Home Assistant completo.
2. Esperar dos ciclos estables.
3. Cambiar tres valores seguidos desde la UI: carga, descarga y modo.
4. No tocar Elekeeper durante dos minutos.
5. Revisar logs.

Resultado esperado:

- Las escrituras deben ejecutarse en cola, separadas por pausas visibles.
- El cambio de modo puede tardar mas, pero no deberia devolver `write_failed`
  si el AIO3 acepta el segundo intento.
- Puede aparecer algun fallo puntual de lectura tras escrituras, pero debe
  recuperarse solo y sin reiniciar Home Assistant.

## 2026-06-03 - Elekeeper guarda el modo de uso como un lote

### Observacion

La app oficial Elekeeper no parece enviar una escritura independiente por cada
campo mientras se edita el modo **Horario de Uso**. El flujo real es:

```text
1. Seleccionar Horario de Uso.
2. Editar dias de la semana.
3. Editar potencia de carga/descarga.
4. Pulsar Guardar.
5. La app procesa todo junto.
```

La integracion, al exponer entidades normales de Home Assistant, recibia una
llamada de servicio por cada entidad modificada. Aunque las escrituras estuvieran
serializadas, seguian siendo guardados separados.

### Causa

El AIO3 tolera mejor una secuencia corta y ordenada de configuracion que varias
escrituras completas separadas por ventanas de cierre, recuperacion y nueva
conexion. Especialmente, el registro `0x3371` de modo de usuario debe aplicarse
despues de los parametros de potencia si el usuario esta preparando el modo
**Horario de Uso**.

### Solucion Aplicada

- Cambiar la cola de escrituras por un lote con ventana de `2 s`.
- Si durante esa ventana llegan cambios de carga, descarga y modo, se aplican en
  una sola secuencia.
- Orden del lote:

  ```text
  0x3608 - Potencia de carga primera franja
  0x361D - Potencia de descarga primera franja
  0x3371 - Modo de usuario
  ```

- Mantener la cache optimista para que Home Assistant refleje el cambio.
- Mantener el reintento lento si el AIO3 rechaza temporalmente una escritura.
- Subir la version de la integracion a `3.0.5`.

### Archivos modificados

```text
const.py
coordinator.py
manifest.json
tests/test_source_static.py
INCIDENCIAS_SOLUCIONES.md
```

### Verificacion Esperada en Home Assistant

1. Copiar la version `3.0.5` y reiniciar Home Assistant completo.
2. Cambiar carga, descarga y modo en menos de dos segundos.
3. Verificar en log que no salen tres bloques completos independientes, sino una
   secuencia agrupada.
4. Esperar a que finalice el guardado antes de tocar Elekeeper.

Resultado esperado:

- Home Assistant puede tardar algo mas en confirmar el cambio porque espera el
  resultado del lote.
- El AIO3 deberia recibir el modo despues de las potencias.
- Deben reducirse los fallos temporales de `0x3371`.

## 2026-06-03 - Automatizaciones necesitan confirmacion rapida y fiable

### Sintoma

La version `3.0.5` agrupa escrituras de entidades durante una ventana de `2 s`,
pero en automatizaciones o cambios secuenciales de UI se puede notar lento. En
el log real se observa que las escrituras Modbus correctas suelen tardar solo
`200-400 ms`, mientras que la lentitud viene de:

- Espera de agrupacion.
- Pausa de asentamiento tras escritura.
- Reintento lento si `0x3371` devuelve excepcion temporal.

Ejemplo observado:

```text
0x3371 devuelve 0x86 0x33
12 s despues acepta la misma escritura
```

### Causa

Las entidades estándar de Home Assistant son utiles para editar manualmente, pero
una automatizacion que llama a `number.set_value`, `number.set_value` y
`select.select_option` esta generando varias llamadas independientes. Aunque la
integracion las agrupe si llegan juntas, Home Assistant o la UI pueden esperar a
que termine una llamada antes de enviar la siguiente.

### Solucion Aplicada

- Anadir el servicio propio `saj_as1_modbus.set_profile`.
- El servicio acepta en una sola llamada:

  ```text
  charge_power_pct
  discharge_power_pct
  user_mode
  config_entry_id
  ```

- Si solo hay un SAJ AS1 configurado, `config_entry_id` es opcional.
- El servicio aplica el lote directamente, sin esperar la ventana de agrupacion
  de entidades.
- Mantiene el orden seguro:

  ```text
  0x3608 - Potencia de carga
  0x361D - Potencia de descarga
  0x3371 - Modo de usuario
  ```

- La llamada del servicio no devuelve hasta recibir respuesta Modbus o agotar el
  reintento configurado.
- Subir la version de la integracion a `3.0.6`.

### Archivos modificados

```text
__init__.py
const.py
coordinator.py
manifest.json
models.py
services.yaml
tests/test_source_static.py
INCIDENCIAS_SOLUCIONES.md
```

### Ejemplo de automatizacion

```yaml
service: saj_as1_modbus.set_profile
data:
  charge_power_pct: 50
  discharge_power_pct: 50
  user_mode: "Horario de Uso"
```

### Verificacion Esperada en Home Assistant

1. Copiar la version `3.0.6`, incluyendo `services.yaml`.
2. Reiniciar Home Assistant completo.
3. Ir a **Herramientas para desarrolladores > Acciones**.
4. Buscar `SAJ AS1 Modbus: Configurar perfil SAJ AS1`.
5. Ejecutar el servicio con carga, descarga y modo.

Resultado esperado:

- Debe realizarse como una sola llamada de servicio.
- Si el AIO3 responde a la primera, deberia terminar mucho antes que tres
  cambios manuales separados.
- Si el AIO3 rechaza temporalmente `0x3371`, el servicio tardara mas porque
  espera el reintento que confirma la escritura.

## 2026-06-04 - Auditoria de calidad y compatibilidad Home Assistant 2026.6

### Sintoma

La integracion ya funciona estable en pruebas reales, pero faltaba dejar una
memoria completa para futuros chats y cerrar varios detalles de calidad de Home
Assistant:

- Servicio registrado desde `async_setup`.
- Errores de servicio traducibles.
- Compatibilidad documentada con Home Assistant 2026.6.
- Iconos movidos a `icons.json`.
- Auditoria de reglas tipo Platino para integracion custom.
- Documento de contexto persistente para Codex.

### Causa

Home Assistant 2026.6 introduce nuevas deprecaciones de flujo de configuracion,
especialmente sobre listeners de config entry combinados con metodos de reload y
la desaparicion progresiva de `show_advanced_options`. Aunque la integracion no
dependia de esas APIs, convenia dejarlo probado y documentado.

Ademas, los servicios registrados solo al cargar una entrada son menos robustos
para automatizaciones, porque Home Assistant no puede validarlos igual si la
entrada no esta cargada.

### Solucion Aplicada

- Registrar `saj_as1_modbus.set_profile` en `async_setup`.
- Validar entrada existente y cargada antes de ejecutar el servicio.
- Cambiar errores de servicio a `ServiceValidationError` o `HomeAssistantError`
  con `translation_key`.
- Envolver la primera lectura del coordinador para cerrar conexion y propagar
  `ConfigEntryNotReady` si el AS1 no responde en setup.
- Crear `icons.json` y retirar `icon=` de las descripciones Python.
- Crear `docs/AI_CONTEXT.md` como memoria tecnica publica para futuras sesiones.
- Crear `AUDITORIA_PLATINO_PERSONAL.md` y `quality_scale.yaml`.
- Documentar que `pymodbus==3.11.2` se mantiene hasta verificar dependencias
  reales en Home Assistant 2026.6.x.
- Preparar version publica inicial `1.0.0`.

### Archivos modificados

```text
__init__.py
binary_sensor.py
config_flow.py
connection_manager.py
const.py
manifest.json
number.py
select.py
sensor.py
services.yaml
strings.json
translations/es.json
es.json
README.md
DOCUMENTACION_TECNICA.md
PRUEBAS_HOME_ASSISTANT.md
tests/
```

### Archivos nuevos

```text
icons.json
codex.md
AUDITORIA_PLATINO_PERSONAL.md
quality_scale.yaml
```

### Verificacion Esperada en Home Assistant

1. Copiar tambien `icons.json` y `services.yaml`.
2. Reiniciar Home Assistant 2026.6.x.
3. Confirmar que no hay deprecaciones por `show_advanced_options`.
4. Confirmar que no hay avisos por listeners de config entry con reload.
5. Ejecutar `saj_as1_modbus.set_profile` desde Acciones.
6. Confirmar que los errores, si aparecen, salen en espanol.
