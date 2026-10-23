# LA AGUJA · Mission control for agents

Read this on arrival, whether you are an external SSH agent or a local harness.
You are running on real hardware from a live medium, not inside a safe VM.
LA AGUJA is an intervention platform: rescue is one mission, not its limit.

## Arrival: observe before choosing a method

1. Read `aguja context`, owner instructions in the workspace, and `SECRETS.md`.
2. Run `aguja hardware --json`, `aguja status --json`, `aguja tools`,
   `sudo -n id`, `free -h`, `df -h` and `findmnt`. `aguja plan --json` adds
   scenario-dependent backup choices; it does not perform a backup.
3. Identify CPU architecture/extensions, usable RAM, free storage, BIOS/UEFI,
   Secure Boot where relevant, GPU/network driver and `/dev/kvm` accessibility.
   `lspci -nnk`, `lsusb`, `rfkill list`, `nmcli device status`, `ip route` help.
   A missing wireless device may need firmware; a blocked radio is not bad DNS.
4. Map the live medium from `/proc/cmdline`, `findmnt /run/live/medium`,
   `lsblk -o PATH,PKNAME,MODEL,SERIAL,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS`.
   Disk letters change. Do not identify the target only by `/dev/sda` or label.
5. State the mission, exact target, desired outcome and downtime. Inspect installed
   OS metadata read-only if needed. For ext4 use `ro,noload`; for XFS use
   `ro,norecovery`. Ordinary `ro` can still replay a journal. Never run filesystem
   repair on a mounted filesystem or SMART self-tests as a routine inventory step.
6. Review BACKUP.md. Present feasible options with measured capacity and the best
   recommendation. User decisions already made remain valid; do not ask repeatedly.

`/run/aguja-hardware.json` is a boot snapshot, not eternal truth. Re-run inventory
before a resource-heavy operation. Do not dump all environment variables or logs:
credentials may be present. SSH stdout must remain byte-clean for tools/protocols.

## Choose the approach, not just a command

| Mission | Useful method | Decisive check / limit |
|---|---|---|
| Revive an unbootable Linux | Read-only inventory, image if failing, chroot with correct bind mounts, GRUB/EFI and fstab inspection | Boot actual repaired disk in its firmware mode; preserve EFI entries and rollback |
| Migrate Linux to another distribution | Fresh target root + selective home/config restore; native installer or documented debootstrap workflow | Do not copy `/etc` wholesale, UID mismatch, incompatible dconf, old repositories or kernel modules |
| Build a server from bare metal | Native distro bootstrap, service configuration, network/storage plan | Running services, cold boot and owner access; RAM changes alone do not install anything |
| Convert a physical system to a VM | ddrescue/qemu-img to another disk, snapshot/overlay, QEMU with correct BIOS/UEFI | No concurrent host/guest access to the same writable filesystem; Windows licensing/drivers may intervene |
| Boot an installer without another USB | Internal staged ISO with supported GRUB loopback, PXE/network boot if available, or carefully planned KVM-assisted install | ISO-specific official boot contract, RAM/resources, network handoff; never assume every ISO supports loopback |
| Windows boot/data repair | Read-only NTFS/BitLocker assessment, wimlib for images; official WinPE/Windows tools for native repairs | Do not claim Linux tools can replace DISM/BCDBoot or bypass encryption; preserve recovery keys |
| Disk dying or accidental deletion | Minimize reads, ddrescue + persistent map to healthy disk; TestDisk/PhotoRec on copy | Never shrink/repair/reinstall the failing source first; no same-disk backup |
| Investigate malware or extract firmware | Offline images, read-only mounts, isolated VM/snapshot; specialist tools under demand | No executing suspect binaries directly on live hardware; control network exposure |
| Build portable development/lab | Containers/SDKs on request or VM; workspace on sufficient DATA/other authorized storage | Overlay RAM is finite; tools/accounts/licenses are not magically included |
| Migrate encrypted volumes/RAID/LVM | Inventory cryptsetup/LVM/mdadm; supplied keys via private stdin | No automatic assemble/write/unlock of unrelated disks; validate actual recovery path |
| Diagnose GPU/network/firmware | Drivers and firmware inventory, DHCP/radio/DNS separately; nomodeset fallback | Firmware package presence does not certify every Wi-Fi/GPU model |

Research current official methods when uncertain. Included binaries are listed by
`aguja tools`; TOOLBOX.md separates included tools from optional ideas. Do not
present a potential mission as a previously successful demonstration.

## Virtualization is a tool, not a shortcut around resource ownership

QEMU x86, qemu-img, qemu-nbd, OVMF and SeaBIOS are included. Prefer KVM only when
`/dev/kvm` is usable; otherwise TCG is slower. Hardware inventory proposes conservative
CPU/RAM ceilings from actual availability. Recheck while running: leave RAM for live,
SSH, decompression and disk caches. Bound vCPUs, memory, image growth and threads.
Use file-backed images/overlays for experiments; bind services to loopback unless
remote exposure is requested. Device passthrough requires exact identity and exclusive
ownership; a mounted disk must not also be writable in QEMU or qemu-nbd.

## Boot handoff: prove the new environment before proceeding

Before any reboot, record target identities, firmware mode, boot entry/UUID, ISO hash,
expected OS/kernel/source and remote reconnection method/host fingerprint. Save a
recovery route independent of the environment you are replacing. Coordinate downtime.
A consumed one-shot GRUB entry or a responding IP proves neither installer boot nor
successful repair. After boot check `/etc/os-release`, `/proc/cmdline`, `findmnt /`,
`lsblk`, helper/service state and authenticated SSH with the expected identity.
If it returns to Rescue, stop installation writes and diagnose the actual boot path.
Never repeat reboot attempts without new evidence. Never claim a migration complete
from a successful copy, package install or GRUB command alone.

## Paths and access

- `/usr/share/aguja/`: canonical offline guides, capabilities and version.
- `/data/workspace`: persistent work if DATA is mounted; otherwise HOME workspace.
- `/config`: boot USB configuration; `/config/private`: mounted LUKS vault when used.
- `/run/aguja-platform`, `/run/aguja-recovery`: runtime private material, not to print.
- `aguja storage status --json`: credential locations/metadata only; never tokens.
- `aguja profile status --json`: automatic, legacy AES or LUKS protection, not a claim
  that every workspace/data partition is encrypted.

The LUKS gate precedes cockpit/SSH/agents. An automatic Imager profile intentionally
needs no passphrase. Unlocking credentials does not grant a new mission or permission
for unrelated disks, accounts or publishing. Preserve full owner access and harness
Safe/Unsafe behavior. Inspect live results, report limitations and retain rollback.
