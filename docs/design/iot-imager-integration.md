# Flash Imager — IoT Mode Integration Spec

Status: **Design ready · Firmware & board manifest implemented (`iot/`)**

## Goal

Extend **LA AGUJA Flash Imager** (Electron `desktop/` and future Rust `imager-rust/`) with an **IoT** tab alongside the existing USB Rescue Disk flow so a user can plug in a supported microcontroller over USB, fill in Wi-Fi + Tailscale/Headscale + node profile, and flash a ready-to-operate tailnet node **without installing ESP-IDF, compilers, or Python toolchains on their computer**.

## Core Architecture: Prebuilt Generic Firmware + Dynamic NVS Partition

Just like Rescue Disk separates the immutable squashfs image from `AGUJA_CFG`, **LA AGUJA IoT** separates the compiled firmware from per-device secrets:

1. **Signed generic firmware release artifacts** (published in the same signed catalog model as Rescue Disk):
   - `bootloader.bin` (`0x0`)
   - `partition-table.bin` (`0x8000`)
   - `ota_data_initial.bin` (`0x15000`)
   - `aguja_iot_<board>_<version>.bin` (`0x20000`)
   - Verified with Ed25519 signature + SHA-256 per artifact.
2. **Per-device NVS provisioning partition (`0x9000`, 48 KB)** generated locally inside Flash Imager right before flashing:
   - Namespace: `aguja_cfg`, key: `blob_v1`, struct layout matching `aguja_config_t` (`AGUJA_CFG_MAGIC = 0x4147554A`, `AGUJA_CFG_VERSION = 1`), or an equivalent CSV/JSON NVS entry parsed at first boot.
   - Contains: ordered Wi-Fi profiles, SoftAP settings, Tailscale/Headscale control host + Noise pubkey (auto-fetched by Flash Imager from `https://<ctrl_host>/key?v=131`!), pre-auth key, DERP region, hostname, exit-node / subnet-router toggles, RF antenna selection, and a freshly generated random `agj_...` API Bearer token.
   - **Never leaves the user's machine** and is written straight to flash at `0x9000` (with optional encrypted export alongside the node's API token for the user's agent CLI).

## Board Discovery & Flashing Engine

`iot/boards.json` is the single source of truth read by Flash Imager:

1. **Auto-detect USB devices** by VID/PID (e.g. `303a:1001` for Espressif USB-Serial/JTAG on Seeed Studio XIAO ESP32-C6).
2. **Optional full flash backup** (4 MB read-flash saved with SHA-256 before erasing, mirroring Rescue Disk's USB safety backup).
3. **Flashing backend**:
   - **Electron (`desktop/`)**: `esptool-js` over WebSerial/serialport, or bundled `espflash` / `esptool` binary.
   - **Rust (`imager-rust/`)**: native `espflash` crate (`espflash` Rust library — zero Python, single static binary on Linux & Windows!).
4. **Post-flash live smoke verification**:
   - Hard-reset via RTS, open serial console at 115200 baud for ~20 s, parse structured boot/status output, confirm Wi-Fi IP + Tailnet `CONNECTED` + assigned `100.x.y.z` VPN IP, and display the generated `aguja-iot` CLI snippet + Web UI URL (`http://<hostname>/`) + routes to approve in Headscale/Tailscale.

## Planned Milestones

1. **Phase 1 (Done):** Verified ESP32-C6 firmware (`v1.2.0`), dual-OTA rollback, full agent REST API, Dark Web UI, `iot/boards.json`, and `iot/cli/aguja-iot.py`.
2. **Phase 2 (Next):** Add a pure-JSON NVS bootstrap file/partition key (`aguja_cfg/init_json` string key alongside `blob_v1`) so Flash Imager can emit standard ESP-IDF NVS partitions without coupling to C struct padding across architectures.
3. **Phase 3:** Add the **IoT** tab in `imager-rust/` (using native `espflash` crate) and `desktop/`, auto-fetching Headscale Noise keys from `/key?v=131` and publishing signed generic firmware images in the LA AGUJA catalog.
4. **Phase 4:** Expand `iot/boards.json` with ESP32-S3 (PSRAM, higher throughput) and Ethernet boards (WT32-ETH01 / W5500).
