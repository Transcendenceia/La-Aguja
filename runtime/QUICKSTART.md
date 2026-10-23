# LA AGUJA RESCUE DISK · Tu consola de rescate

Una entrada pequeña. Control completo.

Manual por niveles, pasos y capturas: https://aguja.transcendenceia.net/docs
(web pública informativa, sin registro). Esta guía de consola no sustituye la preparación del USB.

## Primera vuelta sin reparar nada

1. Arranca el USB correcto desde el menú del fabricante; no selecciones instalación del disco interno.
2. Si el perfil está protegido, se abre antes del menú en la pantalla de arranque. Su frase no es la de SSH ni la clave BitLocker.
3. Comprueba `aguja status`, `aguja doctor` y `lsblk -o NAME,SIZE,MODEL,FSTYPE,LABEL,MOUNTPOINTS`.
4. Distingue USB, disco interno y destino de recuperación. No montes ni repares para completar esta práctica.
5. Si necesitas IA, autentica un proveedor y confirma su estado; no hace falta autorizar los cuatro.
6. Antes de escribir, define copia, destino exacto, procedimiento y verificación. Al terminar, sincroniza y apaga coordinadamente.

Internet no es obligatorio para herramientas locales; sí para IA en nube y alta de tailnet.
Preparar/grabar borra el USB confirmado; arrancar el live no modifica automáticamente los discos internos.


## Listo al arrancar

- La consola local entra automáticamente como `aguja` y muestra **Centro de rescate**.
- El Imager existente prepara una cápsula protegida o arranque directo. Rescue abre la cápsula protegida durante el arranque, antes del menú. La bóveda LUKS nueva se prepara desde la consola local con `sudo aguja profile protect`.
- SSH: usuario `aguja`, contraseña de fábrica pública `aguja`.
- Una contraseña personalizada en aguja.conf reemplaza la de fábrica.
- Una contraseña vacía con clave pública habilita solo esa clave.
- Ethernet conecta por DHCP. El Wi-Fi guardado se activa automáticamente.
- Sin conexión, Centro de rescate permanece abierto. Elige Wi-Fi cuando quieras; puedes trabajar sin Internet.
- La IP se actualiza en el panel: no hace falta reiniciar ni adivinar el nombre de la interfaz.

## Desde otro equipo de la misma red

    ssh aguja@aguja.local
    ssh aguja@IP_MOSTRADA

El nombre `.local` necesita mDNS en el equipo controlador y una LAN que permita multicast.
La IP funciona como alternativa. Si hay dos equipos con el mismo nombre, el panel muestra
el nombre que anuncie Avahi. LA AGUJA Rescue Disk anuncia también el servicio `_ssh._tcp`.
Un puerto personalizado aparece en el comando SSH del panel.

Para un agente que entra por SSH:

    aguja context
    aguja status --json
    aguja tools
    sudo -n id

## Comandos para moverte cómodo

    aguja                      Panel interactivo; flechas, números y Enter
    aguja status               IP actual, SSH, nombre local y huella pública
    aguja status --disks       Añadir inventario de discos
    aguja status --json        Estado sin secretos, legible por un agente
    aguja activity --json      Actividad SSH y procesos en memoria
    aguja run --label "Memoria" -- free -h   Ejecutar una tarea con nombre visible
    aguja wifi                 Configurar Wi-Fi y guardar en el USB
    aguja password             Contraseña SSH personalizada y persistente
    aguja help                 Esta guía
    aguja tools                Herramientas por categoría
    aguja doctor               Comprobar configuración, servicios y red
    aguja doctor --json        Diagnóstico verificable; código 1 si falla una comprobación
    aguja context              Contexto y procedimiento para agentes
    aguja agent codex          También: antigravity, claude, opencode
    sudo -n bash               Root completo, sin pedir contraseña sudo
    tmux new -s rescate        Sesión que sobrevive a una desconexión SSH

