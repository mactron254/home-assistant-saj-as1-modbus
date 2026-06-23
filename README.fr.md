# SAJ AS1 Modbus pour Home Assistant

> **Integration communautaire non officielle. Non affiliee, approuvee, soutenue ni prise en charge par SAJ.**
>
> Ce projet a ete cree avec assistance IA et tests communautaires. Utilisation a vos propres risques. L'auteur ne fournit aucune garantie et n'est pas responsable des dommages, erreurs de configuration, pertes de donnees, comportement de l'onduleur, batterie, reseau electrique ou consequences d'utilisation ou de mauvaise utilisation.

SAJ AS1 Modbus est une integration personnalisee Home Assistant pour SAJ AS1 via **Modbus TCP/IP uniquement**.

Le Modbus RTU/RS485 direct n'est pas pris en charge. L'integration vise un endpoint TCP comme AIO3 en WiFi/LAN.

## Installation avec HACS

1. Ouvrir HACS.
2. Ajouter le depot personnalise:

   ```text
   https://github.com/mactron254/home-assistant-saj-as1-modbus
   ```

3. Choisir la categorie `Integration`.
4. Installer **SAJ AS1 Modbus**.
5. Redemarrer Home Assistant.
6. Ajouter l'integration depuis **Settings > Devices & services > Add integration**.

## Installation manuelle

Copier:

```text
custom_components/saj_as1_modbus/
```

dans le dossier `custom_components/` de Home Assistant, puis redemarrer.

## Configuration

| Champ | Description | Valeur habituelle |
| --- | --- | --- |
| Host | IP ou nom de l'endpoint Modbus TCP | IP AIO3 |
| Port | Port Modbus TCP | `502` |
| Device ID | ID logique Modbus | `1` |

La frequence de polling n'est volontairement pas configurable dans l'interface.

## Securite

L'integration peut ecrire des registres qui changent le mode utilisateur et la puissance de charge/decharge. Testez avec prudence, consultez les logs et n'automatisez pas les ecritures sans comprendre leur effet.

## Documentation

La documentation principale est en anglais:

- [Installation](docs/INSTALLATION.md)
- [Configuration](docs/CONFIGURATION.md)
- [Entities](docs/ENTITIES.md)
- [Services](docs/SERVICES.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Logging](docs/LOGGING.md)
- [Safety](SAFETY.md)
- [Disclaimer](DISCLAIMER.md)
