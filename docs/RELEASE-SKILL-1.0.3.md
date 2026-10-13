# LA AGUJA · Flash Imager Agent Skill 1.0.3

An independently versioned, portable skill for preparing a personalised La Aguja `.img` file with Node.js 22+, without Electron. The bundled Flash Imager engine and current live image remain **0.9.11**.

## Changes

- Align skill metadata, CLI `doctor`, interface documentation and bundle manifest at **1.0.3**.
- Derive package names and generated website skill links from the skill metadata. Reject a CLI/metadata version mismatch before packaging.
- Point installation guidance to this standalone release, with matching archive/checksum versions and preservation of existing installed skills.
- Clarify the boundary between file preparation and operating a booted live system. This skill does not flash physical disks automatically or install live packages.
- Correct the portable Linux Imager download filename and QEMU mission documentation in all eight website languages. QEMU x86, qemu-img/qemu-nbd, OVMF and SeaBIOS are included from 0.9.11; KVM remains host-dependent and TCG is a slower fallback. Container engines, build tools and specialist analysis tools remain optional.

## Validation

Four functional skill tests pass: real synthetic image preparation, runtime decryption interoperability, source preservation/no overwrite, and standalone distribution with reproducible archives. Twelve website tests and 48 desktop/mobile page checks pass, including no-JavaScript documentation and clipboard fallback. These checks do not certify every harness, OS or physical machine.

Download the complete ZIP or TAR and the matching `SHA256SUMS-flash-imager-skill-1.0.3`; verify the checksum before extraction. Follow [harness installation guidance](../skills/flash-imager/references/harnesses.md).

## What stays unchanged

Existing 1.0.2 assets, desktop installers, live images, catalogue signature pin, provider permissions and USBs remain unchanged. The revised canonical live agent context and TOOLBOX in the repository are intended for the next image build; installing this skill does not update instructions already embedded in a USB. No new hardware boot validation is claimed for this documentation/skill release.

## Español

Actualización independiente de la skill a **1.0.3**, con motor **0.9.11**, identidades consistentes y descargas verificables. Corregidos enlaces y documentación multilingüe sobre QEMU. No cambia la imagen publicada ni los USB existentes; la orientación live corregida queda en la fuente para la próxima imagen.
