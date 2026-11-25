# LA AGUJA IoT — Tailnet-Native ESP32 Nodes (v1.4.0)

[Español](IOT.es.md) · [IoT Module README](../iot/README.md) · [Flash Imager 1.2.0](RELEASE-IMAGER-1.2.0.md) · [Agent Skill IoT Ref](../skills/flash-imager/references/iot.md) · [Board Registry](../iot/boards.json)

**LA AGUJA IoT** brings the LA AGUJA portable command post philosophy — small entry point, real control, no proprietary relay — to the **ESP32 microcontroller family**. An enrolled board connects to Wi-Fi, joins your **Tailscale or self-hosted Headscale tailnet** directly over WireGuard/DERP, and exposes a complete agent-controllable remote operations node.

## Supported ESP32 boards & Flash Imager 1.2.0

**Flash Imager 1.2.0** (Linux and Windows) ships with a parallel **IoT · MCU** 4-step wizard bundling **6 generic prebuilt `v1.4.0` firmwares** covering **11 board profiles**:

| Family | Firmware profile | Supported boards | Hardware verification |
| --- | --- | --- | --- |
| **ESP32-C6** | `esp32c6` | Seeed Studio XIAO ESP32-C6 (RF switch), ESP32-C6-DevKitC-1 | Verified on physical XIAO ESP32-C6 |
| **ESP32-S3 (Octal PSRAM)** | `esp32s3-oct` | ESP32-S3-WROOM-1 N16R8, Seeed XIAO ESP32-S3, ESP32-S3-DevKitC-1 N8R8 | Verified on physical N16R8 (Linux & Windows 11) |
| **ESP32-S3 (Std)** | `esp32s3-std` | ESP32-S3 Generic (N4 / N8 / N8R2 / Zero) | Compiled & packaged (`v1.4.0`) |
| **ESP32-C3** | `esp32c3` | ESP32-C3 SuperMini / XIAO C3, ESP32-C3-DevKitM-1 | Compiled & packaged (`v1.4.0`) |
| **ESP32** | `esp32` | ESP32-WROOM-32 DevKit v1, ESP32-WROVER / LilyGO | Compiled & packaged (`v1.4.0`) |
| **ESP32-S2** | `esp32s2` | Wemos / Lolin S2 Mini | Compiled & packaged (`v1.4.0`) |

- **Real USB silicon auto-detection:** probes connected serial ports via `esptool`, identifies chip/flash/PSRAM and selects the matching board automatically.
- **Pure-JavaScript ESP-IDF NVS v2 generator (`desktop/iot-nvs.cjs`):** builds the 48 KiB (`0xC000`) provisioning partition injected at `0x9000` with SoftAP **disabled by default**; also available headlessly in **Agent Skill 1.3.0** (`iot-boards` and `iot-nvs`).
- **Zero-Python Windows flashing:** Windows installers bundle standalone Espressif `esptool.exe` (v5.7.0) and use `.NET System.IO.Ports.SerialPort` for COM discovery, boot verification and 1-click flash erase.

## What an enrolled node provides

- **Tailnet connectivity (MicroLink v2.3.0):** ts2021 Noise control protocol over TLS, WireGuard data plane on lwIP, STUN, DISCO NAT traversal, and DERP relay fallback. Compatible with Tailscale and self-hosted Headscale (including embedded DERP regions).
- **Exit node + Dynamic subnet router:** advertises `0.0.0.0/0` + `::/0` (exit node with lwIP NAPT/NAT66), the live upstream Wi-Fi subnet detected via DHCP, the local SoftAP NAT subnet (`192.168.4.0/24`), plus custom CIDRs from NVS. Includes an on-device **UDP port 53 DNS relay** bound to the VPN IP for exit-node clients.
- **Multi-SSID Wi-Fi STA + SoftAP NAT gateway:** up to 8 ordered Wi-Fi profiles in NVS with round-robin fallback, live TX power and power-save tuning, and toggleable SoftAP NAT (`aguja-iot-ap`).
- **Nanometer-level hardware control (Seeed Studio XIAO ESP32-C6):**
  - RF antenna switch (`GPIO3` enable + `GPIO14` internal ceramic vs external U.FL) initialized before Wi-Fi and switchable live.
  - User LED (`GPIO15`, active-LOW): status heartbeat, on, off, blink, or PWM.
  - All 11 edge GPIOs (`D0`–`D10`): mode (`in`/`out`/`od`), pull-up/down, digital read/write/pulse, plus boot-time presets in NVS.
  - LEDC PWM (5 channels), calibrated ADC1 in mV (`D0`–`D2`), internal die temperature sensor, dynamic CPU frequency scaling (`40`/`80`/`160` MHz).
  - Live **I2C master** (`D4`/`D5` default, bus scan + raw xfer), **UART1 bridge** (`D6`/`D7` default), and **SPI master** (`D8`–`D10` default) so agents can talk to external sensors/modems without recompiling.
