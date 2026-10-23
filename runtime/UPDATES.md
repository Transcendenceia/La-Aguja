# LA AGUJA · interactive updates

Open **Updates** in the live panel, or run `aguja update menu`. The first action is **Check for updates**. Checking queries the official OS repositories, the four native AI providers and the signed Rescue catalogue. It does not install anything; its cache lives in RAM. An incomplete/offline source is shown as incomplete, not “everything is current”.

## Choose for each update

The list shows the component/package and its installed → available version. Every row starts at **No**:

| Choice | Effect |
| --- | --- |
| No | Do not install this update. |
| Yes · RAM | Apply it only to this running live session. These changes disappear at reboot and do not change the USB boot selection. |
| Yes, persistent | Build and verify a clean system generation on this boot USB's DATA. It takes effect at the next boot, including on another computer. |

A complete Rescue Disk release is **persistent only**: replacing the running kernel/root in RAM is not offered. Update a complete Rescue release separately from selected persistent components. Required package dependencies may also change; “No” is not a promise to break dependencies of another explicitly selected package.

Use **Up/Down** to choose a row and **Left/Right/Space** to change its choice, or click its radio field. Mouse wheel/Page Up/Page Down scroll a long list. **A** reviews the selection, counts RAM/persistent choices and displays the exact persistent target. **Enter** on that review starts the work; **Escape** returns to the list without installing. There is no automatic approval. The graphical local panel and text/SSH fallback use the same plan.

## Watch it finish

The screen stays open through checking, download, installation, USB saving, verification and boot-selection commit. Download bytes and APT progress are shown when actually measured; an activity indicator means work is running, not a guessed percentage. **Saving on USB** means a persistent generation is being written, not that RAM changes somehow survived a reboot.

The final screen distinguishes **updated in RAM** from **saved on USB and verified**. A persistent result says **reboot pending**. It never reboots automatically. Press **Enter · Back to menu** after reading the result. A failure is not completion: the previous boot stays selectable; failed temporary package operations may have changed part of the RAM session and need inspection before retrying.

## Persistence and recovery

Generation roots start from a verified clean selected generation/factory, never decrypted RAM HOME or the current overlay. A previously saved pending generation is the next build base, so another update does not discard it. Fixed hash-verified public updater files can accompany the clean generation; profiles, recovery capsules, sessions and workspace cannot.

Persistent package installation runs in a private mount/PID namespace with minimal character devices and service starts blocked. Temporary package installation requires a live RAM overlay, hides block devices from its helper and makes its USB views read-only inside that helper namespace. Configuration, keys and workspace remain separate. The USB is not encrypted in full by encrypting a profile capsule.

A writable boot USB with sufficient DATA and RAM is required for persistence. Factory and the verified previous generation remain available in GRUB. `aguja update rollback` selects the previous/factory entry for the next boot. `aguja update cleanup` retires only inactive unmounted update generations, not active/previous/running generations or personal files. Maintenance commands remain available outside the simplified interactive flow.

`aguja update status --json` distinguishes the running and selected generation. `aguja update check --json` is a noninteractive check. Advanced `packages`, `harnesses`, `all` and `release` commands retain their explicitly persistent behavior; use the interactive list for per-item RAM/persistent choices. Ordinary apt or client self-updates outside the manager remain temporary and do not gain its progress/verification guarantees.

Older media made before 1.0 needs to be prepared again with a compatible image; editing CFG alone cannot add the boot infrastructure. Back up personal DATA before reflashing. A verified executable version does not prove provider login/inference or universal firmware support. Current illustrated guide: https://aguja.transcendenceia.net/en/docs#reinicios

## Español · uso paso a paso

