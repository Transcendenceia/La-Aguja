# LA AGUJA Rescue Disk 1.0.3

The next public release after 1.0.2. Development candidates labelled 1.1.x,
1.2.0 and 1.3.x were not public releases; this release consolidates their changes.
Flash Imager remains 1.0.0 and the standalone preparation skill remains 1.1.0.

## Changes

- Native Rescue Desk, Thunar file management, operational guidance and storage,
  backup and recovery planning without starting an AI session automatically.
- Encrypted global snapshots retain installed packages, file changes and
  deletions. Factory boot remains available; saving is an explicit action.
- One selected keyboard layout and variant for the console, desktop, normal
  browser and native OAuth browser. Changing the selection updates an already
  open graphical session, without inferring the keyboard from the UI language.
- OAuth handoff waits for document load and includes a visible Continue link
  that also works without JavaScript. Provider state, PKCE and callbacks remain
  under the native provider client.

The virt-manager pointer improvement is a separate host configuration change:
an absolute USB tablet replaces relative-only input. An image update cannot
add that virtual hardware to an existing VM.

## Español

La versión pública siguiente a 1.0.2 reúne Desk, explorador nativo, persistencia
global cifrada, teclado compartido y la corrección de apertura OAuth. Las
numeraciones internas 1.1–1.3 no se publicaron como releases. La selección de
teclado se aplica a todas las aplicaciones y también a sesiones gráficas abiertas.

Se distribuye una imagen de fábrica, no una copia del USB personal. No contiene
perfiles preparados ni una identidad tailnet inscrita. Descargar esta release
no actualiza automáticamente un USB existente. Las licencias de terceros y las
cuentas/cuotas de cada proveedor siguen siendo independientes.

## Validation

Final 1.0.3 checks and artifact hashes are recorded in VALIDATION-1.0.3.md.
No universal hardware, Secure Boot, real-provider consent or inference claim is made.
