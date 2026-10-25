# LA AGUJA — credential and recovery map

This guide contains **locations and procedures, not credentials**. It applies to the running live platform, not to the preparer's computer. Start with:

```sh
aguja secrets --json
sudo aguja recovery status --json
aguja profile status --json
```

These commands return metadata only. Do not `cat`, copy to chat, commit, screenshot or log any file containing keys, provider sessions or passwords. Retrieve only the required field **inside a private process** and send it directly to the destination tool through its supported private input. A file tool that shows its contents to the model/transcript is not a secret-input mechanism.

## Disk recovery keys from another computer

- `/config/aguja-recovery.json`: supplemental BitLocker/LUKS capsule written by Flash Imager; independent of which OS prepared the USB. In encrypted mode it is authenticated ciphertext. The identifier/label selects a candidate; format validation does not prove a matching disk.
- `/run/aguja-recovery/keys.json`: decrypted working keys, root-owned 0600 in a root-only 0700 directory, **RAM only**. Its companion `state.json` binds it to the current capsule and key-file hashes. Stale/tampered cache is rejected.
- `/config/bitlocker.json`: legacy backup on older preparations. The current Imager writes an empty compatibility stub and uses the supplemental capsule instead. Inspect legacy structure privately only when the current capsule is absent, and never overwrite/re-publish a legacy key dump.
- `/config/aguja-recovery.py`: older standalone helper supplied by the preparer; fallback for Rescue 0.9.11. New live images include the native `aguja recovery` interface. Prefer the installed helper, not executable code from an untrusted USB.

For a protected profile, the early boot gate asks for its password locally without echo, before cockpit, SSH or agents. Matching recovery keys also load into private RAM. A recovery capsule with its own different password uses `sudo aguja recovery unlock`. Plain capsules load at boot. Neither action opens, mounts, repairs or changes a target disk.

```sh
sudo aguja recovery list --json               # index, type, label and ID; no keys
sudo aguja recovery export                    # prints only the private RAM path
sudo aguja recovery open 1 /dev/disk/by-uuid/EXACT-UUID
```

Identify the target first with `lsblk`, `blkid`, `findmnt`, model/serial/capacity. Never select the boot USB/CFG/DATA as a rescue target. `open` creates `/dev/mapper/aguja-recovery-1` read-only by default; a matching configured LUKS UUID is required. It does not mount a filesystem. Choose the actual entry and device, not the example placeholders. Changing to writable (`--writable`), mounting, repairing, resizing or decrypting permanently requires the owner's task to cover that operation. Close the mapping with `sudo cryptsetup close aguja-recovery-1` after use; check consumers first.

BitLocker entries are 48-digit recovery passwords, not PINs, login passwords or protector IDs. LUKS entries are existing passphrases/recovery keys with exact spaces and Unicode; arbitrary binary keyfiles, VeraCrypt and hardware encryption are not implemented by this interface. Use compatible tools and private key handling for other formats. Never put a key in `cryptsetup`, `dislocker`, `manage-bde`, shell or process arguments.

## Other existing secrets

| Purpose | Canonical location | Use |
| --- | --- | --- |
| Portable boot profile | `/config/aguja-profile.json` | Unlocked at the early boot gate; never dump the capsule |
| Legacy literal Wi-Fi/SSH settings | `/config/aguja.conf` | Read only the needed setting privately; may be stale for an encrypted profile |
| Literal custom environment | `/home/aguja/.config/aguja/custom-env.json` | Native launchers merge literal data; provider-card keys take precedence; never print its values |
| NAS/cloud configuration | `/config/private/storage/rclone.conf` or `/run/aguja-storage/storage/rclone.conf` | `aguja storage status --json` selects the actual location; vault or private RAM, not plain DATA |
| API settings for native agents | `/home/aguja/.config/aguja/provider-env.json` | Native launchers call `profile.provider_environment`; don't print `env` or `/proc/*/environ` |
| Codex file login | `/home/aguja/.codex/auth.json` | Use the existing native login; absence may mean no portable session |
| Claude file login | `/home/aguja/.claude/.credentials.json` | Native CLI consumes it; don't dump refresh/access tokens |
| Antigravity imported login | `/home/aguja/.gemini/antigravity-cli/antigravity-oauth-token` | File-based imported login, not a promise about OS keychains |
| OpenCode native login | `/home/aguja/.local/share/opencode/auth.json` | Use native CLI/settings, not a general export |
| Tailnet enrollment | `/run/aguja-tailnet-private/auth.key` | Root-private service input; do not re-enroll or change ACLs just to test presence |
| Active Wi-Fi keyfile | `/etc/NetworkManager/system-connections/aguja-wifi*.nmconnection` | NetworkManager consumes it; don't print PSK/EAP credentials |
| USB-specific SSH host key | `/data/ssh/ssh_host_ed25519_key` | SSH server identity; not a client login or disk recovery key |

Locations do not imply presence, validity or permission to use a credential. Encrypted profile secrets remain unavailable before unlock and in RAM afterwards; persistent HOME is disabled for protected profiles. A reboot clears the RAM cache and relocks the recovery/profile capsules. Do not create plaintext copies on DATA, in reports, project files, shell history or public release assets. Display/activity redaction is a last layer, not permission to print secrets.

The live recovery skill is `/usr/share/aguja/skills/disk-recovery/SKILL.md`. Read it when a mission requires disk access or credential use. Codex, Claude, Antigravity and OpenCode share this map through the canonical agent context; owner instructions elsewhere in AGENTS.md/CLAUDE.md/GEMINI.md remain authoritative.

## Español

`aguja secrets --json` muestra ubicaciones y estado, nunca valores. Las claves manuales viven cifradas en `/config/aguja-recovery.json`; tras desbloquear se usan en `/run/aguja-recovery/keys.json` (RAM privada, 0600). El desbloqueo temprano del perfil abre también el resguardo compatible; `sudo aguja recovery unlock` permite abrirlo por separado. `list` no muestra las claves y `open` abre el mapping en solo lectura, sin montar ni reparar. Conserva espacios exactos de LUKS y no confunde la clave numérica de BitLocker con su identificador. No copies secretos a conversación, logs, DATA ni GitHub.

## LUKS profiles and cloud storage (1.1)

`/config/aguja-profile.luks` contains a real LUKS2/ext4 vault. Once opened it is
mounted root-only at `/config/private`, before cockpit, SSH and agents. Its copies
of profile/INI/recovery/tailnet settings are authoritative. DATA/workspaces are
not encrypted by this feature. Plain automatic Imager profiles remain unencrypted;
legacy encrypted capsules still unlock at boot and are explicitly reported as AES.
`aguja storage status --json` locates cloud credentials without reading values.
Rclone configuration persists only inside an open vault; otherwise RAM-only.
No cloud credentials/accounts ship in Rescue. LUKS gate protects owner entrypoints,
not a defense against an attacker replacing the unsigned live medium.
