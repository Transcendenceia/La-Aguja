# LA AGUJA · updates and global persistence

## Update this running session

Open **Updates → Check** (`aguja update menu`). The check queries official OS
repositories, the four native agent providers and the signed Rescue catalogue.
It does not install anything or modify USB boot selection. Partial/offline sources
are incomplete, not an all-current verdict. Each component starts at **No**.
Choose **Yes · update**, review with **A**, then **Enter · Install now**.
Dependencies can also change. There is no persistent choice in this screen.

`aguja update packages`, `harnesses` and `all` install in the current RAM session.
Ordinary apt, agent self-updates, settings and files are also temporary until saved
through **Persist changes**. The updater never silently falls back to USB writing.
Downloads/APT use measured progress, not time-based estimates. Work is detached
from the interface; return to Updates to view its result. A partial failure reports
verified completed components and possible RAM changes, not success or rollback.

A newer signed complete Rescue release can be prepared separately in RAM with
`aguja update release` or its own row. Archive hashes, version/protocol and the
protected-profile gate are checked. This may require more RAM than component
updates; insufficient RAM fails before downloading and does not write to USB.
Preparing it does not replace the running kernel. **Persist changes** rebases the
captured live modifications over that prepared root, verifies it and selects it
for the next boot. A reboot remains the operator's decision.

## Persist the whole live

Choose **Persist changes** in the main menu (`P`), or `aguja persist save` on an
interactive terminal/SSH. This is independent of updating: save manual package
installs, files created/changed/deleted, system settings, agent sessions and normal
browser state. It creates a **private encrypted global snapshot** on this same
boot USB, not a public/shareable Rescue image. Choose a password of at least eight
characters; it is requested when booting that snapshot. It is separate from an
existing profile-vault password and never stored in argv, logs or on the USB.

The source is the merged live root, so overlay deletions are honored. Mounted
external/internal disks, CFG, DATA/workspace, /dev, /proc, /sys, /run, /tmp and
package-download staging are not recursively copied. DATA/workspace and the
protected profile keep their existing storage. Known cloud/NAS, tailnet and
recovery application state is saved inside the encrypted snapshot and restored
after the profile gate; sockets, processes and transient OAuth requests are not.
Normal browsing profiles live in HOME (RAM by default); transient OAuth profiles
remain temporary. A mounted legacy persistent HOME stays separate on DATA.

The screen reports actual file counts, copied bytes, native compression progress
and verified bytes. Scanning, encryption, compaction, sync and activation show
activity when no meaningful total exists. Staging is encrypted too. It needs
space for the staged root and compressed root at once, then compacts the saved
container. No guessed overall percentage, automatic reboot or USB removal.

Only after readback verification, synchronization and re-observing the boot USB
is the new boot selection committed. Failed/incomplete snapshots never replace
the previous selection. Factory and the previous generation remain in GRUB.
`aguja update status --json` distinguishes selected and running generations;
`aguja update rollback` and `cleanup` remain advanced generation-maintenance
commands. Cleanup never removes active/previous/running generations or owner data.
A CD/ISO can run and update in RAM but is not a writable persistence target.

## Explicit power actions (Rescue 1.1.1)

`aguja power menu` offers Power off, Restart, Persist and power off, and Persist
and restart. The direct `aguja power poweroff|reboot|persist-poweroff|persist-reboot`
choices still request final confirmation. Cancel/Escape/EOF do not approve.
Updating or saving does not by itself authorize a power action.

Ordinary shutdown/restart discards unsaved RAM changes. A combined action prompts
privately for the snapshot password, saves and verifies, syncs and finishes mount
cleanup before requesting power. If persistence fails, power is cancelled and
the computer stays on. Never chain an unconditional shutdown after a failed save.
New boot activation is not evidence that the next boot has already succeeded.

## Español

**Actualizaciones** solo instala lo elegido en esta sesión: **No / Sí · actualizar**.
No guarda globalmente ni ofrece «Sí persistente». Si quieres conservar lo hecho,
sal al menú principal y abre **Persistir cambios**; funciona aunque no hayas usado
el actualizador. También conserva instalaciones y modificaciones manuales.

Elige y repite una clave: la instantánea completa y su staging quedan cifrados.
Se pedirá esa clave al arrancar los cambios guardados. Mira las fases y medidas
reales hasta **Cambios guardados y verificados**. Fábrica y anterior quedan como
recuperación; no se reinicia solo. No se copian discos montados, temporales ni
procesos vivos, y workspace/CFG se mantienen aparte. Una ISO/CD no permite guardar.

Normal boot validates selection, encrypted-container type and availability. Add
`aguja.verify=full` in GRUB for a complete preboot root checksum diagnostic.
