# LA AGUJA 0.9.16 · recovery keys, agent context and complete localization

## English

This release aligns **Rescue Disk and Flash Imager 0.9.16** and ships **Flash Imager Agent Skill 1.0.5**. LA AGUJA is an independent Linux live platform for building, configuring, investigating and recovering systems.

- All Imager sections and dynamic messages follow the selected application language across Windows and Linux, without changing typed data.
- Manual **BitLocker/LUKS** recovery entries can be prepared on a different computer. Labels/IDs help select an entry; key format alone does not prove it opens a disk. The image protection also protects its recovery capsule.
- Windows releases the selected USB's Explorer/file locks, obtains exclusive access before erasure and keeps its elevated worker hidden. A real removable-media failure found after deleting the disk layout is fixed by clearing headers through the same exclusive raw stream.
- The live now provides `aguja secrets --json` (locations/presence only) and `aguja recovery status|list|unlock|export|open`. Profile unlock also opens its matching recovery capsule into root-private RAM (0700/0600), never DATA. Reboot relocks encrypted capsules.
- Recovery `open` passes the key through private stdin and defaults to a read-only cryptsetup mapping, without mounting, repairing or permanently decrypting a target disk. Exact target selection and task authorisation remain necessary.
- All four live agents receive an updated canonical credential/recovery map and an included disk-recovery skill. Managed context pointers refresh while preserving owner text in AGENTS.md/CLAUDE.md/GEMINI.md.
- The standalone preparation skill accepts manual `disk_recovery` entries, verifies every supplemental file, preserves the base image, and still does **not** flash a physical USB. Skill, engine and selected live-image versions remain separate.
- The Imager uses the pinned, signed catalogue in this explicit GitHub release. No account or token is sent with public downloads; older website/installer releases remain preserved.

No personal credentials, prepared private images, decrypted caches, QA requests or signing keys belong in the public assets. A published image does not upgrade an existing USB/live process automatically. LUKS passphrases and BitLocker numerical recovery passwords are supported; arbitrary binary keyfiles and other encryption systems require their own compatible tooling. Virtual BIOS/UEFI validation is not a physical hardware boot test or provider-login/inference test.

See [disk recovery guide](DISK-RECOVERY.md), [live credential map](../runtime/SECRETS.md), [recovery skill](../skills/disk-recovery/SKILL.md) and [preparation skill](../skills/flash-imager/SKILL.md).

## Español

Entrega conjunta de **Rescue Disk/Flash Imager 0.9.16** y **skill de preparación 1.0.5**. Idiomas completos, claves manuales BitLocker/LUKS para otro equipo, USB exclusivo y grabador oculto en Windows. El live y sus cuatro agentes ya conocen las ubicaciones y el flujo privado: `aguja secrets --json`, `aguja recovery` y la guía SECRETS.md. Desbloquear el perfil abre también el resguardo compatible en RAM privada; reiniciar vuelve a bloquearlo. Se conservan las instrucciones del dueño y la skill sin GUI verifica el transporte de las claves. La apertura de volúmenes es de solo lectura por defecto y no autoriza montar, reparar ni escribir. No se publican credenciales ni imágenes personales. [Guía en español](DISK-RECOVERY.es.md).

Windows environment-query fallback now normalizes PATH without discarding owner locations. Generated pages match the release and independent skill version. The 0.9.15 preparation tags remain preserved; no 0.9.15 binary release was published.
