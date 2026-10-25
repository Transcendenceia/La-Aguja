# Flash Imager Agent Skill 1.2.0

English first · Español después.

The standalone preparation skill is aligned with **Flash Imager engine 1.1.0**
and **public Rescue Disk 1.1.1**. Component versions remain independent.

## Preparation

- Structured extended profiles: up to 16 ordered Wi-Fi networks, 32 portable
  NAS/cloud destinations, literal custom environment and advanced tailnet options.
- Reference contract and private-input example match `capsule.extensions`;
  no invented import, shared-password or physical-writing operations.
- Included `profile-extensions.cjs` supplies the same validator as the desktop;
  the old published skill 1.1.0 bundled engine 1.0.0 and did not contain it.
- Secondary Wi-Fi passwords, storage settings and custom environment values are
  private inputs: encryption is required unless the owner explicitly requests
  `allow_plain_secrets:true`. Secrets never appear in result/error output.
- Reusable encrypted profiles preserve extensions. The output profile is verified
  by FAT32 readback, decryption and source/output hashes, without modifying base.
- Extended fields require `imager-profile-v2`, included in Rescue 1.1.1. A base
  lacking it fails before publishing output; unsupported settings are not dropped.

The CLI prepares regular `.img` files. It does not write a USB, enroll accounts,
mount a NAS, execute environment values or perform GUI-only import operations.
Protection is AES-GCM for preparation, not automatic LUKS conversion or DATA
volume encryption. Shared phrases across SSH/profile/output are an explicit
choice, not a new schema flag. Provider and remote passwords remain separate.

## All three skills and live guidance

- `flash-imager` 1.2.0: current headless preparation and private extended settings.
- `disk-recovery` 1.1.0: distinguishes the live LUKS profile vault, legacy AES
  capsule and separately selected target BitLocker/LUKS volume.
- `live-updates` 1.3.1: RAM updates versus encrypted persistence, and the four
  power actions. Failed persistence cancels a combined shutdown/restart.

The standalone bundle includes reference copies of these live skills plus
AGENT-CONTEXT, UPDATES and SECRETS under `references/live/`. They are documents,
not a live update payload. Read the installed guides and inspect real commands
before acting. Source live guidance is now aligned, but **the public Rescue 1.1.1
image and existing USBs are unchanged**. They already implement the runtime
capabilities; these new wording revisions are not claimed to be embedded there.
No personal installed skill, owner instruction, VM or physical disk is replaced.

## Distribution

Use the explicit `flash-imager-skill-v1.2.0` release, never `releases/latest`.
ZIP/TAR are self-contained with Node.js 22+, dependency licenses, member SHA-256
manifest and deterministic archives. Run `doctor` after extraction and verify
`catalog` from the downloaded package. Preserve older skill versions and their
release source. Latest remains Rescue v1.1.1; Imager installers remain 1.1.0.

## Español

La skill **1.2.0** incluye el motor Imager **1.1.0** y se alinea con Rescue
**1.1.1**: Wi-Fi ordenadas, NAS/cloud, variables literales y opciones ampliadas
de tailnet. El paquete ahora incluye el validador necesario y exige protección
cifrada también cuando los datos privados solo están en las opciones nuevas,
salvo elección explícita de almacenamiento sin cifrar. Perfiles guardados y
preparación mantienen esos campos; una imagen incompatible se rechaza.

También se alinean `disk-recovery` **1.1.0**, `live-updates` **1.3.1** y el contexto
de agentes: bóveda LUKS frente a cápsula AES, discos destino separados y acciones
de persistir/apagar/reiniciar que se cancelan si el guardado falla. Las guías van
como referencias dentro del ZIP/TAR; no se reconstruye Rescue ni se cambian USBs,
instalaciones de skills del propietario, cuentas o permisos.
