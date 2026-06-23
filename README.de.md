# SAJ AS1 Modbus fur Home Assistant

> **Inoffizielle Community-Integration. Nicht mit SAJ verbunden, nicht von SAJ genehmigt, empfohlen oder unterstutzt.**
>
> Dieses Projekt, einschliesslich Code, Dokumentation, Review und Wartung, wurde vollstandig mit KI-generierten Workflows erstellt. Nutzung auf eigenes Risiko. Der Autor gibt keine Garantie und haftet nicht fur Schaden, falsche Konfiguration, Datenverlust, Wechselrichterverhalten, Batterieverhalten, Netzinteraktion oder Folgen von Nutzung oder Fehlgebrauch.

SAJ AS1 Modbus ist eine Home Assistant Custom Integration fur SAJ AS1 uber **nur Modbus TCP/IP**.

Direktes Modbus RTU/RS485 wird nicht unterstutzt. Ziel ist ein TCP-Endpunkt wie AIO3 uber WiFi/LAN.

## Installation mit HACS

1. HACS offnen.
2. Custom Repository hinzufugen:

   ```text
   https://github.com/mactron254/home-assistant-saj-as1-modbus
   ```

3. Kategorie `Integration` wahlen.
4. **SAJ AS1 Modbus** installieren.
5. Home Assistant neu starten.
6. Integration uber **Settings > Devices & services > Add integration** hinzufugen.

## Manuelle Installation

Kopiere:

```text
custom_components/saj_as1_modbus/
```

in den `custom_components/` Ordner von Home Assistant und starte Home Assistant neu.

## Konfiguration

| Feld | Beschreibung | Typischer Wert |
| --- | --- | --- |
| Host | IP oder Hostname des Modbus TCP-Endpunkts | AIO3 IP |
| Port | Modbus TCP-Port | `502` |
| Device ID | Logische Modbus ID | `1` |

Das Polling-Intervall ist absichtlich nicht in der UI konfigurierbar.

## Sicherheit

Die Integration kann Register schreiben, die Benutzer-Modus und Lade-/Entladeleistung andern. Erst konservativ testen, Logs prufen und keine Schreib-Automationen nutzen, ohne die Wirkung zu verstehen.

## Dokumentation

Die Hauptdokumentation ist auf Englisch:

- [Installation](docs/INSTALLATION.md)
- [Configuration](docs/CONFIGURATION.md)
- [Entities](docs/ENTITIES.md)
- [Services](docs/SERVICES.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Logging](docs/LOGGING.md)
- [Safety](SAFETY.md)
- [Disclaimer](DISCLAIMER.md)
