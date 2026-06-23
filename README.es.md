# SAJ AS1 Modbus para Home Assistant

> **Integracion comunitaria no oficial. No afiliada, aprobada, respaldada ni soportada por SAJ.**
>
> Este proyecto se ha creado con ayuda de IA y pruebas comunitarias. Usalo bajo tu propia responsabilidad. El autor no ofrece garantia y no se hace responsable de daños, mala configuracion, perdida de datos, comportamiento del inversor, bateria, red electrica o cualquier consecuencia del uso o mal uso.

SAJ AS1 Modbus es una integracion personalizada de Home Assistant para leer y controlar un SAJ AS1 mediante **Modbus TCP/IP solamente**.

No soporta Modbus RTU/RS485 directo. Esta pensada para un endpoint TCP como AIO3 por WiFi/LAN.

## Instalacion HACS

1. Abre HACS.
2. Añade repositorio personalizado:

   ```text
   https://github.com/mactron254/home-assistant-saj-as1-modbus
   ```

3. Categoria: `Integration`.
4. Instala **SAJ AS1 Modbus**.
5. Reinicia Home Assistant.
6. Ve a **Ajustes > Dispositivos y servicios > Añadir integracion**.

## Instalacion manual

Copia:

```text
custom_components/saj_as1_modbus/
```

en tu carpeta `custom_components/` de Home Assistant y reinicia.

## Configuracion

| Campo | Descripcion | Valor habitual |
| --- | --- | --- |
| Host | IP o nombre del endpoint Modbus TCP | IP del AIO3 |
| Puerto | Puerto TCP Modbus | `502` |
| ID de dispositivo | ID logico Modbus | `1` |

La frecuencia de lectura no es configurable desde la UI. Es intencionado para proteger la estabilidad del AIO3.

## Seguridad

La integracion puede escribir registros que cambian modo de usuario y porcentajes de carga/descarga. Prueba primero con valores conservadores, revisa logs y no automatices escrituras sin entender el efecto.

## Documentacion

La documentacion tecnica principal esta en ingles:

- [Instalacion](docs/INSTALLATION.md)
- [Configuracion](docs/CONFIGURATION.md)
- [Entidades](docs/ENTITIES.md)
- [Servicios](docs/SERVICES.md)
- [Solucion de problemas](docs/TROUBLESHOOTING.md)
- [Logs](docs/LOGGING.md)
- [Seguridad](SAFETY.md)
- [Aviso legal](DISCLAIMER.md)
