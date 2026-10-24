# Validation — Rescue Disk 1.0.3 (2026-10-24)

This is the public numbering of the factory candidate, not a copy of an owner's
USB. Earlier development numbers 1.1.x–1.3.x were not public releases.

## Final artifacts

| Artifact | SHA-256 |
| --- | --- |
| aguja-1.0.3-amd64.img | `fbdbccee75d074b56bee9a4676ea56fda84802351221e6df0be6f9f5c127812c` |
| aguja-1.0.3-amd64.iso | `5491f422b6258c2aa77d29155caa8b30cfc5440e5a9faaed740d8355348826e4` |
| aguja-1.0.3-amd64.img.zst | `391c85179dec155c76837433d01d9a8fb5111e3b40570952047449f7bdabcc1f` |

Build outputs use a personal filename prefix for the complete factory image;
the public filename does not change its bytes. No prepared owner profile or
enrolled tailnet identity is included. Provider licences remain unchanged.

The ISO and compressed IMG exceed GitHub's 2 GiB per-file limit and are hosted
under https://aguja.transcendenceia.net/releases/. Three verified IMG parts,
catalogue, source and checksums are GitHub release assets. Existing Imagers can
consume the signed parts without a new Imager binary.

## Exact-image native checks

The final IMG passed eight checks each under BIOS and UEFI (16/16), using
file-only QEMU USB overlays, two vCPUs and 2 GiB RAM. No physical disk was opened.

- Installed version and graphical runtime hashes match the candidate source.
- Normal Helium browser opens from the live cockpit.
- Factory Spain layout loads; changing to Latin America/nodeadkeys updates the
  same Xorg process, without restarting the graphical session.
- Physical QEMU key positions produce `ñÑ@€á` inside a real browser textarea.
- A synthetic native-OAuth fixture inherits US/international, then updates live
  to Spain. This does not exercise a real provider login or consent.
- Normal and OAuth browser close, Xorg exits and a new SSH command succeeds.
- The BIOS boot saves US/international in CFG; a subsequent UEFI boot loads it.

The final shell-started OAuth fixture returns to its invoking shell; its final
screenshot is not proof of an automatic cockpit return.

## Code and previous feature evidence

All **287 Python tests passed**, no skips, in the Debian build guest with sbin
PATH configured. The build checks source against installed and packed runtime,
including the four pinned native clients, guides and update infrastructure.

Encrypted global snapshot save/restart/deletion retention and factory fallback
were validated separately on the preceding development candidate. The keyboard
and public-numbering rebuild does not constitute another complete native
global-persistence matrix. Those implementation files remain unchanged.

The virt-manager absolute-pointer fix is host virtual hardware configuration,
not a capability that this image can inject into an existing VM.

Not claimed: physical hardware compatibility, Secure Boot, a new personal-USB
write, real provider authentication/inference, or a new Imager binary build.
Private candidates with a numerically higher 1.3.x version are not automatically
updated to 1.0.3 by a newer-version check; manual media preparation is separate.
