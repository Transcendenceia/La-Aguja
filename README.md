<p align="center"><img src="branding/brand-lockup.png" width="700" alt="LA AGUJA Rescue Disk with Agujita, our mascot"></p>

<p align="center"><strong>A small entry point. Full control.</strong><br>Rescue Linux with the tools your AI agent needs.</p>

**English is the primary repository language. [Español](README.es.md) is the secondary language.**

**LA AGUJA Rescue Disk** is experimental x86-64 live Linux for a USB drive. Boot before the installed operating system, inspect hardware, recover authorised data and work locally or over SSH. The complete Rescue 0.9.9 factory image includes Codex CLI, OpenCode, Claude Code and Antigravity, independently of whether you prepare credentials. Third-party clients retain their own licences and terms; see NOTICE.md. Cloud AI needs Internet and your own provider account; traditional tools can work offline.

**Current versions:** Flash Imager **0.9.9** · Rescue Disk image **0.9.9**. [Release notes and downloads](https://github.com/Transcendenceia/La-Aguja/releases/tag/v0.9.9).

**Local console history:** use the mouse wheel to review long CLI output; wheel down returns to the prompt, or press Esc. Local sessions retain up to 10,000 terminal lines in RAM, without saving a transcript. SSH keeps its normal terminal behaviour.

[Website and downloads](https://aguja.transcendenceia.net/en) · [User guide](https://aguja.transcendenceia.net/en/docs) · [Latest Imager release](https://github.com/Transcendenceia/La-Aguja/releases/latest) · [TranscendenceIA](https://www.transcendenceia.net/proyectos/la-aguja-rescue-disk)

<p align="center"><a href="https://ko-fi.com/transcendenceia"><img src="branding/donation/support-en.svg" width="360" alt="Buy us a coffee · Ko-fi"></a></p>

## Start here

### Let your AI agent prepare the image

Alongside the desktop installers, [Flash Imager Agent Skill 1.0.1](https://github.com/Transcendenceia/La-Aguja/releases/download/v0.9.9/aguja-flash-imager-skill-1.0.1.zip) packages the same file-image preparation engine without Electron. Ask your agent to configure language, networking, SSH and optional AI/tailnet profiles; it creates a personalised `.img`, verifies the profile and hashes, and leaves the base image untouched. It does **not** write a USB automatically or rebuild the distribution.

The open `SKILL.md` format has [installation guidance for Codex, Claude Code, OpenCode, Gemini CLI, Cursor and OpenClaw, plus manual loading for other harnesses](skills/flash-imager/references/harnesses.md). A file/shell-capable agent and Node.js 22+ are required. Format compatibility is not a claim that every harness or OS was tested. [ZIP](https://github.com/Transcendenceia/La-Aguja/releases/download/v0.9.9/aguja-flash-imager-skill-1.0.1.zip) · [tar.gz](https://github.com/Transcendenceia/La-Aguja/releases/download/v0.9.9/aguja-flash-imager-skill-1.0.1.tar.gz) · [SHA-256](https://github.com/Transcendenceia/La-Aguja/releases/download/v0.9.9/SHA256SUMS-flash-imager-skill-1.0.1) · [Instructions and JSON interface](skills/flash-imager/SKILL.md).

### Desktop and boot workflow

1. Back up the USB before writing. **Windows has no integrated USB backup yet**; use an external tool. Linux offers an optional verified full-device backup.
2. Download Flash Imager for Windows or Linux. Choose the image from its signed catalogue, or import a decompressed `.img`.
3. Configure language, keyboard, Ethernet/Wi-Fi, hostname and your own SSH password or public key. AI preparation and private networking are optional.
4. Encrypt the configuration capsule when it contains secrets; keep the unlock phrase outside the USB.
5. Confirm the exact USB model, capacity and serial number. Wait for full read-back verification and test booting on your intended hardware.
6. Boot the USB, unlock an encrypted profile with `aguja profile unlock` and inspect disks before changes.

```sh
aguja status
aguja doctor
lsblk -o NAME,SIZE,MODEL,FSTYPE,LABEL,MOUNTPOINTS
```

The Imager runs on the preparation computer; Rescue Disk runs on the computer being examined. An EXE or AppImage is not the rescue image. Booting does **not** automatically mount, repair, install or write to internal disks.

## Local or remote rescue, without a project account

No LA AGUJA account is required for the website, documentation, downloads or preparation. Images and the signed catalogue are hosted on our official website; Imager and source are on GitHub.

- **Local:** use the rescue cockpit, console and diagnostics directly.
- **LAN:** connect with `ssh aguja@IP` using the actual address and verify the host fingerprint.
- **Optional tailnet:** configure your own Tailscale/Headscale key. The live registers after boot, networking and profile unlock. It does not enrol your preparation PC or use our relay or hosted console.

Normal OpenSSH over your authorised tailnet is the default. Tailscale SSH is an advanced, separate option needing compatible SSH policies. Your control plane and ACLs determine client access.

Tailnet identity is in RAM and registers again after reboot. A one-use key may not permit another boot; use valid, scoped reusable keys for repeated boots, and remove old nodes/keys afterwards. This option requires image support for `tailscale-profile-v1`.

## AI authentication and permissions

Locally, `aguja login codex`, `aguja login claude` or `aguja login antigravity` can open sandboxed Chromium on the official sign-in flow with the original PTY. Copying focuses the console; paste explicitly with Ctrl+Shift+V. Closing returns to the original terminal. No QR or automatic consent.

OpenCode keeps `opencode auth login`. SSH/serial/headless sessions use native provider methods; a remote localhost callback is not automatically forwarded. API keys and selective import of compatible portable sessions are separate paths. The complete keychain, history, hooks and MCP configuration are not copied. A portable file does not prove session validity.

The `aguja` account has **unrestricted sudo/root**. The launcher proposes Safe task confirmation by default; YOLO requires explicitly choosing Unsafe. Neither mode removes root access. A read-only instruction is not a sandbox. Provider costs, quotas and transmitted data depend on your account and terms.

## Configuration and storage

- **AGUJA_CFG:** FAT32; edit `aguja.conf` from another operating system.
- **AGUJA_DATA:** ext4 workspace and USB-specific SSH host key.
- Read-only squashfs root plus RAM overlay; no automatic internal-disk modification.
- `persistent_home=no`: HOME and tokens disappear at reboot.
- `persistent_home=yes`: HOME and tokens persist **unencrypted** on USB.
- Capsule encryption protects a locked profile, **not all AGUJA_DATA** or loaded secrets against root. Private images and `.aguja` templates may contain credentials.

Factory SSH user and public password: `aguja`. Set your own password or public key. A blank password with a public key enables key-only access; without a key it preserves factory access. `aguja password` persists a change; `sudo passwd aguja` only changes the running session. Do not publish personal keys or profiles.

## Included tools

| Area | Tools |
| --- | --- |
| Base | Debian 13 amd64, live-boot, systemd; no conventional desktop |
| Network | NetworkManager, DHCP, Wi-Fi, OpenSSH, Avahi/mDNS |
| AI | Personal complete image: Codex CLI, OpenCode, Claude Code and Antigravity; authentication optional |
| Recovery | GNU ddrescue, TestDisk/PhotoRec, rsync |
| Hardware | smartctl, nvme-cli, hdparm, lshw, PCI/USB inventory |
| Storage | ext4, Btrfs, XFS, NTFS, exFAT, FAT; LUKS, LVM, RAID, BitLocker tools requiring the correct key |
| Operations | Zsh, tmux, Python, curl, git, jq, ripgrep, nano |

**LA AGUJA** is the brand and is never translated. **Agujita**, the chrome needle with amber eyes and curled moustache, is the mascot. Technical identifiers remain unchanged. [Brand language](docs/BRAND-LANGUAGE.md).

## Documentation in eight languages

| Language | Website | User guide | Repository |
| --- | --- | --- | --- |
| **English** | [Open](https://aguja.transcendenceia.net/en) | [Read](https://aguja.transcendenceia.net/en/docs) | [Guide](docs/en/USER-GUIDE.md) |
| **Español** | [Abrir](https://aguja.transcendenceia.net/es) | [Manual ampliado](https://aguja.transcendenceia.net/es/docs) | [Manual](docs/es/USER-GUIDE.md) |
| Français | [Ouvrir](https://aguja.transcendenceia.net/fr) | [Guide](https://aguja.transcendenceia.net/fr/docs) | [Guide](docs/fr/USER-GUIDE.md) |
| Deutsch | [Öffnen](https://aguja.transcendenceia.net/de) | [Anleitung](https://aguja.transcendenceia.net/de/docs) | [Anleitung](docs/de/USER-GUIDE.md) |
| Português | [Abrir](https://aguja.transcendenceia.net/pt) | [Guia](https://aguja.transcendenceia.net/pt/docs) | [Guia](docs/pt/USER-GUIDE.md) |
| Italiano | [Aprire](https://aguja.transcendenceia.net/it) | [Guida](https://aguja.transcendenceia.net/it/docs) | [Guida](docs/it/USER-GUIDE.md) |
| Nederlands | [Openen](https://aguja.transcendenceia.net/nl) | [Handleiding](https://aguja.transcendenceia.net/nl/docs) | [Handleiding](docs/nl/USER-GUIDE.md) |

| 简体中文 | [打开](https://aguja.transcendenceia.net/zh) | [指南](https://aguja.transcendenceia.net/zh/docs) | [指南](docs/zh/USER-GUIDE.md) |

Each operational guide covers 26 stages: preparation, SSH, encryption, BitLocker, AI, recovery, troubleshooting and closure. The original extended Spanish reference remains available. Print the current page for a PDF in its language; the separately released historical PDF is Spanish. Screenshots retain actual versions and synthetic-test provenance.

[Imager development](desktop/README.md) · [Document index](docs/README.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

## Build and test

On Debian 13 amd64 with sudo, Internet and at least 15 GB free:

```sh
sudo apt-get install debootstrap squashfs-tools grub-pc-bin grub-efi-amd64-bin xorriso mtools dosfstools gdisk jq fonts-dejavu-core ffmpeg nodejs npm
npm ci
npm run branding
sudo bash scripts/build-rootfs.sh
sudo bash scripts/build-image.sh
python3 -m unittest discover -s tests -v
```

Outputs include ISO, IMG, package inventory and checksums. Never guess a physical device for a write test; use synthetic images and virtual USBs.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests
cd desktop
npm ci
npm test
cd ../server
npm test
```

Translations live in `server/locales/`. Rebuild with `python3 scripts/build-site-locales.py`. Do not translate brands, commands, keys or paths. Keep technical limits consistent across languages.

## Tested scope and limits

Preparation, package and VM results are version-specific, not certification of every physical computer. Read-back checks bytes, not all boot firmware. No universal signed Secure Boot chain or recognised Windows Authenticode signature is currently offered. Windows also lacks integrated USB backup and automatic AGUJA_DATA expansion on larger media. Check provider login and inference independently from installed CLIs or synthetic screenshots.

## Open source

Project-owned code, documentation and artwork: **GPL-3.0-or-later**. Earlier MIT grants remain valid. Third-party components retain their licences and terms; the entire medium is not relicensed as GPL. [LICENSE](LICENSE) · [NOTICE](NOTICE.md) · [Publishing](docs/PUBLISHING.md).

## Support the project

LA AGUJA helps recover computers, memories and work. If it helped you, [buy us a coffee on Ko-fi](https://ko-fi.com/transcendenceia) to help keep this free project alive. Donations are optional; all rescue tools remain available.
