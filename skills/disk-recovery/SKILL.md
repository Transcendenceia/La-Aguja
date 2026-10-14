---
name: disk-recovery
description: Locate existing private disk recovery keys and live credentials on La Aguja, inspect metadata safely, and open an explicitly selected BitLocker or LUKS volume for an authorised task. Not for harvesting secrets, changing protectors or writing to disks without scope.
license: GPL-3.0-or-later
metadata:
  version: "1.0.0"
---

# Disk recovery and private credential handoff

Read `/usr/share/aguja/SECRETS.md` and `/usr/share/aguja/AGENT-CONTEXT.md` first. The machine is a live Linux platform; its own USB is not the target disk. Preserve the owner's instructions and use the user's language.

1. Inspect live state with `aguja secrets --json`, `aguja profile status --json`, `sudo aguja recovery status --json`, `lsblk`, `blkid` and `findmnt`. Output metadata only. No whole-HOME search, credential harvesting or `cat` of secret files.
2. Resolve exact target disk/partition by model, serial, capacity, filesystem and configured ID/UUID. Do not use CFG, DATA or the boot medium as a target. Do not try a recovery key on unrelated disks merely to validate it.
3. If the capsule is locked, let the owner enter the image password in the interactive `aguja profile unlock` or `sudo aguja recovery unlock` prompt. Never accept it via argv, shell history, log or public request template. This makes keys available in root-private RAM only and does not open a disk.
4. Use `sudo aguja recovery list --json` to select an entry. BitLocker: eight six-digit recovery-password groups. LUKS: exact existing passphrase, including spaces/Unicode. The ID/label and a valid key format are not proof of a working credential. Unknown/binary-keyfile encryption needs a separately verified compatible tool.
5. Within authorised read access, run `sudo aguja recovery open INDEX EXACT-BLOCK-DEVICE`. It passes the key through private stdin to cryptsetup, requires the configured LUKS UUID to match, and creates a read-only mapping without mounting. Don't print the decrypted cache; `export` prints only its private RAM path. For another authorised tool, extract only its required key inside a private process and pass it directly through a supported private input. Do not expose the value to the model/transcript.
6. Inspect/mount only within task scope, normally read-only with appropriate journal handling. Opening a mapping does not authorise fsck, repair, resizing, permanent decryption, protector changes or writable mounts. `--writable` is an explicit operational choice that needs the user's scope, not an automatic fallback.
7. Verify the requested observable outcome. Report separately: key located, capsule unlocked, mapping opened, filesystem read, data recovered. Close mappings after consumers stop. Keep only secret-free reports/rollback; reboot clears private RAM and relocks encrypted capsules.

Other live credentials are mapped in SECRETS.md. Prefer native provider launchers and services over manual token copying. Never publish personal images, private requests, decrypted caches, keys, sessions or signing material. Missing or expired credentials require the owner's existing login/secure entry route, not broad permission changes.
