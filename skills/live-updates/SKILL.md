---
name: live-updates
description: Check and explicitly select temporary RAM or USB-persistent LA AGUJA updates, track real progress, and preserve configuration, secrets, previous boot and owner workspace.
metadata:
  version: "1.0.1"
---
# Interactive and persistent live updates

This operates an already booted LA AGUJA live, not the preparer's installed OS or target recovery disks. A check never authorizes installing, rebooting, writing to internal disks or changing provider authentication.

1. Read `/usr/share/aguja/UPDATES.md`. Inspect `aguja update status --json`, `findmnt`, `lsblk`, `df -h /data` and `free -h`. Observe the exact boot medium. Persistence requires CFG and DATA as verified mounted siblings of that removable USB, with enough space/RAM. A plain ISO is not a writable update destination.
2. Prefer `aguja update menu`: Check → installed/available list → each row **No / Yes · RAM / Yes, persistent** → review → explicit apply. Every check resets choices to No. RAM choices are temporary and do not alter the USB boot selection; persistence takes effect next boot, also on another computer. A complete signed Rescue release is persistent-only, separately from other persistent components. Required dependencies can change alongside selected packages.
3. `check --json` queries official repositories, providers and the signed catalogue, caching in RAM. Partial/offline sources are not an all-current verdict. Notifications only check. The menu shows download bytes/APT measurements when available and otherwise activity by stage, then a result that waits for Back to menu. Do not infer percentages from elapsed time or claim completion before verification/commit.
4. Advanced `packages`, `harnesses`, `all` and `release` CLI operations remain explicitly persistent; the menu provides per-item/session choices. Explain the actual scope and resource budget first. Run one manager operation at a time. Temporary package updates require a live RAM overlay, minimal devices and read-only USB views in their private namespace. Do not promise rollback of partially installed RAM packages.
5. Persistent roots originate from the verified selected pending/running generation or factory, never decrypted HOME or RAM overlay. The manager verifies archives/catalogue, installs in a private mount/PID namespace without host block devices, packs kernel/initrd/root and commits only verified synced bytes. Only fixed manifest-verified public updater code/docs can accompany that clean root. Never copy profiles, recovery keys, sessions, network identities or owner work into it. CLI version is not provider authentication/inference proof.
6. Report temporary changes, saved generation, verification and **reboot pending** separately. No automatic restart. At an authorized next boot verify the actual versions/kernel and preservation of CFG/DATA. BIOS/UEFI and changed device topology are separate checks. Existing pre-1.0 USBs need new boot infrastructure; CFG editing or a skill update alone cannot supply it.
7. `rollback` selects previous/factory for next boot. `cleanup` retires only inactive unmounted generations, never active/previous/running or personal files. If resources or validation fail, preserve the previous boot, report the observed error and avoid filling the USB. Do not recreate the fresh-media DATA initialization marker on an existing USB.
