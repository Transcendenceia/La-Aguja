# Tailnet persistence and backup entry review

Owner: Angie. Requested review: connected tailnet shown as pending despite Imager
provisioning; inspect the purpose, label and placement of backup planning.

Scope: runtime tailnet persistence/status and focused regression checks. Preserve
the running node, native keys, control-plane registration and SSH sessions. No
logout, re-enrollment, host/VM reboot, reflash or release publication.

Acceptance: connection and durable identity status distinguished; encrypted
capsule checkpoint configuration retained when applying the same imported extended
preferences; incompatible RAM-only preferences must never overwrite a previous
identity or store new secrets in plain CFG. Verify authenticated SSH and encrypted
checkpoint readback on the actual live without restarting the daemon.

## Existing release defects to carry forward

- Fresh DATA initialization rejects fixed/SCSI presentation as intended, but its
  post-unlock failure is hidden by a generic boot error and may redisplay the gate.
  Linux Imager expands DATA without completing the factory initialization marker.
  Fix the state/error handling in a separately tested release; retain the guard
  against initializing arbitrary fixed disks. VM USB-removable presentation is a
  workaround, not a published product fix.
- Extended tailnet preferences are applied after encrypted-capsule persistence
  configuration. With no LUKS vault, `tailnet_config.boot_apply()` deletes
  `persistence.json` even when the imported preferences match the capsule. The
  encryption key remains, checkpoints skip successfully due to their condition,
  and the public status stays pending although the native daemon is connected.

## Backup entry findings

The active cockpit action `backup` runs `aguja plan`, showing JSON hardware
inventory and generic destination preference/requirements. It does not schedule,
copy, measure a selected source or produce a completed backup. The GTK
`page_backup` implementation creates a mission note but is unreachable from the
current single-task Desk page allowlist. These are different, incomplete user
flows, not one backup assistant.

Recommendation: move this guidance under Missions and methods as “Choose a backup
destination” / “Elegir destino de respaldo”. Keep hardware JSON in CLI/agent
diagnostics; show a readable guide in the user menu and clearly distinguish
source-data backup from “Persist changes” (the Rescue live itself). Do not imply
that a destination choice authorizes or executes a copy. No UI relocation applied
until this review establishes the desired user flow.

## Live evidence and follow-up

Initial metadata: native daemon Running/Online and has a tailnet IP; persistence
settings missing, encrypted key present, checkpoint absent; timer/path active but
oneshot condition skips. Private diagnostics contain no credentials or node IDs.
Live remediation: backed up the two runtime modules and private checkpoint
configuration in a root-only `/run` directory. Applied only those modules in RAM,
reconstructed checkpoint configuration from the already authorized encrypted
capsule, and verified the corrected preference path retains its encryption.
Saved the native identity as an encrypted USB checkpoint and decrypted/read it
back; it matches the current native state, with the same machine key and unchanged
capsule. Rechecked after timer activity: connected=true, saved=true, encrypted=true,
checkpoint_matches_native=true. No daemon restart, re-enrollment, logout or reboot.

The live runtime hotfix is volatile; the encrypted checkpoint is durable. The
published image and Imager are unchanged, so their boot path still needs this fix
in the next tested release. Rebooting the original image is not claimed fixed.

Validation: 54 focused tests passed, zero skipped (identity, Tailscale service,
extended profile, raster display and translations). The new regression reproduces
missing checkpoint settings against the published `v1.1.1` implementation.
Initial build-host dependency failures were resolved in an isolated temporary
test environment; no host packages changed. Actual live LAN SSH authenticated;
a new tailnet-IP SSH attempt from Cachy timed out, so this review does not claim
an independent tailnet SSH end-to-end test. User-reported tailnet SSH and daemon
Running/Online are distinct evidence. No control-plane or ACL changes attempted.

Source UI labels now distinguish live connectivity from saved/pending/error/RAM
identity persistence, with complete catalog translations. They are not injected
into the user's active cockpit process or published. The owner was using the
tools submenu during observation; no keystrokes were sent to change that view.

Private operational evidence: `operations/tailnet-backup-review-20261025/`
in the assistant workspace (`live-repair.json`, `final-check.json`, test logs).
Rollback in the live: `/run/aguja-tailnet-review-20261025/`; restore only the
backed-up runtime/config files if required, without replacing native daemon state.

Next: agree the readable backup-destination guide flow, then integrate this fix
and the separately recorded DATA error-handling correction into a new version.
