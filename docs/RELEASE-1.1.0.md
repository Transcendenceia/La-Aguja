# LA AGUJA Rescue Disk 1.1.0 — the native workstation release

**A feature release compared with Rescue Disk 1.0.2, not a keyboard-only patch.**
This release brings together the cockpit redesign, native applications, early
profile protection, encrypted whole-system persistence, connection forms,
update workflow and agent operating guides developed since 1.0.2.

Rescue Disk is **1.1.0**. Flash Imager remains **1.0.0**; the standalone preparation
skill remains **1.1.0** independently. No new Imager executable is required.
The brief 1.0.3 publication is superseded and withdrawn; development candidates
labelled 1.1.x, 1.2.0 and 1.3.x were internal milestones, not public release lineage.

## 1. One cockpit, direct tools and consistent presentation

- A single framebuffer cockpit groups **Agents, Connections, Tools and Settings**,
  instead of introducing a second desktop hub to navigate through.
- Direct entries open the browser and file manager; connection actions construct
  only the requested native form. Closing an application returns to its caller.
- The cockpit and submenus use a graphite/spectrum visual family, Inter typography,
  styled controls and updated GRUB/Plymouth artwork while retaining Agujita.
- Short-display menu layout and pointer hit geometry are handled together.
  Traditional console/diagnostic and graphics-compatibility boot paths remain.
- Static panel composition is cached; mouse movement updates its dirty rectangle.
  Input polling and network refresh no longer trigger a full idle-panel render.
  These implementation changes are not a universal FPS or hardware-speed claim.

## 2. Native files, browser and graphical lifecycle

- **Thunar is the primary graphical file manager**, including explicit root file
  management, visible mouse interaction and explicit mount/unmount operations.
  Internal target disks are not mounted automatically at boot.
- Yazi remains available for terminal navigation and preview, with native text,
  image, PDF, media, archive and read-only hexadecimal viewers/editor handoffs.
- **Helium is the default browser**, with Debian Chromium selectable as a
  compatibility alternative. The normal browser runs as the owner with its
  sandbox; privileged file operations do not imply a root browser.
- A branded local start page, browser theme, GTK forms and window manager share
  the visual family. Provider websites retain their own appearance.
- Normal browsing reuses a RAM-only profile with bounded cache; OAuth uses a
  separate short-lived private profile. Authentication is still provider-owned.
- Graphical applications wait for window-manager readiness. Directory pickers
  start in an accessible location and are shown correctly.
- CD boots without accessible DATA fall back to the owner's workspace/home,
  instead of crashing all forms while eagerly constructing the Files page.
- D-Bus uses the boot's machine identity, avoiding a stale copied identity.

## 3. One keyboard selection everywhere

- Console, graphical forms, file tools, normal browser and native OAuth browser
  apply the same configured keyboard layout and variant.
- Starting Xorg no longer falls back to US while the console is configured for
  Spain. A change from Settings or the CLI also updates already-open local
  Xorg sessions, without restarting them.
- Keyboard choice is independent of interface language; Spain is not forced on
  other users. Validated layout/variant values come from the shared configuration.

## 4. Protected profiles before access starts

- A real **file-backed LUKS2 profile vault** can be opened at the early boot gate,
  before the cockpit, owner shells, SSH and agent access are started.
- Failed or cancelled unlock does not start those access paths. Splash requests
  own their password interaction, with a console fallback.
- Existing automatic/plain Imager profiles remain supported and are intentionally
  not encrypted. Existing encrypted legacy capsules remain readable and are
  identified as legacy, not relabelled LUKS.
- Migration from a legacy capsule to the new vault is explicit; the inner profile
  need not introduce a second password prompt after the vault is unlocked.
- The profile vault covers its profile/recovery/cloud/tailnet configuration, not
  every arbitrary file in DATA or the workspace. Whole-system snapshots are a
  separate mechanism described below. Neither mechanism encrypts target disks.

## 5. Explicit encrypted whole-system persistence

- **Persist changes** is separate from **Updates**. Installing into the live RAM
  session and deciding to save the complete session are distinct actions.
- The global snapshot captures installed packages, settings, application state,
  created/modified files and deletions, rather than only a fixed update file list.
- Scanning, copying, compression, integrity checking and synchronization report
  actual stages/progress; unmeasured work is not represented as a guessed percent.
- Saved global generations use **LUKS2** and a verified early-boot path. Pseudo
  filesystems, other disks and specified transient state are excluded.
- Kernel and initramfs are selected as a matching Debian pair with module checks;
  snapshot construction regenerates the initramfs from the captured root.
- Factory boot and recovery/rollback remain available. Explicit activation follows
  verification; a successful save is not an automatic reboot.
- This is persistence of the captured live system, not a backup of every attached
  disk, blanket encryption of DATA, or permission to pull the USB while in use.

## 6. Updates: bulk choices, visible installation and honest results

- Choose **all in RAM**, **all persistent** or **clear choices**, retaining per-item
  choices and review before installation.
- The native update screen keeps installation controls and progress visible.
  It displays measurable download/install/save work and retains useful failures.
