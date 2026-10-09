# Rescue Disk 0.9.6 — CLI installation is not authentication

## Cause

The historical public 0.9.0 image omitted Claude Code and Antigravity while keeping
credential preparation available. Its smoke test required those two binaries to be
absent, and `aguja doctor` excluded them from overall health. Importing a session
could therefore succeed without an executable available on the live system.

## Correction

- The complete personal image installs Codex, Antigravity, Claude Code and OpenCode
  regardless of selected provider modes, preauthentication, or persistent HOME.
- Provider executables live in the immutable rootfs, not in a credential capsule or
  a first-boot download. Installation never authenticates or starts an AI agent.
- Downloads are version-locked and checksum-verified; upstream notices are retained.
- The builder executes all four versions under the normal user with an empty HOME,
  checks versions against the lock, and compares executable bytes after squashfs.
- `aguja doctor` now fails when any required CLI is absent. BIOS/UEFI smoke tests
  execute all four; the optional restart check repeats them after a real clone reboot.
- The personal output has a distinct filename and distribution marker. Existing
  public downloads, Imager 0.9.5 and provider licensing are not changed by this build.

## Validation

155 unique runtime tests passed across the Debian rootfs and host GPT/FAT test.
All four versions also ran in a network namespace with no external connectivity.
Boot and reboot results are recorded privately under
`operations/rescue-required-clis-20261009/final-bios/` and `final-uefi/`.
Both BIOS and UEFI passed boot, SSH, sudo, all four versions without network,
and a real QA-clone reboot followed by the same CLI checks. This does not make
the RAM patch persistent on the old USB image.

## Delivery and rollback

The corrected source is on local branch `fix/rescue-required-clis`.
`dist/aguja-personal-0.9.6-amd64.img` is a personal complete image, not a public release.
The original running rescue was patched only in RAM; it was not reimaged or restarted,
and its internal Windows disk was not mounted or modified. Rebooting that old medium
restores its old rootfs; use the new image for permanent CLI installation.
No login, provider inference, credential import, or publication was performed.

Image SHA-256: `6bae405c0d35edcdb342802c7112d51423ba883c7af14eeffd2889186a02224c`. Image size: 3882876928 bytes.
