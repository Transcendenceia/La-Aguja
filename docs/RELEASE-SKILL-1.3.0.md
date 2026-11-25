# Flash Imager Agent Skill 1.3.0

English first · Español después.

The standalone preparation skill is aligned with **Flash Imager engine 1.2.0**,
**public Rescue Disk 1.1.2**, and the new **LA AGUJA IoT (ESP32 family)** module.
Component versions remain independent.

## What's new in 1.3.0

- **Headless ESP32 IoT provisioning (`iot-boards` and `iot-nvs`):**
  - `iot-boards` lists all 11 supported ESP32-family boards (`ESP32-C6`, `ESP32-S3`,
    `ESP32-C3`, `ESP32`, `ESP32-S2`), their flash offsets, PSRAM/RF-switch capabilities
    and matching generic `v1.4.0` firmware profile.
  - `iot-nvs` uses the same pure-JavaScript ESP-IDF NVS v2 generator (`desktop/iot-nvs.cjs`)
    as the desktop Imager to build verified 48 KiB (`0xC000`) provisioning binaries
    from private JSON stdin, with SoftAP disabled by default, atomic new-file output
    (`0600` on POSIX), zero credential echo and `device_written:false`.
- **IoT documentation and CLI reference bundled:** includes `references/iot.md`,
  credential-free `assets/iot-request.example.json`, `references/iot/README.md`
  and `references/iot/aguja-iot.py` for operating flashed nodes over your tailnet.
- **Bundled Imager engine updated to 1.2.0:** preserves all extended Rescue Disk
  `imager-profile-v2` capabilities (up to 16 Wi-Fi networks, 32 NAS/cloud destinations,
  literal custom environment, advanced tailnet options, reusable `.aguja` profiles,
  and BitLocker/LUKS recovery capsules).

The CLI prepares regular `.img` and `.bin` files. It does **not** write physical
USBs, flash serial ports, enroll accounts or mount remote storage. Physical USB
writing and ESP32 serial flashing remain explicit user actions in Flash Imager 1.2.0
or authorised local commands.

## Distribution

Use the explicit `flash-imager-skill-v1.3.0` release, never `releases/latest`.
ZIP and `.tar.gz` archives are self-contained with Node.js 22+, dependency licenses,
member SHA-256 `BUNDLE-MANIFEST.json` and deterministic archives. Run `doctor` and
`iot-boards` after extraction and verify `catalog` from the downloaded package.
Rescue Disk remains `v1.1.2`; Flash Imager desktop installers are `1.2.0`.

## Español

La skill **1.3.0** incorpora el motor Imager **1.2.0** y añade soporte headless para
**LA AGUJA IoT (familia ESP32)** junto a la preparación completa de Rescue Disk **1.1.2**:

- `iot-boards`: consulta las 11 placas ESP32 soportadas (`ESP32-C6`, `ESP32-S3`,
  `ESP32-C3`, `ESP32`, `ESP32-S2`), sus offsets de flash y su perfil de firmware `v1.4.0`.
- `iot-nvs`: genera en JavaScript puro la partición binaria ESP-IDF NVS v2 de 48 KiB
  desde JSON privado por `stdin`, con SoftAP desactivado por defecto, sin sobrescribir
  archivos, sin devolver secretos en salida y con `device_written:false`.
- Incluye `references/iot.md`, el esqueleto sin credenciales `assets/iot-request.example.json`
  y la CLI de operación remota `references/iot/aguja-iot.py`.

No escribe USBs físicos ni flashea puertos serie automáticamente; mantiene intactos
los paquetes publicados de Rescue 1.1.2 y las versiones anteriores de la skill.
