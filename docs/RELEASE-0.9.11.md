# LA AGUJA 0.9.11 · Bring your AI to boot, ready to investigate

## Windows Wi-Fi import

**Import active network now requests Windows UAC for the Wi-Fi query**, not for
the whole Imager. It reads only the connected WLAN profile using Windows APIs,
without localized `netsh` parsing. WPA/WPA2 personal, WPA3 personal and open
networks retain their mode. Cancellation is retryable; unreadable keys and
enterprise networks fail instead of reporting success with an empty password.

Credential transfer remains local: private owner/SYSTEM/Administrators ACL,
no password in process arguments or logs, and removal of the temporary result.
Existing BitLocker and USB flashing elevation remain available.

## Rescue Disk: native virtual lab and agent orientation

Included natively: **QEMU x86, QEMU GUI, qemu-img, qemu-nbd, OVMF/UEFI and SeaBIOS**.
KVM is used when the host permits it; TCG remains an alternative. No VM starts
and no optional specialist tools are downloaded automatically.

SSH connections receive a short introduction and offline guide paths, including
command-only agents. The banner does not inject bytes into command stdout or
file-transfer protocols. `aguja tools` shows the native virtualization inventory.
The canonical context is also supplied to local agent workspaces.

`/usr/share/aguja/TOOLBOX.md` provides resource-aware virtualization guidance and
**optional** starting points: REA/MCP, Rizin, Unblob, Volatility 3, btop, lnav,
bpftrace, stress-ng, restic and VisiData. Agents may research current alternatives
and selectively install what their mission needs. Mentions are not bundled
packages, a compatibility guarantee, or permission to modify unrelated systems.

## Español

**Tu IA en el arranque, con herramientas para investigar.** Importar red activa
pide UAC en Windows y conserva WPA3; no anuncia éxito con una contraseña vacía.
Rescue Disk incluye virtualización BIOS/UEFI sin instalaciones posteriores.
La bienvenida SSH y TOOLBOX orientan a humanos y agentes; REA y las otras
herramientas especializadas son sugerencias bajo demanda, no descargas incluidas.

## Delivery

Rescue Disk and Windows/Linux Imager **0.9.11** use the existing signed catalogue
pin. Agent Skill **1.0.2** remains compatible. Provider versions, owner privileges
and Codex Safe/YOLO policies are unchanged. Public factory media contain no
personal profiles. Older images and already-written USBs are not updated by
installing the Imager: prepare and flash a new image explicitly.

- [Rescue USB IMG.ZST](https://aguja.transcendenceia.net/releases/aguja-0.9.11-amd64.img.zst)
- [BIOS/UEFI ISO](https://aguja.transcendenceia.net/releases/aguja-0.9.11-amd64.iso)
- [Rescue SHA-256](https://aguja.transcendenceia.net/releases/SHA256SUMS-rescue-0.9.11.txt)
- [Optional tools guide](https://github.com/Transcendenceia/La-Aguja/blob/main/runtime/TOOLBOX.md)

VM validation does not certify every physical machine or provider login. KVM
availability is host-dependent; suggestions require their own prerequisites and
licences. Original screenshot provenance on the website is retained.

## Verification

- Real packaged Windows Imager on a Windows ThinkPad: limited user process,
  UAC cancellation preserves manual values, retry/approval succeeds, and imported
  WPA3 credentials match the connected native profile. Real credentials were not
  printed or included in screenshots. No physical USB was written.
- Four independent BIOS/UEFI boots and restarts, plain/encrypted profiles. Inside
  each booted live, native QEMU starts BIOS and UEFI lab machines under TCG;
  firmware, native utilities, offline guides and SSH banner are verified. Command
  stdout remains exact. Installed Codex Safe policy and owner sudo are preserved.
- Runtime: 171 tests, 170 passed and one skipped; Imager: 116 tests, 106 passed and
  10 Windows-specific tests skipped on Linux, supplemented by the real Windows
  checks above; website: 11 tests passed; packaged Electron: 38 checks passed.
- Seven Imager interface languages and eight website/documentation languages;
  public pages tested at desktop/mobile widths without account cookies.

Factory IMG SHA-256: `c6c463faf17e742ecf8a25d6bed95d684c4e39345040d71c298aa5cb4b909d25`
(3,926,917,120 bytes). Catalogue signatures and per-part hashes retain the existing pin.
