# LA AGUJA · persistent updates

`aguja update menu` opens the update choices. `status --json` reads state; `check --json` queries public version metadata without installing. A bounded background check notifies through the local cockpit. No package installation or reboot is automatic.

Choose OS packages, the four native harnesses, both, or a signed Rescue Disk release. The current generation/factory boots while the next generation is prepared on DATA. Generation root files originate from clean squashfs, never the running credential-bearing RAM overlay; configuration, disk-recovery capsules, imported sessions and workspaces stay separate. Package upgrades run in a private namespace with no host disks and disabled service starts. Kernel, initrd and root travel together. All changes take effect on the next boot into that generation, including on another computer.

The original factory and previous generation remain in GRUB. `aguja update rollback` chooses the previous/factory boot for the next restart. `cleanup` removes only inactive, unmounted generations. Do not use ordinary RAM-overlay apt or CLI self-update commands and claim they persist. Do not remove an active squashfs while the live still uses it. No internal disk is an update destination.

A writable USB with sufficient free DATA and RAM is required. Windows-written fresh 1.0 media expands its DATA space once on first boot; Linux's guarded writer already does so. Configuration changes do not recreate that initialization flag. Metadata checks may be incomplete offline: report which source failed. A verified executable/version does not prove provider login/inference or hardware boot.

## Español

Consultar no instala. El panel avisa de actualizaciones; tú eliges cuándo aplicarlas. Se guardan en DATA como una generación con kernel, initrd y sistema, separada de los perfiles y secretos. Al reiniciar con ese pendrive en otra máquina se usa esa generación. Fábrica y la versión anterior quedan disponibles. No se reinicia ni se actualizan discos internos por esta opción. Si falta espacio o RAM, se conserva la versión actual.
