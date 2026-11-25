# Getting started · LA AGUJA (Rescue 1.1.2 · Imager 1.2.0 · IoT ESP32 v1.4.0)

[Español](GETTING-STARTED.es.md) · [Documentation](README.md) · [IoT ESP32](IOT.md) · [Troubleshooting](TROUBLESHOOTING.md) · [Workflow ideas](SHOWCASE.md)

**Goal:** prepare your portable operations command — either a bootable **Rescue Disk 1.1.2** USB drive for x86-64 PCs, a pocket **ESP32 IoT v1.4.0** tailnet node, or both — using **Flash Imager 1.2.0** (Linux/Windows) or **Agent Skill 1.3.0** (headless). No LA AGUJA account or proprietary relay is needed. [Explore 20 platform missions](PLATFORM.md).

## 1. Gather the right things

- **Preparation PC:** a working Windows 10/11 or Linux computer with Internet for downloads and enough free space for the base image, decompression and private output.
- **For Rescue Disk USB (x86-64):** an x86-64 PC capable of USB boot (BIOS/UEFI) and a USB drive of **8 GiB+** whose real usable capacity exceeds the image size. Flashing replaces the selected USB.
- **For LA AGUJA IoT (ESP32):** any of the **11 supported ESP32-family boards** (`ESP32-C6`, `ESP32-S3`, `ESP32-C3`, `ESP32`, `ESP32-S2`), a USB data cable, Wi-Fi credentials and an authorised Tailscale or Headscale pre-auth key.
- **Permission & backups:** explicit authorisation for the target machine/network, a separate healthy destination before recovering data, and the owner's BitLocker/LUKS keys where applicable. LA AGUJA never bypasses disk encryption.

## 2. Download Flash Imager 1.2.0 and media

