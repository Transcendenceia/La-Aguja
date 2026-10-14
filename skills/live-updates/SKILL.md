---
name: live-updates
description: Check notifications and update the booted LA AGUJA system, native harnesses or live generation persistently on its own USB; preserve configuration, secrets, previous boot and owner workspace.
metadata:
  version: "1.0.0"
---
# Persistent live updates

This operates an already booted 1.0 USB, not the preparer's installed OS and not target recovery disks. An update check does not authorize installing, rebooting, writing to internal disks or changing provider authentication.

1. Read `/usr/share/aguja/UPDATES.md`, then inspect `aguja update status --json`, `findmnt`, `lsblk`, `df -h /data`, `free -h` and the exact boot medium. CFG and DATA must be mounted siblings of this removable boot USB. A file image/ISO without enough writable DATA is not an update target.
2. `aguja update check --json` checks signed LA AGUJA releases, official OS repositories and the four native providers. It returns metadata, not keys; partial/offline results are not a clean bill of health. Notifications check only, never install.
3. For the owner's requested scope choose `aguja update packages`, `harnesses`, `all` or `release`, or the interactive `menu`. Explain the concrete plan/resources and preserve active/factory/previous generations. Run one update at a time. No direct apt/npm/agy self-update outside this manager if persistence is required: ordinary RAM-overlay changes are temporary.
4. The manager starts from clean squashfs, not decrypted RAM HOME or the current overlay. It verifies native archives/catalogue hashes, installs in a private mount/PID namespace without host block devices, packs a kernel/initrd/root generation and activates only verified, synced bytes. Never copy profiles, recovery caches, sessions, machine-specific network keys or agent work into that root. Provider version is not authentication or inference proof.
5. Report the generation, verification receipt and **reboot required** separately. Do not reboot automatically. At the owner's authorized next boot verify actual version/CLI/kernel/package changes and configuration/DATA preservation on the target machine. BIOS/UEFI and changed device topology require independent tests for a release claim.
6. `rollback` selects previous or factory for next boot; it does not shrink DATA or erase credentials/workspace. `cleanup` retires only inactive, unmounted task-owned generation trees, never active/previous/running generations or personal files. If disk/RAM are insufficient, stop the update, preserve current boot and report the observed budget instead of filling the USB.

Existing USBs made before 1.0 need the 1.0 boot infrastructure; a skill update alone cannot install it. The desktop CFG editor preserves data and updates, but does not upgrade the kernel/root. A fresh 1.0 Windows-written USB initializes DATA once at boot on the exact boot disk; do not recreate that marker on an existing USB to resize someone else's storage.
