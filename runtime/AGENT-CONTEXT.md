# LA AGUJA — canonical instructions for AI agents on the live system

You are on **LA AGUJA Rescue Disk**, an x86-64 Linux live booted from removable
media, NOT the operating system installed on the target computer. **Agujita**
is the original mascot. Technical identifiers remain `aguja` and `AGUJA_*`.
Rescue, investigation, deployment, development and configuration are possible
missions: understand the operator's objective before assuming a repair task.

These instructions apply equally to installed agents and external agents
connected through SSH/MCP. Read owner/project instructions too. Use the
operational ODD method in `/usr/share/aguja/ODD.md`; do not install global hooks
or external memory services as a side effect. Canonical guidance is English;
**respond in the operator's requested language, otherwise the configured live
locale** (`locale`, `/etc/default/locale`). Keep commands and paths literal.

## AI and Internet

There is **no local model runtime or bundled model**. AI functionality requires
Internet, a supported remote provider and the operator's authorized account.
An IP address does not prove Internet, successful OAuth or provider inference.
Local file, disk, backup and diagnostic tools can work offline, but the full
agent-assisted platform requires connectivity. No provider accounts or tokens
are shipped. Never infer valid access from an installed CLI or a copied profile.

## First observation and authority

The `aguja` owner has full passwordless `sudo -n`; this live is not a container.
Native Safe/Unsafe harness modes are independent of sudo. Codex Safe uses its
workspace-write sandbox, network restrictions, human approvals and PreToolUse
confirmation. Unsafe/YOLO is explicit. Preserve these choices and the owner's
access. Permissions do not authorize work outside the requested objective.

Start with bounded read-only observations:

    aguja status --json
    aguja doctor --json
    aguja hardware --json
    aguja plan --json
    aguja tools
    lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS
    findmnt
    sudo -n id
    date

Current observations override this guide and memories from another machine.
Identify exact sources/destinations by model, serial, capacity, filesystem and
firmware before writes. Do not mount or repair internal disks automatically.
Use `aguja run --label "Short public task name" -- COMMAND` for visible tasks;
stdin scripts remain private. Never put secrets in labels, argv or output.

## Storage boundaries

- `/` is squashfs with a RAM overlay. Changing it does not change the installed OS.
- `/run/live/medium` is the running live media, NEVER a rescue target.
- `/config` is the same USB's AGUJA_CFG; literal settings are private.
- `/data` is AGUJA_DATA on the live USB, not an internal target partition.
- `/data/workspace` persists job artifacts if DATA is mounted. HOME is RAM unless
  the operator chose `persistent_home=yes`; that choice alone is not encryption.
- Protected profiles unlock before cockpit/SSH/agents. LUKS protects the profile
  vault at `/config/private`, **not all DATA**. Legacy/automatic profiles still work.
- `aguja profile status --json` reports protection state; never print its secrets.
- SSH host identity persists in `/data/ssh`; config backups are root-private in
  `/data/config-backups`. Preserve owner settings and recovery material.

`aguja desk` opens the on-demand local graphical Desk. `aguja files` opens its
file page with Yazi, previews, editing and explicit target mounts. Mounted host
files are accessible; ext4 read-only mounts use noload, XFS uses norecovery.
Read-only is not forensic hardware write-blocking. Never run fsck on a mounted
filesystem or launch an unknown binary merely to preview it. Avoid host/VM
simultaneous writes to one volume. QEMU/KVM/TCG, qemu-img, qemu-nbd, OVMF and
SeaBIOS are available; read TOOLBOX.md and measure RAM/space before using them.

## Connectivity, browser and accounts

    aguja network --wait
    aguja wifi
    nmcli device status
    rfkill list
    ip route
    aguja desk network
    aguja desk tailnet
    aguja tailscale

The local Desk configures Wi-Fi, network profiles and Tailscale/Headscale:
HTTPS login URL, native browser enrollment or auth-key file, hostname, DNS,
routes, exit nodes, LAN access, tags, SSH, shields, SNAT and forwarding. Route
and exit-node advertisement also require server approval/policy. Control and
transport are distinct. Changing network settings may disconnect remote work.
Do not publish WAN ports or enable tunnels merely because a feature exists.
The public factory SSH password is `aguja`; a custom password/key may replace
it. Use `aguja password` or Desk settings without printing custom credentials.

`aguja web` / `aguja browser` uses the same unprivileged browser opener as native
agent OAuth: Helium by default, Chromium for compatibility. Browser cookies
stay in RAM, downloads go to the chosen path. Local OAuth retains the original
CLI PTY and callback; never substitute a model's browser session for the owner's
account. Headless SSH retains native login handoff; graphical Desk needs local
console. No login or inference is implied by browser/CLI availability.

    aguja agent codex
    aguja agent antigravity
    aguja agent claude
    aguja agent opencode

Use tmux for remote sessions. The physical cockpit shows bounded SSH activity,
not keystrokes or credential values. The monitor grants no authority and is not
a permanent transcript. Do not rely on redaction to recognize every new secret.

## Missions, backups and credentials

Read MISSIONS.md and BACKUP.md before installation, P2V, repair or bulk transfer.
Compare separate internal/external disk, NAS/SSH, cloud (owner choice), Rescue
DATA (temporary), same-disk staging (healthy source only, not a disaster backup)
and explicit no-backup. Measure capacity and agree restoration/retention. Do
not insist on a single destination regardless of actual hardware/resources.
Clean only this job's backup after verified restoration and the owner's choice.

`aguja desk cloud` provides provider fields, file/directory import, native
rclone OAuth, destination checks and read-only browsing. `aguja storage` reports
metadata; `aguja storage configure` is the terminal alternative. Credentials are
stored in the unlocked LUKS vault or RAM, never newly persisted in plain DATA.
Do not upload/synchronize automatically or mistake a cloud listing for a restore
test. Verify quotas, bandwidth, costs and data privacy before transfers.

Before using credentials, read SECRETS.md and the disk-recovery skill. Run
`aguja secrets --json` and `sudo aguja recovery status --json` for metadata only.
Disk recovery material is materialized in root-private RAM; select labels/IDs
without loading keys into the model context. Pass only the necessary value
privately to its native consumer, never logs, history, chat or a repository.
Opening a recovery mapping is read-only by default; it does not mount/repair.
Managed AGENTS.md/CLAUDE.md/GEMINI.md pointers preserve owner instructions.

## Updates and result verification

`aguja update check --json` only checks. The Updates page offers individual or
All RAM / All persistent selections. Full Rescue requires persistence; All RAM
selects components and clearly leaves the full image out. All persistent stages
the signed official Rescue (if newer) plus selected components before activating
the resulting generation. Read UPDATES.md and the live-updates skill first.
Factory, previous generation, profiles and workspace remain separate. Activation
is for next boot, never an automatic restart. Plain apt changes in RAM do not
persist. Do not update a target OS or reboot without the requested scope.

Back up recoverable state before delicate changes. Obtain authorization for new
irreversible scope, keep already-authorized work moving, and verify observable
files/services/boot rather than exit codes alone. Save sanitized evidence and
rollback before reboot. Guide: `/usr/share/aguja/QUICKSTART.md`; tools:
`aguja tools`; docs: https://aguja.transcendenceia.net/docs.
