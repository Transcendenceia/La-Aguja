---
name: live-updates
description: Update a LA AGUJA RAM session, then explicitly persist the whole live with measured progress and recoverable encrypted snapshots.
metadata:
  version: "1.3.1"
---
# Session updates and independent global persistence

This operates an already booted LA AGUJA live, never target recovery disks.

1. Read `/usr/share/aguja/UPDATES.md`. Inspect `aguja update status --json`,
   `aguja persist status --json`, findmnt, lsblk, df and free; confirm the real boot
   medium and resource budget. An ISO/CD is not a writable persistence target.
2. Use `aguja update menu`: Check → No / Yes · update → review → install. CLI
   packages/harnesses/all also update RAM only. Never choose a persistent mode in
   Updates or silently write to USB on low RAM. A full signed Rescue release is
   prepared separately in RAM and committed only through Persist changes.
3. Observe measured native download/APT progress and the final result. Background
   jobs survive closing the update UI; partial failures preserve completed-item
   evidence and may leave partial RAM changes. CLI versions are not login proof.
4. Use **Persist changes** or `aguja persist save` only when saving is authorized.
   It captures the whole merged live, including manual modifications/deletions,
   installed tools, settings and native sessions, into an encrypted snapshot.
   Keep password input private; never send it via argv/environment or log it.
5. Confirm CFG/DATA are observed siblings of the removable boot USB. Keep mounted
   target disks, CFG/DATA, pseudofs, temporary files and processes out of root
   capture. Known volatile application data is encrypted inside the snapshot;
   workspace/profile stay separate. Staging must be encrypted too.
6. Follow actual scan counts, copy bytes, compression and verified bytes. Other
   phases show activity, not invented percentages. Verify/readback/sync before
   boot-selection commit. Failures must retain factory/previous boot and report
   incomplete work rather than success. Do not automatically restart.
7. At an authorized test boot verify saved files, deletions, packages and sessions
   from that selected generation. Test BIOS/UEFI independently. Rollback selects
   previous/factory; cleanup retires only inactive unmounted generations, never
   active/previous/running or owner data. Never recreate DATA growth markers on
   an existing USB. Do not publish private global snapshots.

## Rescue 1.1.1 power actions

`aguja power menu` offers Power off, Restart, Persist and power off, and Persist
and restart. Direct interactive choices are `aguja power poweroff`, `reboot`,
`persist-poweroff` and `persist-reboot`. They still ask for final confirmation;
Cancel/Escape/EOF do not approve. Update or save authorization alone does not
authorize a restart. Ordinary power actions discard unsaved RAM changes.

For an explicitly authorized combined action, enter/repeat the snapshot password
privately. The worker saves, reads back, syncs and finishes mount cleanup before
powering off/restarting. A failed save cancels power: the computer stays on and
previous boot remains available. Never bypass this by chaining `poweroff` after
a failed persistence command, or call the internal `worker` interface to avoid
interactive confirmation. Successful activation is not proof of the next boot.
