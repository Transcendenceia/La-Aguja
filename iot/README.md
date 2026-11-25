# LA AGUJA IoT (Experimental)

[Español](README.es.md) · [Full IoT Architecture](../docs/IOT.md) · [Flash Imager IoT Spec](../docs/design/iot-imager-integration.md) · [Third-Party Notices](THIRD-PARTY-NOTICES.md)

**LA AGUJA IoT** extends the LA AGUJA platform beyond x86-64 bootable USB rescue disks into **pocket-sized, tailnet-native microcontroller nodes** controlled by AI agents and operators.

Plug in a compatible microcontroller, let it join Wi-Fi, and it automatically enrolls into your **Tailscale or self-hosted Headscale tailnet** as an agent-controllable mobile operations center — with **exit node**, **dynamic upstream subnet routing**, **SoftAP NAT**, **full hardware control** (RF antenna switch, GPIO, PWM, ADC, I2C, UART, SPI, die temperature), **network diagnostics**, **live NVS reconfiguration**, and **dual-slot OTA updates with automatic rollback**.

## Directory layout

| Path | Purpose |
| --- | --- |
| `iot/boards.json` | Machine-readable board registry (USB VID/PID, flash offsets, pin maps, NVS schema) prepared for the upcoming **Flash Imager IoT** tab. |
| `iot/firmware/esp32c6/` | ESP-IDF v5.5 firmware for **Seeed Studio XIAO ESP32-C6** (`ESP32-C6FH4`, 4 MB flash, 512 KB SRAM, no PSRAM), built on patched MicroLink v2.3.0. |
| `iot/cli/aguja-iot.py` | Zero-dependency Python 3 CLI for agents and operators to control an enrolled node over Tailscale/Headscale. |
| `iot/THIRD-PARTY-NOTICES.md` | License attribution and local non-PSRAM patch notes for MicroLink, wireguard-lwip, and ESP-IDF. |

## Supported boards

| Board | Chip | Status | Flash / RAM |
| --- | --- | --- | --- |
| **Seeed Studio XIAO ESP32-C6** | ESP32-C6FH4 (RISC-V 160 MHz) | **Verified on real hardware** (v1.2.0) | 4 MB Flash / 512 KB SRAM (no PSRAM) |
| ESP32-S3 N16R8 | ESP32-S3 (Xtensa dual-core) | Planned (`boards.json` ready) | 16 MB Flash / 8 MB PSRAM |

## Quick build & flash (ESP-IDF v5.5+)

```sh
cd iot/firmware/esp32c6
cp sdkconfig.secrets.example sdkconfig.secrets
# Edit sdkconfig.secrets with your Wi-Fi, Headscale/Tailscale key, and token (never commit it)

. ~/esp/esp-idf/export.sh
idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.secrets" set-target esp32c6
idf.py build
idf.py -p /dev/ttyACM0 flash monitor
```

Once the node joins your tailnet, approve its advertised routes (`0.0.0.0/0`, `::/0`, upstream Wi-Fi subnet, `192.168.4.0/24`) in Tailscale/Headscale and manage it remotely:

```sh
python3 iot/cli/aguja-iot.py --host aguja-iot --token "$AGUJA_IOT_TOKEN" status
python3 iot/cli/aguja-iot.py --host aguja-iot --token "$AGUJA_IOT_TOKEN" wifi-scan
python3 iot/cli/aguja-iot.py --host aguja-iot --token "$AGUJA_IOT_TOKEN" ota iot/firmware/esp32c6/build/aguja_iot.bin
```

## Security & public hygiene

- The HTTP control plane listens **only on the WireGuard tailnet IP** by default (`http_allow_lan=false`) and requires Bearer/Basic token authentication on all endpoints except `/api/v1/health`.
- Never commit `sdkconfig.secrets`, `sdkconfig`, or device flash dumps. Generic builds ship with empty credentials and accept provisioning via NVS, USB Serial CLI, or the planned **Flash Imager IoT** workflow.
