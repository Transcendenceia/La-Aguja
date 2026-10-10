<p align="center"><img src="branding/brand-lockup.png" width="700" alt="LA AGUJA Rescue Disk with Agujita, our mascot"></p>

<p align="center"><strong>Your AI. Your machine. Before the installed OS.</strong><br>A bootable Linux workbench for building, configuring, experimenting and recovering.</p>

<p align="center"><a href="https://aguja.transcendenceia.net/en">Download</a> · <a href="docs/GETTING-STARTED.md">Get started</a> · <a href="docs/PLATFORM.md">Explore missions</a> · <a href="docs/README.md">Documentation</a> · <a href="README.es.md">Español</a></p>

**Flash Imager 0.9.9 · Rescue Disk 0.9.9 · Experimental · x86-64**
English is the primary repository language; [Spanish](README.es.md) is secondary. The website and operational guides remain available in **eight languages**.

**Your computer does not need an installed OS to start its next project.** LA AGUJA boots an independent Linux from USB, including on a machine with a blank disk. Bring **Codex CLI, OpenCode, Claude Code and Antigravity**, root-capable Linux tools and optional SSH to the hardware: install and configure systems, bootstrap a server, build software, extend the session into a virtual lab, migrate storage or recover data. Recovery is one mission, not the whole product.

**Your working PC → Flash Imager → your live USB → the machine you want to build on.**

The live session uses a **writable RAM overlay over a read-only USB image**; it does not copy the entire USB into RAM or run AI in firmware. No internal disk is changed automatically at startup. Save useful outputs to chosen storage: RAM is temporary, but deliberate writes to disks persist. Cloud AI needs your account and networking; conventional tools can work offline. [Explore eight ambitious missions](docs/PLATFORM.md).

No LA AGUJA account, proprietary relay or hosted terminal. Cloud AI still requires Internet, your own compatible provider account and available quota. Third-party licences and terms remain separate: [NOTICE](NOTICE.md).

> **Real control, real responsibility.** The `aguja` account has unrestricted sudo/root. Safe mode asks for task confirmation; it is **not a sandbox**. Booting does not automatically mount, repair, install or write to internal disks. Identify the source and destination, preserve a backup and approve changes before making them.

## See the actual product

![Flash Imager 0.9.9 on Linux with English selected](server/public/docs-images/099/imager-en.png)

*Real packaged Linux Imager 0.9.9. English is selected; some Spanish labels remain in this build. No account authentication or physical USB write is demonstrated.*

![Rescue Disk 0.9.9 cockpit in a Spanish QA VM](server/public/docs-images/099/rescue-dashboard.png)

*Real Rescue 0.9.9 capture in a synthetic QA VM, in Spanish. The visible hostname and QEMU NAT address are test data—not an address to connect to. A running cockpit is not evidence of a completed rescue.*

[Eight real captures, captions and evidence limits](docs/SCREENSHOTS.md).

## Choose your first mission

