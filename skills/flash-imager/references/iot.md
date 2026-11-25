# ESP32 IoT provisioning interface · 1.3.0

Flash Imager **1.2.0** introduces a parallel **IoT · MCU** mode for the ESP32 microcontroller family (`ESP32-C6`, `ESP32-S3`, `ESP32-C3`, `ESP32`, `ESP32-S2`), turning supported boards into remote Tailscale/Headscale proxy nodes (exit node, dynamic upstream subnet router, DNS relay, optional SoftAP NAT, dual-OTA and REST control plane for AI agents).

This skill exposes the **same pure-JavaScript ESP-IDF NVS v2 generator** (`desktop/iot-nvs.cjs`) and board registry (`iot/boards.json`) used by the desktop application, without Electron, Python or physical serial writes.

## Commands

### `iot-boards` (no stdin)

```sh
node "<skill-dir>/scripts/imager.cjs" iot-boards
```

Returns `{ok:true, schema_version, nvs_provisioning, boards:[...]}` listing all 11 ESP32-family board definitions, chip architecture, flash/PSRAM profile, `firmware_profile` (`esp32c6`, `esp32s3-oct`, `esp32s3-std`, `esp32c3`, `esp32`, `esp32s2`), `has_rf_switch`, `usb_ids`, `flash_offsets` and `capabilities`.

### `iot-nvs` (private JSON stdin)

```sh
node "<skill-dir>/scripts/imager.cjs" iot-nvs < "/private/iot-request.json"
```

PowerShell:

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Get-Content -Raw -Encoding UTF8 'C:\private\iot-request.json' | node 'C:\skills\flash-imager\scripts\imager.cjs' iot-nvs
```

See `../assets/iot-request.example.json` for a credential-free skeleton.

#### Input keys

- `board_id`: exact board `id` returned by `iot-boards` (e.g. `seeed-xiao-esp32c6`, `esp32s3-wroom-n16r8`, `esp32c3-supermini`, `esp32-devkit-v1`, `esp32s2-mini`).
- `output_path`: absolute path ending in `.bin` inside an existing private directory. Existing files and symlinks are refused. Written with mode `0600` on POSIX.
- `wifi_profiles`: 1 to 8 prioritized objects `{ssid, password}`. First reachable SSID wins on boot; failover rotates automatically.
- `ap` (optional): `{enabled, ssid, password, channel}`. **Disabled by default** (`enabled: false`). When enabled, password must be empty (open) or at least 8 characters, and channel 1–13.
- `tailnet`:
  - `hostname`: node name in tailnet (`[A-Za-z0-9][A-Za-z0-9-]{0,46}`, default `aguja-iot`).
  - `ctrl_host` (or `login_server`): empty for official Tailscale (`controlplane.tailscale.com`), or your own Headscale hostname / `https://` URL.
  - `ctrl_noise_pubkey_hex`: 64 lowercase hex chars when targeting Headscale (`tailscale debug` / `/key?v=116`); omit or empty for official Tailscale.
  - `auth_key`: authorised Tailscale or Headscale pre-auth key (required).
  - `derp_region`: integer 1–65535 (default `9` for official Tailscale, `999` for custom Headscale).
  - `exit_node_enabled`: boolean (default `true`).
  - `advertise_upstream_subnet`: boolean (default `true`).
  - `advertise_ap_subnet`: boolean (default `false`; only active when `ap.enabled` is true).
  - `extra_routes`: optional comma-separated CIDRs.
  - `dns_relay_enabled`: boolean (default `true`).
  - `dns_upstream`: IPv4 upstream DNS resolver (default `1.1.1.1`).
- `hw` (optional): `{antenna_external: false}` — only honoured on boards with `has_rf_switch: true` (such as Seeed Studio XIAO ESP32-C6).
- `agent` (optional): `{api_token, http_allow_lan, beacon_enabled, beacon_ip, beacon_port}`. If `api_token` is omitted or empty, a random 48-hex `agj_...` token is generated inside the NVS binary (not printed to stdout; provide your own private token in stdin if you want to keep a copy for `aguja-iot.py`).

#### Output and privacy

Returns sanitized metadata only:

```json
{
  "ok": true,
  "output_path": "/private/aguja-iot-nvs.bin",
  "bytes": 49152,
  "sha256": "...",
  "json_bytes": 412,
  "board_id": "seeed-xiao-esp32c6",
  "chip": "esp32c6",
  "firmware_profile": "esp32c6",
  "nvs_offset": "0x9000",
  "hostname": "aguja-iot",
  "ctrl_host": "headscale.example",
  "wifi_count": 1,
  "ap_enabled": false,
  "exit_node_enabled": true,
  "advertise_upstream_subnet": true,
  "dns_relay_enabled": true,
  "api_token_generated": false,
  "secret_values_returned": false,
  "device_written": false
}
```

Wi-Fi passwords, tailnet auth keys, Noise keys and API tokens are **never** printed to stdout or stderr. Note that the generated `.bin` file itself contains the cleartext NVS provisioning JSON required by the microcontroller on first boot: store it privately and delete temporary copies after flashing.

## Flashing and post-flash operation

- **Desktop Imager (recommended):** LA AGUJA Flash Imager **1.2.0** (Linux and Windows) bundles all 6 prebuilt `v1.4.0` ESP32-family firmwares, auto-detects connected boards by USB silicon (`esptool`), flashes firmware + generated NVS + boot verification, and offers 1-click flash erase. Windows builds bundle standalone Espressif `esptool.exe` and require zero Python installation.
- **Manual flashing:** Only after explicit owner confirmation of the target serial port, flash the matching `iot/prebuilt/<firmware_profile>/` binaries (`bootloader.bin` at `0x0` or `0x1000` depending on `flash_offsets.bootloader`, `partition-table.bin` at `0x8000`, `ota_data_initial.bin` at `0x15000`, `aguja_iot.bin` at `0x20000`) plus your private `nvs.bin` at `0x9000`.
- **Remote control after enrollment:** Once the node joins the owner's tailnet, see `references/iot/README.md` and `references/iot/aguja-iot.py` for remote telemetry, Wi-Fi profile editing, GPIO/PWM/ADC/I2C/SPI/UART/OneWire control, and dual-slot OTA updates over the tailnet IP.
