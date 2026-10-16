# Validation — Rescue Disk 1.0.2 (2026-10-16)

These are the final factory-image tests performed before publication. The
feature-validation task used synthetic identities only and did not change a
production Headscale configuration, ACL or node. Personal USB deployment is a
separate operation; private deployment records are not release assets.

## Exact final artifacts

| Artifact | SHA-256 |
| --- | --- |
| aguja-1.0.2-amd64.img | `3a6d37cf5f2aa649862c53fe4bdcda4da012979df66fd56cb59e9f2d2a878c5a` |
| aguja-1.0.2-amd64.iso | `668e8318e5b4d0aa488434ae454edfa57a4b99851f16234de49879fbda06957f` |

Build outputs used an `aguja-personal-` filename prefix; publication renames
these factory artifacts without changing their bytes. They contain no prepared
owner profile or enrolled node identity. This is not an image of a user's USB.

The build checked current source against installed root and packed SquashFS,
including the new units, Python runtime, update worker and fast boot guard.
The transferred IMG checksum matched before native tests. The existing Imager
profile schema was used without changing its provisioning protocol.

## Code and UI checks

- Python unittest: **235/235 passed**, no skips, using an isolated test environment,
  explicit sbin PATH and isolated generated locale data.
- Imager translation/catalog tests: **4/4 passed**.
- Shell syntax and git whitespace checks passed; new systemd units verified.
- Cases include no full root read on normal boot, explicit full-mode corruption
  rejection, identity encryption/restoration, no rewrite for unchanged state,
  failed sync preserving the old checkpoint, profile mismatch refusal, consumed
  enrollment key not reused while restored state reconnects, detached job
  reattachment and interrupted-task reporting.

## Native final-image matrix

One QEMU/KVM guest at a time, 2 GiB RAM, USB mass-storage emulation backed by
fresh disposable image copies. Each boot used another UUID/MAC. Native Tailscale
1.102.5 enrolled against an isolated loopback-only Headscale 0.29.5 controller
using single-use test keys. The controller CA was a RAM-only test fixture.

| Profile | Firmware | Generation | Node ID | IPv4 | Kernel + userspace |
| --- | --- | --- | --- | --- | --- |
| Automatic | BIOS | Factory | 3 | 100.64.0.3 | 9.722s |
| Automatic | UEFI | Factory | 3 | 100.64.0.3 | 8.833s |
| Automatic | BIOS | Saved update | 3 | 100.64.0.3 | 15.608s |
| Encrypted | UEFI | Factory | 4 | 100.64.0.4 | 6.018s |
| Encrypted | BIOS | Factory | 4 | 100.64.0.4 | 6.104s |

All five boots passed native Online status, exact native machine-identity
fingerprint comparison within each medium, saved checkpoint readback/decryption
matching current native state, and the automatic update-check timer. Checkpoints
were verified **before shutdown**, not merely saved by shutdown hooks. Automatic
profiles required no unlock; encrypted ones used their existing console unlock.
The same automatic node survived booting the newly updated generation.

Timing is systemd's kernel/initramfs + userspace measurement, not firmware/GRUB,
manual unlock, complete network readiness or a physical USB speed benchmark.

## Real background persistent update

- Updated `libexpat1` from `2.8.3-1~deb13u1` to `2.9.0-1~deb13u1`.
- Completed, hashed and committed a clean persistent generation in **74.762 s**.
- Submission SSH closed; the task continued and the reopened UI attached.
- **20** independent shell probes; maximum response **0.330 s** in this lab.
- Verified saved boot-file hashes; packed root contained no profile, saved node
  identity or live native daemon state. The final matrix booted that generation.
- Actual QMP VGA frames inspected: available-update notice, active progress,
  Escape returning to tools while the job ran, saved-and-verified result, and
  nonmodal restart-pending notice. No automatic install or reboot occurred.

## Integration findings retained

Background APT initially failed because its temporary resolver inherited mode
0600 from the service umask. The final worker explicitly grants read access to
that temporary nonsecret resolver and restores the original afterwards.
The public carryover hook now retains executable mode.

Harness corrections were separate from product changes: continuous serial drain
avoids QEMU/Plymouth backpressure; encrypted-profile automation no longer depends
on a fleeting login marker. Failed first-round runs are not final-image passes.
The initial build and RAM-only DNS experiment do not certify these final hashes.

## Evidence and limits

Local receipts, build logs and screenshots are retained under
`operations/portable-tailnet-background-updates-20261016/`. That ignored directory
is not release source and must not be blindly published. QA disks, synthetic
credentials and the isolated controller are retired after collecting receipts.

Not claimed: physical boot on another computer, Wi-Fi/firmware compatibility,
Secure Boot, live production Tailscale SaaS enrollment, provider inference or an
Imager binary rebuild. Headscale tested the real shared Tailscale client path;
unit tests also cover default-provider configuration. Server node expiry and
revocation still apply. Do not use cloned copies of one identity concurrently.
