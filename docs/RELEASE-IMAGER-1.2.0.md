# LA AGUJA Flash Imager 1.2.0 · Windows and Linux (with ESP32 IoT Mode)

Flash Imager 1.2.0 introduces a parallel **IoT · MCU** workflow alongside the existing
USB Rescue Disk preparer. **Rescue Disk remains 1.1.2** and is not rebuilt or modified
by this release.

## What's new in 1.2.0

- **Parallel IoT · MCU mode for the full ESP32 family (Linux and Windows):**
  - 11 supported board profiles across **ESP32-C6, ESP32-S3 (Octal & Standard), ESP32-C3,
    ESP32 and ESP32-S2**, backed by 6 bundled generic prebuilt `v1.4.0` firmwares
    (`esp32c6`, `esp32s3-oct`, `esp32s3-std`, `esp32c3`, `esp32`, `esp32s2`).
  - **Real USB silicon auto-detection:** probes connected USB-serial boards via `esptool`,
    identifies chip, flash size and PSRAM, and automatically selects the matching board profile.
  - **4-step intuitive & technical wizard:** Board & Auto-detect → Multi-Wi-Fi (up to 8
    prioritized networks, SoftAP **disabled by default**) → Tailscale / Headscale proxy
    (exit node, dynamic upstream subnet router, DNS relay, optional Noise pubkey & DERP
    region) → Flash map, direct flashing, serial boot verification and 1-click full flash erase.
  - **Pure-JavaScript ESP-IDF NVS v2 generator (`desktop/iot-nvs.cjs`):** zero external
    dependencies, deterministic 48 KiB (`0xC000`) provisioning binary injected at `0x9000`.
  - **Zero-Python Windows flashing:** Windows builds bundle official standalone Espressif
    `esptool.exe` (v5.7.0) and use native `.NET System.IO.Ports.SerialPort` via PowerShell
    for COM discovery and post-flash boot verification.
- **Full Rescue Disk 1.1.2 compatibility preserved:** all 7 USB steps, extended `imager-profile-v2`
  profiles (16 Wi-Fi networks, 32 NAS/cloud destinations, literal environment, advanced tailnet),
  reusable encrypted `.aguja` profiles, BitLocker/LUKS recovery capsules and CFG editing remain intact.

## Distribution and provenance

Windows portable `.exe`, Linux `AppImage`, `.deb` and portable `.tar.gz` are accompanied by
`SHA256SUMS-imager-1.2.0-windows`, `SHA256SUMS-imager-1.2.0-linux`, `SHA256SUMS-imager-1.2.0`,
`aguja-flash-imager-1.2.0-source.tar.gz`, signed `catalog.json` and `VALIDATION-IMAGER-1.2.0.md`.

The corresponding Imager source is tagged `flash-imager-v1.2.0`. Installers are hosted under
release tag `v1.2.0` to satisfy the Imager updater URL contract (`/releases/download/v<version>/`),
while `v1.1.2` remains the latest Rescue Disk release and carries the updated signed `catalog.json`
advertising both Rescue Disk 1.1.2 and Flash Imager 1.2.0.

## Español

Se publica **Flash Imager 1.2.0** para **Linux y Windows** con el nuevo modo paralelo
**IoT · MCU** para la familia **ESP32**:

- **11 placas ESP32 soportadas** (`ESP32-C6`, `ESP32-S3`, `ESP32-C3`, `ESP32`, `ESP32-S2`)
  con 6 firmwares genéricos `v1.4.0` precompilados e integrados en la aplicación.
- **Detección automática real del chip por USB**, asistente guiado de 4 pasos, múltiples redes
  Wi-Fi con prioridad, **SoftAP desactivado por defecto**, alta Tailscale/Headscale con exit
  node / subnet router / DNS relay, verificación serie tras el flasheo y borrado de flash en 1 clic.
- **Generador NVS v2 en JavaScript puro** y **Windows sin Python** (incluye `esptool.exe` oficial
  independiente y verificación serie con `.NET SerialPort`).
- **Rescue Disk sigue en 1.1.2** sin modificaciones; todos los flujos USB existentes se mantienen intactos.