- **Network Ops toolkit:** remote ICMP ping, TCP port probe, DNS lookup, Wake-on-LAN magic packet sender, Wi-Fi spectrum scan, SoftAP client list, and UDP check-in beacons to an agent host.
- **On-device automation rules:** up to 8 NVS-persisted rules (`gpio_high`/`gpio_low`/`adc_gt`/`adc_lt`/`temp_gt` → `gpio_set`/`led`/`udp_alert`).
- **Dual-slot OTA with automatic rollback:** 4 MB flash layout (`ota_0` 1920 KB + `ota_1` 1920 KB). New images uploaded over Tailscale are confirmed only after reaching `CONNECTED`; otherwise the bootloader automatically rolls back.

## Agent REST API (`/api/v1/*`)

Accessible on the node's Tailscale VPN IP (`http://<hostname>/`) by default (`http_allow_lan=false`). All endpoints except `/api/v1/health` require `Authorization: Bearer <token>`, `X-Aguja-Token: <token>`, or HTTP Basic auth (`admin:<token>`).

| Group | Endpoints |
| --- | --- |
| System & Telemetry | `GET /` (Dark Ops Web UI), `GET /api/v1/health`, `GET /api/v1/status`, `GET /api/v1/peers`, `POST /api/v1/system/cpu`, `POST /api/v1/system/sleep`, `POST /api/v1/system/restart-tailnet`, `POST /api/v1/system/reboot`, `POST /api/v1/system/factory-reset` |
| Config & Rules | `GET/PUT /api/v1/config`, `GET/PUT /api/v1/rules`, `GET/DELETE /api/v1/logs`, `POST /api/v1/logs/level` |
| Hardware (XIAO C6) | `POST /api/v1/hw/antenna`, `POST /api/v1/hw/led`, `GET/POST /api/v1/hw/gpio`, `POST /api/v1/hw/pwm`, `GET /api/v1/hw/adc`, `GET /api/v1/hw/i2c/scan`, `POST /api/v1/hw/i2c/config`, `POST /api/v1/hw/i2c/xfer`, `POST /api/v1/hw/uart/config`, `POST /api/v1/hw/uart/tx`, `GET /api/v1/hw/uart/rx`, `POST /api/v1/hw/spi/xfer` |
| Wi-Fi & NetOps | `GET /api/v1/wifi/scan`, `POST /api/v1/wifi/ap`, `POST /api/v1/wifi/rf`, `POST /api/v1/net/ping`, `POST /api/v1/net/probe`, `POST /api/v1/net/dns`, `POST /api/v1/net/wol`, `GET /api/v1/net/clients`, `POST /api/v1/net/beacon` |
| Firmware OTA | `POST /api/v1/ota` (raw `.bin` body -> inactive OTA slot -> reboot with rollback guard) |

## USB Serial CLI (local recovery)

Connect at `115200` baud over native USB-Serial/JTAG (`/dev/ttyACM0`):

`help`, `status`, `token`, `config`, `scan`, `wifi <ssid> <pass>`, `authkey <key>`, `antenna <ceramic|ufl>`, `led <status|on|off|blink>`, `lan <on|off>`, `reboot`, `factory-reset`.

## Real-world limits (ESP32-C6 without PSRAM)

- Userspace WireGuard + lwIP NAPT on a single-core 160 MHz RISC-V MCU targets **reach and remote operations** (~0.5–1.5 Mbps), ideal for agent control, SSH/API hops, IoT telemetry, Wake-on-LAN, and LAN diagnostics — not video streaming or bulk backups.
- To run reliably in 512 KB SRAM without PSRAM against multi-node Headscale tailnets (~50 KB MapResponses), `iot/firmware/esp32c6` ships with `CONFIG_MBEDTLS_SSL_IN_CONTENT_LEN=16384` and local non-PSRAM streaming-JSON + zero-RAM reconnect-drain patches in vendored MicroLink (documented in [THIRD-PARTY-NOTICES.md](../iot/THIRD-PARTY-NOTICES.md)).