- Space and operation preflight happen before mutation; updater-owned RAM archive
  caches are cleaned and partial completion is not reported as total success.
- A complete Rescue image cannot be installed only in RAM. The bulk RAM choice
  explains that exception instead of silently pretending to apply it.
- A full-image update is staged without premature activation; component changes
  can be assembled into the final verified derived generation before activation.
- Official signed Rescue discovery precedes optional package/provider discovery;
  apply remains bound to the approved version and validates staged boot support.
  Protected LUKS profiles reject incoming generations without the early gate.
- Existing detached/background job handling, factory/previous generations,
  USB-persistent tailnet identity and explicit confirmation remain supported.

## 7. Cloud/NAS and private-network setup through native forms

- Manual provider-appropriate forms support **Drive, OneDrive, Dropbox, S3,
  SFTP, SMB and WebDAV**, with explicit configuration-file/directory import.
  Available fields are not proof that a real account has been connected.
- Imported relative key/configuration paths are handled explicitly. Passwords
  are obscured, blank-field retention is supported, and status exposes metadata
  rather than credential values.
- Privileged form operations pass structured input over stdin rather than
  putting secrets in command arguments. No LAN web-admin port is added.
- Tailscale/Headscale configuration includes server URL, authorized enrollment
  key or native browser enrollment, DNS preferences, routes, tags, exit-node and
  SSH choices. Controller policy and approval requirements still apply.
- Traditional rclone/restic and CIFS/NFS/SSHFS tools remain available for agents
  and manual work. Configuring a destination does not silently start a transfer.

## 8. Native agents and OAuth handoff

- Agent launch paths retain **Safe/Unsafe** choices and native client interfaces;
  fixes cover Codex startup/package metadata and Antigravity authentication.
- Normal browsing and OAuth share the same local browser implementation while
  the native CLI keeps its PTY, state, PKCE and callback handling.
- OAuth continuation is a complete visible document: navigation waits for load
  and a **Continue** link works even with JavaScript disabled.
- Where the native flow requires a copied code, the handoff can return it to
  the same native CLI PTY without demanding the old clipboard shortcut.
- Included CLI versions are pinned and checked offline in a clean HOME during
  construction; presence/version is not a provider-login or inference test.
- AI requires Internet and an authorized provider/account. This release does
  not install local models or supply provider subscriptions, credit or quotas.

## 9. Agent orientation, operational method and practical planning

- Updated canonical **AGENT-CONTEXT**, SSH welcome, Quickstart, Toolbox and Secrets
  guidance orient local and external SSH agents to the live environment.
- Canonical agent instructions are in English and ask agents to respond in the
  owner's requested/configured language; managed pointers preserve owner text.
- New **MISSIONS**, **BACKUP** and **ODD** guides describe operational planning,
  scope, live observations, execution, verification and evidence handoff.
- ODD is an adapted operational workflow, not automatic installation of the
  complete Gentle AI ecosystem, global hooks or an external review service.
- Hardware/resource preflight and scenario-aware backup planning give agents
  observations and options without automatically mounting or repairing disks.
- Debian firmware/network/display support and portable initramfs remain part
  of the bootable toolset; actual Wi-Fi/GPU models need their own hardware tests.

## Downloads, upgrade and validation

- ISO and IMG.ZST are hosted on the product website; three IMG parts, signed
  catalogue, checksums, source and notices are attached to the GitHub release.
- Existing Flash Imager 1.0.0 discovers the image through its signed catalogue.
  Downloading or installing Imager does not itself upgrade an already-written USB.
- Decompress IMG.ZST before manual import. Do not write a single IMG fragment.
- See **VALIDATION-1.1.0.md** for exact final hashes and tests. Previous candidate
  matrices and final-image tests are distinguished; no real provider consent,
  inference, physical Wi-Fi/GPU, Secure Boot or physical USB write is claimed.
- An absolute USB tablet corrected relative-only virt-manager pointer behavior
  in a test VM. That is host virtual hardware configuration, not something a new
  image can inject into every existing VM.

---

# Español — 1.1.0, una versión de funcionalidades

**El salto desde 1.0.2 es una renovación del entorno live, no un parche de teclado.**
La breve publicación 1.0.3 se sustituye y retira. Las candidatas internas
1.1.x–1.3.x no determinan la numeración pública. Rescue pasa a **1.1.0**;
Flash Imager sigue en **1.0.0** y la skill de preparación en su **1.1.0** independiente.

## Cambios completos por área

1. **Cockpit único y presentación.** Menú framebuffer reorganizado en Agentes,
   Conexiones, Herramientas y Ajustes; acceso directo a navegador/archivos y
   formularios de una sola tarea, sin un segundo hub gráfico. Estilo grafito y
   espectro, Inter, controles y arte de GRUB/Plymouth actualizados, conservando
   Agujita. Geometría de puntero y pantallas cortas coherente; consola y arranque
   diagnóstico/compatibilidad siguen disponibles. Render estático cacheado,
   repintado del área del ratón y refresco de red fuera del manejo de entrada.
