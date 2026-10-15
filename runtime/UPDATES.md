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