Las consolas locales abiertas desde LA AGUJA conservan hasta 10.000 líneas
en memoria, también si no funciona la interfaz gráfica. **RePág** (o
**Mayús+RePág**) abre el historial; usa **RePág/AvPág** o las flechas para
navegar y **Esc** para volver al CLI. Si el terminal transmite eventos de
ratón, también funciona la rueda. En una consola Linux pura, LA AGUJA lee
sólo los movimientos de la rueda del dispositivo local mientras esa consola
esté visible y en modo texto: gira hacia arriba para consultar el historial y
hacia abajo para volver; al llegar al final regresas al prompt. No necesitas X
ni un escritorio gráfico. La rueda no cambia de modo cuando estás en el panel.
El historial no se guarda en archivos. Los CLI que redibujan toda su pantalla
pueden conservar sólo su contenido visible; usa también su navegación nativa.

Zsh está lista: Tab completa comandos y rutas, flecha derecha acepta sugerencias,
Ctrl-R busca en el historial. `ll`, `panel`, `ayuda`, `red`, `wifi` y `herramientas`
son atajos. No necesitas Oh My Zsh, fuentes especiales ni descargar plugins al iniciar.
La shell root opcional sigue siendo Bash; tu consola normal es Zsh.

## Seguir y explorar el trabajo remoto

La vista inicial muestra tareas con estado, duración y salida filtrada. Flechas ↑↓
seleccionan una tarea; Enter o clic abre/cierra su detalle, Esc o clic derecho vuelve a la lista. S cambia
entre todas las sesiones y una sola, F muestra solo fallos/interrupciones, P pausa
la vista, PgUp/PgDn recorren el historial y L vuelve al directo. Tab alterna tareas,
terminal, procesos y ayuda. H abre herramientas, W Wi-Fi, Q consola.

El detalle conserva el comando completo con argumentos, comillas, tuberías y scripts
incluidos en la línea de comandos; solo se enmascaran valores de credenciales.
Se ajusta al ancho sin perder el texto. ↑↓ o la rueda desplazan el detalle;
PgUp/PgDn, Inicio/Fin recorren sus páginas y ←→ cambia de comando sin plegarlo.
El comando seleccionado no cambia cuando llegan tareas nuevas. Se muestran sesión,
origen (SSH o consola local), hora, duración y resultado. Se retienen hasta
100 comandos y 180 eventos, con un límite explícito de 16384 caracteres por comando.

B muestra los sondeos técnicos agrupados: consultas Git automáticas desde un editor
sobre una carpeta sin `.git` no son un fallo del sistema. Sus códigos 128/129 siguen
disponibles en la vista técnica y por SSH; no se convierten en éxitos. Un error real
de una tarea normal conserva su estado y código. Interrupciones por señal se indican
como tales. Una duración transcurrida no es porcentaje de progreso ni tiempo restante.

Para hacer comprensible una operación sin publicar un script o datos privados:

    aguja run --label "Inventario de hardware" -- sudo -n python3 -

El script llega por stdin y no se registra. La etiqueta debe describir la tarea,
sin claves ni datos personales. La salida de diagnósticos reconocidos se muestra
filtrada; la de scripts, cuentas y protocolos solo se entrega al cliente SSH.

## Ver al agente trabajar

La consola local anuncia cada conexión SSH autenticada y la consola local instrumentada, y actualiza comandos, procesos
asociados y salida de diagnósticos permitidos. Agujita cambia de pose y acompaña la actividad.
El panel aprovecha la pantalla con gráficos si el framebuffer está disponible; en equipos
incompatibles usa texto. No necesita un escritorio ni descargas al arrancar.

La vista es temporal, en RAM: no crea un historial de transcripciones en el USB. No graba
entradas interactivas ni contraseñas tecleadas. Credenciales, lectura de configuración privada, scripts recibidos por
stdin y protocolos de transferencia ocultan sus contenidos, sin cambiar la respuesta SSH.
No interpretes una salida ocultada como un comando fallido: comprueba su resultado remoto.

## Autenticación IA · mini navegador local

    aguja login claude
    aguja login antigravity
    aguja login codex
    opencode auth login          Recorrido nativo; no promete navegador para todos sus proveedores

Desde consola local compatible se abre Chromium normal con sandbox y una consola gráfica
unida a la misma PTY del CLI. Tú autorizas el dominio oficial; callback localhost y state/PKCE
siguen siendo del proveedor. Si copias un código, la consola toma foco; pega explícitamente
con Ctrl+Shift+V y Enter cuando el CLI lo solicite. Copiar no entrega ni ejecuta el código.
Cerrar navegador/consola gráfica devuelve al terminal original sin matar el CLI.
Ctrl+] abre una URL pendiente capturada o cierra el asistente activo.