[Official download page](https://aguja.transcendenceia.net/en) · [Flash Imager 1.2.0 release](https://github.com/Transcendenceia/La-Aguja/releases/tag/v1.2.0) · [Rescue Disk 1.1.2 release](https://github.com/Transcendenceia/La-Aguja/releases/tag/v1.1.2) · [Agent Skill 1.3.0](https://github.com/Transcendenceia/La-Aguja/releases/tag/flash-imager-skill-v1.3.0)

| File | Purpose |
| --- | --- |
| `aguja-flash-imager-1.2.0-win-x64.exe` / AppImage / DEB / `.tar.gz` | Runs Flash Imager (both USB Rescue & ESP32 IoT modes; bundles 6 ESP32 v1.4.0 firmwares + Windows `esptool.exe`) |
| `aguja-1.1.2-amd64.img.zst` | Compressed x86-64 Rescue Disk USB image; decompress before manual import |
| `aguja-1.1.2-amd64.iso` | BIOS/UEFI ISO for VM/optical boot tests (not a configurable IMG) |
| `.aguja` | Reusable encrypted configuration profile for USB preparation |
| `aguja-flash-imager-skill-1.3.0.zip` | Standalone Agent Skills bundle (Node 22+, zero Electron/Python) for headless `.img` & ESP32 NVS v2 generation |

Prefer Flash Imager's signed catalogue: it verifies the Ed25519 signature, multipart chunks and complete SHA-256 automatically. For manual downloads use [Rescue 1.1.2 `.img.zst`](https://aguja.transcendenceia.net/releases/aguja-1.1.2-amd64.img.zst), [ISO](https://aguja.transcendenceia.net/releases/aguja-1.1.2-amd64.iso) and [GitHub SHA256SUMS](https://github.com/Transcendenceia/La-Aguja/releases/download/v1.1.2/SHA256SUMS).

Launch Flash Imager as your normal user; only physical USB writing (or Linux Wi-Fi import) asks for UAC/Polkit elevation. Windows builds are portable and require zero Node.js or Python. See [desktop/README.md](../desktop/README.md).

## 3. Path A — Prepare a Rescue Disk 1.1.2 USB

Follow the 7-step USB wizard in Flash Imager 1.2.0:

1. **Image:** select Rescue Disk `1.1.2` from the signed catalogue (or a decompressed local `.img`).
2. **Network & locale:** set live language, keyboard layout/variant, Ethernet DHCP/static and up to 16 prioritized Wi-Fi networks (`imager-profile-v2`).
3. **SSH access:** choose a hostname and your own SSH password or public key (never paste a private key). Factory credentials `aguja`/`aguja` should be replaced immediately.
4. **AI tools & extensions:** optionally configure Codex CLI, Claude Code, Antigravity or OpenCode, portable NAS/cloud destinations (Drive, OneDrive, Dropbox, S3, SFTP, SMB, WebDAV) and literal environment variables.
5. **Private network (Tailscale / Headscale):** optionally add an authorised auth/pre-auth key and HTTPS Headscale URL (leave empty for official Tailscale). Rescue `1.0.2+` / `1.1.2` persists tailnet identity cleanly across reboots.
6. **Encrypted disks:** optionally include BitLocker/LUKS recovery keys (in Windows, local BitLocker appears above manual keys).
7. **Create disk:** choose **Unlock at boot** encryption for any secret-bearing profile, verify the exact USB model/serial/capacity in the native confirmation dialog, and wait for full SHA-256 read-back verification.

Outside the wizard, **Profiles and USB** lets you save/reuse encrypted `.aguja` templates or edit an existing USB's `CFG` without reflashing, and **Updates** checks signed Imager releases.

## 4. Boot, unlock and verify your USB

Boot from the USB via your PC's firmware menu, unlock the profile if encrypted, and run:

```sh
aguja profile unlock   # encrypted profiles only
aguja status
aguja doctor
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS
findmnt
```

- Start an AI agent with `aguja login codex|claude|antigravity` (or `opencode auth login`) and `aguja agent codex` (Codex Safe uses `workspace-write` sandbox + human tool approval).
- Manage persistent RAM or USB updates with `aguja update menu` / `aguja update rollback`.
- Save work cleanly outside RAM before shutdown; use the power menu's verified persist-and-poweroff options when using encrypted global persistence.

## 5. Path B — Flash your first ESP32 IoT node

Switch the sidebar toggle in **Flash Imager 1.2.0** to **IoT · MCU** and follow the 4 steps:

1. **Board & USB detection:** plug in any supported ESP32 board (`ESP32-C6`, `ESP32-S3`, `ESP32-C3`, `ESP32`, `ESP32-S2`) and click **Auto-detect** — Flash Imager probes the chip over USB (`esptool`), identifies flash/PSRAM and picks the matching prebuilt `v1.4.0` firmware automatically.
2. **Wi-Fi profiles:** add 1 to 8 prioritized Wi-Fi SSIDs/passwords. **SoftAP is disabled by default** (can be enabled explicitly if you want a local NAT fallback AP).
3. **Tailscale / Headscale proxy:** enter node hostname, control server (official Tailscale or your Headscale host + 64-hex Noise pubkey + DERP region), auth key, exit-node/subnet-router/DNS-relay toggles and agent API token (auto-generated if blank).
4. **Flash & verify:** review the exact partition flash map (`0x0`/`0x1000` bootloader, `0x8000` partitions, `0x9000` pure-JS NVS v2, `0x15000` otadata, `0x20000` app), click **Flash board** and watch real-time serial boot verification. Use **Erase flash** anytime to wipe a test board cleanly.

Once the board joins your tailnet, operate it remotely with [iot/cli/aguja-iot.py](../iot/cli/aguja-iot.py) or its Dark Ops Web UI (`http://<node-tailnet-ip>/`). Full details in [IOT.md](IOT.md).

## 6. Path C — Headless preparation with Agent Skill 1.3.0

Extract `aguja-flash-imager-skill-1.3.0.zip` (Node.js 22+, no Electron or Python):

```sh
node /path/to/flash-imager/scripts/imager.cjs doctor
node /path/to/flash-imager/scripts/imager.cjs iot-boards
node /path/to/flash-imager/scripts/imager.cjs iot-nvs < /private/iot-request.json
node /path/to/flash-imager/scripts/imager.cjs prepare < /private/usb-request.json
```

The skill stops at verified local `.img` / `.bin` artifacts (`device_written: false`) and never flashes physical USB or serial ports automatically. See [harnesses.md](../skills/flash-imager/references/harnesses.md) and [iot.md](../skills/flash-imager/references/iot.md).

Next: [20 platform missions](PLATFORM.md) · [IoT architecture](IOT.md) · [Troubleshooting](TROUBLESHOOTING.md) · [Imager 1.2.0 notes](RELEASE-IMAGER-1.2.0.md).