2. **Aplicaciones nativas.** Thunar pasa a ser el explorador gráfico principal,
   con exploración root y montaje/desmontaje explícitos, nunca automáticos de
   discos internos. Yazi conserva navegación/preview y herramientas nativas para
   texto, imágenes, PDF, multimedia, archivos y hexadecimal de solo lectura.
   Helium es el navegador por defecto y Chromium la alternativa compatible;
   navegador con usuario normal y sandbox, perfil cotidiano en RAM con caché
   acotada y perfil OAuth temporal separado. Inicio condicionado al gestor de
   ventanas, selectores visibles y directorios accesibles, fallback sin DATA en
   arranque CD e identidad D-Bus válida para cada arranque.
3. **Un solo teclado.** Consola, formularios, archivos, navegador y OAuth usan la
   distribución y variante configuradas. Cambiarla actualiza Xorg ya abierto;
   el idioma de interfaz no impone el teclado ni se fuerza España a todos.
4. **Perfiles protegidos desde el arranque.** Bóveda real LUKS2 antes de cockpit,
   shells, SSH y agentes; fallo/cancelación no abre esas vías. Contraseña con
   splash y fallback consola. Se mantienen perfiles automáticos deliberadamente
   sin cifrar y cápsulas antiguas identificadas como legacy; migración explícita
   a LUKS sin duplicar el desbloqueo interior. Protege configuración de perfil,
   recuperación, nube y tailnet, no todo DATA/workspace ni discos ajenos.
5. **Persistencia global cifrada.** «Persistir cambios» separado de Actualizaciones:
   conserva paquetes, ajustes, estado, archivos creados/modificados y borrados.
   Etapas/progreso reales, compresión, integridad, sync, LUKS2 y restauración
   temprana verificada; excluye pseudofs, otros discos y temporales previstos.
   Pareja kernel/initramfs y módulos comprobados; regeneración desde la raíz
   capturada. Fábrica y recuperación/rollback permanecen; no reinicia por guardar.
   No equivale a respaldar todos los discos ni permite retirar el USB en uso.
6. **Actualizaciones operativas.** Todo en RAM, todo persistente o limpiar selección,
   además de decisiones por elemento; controles de instalar y progreso visibles.
   Preflight de espacio antes de modificar, limpieza solo de cachés del updater,
   errores y resultados parciales honestos. Una imagen Rescue completa no cabe
   como actualización solo RAM: se explica y se prepara sin activación prematura;
   componentes y generación derivada se verifican antes de activar. Catálogo
   oficial primero, versión aprobada vinculada a aplicar y rechazo de generaciones
   sin puerta temprana cuando el perfil LUKS la necesita. Se conservan trabajos
   en segundo plano, confirmación, identidad tailnet y generaciones previas.
7. **Nube, NAS y red privada.** Formularios manuales para Drive, OneDrive, Dropbox,
   S3, SFTP, SMB y WebDAV e importación explícita de archivos/directorios. Claves
   relativas, campos secretos ocultos, conservación de campos vacíos y estado
   solo de metadatos. Operaciones privilegiadas por stdin, sin secretos en argv
   ni servidor web administrativo LAN. Tailscale/Headscale con URL, clave o alta
   nativa en navegador, DNS, rutas, tags, nodo de salida y SSH, sujetos al control
   plane. rclone/restic/CIFS/NFS/SSHFS disponibles; guardar destino no transfiere.
8. **Agentes y OAuth.** Se conservan Seguro/Inseguro y clientes nativos; corrección
   de inicio/metadatos Codex y autenticación Antigravity. Navegador compartido con
   CLI dueño de PTY, state, PKCE y callback; documento visible, salto tras carga y
   enlace Continuar sin JavaScript. Retorno del código copiado a la misma PTY en
   el flujo aplicable. Versiones fijadas verificadas con HOME limpio. IA requiere
   Internet/cuenta propia: sin modelos locales, saldo ni suscripciones incluidas.
9. **Orientación y método de trabajo.** AGENT-CONTEXT, bienvenida SSH, Quickstart,
   Toolbox y Secrets renovados; guías canónicas en inglés con respuesta en el
   idioma del propietario, sin pisar sus instrucciones. Nuevas MISSIONS, BACKUP
   y ODD: alcance, observación, plan, ejecución, comprobación y relevo con pruebas.
   ODD adaptado, no instalación del ecosistema Gentle AI ni hooks/revisión global.
   Inventario de recursos/hardware y planificación de backup por escenario sin
   montar/reparar automáticamente; firmware e initramfs portables sin prometer
   compatibilidad física universal.

## Entrega y límites

ISO e IMG.ZST en la web propia; partes IMG, catálogo firmado, sumas, fuentes y
avisos en GitHub. Imager 1.0.0 sigue compatible. Descomprime IMG.ZST antes de la
importación manual; no grabes una parte aislada. Descargar no actualiza un USB.
Consulta VALIDATION-1.1.0.md: se separan pruebas de candidatas y artefacto final,
sin atribuir OAuth real, inferencia, Secure Boot ni prueba de hardware/USB físico.
La tableta USB absoluta que mejoró virt-manager es configuración del hipervisor,
no una modificación de hardware virtual que la imagen pueda aplicar por sí sola.