No QR en el recorrido nuevo. En SSH/serie/sin pantalla compatible permanece la URL y el método
nativo; localhost del disco no se reenvía automáticamente al PC remoto. Usa el método remoto
oficial o un reenvío de puerto explícito apropiado, no una URL/code antiguo ni TLS desactivado.
El perfil del navegador vive temporalmente en /run y se retira al cerrar; el token guardado por
el CLI tiene su propio ciclo de vida. Login real e inferencia requieren tu cuenta y no se
certifican solo por una prueba de ventana/pegado. No hay cuenta de LA AGUJA: las descargas son públicas en GitHub. Las cuentas IA y la administración de la tailnet son independientes.

## Tu red privada · Tailscale / Headscale

El Imager Windows/Linux puede incluir alta opcional con tu clave, URL Headscale (vacía para
Tailscale oficial) y nombre del nodo. Solo se inscribe al arrancar con la opción habilitada,
red y perfil disponible/desbloqueado. No prepara un túnel propietario de nuestra plataforma.

    aguja profile status --json  Protección efectiva; el desbloqueo se hace al arrancar
    aguja tailscale status
    aguja tailscale status --json
    ssh aguja@IP_TAILNET         Desde otro equipo autorizado en la misma tailnet
    ssh -p PUERTO aguja@IP_TAILNET

OpenSSH normal usa contraseña/clave pública y puerto del perfil. Tailscale SSH es una opción
avanzada distinta, puerto 22 e identidad/política SSH del control plane. Una clave de alta
no concede acceso universal. No actives Tailscale SSH sin su política compatible.

Estado/identidad de tailnet en RAM: cada reinicio reinscribe. Clave de un uso solo permite
el primer registro; para varios arranques automáticos usa una reutilizable vigente y limitada.
No se promete la misma IP ni limpieza automática de nodos. El operador debe retirar nodos
viejos y revocar claves cuando termine. Revocar una clave no expulsa por sí solo todos los
nodos ya inscritos. Cifra la cápsula del USB: no cifra todo DATA ni protege frente root una
vez desbloqueada. Sin red/tailnet el rescate local continúa disponible.


## Archivos y persistencia

- `/config/aguja.conf`: configuración en la partición FAT AGUJA_CFG; no es un script.
- `/data/workspace`: trabajo y contexto en la partición AGUJA_DATA del pendrive.
- `/usr/share/aguja/AGENT-CONTEXT.md`: instrucciones actuales de esta versión.
- `/data/config-backups`: configuración anterior recuperable, solo accesible con sudo.
- El Wi-Fi y la contraseña personalizada se guardan en aguja.conf, en texto plano.
- Sin USB configurable (solo ISO), los cambios quedan en la sesión actual.
- HOME/tokens solo persisten al elegir `persistent_home=yes`; no se cifran.
- `sudo passwd aguja` cambia solo esta sesión. Para conservarlo, usa `aguja password`.

## Rescate y agentes IA

El sistema instalado y sus discos no se montan ni reparan automáticamente.
Empieza identificando discos y modelo/serie, diagnostica en lectura y acuerda el objetivo.
Usa otro disco para recuperaciones grandes: el USB de rescate no tiene capacidad ilimitada.
La raíz del sistema live está en RAM; tus cambios al OS live no persisten al reiniciar.

Codex, OpenCode, Claude Code y Antigravity se incluyen en la imagen personal completa, aunque no prepares credenciales. Para usar IA necesitan tu propia cuenta
y conectividad para usar servicios IA. Las herramientas tradicionales funcionan offline.
Para ver todo el inventario, usa `aguja tools`; para la guía del agente, `aguja context`.

## Si falta red

    aguja wifi
    nmcli device status
    rfkill list
    aguja doctor

Si no aparece una interfaz Wi-Fi, comprueba hardware/driver con `lspci -nnk`, `lsusb`
y `sudo dmesg`; puedes usar Ethernet o un adaptador USB soportado.
Las redes empresariales y perfiles avanzados se gestionan con `sudo nmtui`.
No se abren puertos del router ni se crean túneles a Internet automáticamente.

## Instalar proveedores opcionales

