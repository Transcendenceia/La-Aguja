# Rescue: agentes, archivos y persistencia global

## Objetivo y alcance

Corregir el inicio de Codex y OAuth de Antigravity desde Agentes. Sustituir Yazi
como explorador principal por un gestor gráfico ligero con ratón visible y
montaje/desmontaje explícitos. Añadir «Persistir cambios» al menú principal:
guardar el sistema live completo, no solo actualizaciones, con progreso medido,
integridad y recuperación. Actualizaciones solo instala; persistir es independiente.

Propietario: Angie. Fuente: este checkout. Build y QA: directorio aislado
`~/Aguja/rescue-global-20261023` en CachyOS, con prioridades y memoria acotadas.
No usar teclado, ratón, ventanas ni navegador del host. No tocar Imagers, USB
personal, credenciales reales, discos de trabajo, publicar ni reiniciar el host.

## Criterios observables

- Codex abre desde menú en Seguro/YOLO. Cada agente incluido llega a su interfaz
  nativa o login; OAuth abre el navegador del live, sin consumir cuentas reales.
- Explorador root abre sin demora de render TUI; crear/editar un fixture, montar
  y desmontar un disco sintético y cerrar normalmente al menú con SSH intacto.
- Entrada principal «Persistir cambios» separada de Actualizaciones; progreso
  real durante escaneo/copia/compresión/verificación/sync, sin porcentajes ficticios.
- Guardado global: archivos creados/modificados/borrados, paquetes y ajustes
  sobreviven reinicio en USB sintético. Excluir pseudofs/otros discos y secretos
  efímeros; proteger datos privados con el perfil cifrado donde corresponda.
- Imagen final BIOS/UEFI, hash y coherencia de fuente; documentar exactamente
  alcance probado y pendiente sin atribuir consentimiento/inferencia no hechos.

## Línea base y reversión

Commit `008e22d191d81f4896da72422b14b1aafb6645e4` limpio. Entrega previa intacta en
CachyOS `rescue-efficient-20261023/final`. VM win11 ejecuta IMG 1.2.0 como CD,
sin CFG/DATA y sin montar discos de trabajo. Conservar XML y esa entrega.
CT: raíz 22 GiB libres, 7.7 GiB RAM disponibles. CachyOS: raíz 243 GiB libres,
5.4 GiB RAM disponibles en observación inicial. No QEMU/build local antiguo activo.

## Estado final · 24/10/2026

Completado y verificado. Las fuentes, build y todos los artefactos permanecen
locales; no se publicaron ni se grabó un USB físico. CachyOS y win11 conservaron
su sesión/proceso original. No hubo entrada dirigida al escritorio anfitrión.

Correcciones: loop readonly explícito antes de cryptsetup en initramfs,
prompt local fuera del splash, regeneración desde la raíz capturada y selección
de kernel/initramfs por versión Debian con comprobación real de módulos mediante
`lsinitramfs`. El arranque final usa `6.12.113+deb13-amd64`.

Matriz sobre la misma IMG final:

- Fábrica BIOS y Thunar root desde cockpit, con cierre normal y SSH posterior.
- Captura global nueva, compresión, compactación, verificación y activación LUKS2.
- Bloqueo previo a contraseña y snapshots BIOS y UEFI: creados /etc y /root,
  modificado /etc/issue, borrado /etc/motd, paquete hello y estado de aplicación
  restaurados; temporales excluidos.
- Rollback confirmado desde recuperación y siguiente arranque normal de fábrica
  UEFI, conservando el snapshot anterior. API de rollback comprobada además desde
  el snapshot recuperado con código final en RAM y consulta automática inactiva.

Suite Debian equivalente: 283 casos, 282 PASS y uno omitido por GPT/FAT; ese
caso pasó por separado con PATH de sbin completo. Todos los 283 casos tienen PASS
entre ambos entornos. Source→rootfs→squashfs y guard dentro del initramfs cotejados.

## Entrega y evidencia

Artefactos locales: `dist-global/`. Copia en CachyOS:
`~/Aguja/rescue-global-20261023/final/`, con IMG, ISO, fuentes, inventarios y hashes.

- IMG SHA256: `44737573d522e78f3e69a9a648d3b21e3c7d8be73a2c0a847942ffddc775160f`.
- ISO SHA256: `caf47b710d344309d4cbfdbd72a1a74d8c6696d0fd205215b91aa5df29158ca4`.
- Informe: `/home/angie/clawd/operations/rescue-global-20261023/DELIVERY.md`.
- Resultado consolidado: `final-validation-result.json` junto al informe;
  resultado inicial del auxiliar conservado sin reemplazar.

El auxiliar inicial esperaba el prompt por serial aunque la consola prevista es
VGA. Se revisaron capturas reales de ambos desbloqueos y se anotó explícitamente
la observación (no como salida serial), permitiendo al auxiliar introducir su
clave sintética por QMP. Se retuvieron capturas, hashes y logs previos a anotación.
El auxiliar corregido no espera ese prompt en serial.

La primera llamada extra de rollback retornó error sin stderr; el auxiliar no
guardó stdout, por lo que no se atribuye causa. La comprobación suplementaria
confirmó la selección persistida y el siguiente boot UEFI de fábrica. No confundir
el error del auxiliar conservado con un éxito automático ni con fallo de
persistencia: todos los fixtures BIOS/UEFI pasaron antes de esa llamada.

Rollback de fuente: baseline/diff y archivos nuevos conservados bajo
`/home/angie/clawd/operations/rescue-global-20261023/resume-*`; entrega previa
1.2.0 intacta. QA usa solo archivos y credenciales sintéticas. Hardware físico,
Wi-Fi/GPU reales y login/inferencia de proveedores no forman parte de esta prueba.
