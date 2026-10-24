# Validation — Rescue Disk 1.1.0 (2026-10-24)

This feature release replaces the brief public 1.0.3 publication. It consolidates
all changes since 1.0.2 documented in RELEASE-1.1.0.md. Flash Imager stays 1.0.0.

## Exact factory artifacts

| Artifact | SHA-256 |
| --- | --- |
| aguja-1.1.0-amd64.img | `eb9e685131de0f8a79ee364aef4a510e8094b0711d0434c8ed4059d1507c8d4c` |
| aguja-1.1.0-amd64.iso | `1ac50341e71170566e5982b56991667290d565b38b61ebd0b5c6d5e6433fc00c` |
| aguja-1.1.0-amd64.img.zst | `f2291a1f1ffc866ffa0f81e82cf59a9a5f6c230f63e9ca8de4c3135bdd42ea57` |

The clean immutable factory root from 1.0.3 was extracted into a new isolated
build disk, not copied from a running session or a personal USB. VERSION was
installed as 1.1.0, the carryover manifest regenerated, and IMG/ISO rebuilt with
source-to-installed-to-packed runtime comparison and the pinned client checks.
The builder's package installation did not change the factory rootfs packages.
No prepared owner profile, credentials or enrolled tailnet state is included.

The complete factory builder uses an aguja-personal filename prefix. Renaming
the public outputs does not change their bytes or third-party licences.
ISO and compressed IMG exceed GitHub's per-asset limit and use the product
website; three signed/checksummed IMG parts are GitHub release assets.

## Code checks

- 287 Python tests passed in the Debian build guest, no skips.
- 13 public-site server/contract tests passed.
- Public source audit and whitespace validation passed.

## Final image and prior feature evidence

Final BIOS/UEFI result is recorded after the native test run. The test uses
file-only USB overlays, 2 vCPUs/2 GiB, normal browser and a synthetic OAuth fixture,
physical QEMU key positions, live layout/variant changes and the next-boot CFG
preference. No provider account, host disk or physical USB is used.

The early LUKS/legacy/automatic-profile matrix, snapshot save/boot/deletion
retention and rollback/factory recovery were exercised on earlier development
candidates. This public-numbering rebuild retains those runtime implementations;
it is not another execution of every historical feature matrix. Historical
candidate hashes and limits remain in the design documents.

No universal hardware, Secure Boot, real provider consent/inference, cloud/NAS
transfer, host-VM reconfiguration or physical USB write is claimed. The absolute
SPICE pointer improvement is host virtual-tablet configuration, not an image fix.