Los cuatro CLI están preinstalados en la imagen personal completa. Configurar después omite las credenciales, no los ejecutables. `aguja doctor` señala cualquier CLI ausente como fallo. La imagen pública histórica 0.9.0 no incluye Claude/Antigravity; no confundirla con esta imagen personal completa.

## Control e idioma (0.9.7)

Cada `aguja agent NOMBRE` muestra Seguro (predeterminado) e Inseguro (YOLO). Seguro pide confirmación para las herramientas; Inseguro conserva la ejecución autónoma. Desde 0.9.10, Codex Seguro usa sandbox workspace-write, red deshabilitada y aprobación humana para salir, además de confirmar cada herramienta. El usuario conserva sudo fuera del sandbox. Escape cancela. Los ejecutables directos conservan sus opciones nativas.

`aguja locale` permite cambiar idioma, teclado y variante. La configuración del Imager se aplica antes de desbloquear y las preferencias locales guardadas prevalecen al reiniciar. Solo esos datos no secretos quedan públicos; las credenciales siguen cifradas.

`aguja donate` muestra un QR local para apoyar voluntariamente el proyecto. No hace falta donar ni iniciar sesión para usar LA AGUJA.

La actividad muestra comando, actor, estado y salida, enmascarando únicamente credenciales. La ventana de actividad es acotada (2048 eventos, 100 tareas); no sustituye un archivo de auditoría completo. La entrada de contraseñas y protocolos binarios no se graba.

Las consultas del propio monitor devuelven el estado íntegro al solicitante. En el panel se registran como consultas, no se duplica recursivamente el historial dentro del historial.

## Virtualización y herramientas por descubrir

QEMU/KVM o TCG, qemu-img/qemu-nbd, OVMF/UEFI y SeaBIOS vienen incluidos desde
0.9.11. No se inicia ninguna VM automáticamente. Consulta el presupuesto de
RAM/disco y `/usr/share/aguja/TOOLBOX.md`: incluye ejemplos y sugerencias opcionales
(REA, Rizin, Unblob, Volatility, btop, lnav, etc.), sin descargarlas. Los agentes
pueden investigar e instalar otras herramientas según la misión y los recursos.
La bienvenida SSH muestra estos caminos también al conectarse sin terminal.


## Private recovery and credentials / Recuperación y credenciales

Read `/usr/share/aguja/SECRETS.md`; run `aguja secrets --json` and `sudo aguja recovery status --json` for metadata only. The early boot profile gate also unlocks matching recovery keys in RAM. Select with `sudo aguja recovery list --json`; never print key values. The native `open` action requires an exact disk and defaults to read-only, without mounting.

## USB-persistent updates / Actualizaciones persistentes

`aguja update status --json` shows the USB generation and cached notices. `aguja update check --json` checks only; `aguja update menu` offers optional persistent system, live and harness upgrades. Read `/usr/share/aguja/UPDATES.md` and `/usr/share/aguja/skills/live-updates/SKILL.md` before updating. Root generations are separate from profiles/secrets/DATA workspaces. Updates take effect on next boot, not automatically; retain factory and previous generations. Ordinary apt/CLI updates in RAM are not persistent. Never upgrade a target internal disk or reboot without the owner’s requested scope.


## Rescue 1.1 · equipo, misiones y respaldos

`aguja hardware --json`: inventario y recursos actuales. `aguja plan --json`: opciones
de respaldo, sin tocar discos. `aguja storage status --json` / `sudo aguja storage
configure`: cloud y NAS; credenciales en LUKS o solo RAM. Lee MISSIONS.md y BACKUP.md.
El menú se organiza en Trabajar, Agentes, Conectar y Sistema; ↑↓/Enter o ratón.
El perfil protegido se abre antes del panel, SSH y agentes, no desde el menú.
La preparación automática del Imager sigue funcionando. Cápsulas AES antiguas son
compatibles en el mismo paso temprano, pero no se presentan como LUKS.
`sudo aguja profile protect` convierte explícitamente la configuración local a una
bóveda LUKS2; exige consola local, confirmación y frase nueva. No cifra DATA ni
borra de forma segura rastros previos de flash. No requiere actualizar Imagers.

Al convertir un perfil anterior, se valida su frase antigua y se guardan perfil y
resguardos normalizados dentro de LUKS: el siguiente arranque requiere solo la frase
LUKS nueva. La identidad tailnet se conserva si su estado anterior se puede validar.
