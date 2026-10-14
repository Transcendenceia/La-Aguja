# LA AGUJA 1.0.0

Imager and Rescue Disk move together to 1.0. The Flash Imager automation skill is independently versioned as 1.1.0.

## Imager — Windows and Linux

- Optional signed update discovery and SHA-256-verified downloads; no automatic replacement or execution.
- Reusable encrypted `.aguja` configuration profiles, with disk-recovery keys preserved. Provider sessions remain explicitly selected, not indiscriminately copied into templates.
- Read, decrypt and edit an existing LA AGUJA USB's CFG without reflashing. Exact disk identity, stale-snapshot rejection, stored-byte backups, interrupted-transaction recovery and readback verification. Preserve DATA, boot generations and unrelated files.
- Dedicated **Encrypted disks** section before Create disk. Manual BitLocker/LUKS keys and detected BitLocker use the same protected recovery capsule.
- Edited language/keyboard preferences use the exact public pre-unlock file consumed by the live.

## Live — persistent generations

`aguja update menu` checks and optionally applies OS packages, native harnesses or a signed Rescue release. Notifications only check; they never install or reboot. The manager builds from clean squashfs, not the running credential-bearing RAM overlay, inside a private mount/PID namespace with only minimal character devices. It verifies and saves kernel/initrd/root on DATA before activation.

Changes take effect on the next boot, including another computer. Factory and a verified previous generation remain selectable; explicit rollback and inactive-generation cleanup are available. Configuration, recovery keys, imported sessions and workspace remain separate. Ordinary apt or native self-update outside the manager is still temporary.

Fresh Windows-written 1.0 media expands DATA once on the observed removable boot USB, preserving its GUID. Editing an older USB's CFG does not install the 1.0 boot infrastructure or recreate initialization markers. Reprepare from 1.0 to gain generation updates; preserve personal DATA externally before reflashing.

Resource checks, a single compression worker and a bounded cache prevent activation of incomplete staging. Insufficient space, memory, offline metadata or invalid downloads preserve the previous boot selection. Use the [offline update guide](../runtime/UPDATES.md) and [live-updates skill](../skills/live-updates/SKILL.md).

## Validation and limitations

Release evidence distinguishes source tests, real native Imagers, virtual USB/BIOS/UEFI boots, provider executable versions and actual provider inference. An executable version is not authentication/inference proof. No Secure Boot, universal hardware compatibility or code-signing reputation claim is implied. Public images contain no personal profiles or recovery keys.

## Español

La 1.0 añade actualización opcional del Imager, perfiles cifrados reutilizables y edición de configuración del pendrive sin regrabar. **Discos cifrados** tiene un apartado propio. El live avisa de actualizaciones y permite guardarlas en DATA como generaciones verificadas, independientes de las claves y del workspace. Se aplican al siguiente arranque, también en otra máquina; fábrica y anterior permanecen disponibles. No hay instalación ni reinicio automático. Los USB anteriores necesitan prepararse con la imagen 1.0 para incorporar el nuevo arranque; editar el CFG no sustituye esa preparación.

## Imager navigation correction

The preparation wizard ends at Create disk (step 07). Profiles/USB configuration and Imager updates are independent unnumbered tools. Their return action preserves the selected preparation step and entered settings, including across language changes. Windows shows local BitLocker before manual disk recovery keys. This correction rebuilds the Imager packages only; the tested Rescue image, boot generations and standalone automation skill are unchanged.

Español: el asistente termina en Crear disco (07); perfiles, edición USB y actualizaciones quedan fuera del flujo. BitLocker local aparece antes de las claves manuales.
