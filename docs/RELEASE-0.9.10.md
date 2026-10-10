# LA AGUJA 0.9.10 · IA en el arranque, con control humano

## Codex Seguro

- Sandbox **workspace-write** en vez de **danger-full-access**.
- Confirmación humana nueva antes de cada herramienta mediante la puerta PreToolUse de LA AGUJA; Enter, Escape, EOF o fallo del broker no aprueban.
- Política nativa **on-request** para solicitar salidas del sandbox; revisión **humana**, no aprobación automática. `on-request` por sí solo no significa preguntar antes de todo.
- Red deshabilitada dentro del sandbox, sin raíces de escritura adicionales heredadas. Workspace y temporales siguen siendo escribibles.
- YOLO conserva ejecución sin restricciones. La cuenta conserva sudo fuera del sandbox; otros clientes mantienen sus propios mecanismos de confirmación.
- Rechazo de parámetros que reemplacen silenciosamente el modo Seguro.

La nueva política está **dentro de la imagen** y se conserva después de reiniciar. No requiere el parche temporal aplicado a una VM 0.9.9. Las imágenes antiguas no se modifican retroactivamente: preparar o instalar el Imager nuevo tampoco actualiza un USB ya grabado.

## Entrega

Rescue Disk e Imager **0.9.10** para Windows/Linux; Agent Skill **1.0.2**. Catálogo Ed25519 firmado con el pin existente, partes y hash total verificables. Conserva los cuatro CLI bloqueados, historial con rueda en RAM, perfiles cifrados, idiomas/teclados, login local y herramientas Linux/Windows. No se cambian cuentas ni versiones de los proveedores.

- [Imagen USB IMG.ZST](https://aguja.transcendenceia.net/releases/aguja-0.9.10-amd64.img.zst)
- [ISO BIOS/UEFI](https://aguja.transcendenceia.net/releases/aguja-0.9.10-amd64.iso)
- [SHA-256 del Rescue](https://aguja.transcendenceia.net/releases/SHA256SUMS-rescue-0.9.10.txt)
- Imagers, skill, fuentes, inventarios, licencias y sumas: archivos adjuntos de esta publicación.

Imagen de fábrica sin cuentas personales. Las versiones anteriores permanecen disponibles. Los componentes externos conservan sus licencias y condiciones en NOTICE.md y packages.tsv; el marcador interno distribution=personal permanece.

## English

**Bring your AI to boot—with human control.** Codex Safe now combines a **workspace-write sandbox**, **on-request** escalation and a fresh human confirmation before every tool. Network access is disabled inside the sandbox, additional writable roots are cleared, and escalation uses a human reviewer rather than automatic approval. YOLO remains unrestricted; the OS account retains sudo outside the sandbox.

The policy is included in the **0.9.10 image** and survives reboot. Older images and already-written USBs are not updated automatically. Imager 0.9.10 and Agent Skill 1.0.2 use the existing signed catalogue pin. Factory media contain no personal accounts; prior downloads remain available.

VM testing does not certify physical USB boot, all hardware, or provider login/inference. Screenshots on the website remain explicitly labelled with their original 0.9.9 QA provenance.

## Verificación de esta versión

- Cuatro clones independientes: BIOS y UEFI, con y sin perfil cifrado; arranque y reinicio correctos. Sudo, DHCP, SSH, particiones config/datos y cuatro CLI disponibles sin red.
- En cada clon y después de reiniciar: Codex 0.160.0 confirma workspaceWrite, on-request y reviewer user; escritura dentro del workspace permitida, escritura exterior/red/sudo dentro del sandbox bloqueados. Sudo del usuario fuera del sandbox conservado. Sin turnos de modelo ni nuevas cuentas de proveedor.
- En los dos clones cifrados: idioma/teclado antes del desbloqueo y al reiniciar, perfil cifrado, rueda virtual del kernel y suite runtime con identidades apropiadas verificados.
- 171 pruebas runtime: 170 aprobadas y una omitida; 103 pruebas Imager aprobadas y 10 específicas de Windows omitidas en Linux; 11 pruebas del sitio; 38 comprobaciones del Electron Linux empaquetado; 28 archivos empaquetados Linux/Windows coincidentes con la fuente.
- 48 vistas web locales en ocho idiomas y tres anchos; búsqueda, copia, teclado, zoom y lectura sin JavaScript.
- La IMG descomprimida coincide con el SHA total del catálogo firmado; código de runtime, rootfs e imagen empaquetada coinciden. CFG de fábrica sin cápsula privada.

IMG: `a70a51b6666b25563c3a1773331f8d7d9cd05e0c0ce3dc50a0d5969b9917a8db` · 3,882,876,928 bytes.