1. Abre **Actualizaciones → Comprobar actualizaciones**. Consultar no instala ni guarda actualizaciones en el USB; la caché de consulta está en RAM. Si falla una fuente, la consulta se indica como incompleta.
2. Revisa la lista con versión instalada y disponible. Cada fila empieza en **No**. Elige **Sí · RAM** para esta sesión o **Sí persistente** para guardarla en el pendrive. El Rescue completo solo admite persistencia y próximo arranque; no se combina con otros componentes persistentes en la misma operación.
3. Usa flechas/espacio o los campos con el ratón. **A · Revisar selección** muestra el plan y el USB de destino. **Enter · Aplicar selección** confirma; Escape vuelve sin instalar. También se instalarán las dependencias necesarias.
4. Mira el progreso: consulta, descarga, instalación, guardado en el pendrive y verificación. Los bytes/porcentajes solo aparecen cuando están medidos. Un indicador de actividad no es un porcentaje inventado.
5. Espera el resultado. **Actualizado en RAM** se pierde al reiniciar. **Guardado en el pendrive y verificado** queda pendiente del próximo arranque, también en otra máquina. No se reinicia automáticamente. **Enter · Volver al menú** cierra el resultado.

Fábrica y la generación anterior siguen disponibles. Una generación pendiente ya guardada no se descarta al preparar otra actualización. Los secretos, las sesiones y el workspace no se copian desde RAM al sistema empaquetado. Si falla una instalación temporal puede haber cambios parciales en RAM; revisa el estado antes de repetir. `rollback` y `cleanup` permanecen como herramientas avanzadas, no como siete opciones mezcladas con la consulta inicial.

## Boot verification

Normal boot checks generation selection and root-image availability without
rehashing the complete root image. Download, write and activation verification
remain mandatory. For a full pre-boot root checksum diagnostic, temporarily add
`aguja.verify=full` to the kernel command line in GRUB. This detects changes since
activation, at the cost of reading the entire root image before startup.

## Background work and startup notices (1.0.2)

A read-only update check starts shortly after boot, without delaying the panel.
The panel reports available updates or incomplete/offline checks. Nothing installs
without your selection and confirmation. Opening Updates reuses the inventory.

Confirmed work runs in a separate system service, with lower CPU/I/O priority.
Press Escape to return to other tools; reopen Updates to see progress and the
verified result. Closing a local menu or SSH session does not cancel the job.
Keep the USB connected and do not power off while a write is active. Persisted
changes become active only after the existing full verification and commit; a
restart remains your choice. A failed/interrupted task is reported as such.

## Portable tailnet identity (1.0.2)

The first connected enrollment triggers an immediate background identity
checkpoint on this boot USB. Further native state changes are observed, with a
retry timer and a final checkpoint during clean daemon shutdown. Success means
atomic file write, fsync and readback all completed; until then the panel says
pending/saving, or reports an error. Unchanged state does not rewrite the USB.

The next boot restores that native identity before starting the daemon, even on
another computer. It does not enroll a replacement just because a saved state
cannot be read. Automatic profiles restore without prompts. For an encrypted
profile the checkpoint is encrypted too and restores only after the existing
local profile unlock; its key stays in private RAM, never on the USB. Node
revocation/expiry still applies. Configuration, identity and workspace are not
included in clean public system generations. Do not run cloned copies of the
same provisioned identity simultaneously.


## Official Rescue releases (1.1)

Every interactive/background check queries the signed latest Rescue catalog first,
independently of APT or agent provider failures. A newer Rescue release is the first
row in the list; choose **No** or **Sí persistente** (not RAM). The reviewed version
is pinned for the operation: a changed catalog requires another review, not a silent
upgrade to different bytes. Download parts and assembled image hashes are verified,
then a new boot generation is staged. CFG, LUKS vault and DATA/workspace are not
reflashed. Factory/previous remain available; no automatic reboot. If a LUKS vault
is present, a release without the early gate capability is rejected. Catalog errors
mean “unverified”, not “up to date”. This does not update Flash Imager.

## Bulk selection (Rescue Desk)

All RAM selects all component updates, not the complete Rescue image, which
requires persistent storage. All persistent can combine the signed official
Rescue and components: stage the verified release without activation, update
components in a new generation based on it, and activate only the final verified
generation. Components already at a newer version in the Rescue are not
downgraded. A failed stage leaves the previous active generation unchanged.
No automatic reboot. Closing the UI does not stop background update jobs.
