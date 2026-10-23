# Rescue next · 2026-10-23

Owner: Angie. Baseline: 1b14ae5 (Rescue 1.0.2). Branch: feat/rescue-next-20261023.

## Scope

Rescue only: TranscendenceIA graphite/spectrum styling while retaining original Agujita artwork; task-oriented accessible menus; protected profile unlock before cockpit/SSH/agents using a real LUKS2 vault; automatic plain Imager profiles remain compatible. Canonical onboarding for local and SSH agents, hardware/resource preflight, scenario-aware backup choices, cloud/NAS credential plumbing without changing Imagers, broader firmware/network/display support.

No Imager/UI/provisioning changes, no publication, no personal USB writes, no Dell installation/reboots. Old AES capsules remain readable at the early boot gate and are explicitly identified as legacy, not LUKS. Conversion to a new vault is explicit; never silently rewrite an existing profile. Vault protects profile/recovery/cloud/tailnet settings, not all DATA/workspace. User explicitly permits automatic profiles; these remain unencrypted by design.

## Acceptance

- Original mascot assets unchanged; styled framebuffer and text fallback, menu reachable on short displays with matching pointer geometry.
- Protected boot cannot start SSH/getty/agents before successful gate; failed/cancelled authentication fails closed; no secret arguments/logs. Plain/no-profile boots work unchanged.
- Real file-backed LUKS2 provision/unlock, bad passphrase, reboot/relock tested in private VM; legacy gate tested separately.
- Agent entry points link current canonical mission/backup/boot guidance; no stdout contamination of binary SSH protocols.
- Resource inventory and backup recommendations use current observations; no internal mounts/writes/repair by inspection. Cloud metadata never exposes values; credentials absent from public image.
- Drivers/firmware from Debian packages, portable initramfs; no forced overclock, blanket tuning or universal hardware claims.
- Image BIOS/UEFI boots tested; source/rootfs/packed hashes agree; physical Wi-Fi/GPU still requires real-device validation.

## Rollback and evidence

Clean independent worktree; baseline image retained under ignored build/. All runtime/image changes in candidate only. QA uses synthetic data/disks. Evidence under operations/rescue-next-20261023. Deliver candidate with hashes; no automatic public release or overwrite of USB.

## State

Implementation complete; 126 focused regression checks ran (125 passed; 1 skipped because the chroot lacks GPT/FAT host tools). Native root unit dependency verification passes. Final image has 43 runtime modules matching source, installed root and packed squashfs. Original mascot sprites and Imager sources are unchanged.

Boot validation exposed an inherited path-unit ordering cycle and an orphaned graphical password retry through the systemd agent. Both were corrected before the final build: the splash now owns its password requests directly, with a console-agent fallback when Plymouth is unavailable. Migration task intentionally paused at user's change of priority.

Final-image KVM checks completed using only synthetic file-backed disks, 2 vCPUs and 2–3 GiB RAM:

| Case | Observed result |
|---|---|
| UEFI, new LUKS vault | SSH blocked before unlock and after wrong phrase; correct phrase opens profile and API fixture; next reboot locks again |
| BIOS, encrypted legacy capsule converted to LUKS | Verified conversion, one LUKS phrase only; wrong/correct phrase and second reboot pass; inner capsule is plain inside the vault |
| UEFI, unchanged encrypted legacy capsule | Early gate, wrong/correct phrase, owner SSH, materialization and second reboot pass; explicitly remains legacy AES |
| BIOS, automatic INI configuration | Boot and restart; all four clients offline/version; DHCP, configuration/DATA, key/password SSH, owner sudo, native Codex Safe sandbox, browser dependencies and local panel pass |
| UEFI, automatic plain capsule | No unlock question; profile loaded; hardware/plan/storage commands return expected metadata; rclone/restic/CIFS/NFS/SSHFS tools present |

Keyboard gate tests used real QMP key events after visually checking each actual Plymouth prompt. No passphrase was recorded in console evidence. The BIOS smoke also started included QEMU firmware paths for BIOS and UEFI; it did not pass through any physical disk.

Candidate IMG SHA-256: `4162e54c6bcff1d6057c5d01c7fad99ca73dfce6cd8dbb254ee0359cfd9ead9a`.
Compressed IMG SHA-256: `31c3f89a1d0e756dea7ad3543b4007e5cf5cb038c8c6ddd55f5b4f99d7f4094b`; streaming decompression matches the IMG. ISO and supporting hashes are in `dist/SHA256SUMS`. Evidence is under the ignored/private `operations/rescue-next-20261023/` directory. Images and previews were also copied to the owner's CachyOS task directory; no USB was written.

Physical Wi-Fi/GPU coverage, real cloud OAuth/transfers, model-provider inference, a headless console-password roundtrip, and installing a future signed public Rescue release are **not** certified by these checks. The signed official catalog was verified (latest 1.0.2); the 1.1.0 candidate correctly does not downgrade itself. No public release was published.

Official Rescue discovery precedes optional package/provider discovery. The updater verifies the signed catalog, binds the approved version to apply, validates staged images and preserves profile/DATA and previous/factory generations. A LUKS profile refuses an incoming generation without the early-gate capability. No public catalog or release was changed to manufacture an update test.
