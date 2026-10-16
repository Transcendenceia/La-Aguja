# 1.0.2 candidate — portable identity and background updates

This is an unpublished candidate, not a release announcement.

## Changes

- Normal generation boot no longer reads/hashes the entire SquashFS. Selection,
  path and availability checks remain; full download/write/activation verification
  is unchanged. `aguja.verify=full` explicitly enables the slower boot diagnostic.
- Tailnet enrollment/reconnection no longer delays the local panel. The native
  Tailscale state is restored from this USB before starting its private daemon.
  A consumed/expired enrollment key does not replace a healthy restored identity.
- Initial enrollment and subsequent state changes request asynchronous USB
  checkpoints. Atomic write, file/directory sync and readback precede the saved
  indicator. Unchanged native state does not rewrite the USB. A retry timer and
  clean shutdown checkpoint cover transient failures.
- Automatic profiles reconnect without a new prompt. Existing encrypted profiles
  retain their explicit unlock; their node checkpoints use authenticated encryption
  with a RAM-only key derived from that same unlock. Changing computers does not
  change the USB's node identity. Server-side node expiry/revocation still applies.
- The update check starts about 15–20 seconds after boot without blocking the
  panel, which reports available updates or incomplete checks. It never installs
  automatically.
- Confirmed updates run as detached, lower-priority system services. Escape returns
  to other tools; reopening Updates reattaches to progress/result. Closing SSH or
  the menu does not cancel the job. Persistent updates still require successful
  verification before the next-boot selection is committed; no automatic reboot.
- Clean generation carryover includes only a fixed hash-verified public runtime
  list, never profiles, node state, credentials or the current RAM overlay.
- Fixed temporary chroot DNS permissions for APT's unprivileged download helper
  under background service umasks; executable initramfs-hook mode is preserved.

The existing Imager profile schema remains compatible. Its explanatory text now
distinguishes 1.0.2 persistent node state from older volatile images.

## Verification and deployment boundary

See `VALIDATION-1.0.2.md` for the exact final artifacts and observed tests.
This candidate does not modify an already provisioned USB merely by being built.
Neither publication nor physical flashing was performed as part of this work.

## Español

Arranque normal sin recalcular el hash completo; identidad propia del pendrive,
guardada y comprobada en segundo plano; aviso temprano de actualizaciones y
aplicación confirmada en segundo plano con progreso recuperable. El perfil
automático no añade desbloqueos. El cifrado conserva su desbloqueo ya existente.
Durante una escritura activa no se debe retirar el USB ni apagar el equipo.
