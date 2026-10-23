# LA AGUJA · Backups adapted to the mission

First run `aguja hardware --json` and `aguja plan --json`. These are read-only
observations/recommendations, not an automatic partitioner or backup policy.

## Offer real choices

Estimate selected data bytes, expected growth, free destination bytes, disk health,
encryption state, available network bandwidth and restoration time. Do not assume
that an entire disk must be copied when the goal only needs home/configuration;
do not promise a full rollback from a selective archive. For damaged media prefer
an image and ddrescue map before repair, with a healthy separate destination.

| Choice | When it fits | Explain before using |
|---|---|---|
| Another internal disk | Healthy separate physical disk with sufficient free space | Confirm model/serial and preserve existing contents; another partition is not another disk |
| External disk | Owner can provide one | Confirm destination, filesystem, capacity and permissions; never overwrite a disk merely because it is USB |
| NAS / SSH server | Reliable reachable storage and recovery access | Capacity, credentials, quota and independent reconnect method; mount only the approved share |
| Cloud | Owner approves provider/account and data transfer | Ask first; bandwidth, quota/cost, privacy and restore feasibility; use client-side encryption for sensitive data |
| Rescue USB DATA | Owner approves available space | Never use live/CFG/generation directories; reserve room for runtime updates and mapfiles; isolate this job under workspace |
| Temporary partition on source disk | Healthy filesystem, safe supported shrink, unmounted, enough space | Only with owner agreement; partition metadata backup first; power-loss risk; does not protect against physical failure; never for a failing source |
| No backup | Owner explicitly chooses data loss for the exact target | Explain what is lost and what cannot be recovered; silence and urgency are not consent |

Present only feasible choices and recommend one. If an authorization already covers
the action, proceed without repeating permission prompts. If no destination fits,
ask for the missing choice instead of improvising destructive repartitioning.

## What to preserve

For migrations: personal files, dotfiles, UID/GID/ACL/xattrs, package inventory,
services, repositories, selected `/etc`, SSH host keys if intentionally preserving
identity, and partition/EFI metadata. Restoring account/password databases, whole
`/etc`, drivers or desktop settings across distros can break the new OS: keep a copy
and restore compatible portions. Include a manifest of exclusions. Never dump
credential files to an agent transcript. Archive ACL/xattrs/numeric IDs using tools
that support them; remember FAT destinations cannot represent Unix metadata directly.

Use rsync/tar/zstd for file copies, ddrescue for unstable media, restic for encrypted
versioned backups, rclone for cloud transport, SSH/rsync for NAS hosts. Compression
is not encryption. Rclone password obscuring alone is not strong at-rest encryption;
use a LUKS vault for stored credentials and restic or rclone crypt for data when needed.

## Credential preparation, ready without new Imagers

`aguja storage status --json` shows metadata only. `sudo aguja storage configure`
opens native rclone configuration (Google Drive, S3, OneDrive, WebDAV, SFTP and more).
No provider is contacted by status. No automatic upload, account enrollment or
billing. In a LUKS profile the file is `/config/private/storage/rclone.conf` (0600,
root-only directory). Without a vault it is `/run/aguja-storage/storage/rclone.conf`:
RAM only, lost on shutdown. Never place cloud tokens in the public image or INI.

For transfers pass only the configuration path, e.g. use `sudo rclone --config PATH`
with the approved remote/path and operation. Native OAuth may need a browser or
another device; follow its exact instructions, never paste tokens into the model.
SMB/NFS mounts use cifs-utils/nfs-common; SFTP uses SSH keys and strict host checking.
Do not put passwords in argv, shell history or mount URLs. Put a credentials file
inside the vault if a CIFS mount needs it. Do not disable host/certificate checks.

## Verify, restore, then retire temporary copies

Check tool exit status, manifest/count/bytes and hashes when appropriate. Confirm
an archive can be read and restore representative files into an isolated destination
with permissions intact. Source/destination hashes agree only on bytes, not on
whether every intended file was included. Keep a recovery path until the actual
new system boots and important data/services are usable.

A backup on Rescue USB is temporary: after successful verified restoration, remove
only this job's backup (and its private credentials if transient), respecting any
owner request to retain it and unrelated workspaces. Never clean it at boot or on
an error, never delete broad `/data` trees. Same-disk temporary partitions are removed
or reclaimed only after restoration and owner approval of that final layout.
If verification fails or the mission is interrupted, retain the copy and report why.