| You want to… | Start with… | What you should finish with |
| --- | --- | --- |
| Install and configure Linux on a blank SSD | [System builder](docs/PLATFORM.md#1-from-blank-ssd-to-a-configured-linux) | A configured OS and verified first boot |
| Run guests without installing a host OS | [Pocket datacenter](docs/PLATFORM.md#2-a-pocket-datacenter-on-a-pc-with-no-host-installation) | A resource-budgeted lab with QEMU added and guest images saved |
| Use a spare PC for a LAN demo or workshop | [Pop-up services](docs/PLATFORM.md#3-a-pop-up-lan-workshop-or-demo-station) | A tested temporary service and clean shutdown |
| Build and package software outside the disk environment | [Software factory](docs/PLATFORM.md#4-a-software-factory-independent-of-the-disk) | Reproducible scripts, test results and exported artifacts |
| Prepare a NAS or application server | [Bare-metal bootstrap](docs/PLATFORM.md#5-bootstrap-a-nas-or-application-server-from-bare-metal) | Installed services verified from an authorised client |
| Migrate storage or test a bold configuration | [Migration and experiments](docs/PLATFORM.md#6-a-migration-workshop-outside-both-systems) | Verified data, rollback and repeatable recipes |
| Diagnose or recover an existing system | [Recovery workflows](docs/SHOWCASE.md) | Observable results and retained backups |

These are **workflow ideas and prompt templates**, not customer testimonials or fabricated success stories. Each example includes tools, expected deliverables and stop conditions.

## Get started

1. **Prepare on a working Windows or Linux PC.** [Download Flash Imager](https://github.com/Transcendenceia/La-Aguja/releases/tag/v0.9.9). The EXE/AppImage is the preparer, not the rescue image.
2. **Select the image.** Use the signed catalogue, or decompress a manually downloaded `.img.zst` before selecting the `.img`. The ISO is useful for VM boot tests.
3. **Set language, keyboard, networking and SSH.** Replace the public factory SSH password `aguja` with your own password or public key. AI and tailnet preparation are optional.
4. **Protect the profile.** Use an encrypted capsule for secrets. Replace the public initial unlock phrase `aguja` and keep the new phrase outside the USB. This does not encrypt persistent HOME or all AGUJA_DATA.
5. **Back up, then flash the exact USB.** Compare model, serial and actual capacity. Windows needs an external USB backup; Linux offers an optional verified full-device backup. Wait for full read-back verification.
6. **Boot and inspect.** Unlock locally if required; confirm the live system and identify every disk before considering changes.

```sh
aguja profile unlock   # only if the profile is encrypted
aguja status
aguja doctor
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS
```

[Detailed first-boot guide](docs/GETTING-STARTED.md) · [Troubleshooting](docs/TROUBLESHOOTING.md)

### Let an agent prepare the image

**Flash Imager Agent Skill 1.0.1** packages the real file-image preparation engine without Electron. A file/shell-capable agent with **Node.js 22+** can configure language, network, SSH and optional AI/tailnet profiles, verify the profile and hashes, and leave the base image unchanged. It does **not** automatically flash a USB or rebuild the distribution.

[ZIP](https://github.com/Transcendenceia/La-Aguja/releases/download/v0.9.9/aguja-flash-imager-skill-1.0.1.zip) · [tar.gz](https://github.com/Transcendenceia/La-Aguja/releases/download/v0.9.9/aguja-flash-imager-skill-1.0.1.tar.gz) · [SHA-256](https://github.com/Transcendenceia/La-Aguja/releases/download/v0.9.9/SHA256SUMS-flash-imager-skill-1.0.1) · [Install for your harness](skills/flash-imager/references/harnesses.md)

Installation guidance covers Codex, Claude Code, OpenCode, Gemini CLI, Cursor, OpenClaw and manual loading. Portable format support does not certify every harness or OS.

## A workbench, not a one-click promise

| Area | Included capabilities |
| --- | --- |
| Live base | Debian 13 amd64, BIOS/UEFI paths, read-only squashfs + RAM overlay; no conventional desktop |
| Recovery | GNU ddrescue, TestDisk/PhotoRec, rsync |
| Hardware | smartctl, nvme-cli, hdparm, lshw, PCI/USB inventory |
| Storage | ext4, Btrfs, XFS, NTFS, exFAT, FAT; LUKS, LVM, RAID, BitLocker tooling with the correct key |
| Connectivity | NetworkManager, Ethernet/Wi-Fi, OpenSSH, Avahi/mDNS, optional own tailnet |
| AI clients | Codex CLI, OpenCode, Claude Code, Antigravity; installation is independent of credential preparation |
| Operations | Zsh, tmux, Python, curl, git, jq, ripgrep, nano |
| System building | debootstrap, arch-install-scripts, partition/filesystem tools and GRUB utilities |

**Extend it for the mission:** QEMU/KVM, container engines, compilers and SDKs can be added when compatible with the live kernel, hardware and resource budget. They are not promised as bundled or as one-click workflows. The platform provides an independent Linux and capable agents, not a built-in hypervisor, local AI model or automatic fleet orchestrator. [Requirements, prompts and deliverables](docs/PLATFORM.md).

**New in 0.9.9:** local console mouse-wheel history, up to 10,000 lines in RAM without saved transcripts; scroll down to the prompt or press Esc to return. SSH keeps the client terminal behaviour. Imager checks working-space availability before copying a private image; Windows can choose another work folder. [Release notes](docs/RELEASE-0.9.9.md).

### Local console or SSH

Connect using `ssh aguja@IP` with the actual live address and verified host fingerprint. Optional Tailscale/Headscale registers the live after boot, networking and profile unlock—not the preparation PC. Normal OpenSSH over tailnet is the default; Tailscale SSH is a separate advanced option needing compatible policy.

Tailnet identity is **RAM-only** and registers again after reboot. A one-use key may not work twice. For repeat boots use appropriately scoped, valid reusable keys under your administration; remove obsolete nodes and keys afterwards. Your ACLs and control plane determine access.

### Sign in to your AI provider

Locally, `aguja login codex`, `aguja login claude` or `aguja login antigravity` can open sandboxed Chromium on the official sign-in flow with the original PTY. Copying focuses the console; paste explicitly with Ctrl+Shift+V. OpenCode uses `opencode auth login`. No automatic consent and no QR in this login flow.

SSH/serial/headless sessions use native provider methods; a remote localhost callback is not automatically forwarded. API keys and selective portable-session import are alternatives, not proof of valid authentication. The complete keychain, history, hooks and MCP configuration are not copied. Provider costs, quotas and data transmission remain your responsibility.

### Know what persists

| Location or option | Behaviour |
| --- | --- |
| AGUJA_CFG | FAT32 configuration, including editable `aguja.conf`; plaintext values are readable from the USB |
| AGUJA_DATA | ext4 workspace and USB-specific SSH host key; not wholly encrypted by capsule protection |
| `persistent_home=no` | HOME and session tokens disappear on reboot |
| `persistent_home=yes` | HOME and tokens persist **unencrypted** on the USB |
| Encrypted capsule | Protects the locked profile, not loaded secrets against root |

Encrypted profiles force `persistent_home=no` at boot. The unencrypted persistence option applies to older/plaintext configurations.

Private images and `.aguja` templates may contain credentials. Never publish them. `aguja password` persists an SSH password change; `sudo passwd aguja` only changes the running session. Blank SSH password **with** a public key enables key-only access; **without** a key it preserves public factory access.

## Documentation and languages

| Read next | English | Español |
| --- | --- | --- |
| Prepare and boot | [Getting started](docs/GETTING-STARTED.md) | [Primeros pasos](docs/GETTING-STARTED.es.md) |
| Build, configure and experiment | [Platform missions](docs/PLATFORM.md) | [Misiones de la plataforma](docs/PLATFORM.es.md) |
| Prompts, tools and deliverables | [Showcase](docs/SHOWCASE.md) | [Ejemplos](docs/SHOWCASE.es.md) |
| Diagnose by layer | [Troubleshooting](docs/TROUBLESHOOTING.md) | [Solución de problemas](docs/TROUBLESHOOTING.es.md) |
| Real product captures | [Gallery](docs/SCREENSHOTS.md) | [Galería](docs/SCREENSHOTS.es.md) |
| All references and history | [Documentation index](docs/README.md) | [Índice](docs/README.es.md) |

Website and operational guides: [English](https://aguja.transcendenceia.net/en/docs) · [Español](https://aguja.transcendenceia.net/es/docs) · [Français](https://aguja.transcendenceia.net/fr/docs) · [Deutsch](https://aguja.transcendenceia.net/de/docs) · [Português](https://aguja.transcendenceia.net/pt/docs) · [Italiano](https://aguja.transcendenceia.net/it/docs) · [Nederlands](https://aguja.transcendenceia.net/nl/docs) · [简体中文](https://aguja.transcendenceia.net/zh/docs).

## Develop and verify

[Build and test guide](docs/DEVELOPMENT.md) · [Imager implementation](desktop/README.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Publishing](docs/PUBLISHING.md)

Published 0.9.9 evidence includes BIOS/UEFI VM boot/reboot with and without encrypted profiles, virtual-wheel history checks, runtime/Imager tests and packaged-app checks. These are **version-specific results**, not fresh tests performed for this README or certification of physical hardware. No physical USB write, universal hardware support or real-account AI inference is established by these screenshots. There is no universal signed Secure Boot chain or recognised Windows Authenticode signature. Windows also lacks integrated USB backup and automatic AGUJA_DATA expansion.

## Open source, with a name and a face

Project-owned code, documentation and artwork are **GPL-3.0-or-later**. Earlier MIT grants remain valid; third-party components keep their own licences and terms. The entire medium is not relicensed as GPL. [LICENSE](LICENSE) · [NOTICE](NOTICE.md).

**LA AGUJA** is the brand; **Agujita**, the chrome needle with amber eyes and a curled moustache, is the mascot. Names and technical identifiers are not translated. [Brand language](docs/BRAND-LANGUAGE.md) · [TranscendenceIA](https://www.transcendenceia.net/proyectos/la-aguja-rescue-disk).

## Support the project

Every machine can become the start of something new. If LA AGUJA helps you build, experiment or recover, a coffee helps keep the project moving. Donations are optional; the tools remain available.

<p align="center"><a href="https://ko-fi.com/transcendenceia"><img src="branding/donation/support-en.svg" width="360" alt="Buy us a coffee · Ko-fi"></a></p>
