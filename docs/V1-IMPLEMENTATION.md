# 1.0 implementation contract

Owner scope: Imager update discovery/download (never silently run a new executable), reusable encrypted profiles, read/edit an existing LA AGUJA USB configuration without reflashing, a dedicated Encrypted disks step before Create disk, optional notifications and persistent OS/live/harness updates, aligned agent skills. Preserve owner capability and credentials. Heavy builds and guests run serially within measured disk/RAM budgets.

## Persistence model

Immutable bootable generations in AGUJA_DATA, each containing its own kernel, initrd and squashfs. Build from the active clean squashfs, not the running credential-bearing RAM overlay. System packages are installed in a private mount namespace/chroot of that clean staging root; provider sessions, keys, profiles and workspace never enter a system generation. Verify and sync a completed generation before activating its boot pointer on AGUJA_CFG. Factory and previous generation remain bootable, with an explicit rollback action. Configuration, recovery capsules and DATA remain separate. A release image does not automatically update an old USB's boot loader.

Only siblings of the current boot disk are eligible; no global label search for mount/write. When a generation boots from DATA, bind its existing medium mount as /data rather than mounting the same partition again. No change to host disks, no unattended reboot. Space and memory failures must preserve the active generation. Persisted package installations take effect on the next boot into their generation; transient apt commands outside this manager are still RAM-only.

## Desktop

Signed update metadata under the existing Ed25519 release key, exact repository/platform/size/digest validation and atomic downloads. Configuration edits use a narrow, identity-bound elevated helper on the selected removable USB's CFG partition. Preserve unrelated files and encrypted provider imports. Back up the original stored capsule bytes (never a decrypted backup), verify replacement/readback and keep an interruption-recoverable transaction. A stale USB/config snapshot must reject overwrite.

## Validation gates

Meaningful tests for tampered metadata, corrupt downloads, interrupted transactions, changed USB identity/config, encrypted read/edit/roundtrip, preservation of unrelated bytes, generation rollback, cold boot on different virtual firmware/device topology, package/harness persistence and no secret spill. Final Linux/Windows packages and BIOS/UEFI images must match the frozen source, then publish versioned artifacts and independently verify public downloads. Physical writing/boot and provider inference are separate evidence.

## Build isolation

Native CLI verification and setup run inside private mount/PID namespaces with minimal character-device binds. Never recursively bind host /dev into the main/service namespaces. Do not stop unrelated services or purge old root trees retained in their namespaces; use a separate clean factory path (AGUJA_ROOT under project/build) and preserve the old tree.
