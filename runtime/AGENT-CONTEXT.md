# LA AGUJA Rescue Disk — Instrucciones para el agente de rescate

Estás en un Linux live x86-64 de rescate iniciado desde un USB, NO en el sistema instalado.
Marca: **LA AGUJA Rescue Disk**. Mascota: **Agujita**. Identificadores técnicos: `aguja`, `AGUJA_*`.
Esta es la guía canónica instalada en `/usr/share/aguja/AGENT-CONTEXT.md`.
Las copias de trabajo pueden contener instrucciones del propietario: léelas también.

## 1. Orientación inicial por SSH o consola

Usuario: `aguja`. `sudo -n` concede root completo en el hardware, sin contraseña sudo.
No hay sandbox ni entorno de contenedores: cada cambio puede afectar al equipo real.
La contraseña SSH de fábrica es pública y conocida, `aguja`; puede haber una personalizada
o acceso solo por clave. Nunca imprimas credenciales personalizadas.

Antes de actuar:

    aguja status --json
    aguja doctor
    aguja doctor --json
    aguja tools
    lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS
    findmnt
    sudo -n id
    date

`status --json` ofrece IPs/interfaz, hostname/mDNS, puerto/estado SSH y workspace,
sin contraseñas, tokens ni keyfiles. Una IP no prueba Internet ni acceso a un proveedor.
El estado vivo tiene prioridad sobre esta guía y sobre recuerdos de otro equipo.
Determina con el usuario qué objetivo, sistema y disco quiere rescatar.

Da nombres públicos y breves a los trabajos visibles usando
`aguja run --label "Inventario de hardware" -- sudo -n python3 -` para scripts
recibidos por stdin. No incluir secretos en la etiqueta ni en argv. La etiqueta,
estado y duración aparecen en el panel; los scripts/entradas privadas no se registran.
Diagnósticos simples como `aguja run --label "Memoria" -- free -h` permiten salida
filtrada. Los códigos y bytes recibidos por SSH conservan su significado.

## 2. Almacenamiento y persistencia

- `/` es squashfs + overlay RAM. Modificar el Linux live NO instala ni repara el OS del disco.
- `/run/live/medium` es el propio medio arrancable. Nunca lo uses como disco objetivo.
- `/config/aguja.conf` pertenece a AGUJA_CFG en el USB; contiene valores literales privados.
- `/data` es AGUJA_DATA del mismo USB, no una partición interna.
- `/data/workspace` conserva informes/scripts/archivos de trabajo cuando DATA está montada.
- HOME está en RAM salvo `persistent_home=yes`; su persistencia NO añade cifrado.
- La host key SSH se crea para este USB y se conserva en `/data/ssh`.
- `/data/config-backups` conserva configuraciones previas, solo accesibles con sudo.
- `/mnt/target` es una ruta convencional para un montaje explícito del disco que se rescate.

Los discos internos no se montan, reparan ni particionan al iniciar.
Identifica modelo, serie, tamaño, particiones y modo UEFI/BIOS antes de escribir.
El USB live puede aparecer como disco ISO9660 con particiones/vistas loop: eso es normal.
Comprueba `findmnt`, `lsblk --tree` y los offsets antes de sacar conclusiones sobre un loop.
No confundas AGUJA_CFG/DATA ni el USB de rescate con el disco objetivo.

## 3. Consola, conectividad y sesiones

La consola local entra automáticamente; Zsh tiene Tab, sugerencias y colores listos.
`aguja` abre el panel interactivo. `aguja help` explica uso y comandos.
La pantalla física anuncia las sesiones SSH autenticadas y muestra comandos y procesos
asociados; `aguja activity --json` devuelve la misma vista temporal. Solo se refleja la
salida de diagnósticos permitidos: las entradas de teclado nunca se registran, y las
operaciones sensibles/protocolos/scripts por stdin no exponen contenidos. No vuelques
credenciales pensando que el filtro siempre identificará cualquier secreto desconocido.
El monitor no cambia permisos ni autoriza acciones y no conserva transcripciones en DATA.
En SSH conserva una sesión con `tmux new -s rescate` y reconecta con `tmux attach -t rescate`.
No reinicies ni apagues sin coordinarlo: perderás la conexión y los cambios de la raíz RAM.

Red:

    aguja network --wait       # JSON; espera hasta 30 segundos por una IP
    aguja wifi                 # asistente local/SSH interactivo; guarda Wi-Fi en el USB
    nmcli device status
    rfkill list
    ip route
    sudo nmtui                 # perfiles avanzados, empresariales y Ethernet
    avahi-browse -rt _ssh._tcp  # descubrir servicios SSH en una LAN con mDNS

La red guardada se activa automáticamente; sin red aparece el asistente en la consola.
Avahi anuncia el hostname `.local` y SSH en la LAN; el panel refleja el nombre real si hay colisión.
No hay publicación WAN, port-forwarding de router ni túneles automáticos.
No cambies la red si estás trabajando por ella sin una vía de reconexión.
`aguja password` pide y guarda una contraseña personalizada sin imprimirla.
`sudo passwd aguja` solo cambia la contraseña de la sesión actual.

## 4. Herramientas y posibilidades

Consulta `aguja tools`: es el inventario comprobable de los binarios instalados.

| Objetivo | Herramientas |
|---|---|
| Sesiones/scripts | Zsh, Bash, tmux, Python, Git, jq, ripgrep, nano |
| Copiar/recuperar | rsync, scp, GNU ddrescue/ddrescuelog, TestDisk/PhotoRec |
| Diagnóstico físico | smartctl, nvme-cli, hdparm, lshw, lspci, lsusb |
| Particiones/arranque | lsblk, blkid, parted, gdisk/sgdisk, efibootmgr, GRUB BIOS/UEFI |
| Filesystems | e2fsprogs, Btrfs/XFS, NTFS, FAT, exFAT |
| Cifrado/volúmenes | cryptsetup/LUKS, LVM, mdadm, Dislocker (con clave BitLocker) |
| Desplegar un OS | debootstrap, arch-install-scripts, wimlib; instaladores/ISOs oficiales |
| Acceso/red | NetworkManager/nmtui/nmcli, OpenSSH, curl/wget, Avahi |

No incluye escritorio, Windows/WinPE, licencias, modelos IA locales ni un instalador universal.
La presentación gráfica directa al framebuffer no es un escritorio de aplicaciones.
Una ISO Windows no se convierte en instalador simplemente grabándola con dd.
Para otros sistemas/hardware, comprueba compatibilidad y documentación oficial.

Los cuatro agentes nativos están disponibles:

    aguja agent codex
    aguja agent antigravity
    aguja agent claude
    aguja agent opencode

El launcher usa usuario normal con sudo disponible, no Claude directamente como root.
El modo `full` desactiva aprobaciones del arnés; no autoriza tareas ajenas al objetivo del usuario.
Las cuentas, login/inferencia de proveedores y conectividad a Internet se verifican por separado.
No hay tokens ni cuentas de proveedor incluidos de fábrica.

## 5. Procedimiento de rescate

1. Acordar objetivo y destino exacto; capturar diagnóstico y estado actual.
2. Empezar por lectura. Si el disco falla físicamente, minimizar accesos repetidos.
3. Crear imagen/backup recuperable en un medio distinto y con espacio suficiente.
4. Trabajar sobre copia cuando corresponda. No ejecutar fsck en un filesystem montado.
5. Un montaje `aguja mount-ro DEVICE RUTA` solicita lectura; un journal puede requerir
   `noload` (ext4) o `norecovery` (XFS). Para peritaje, bloqueo de escritura/imagen.
6. Confirmar operaciones destructivas o irreversibles que no estén ya autorizadas.
7. Verificar archivos recuperados, servicio o arranque real: exit code 0 no basta.
8. Guardar informe y rollback en el workspace sin secretos, antes de reiniciar.

No vuelques aguja.conf, contraseñas Wi-Fi/SSH, claves privadas, tokens ni archivos OAuth
al chat, logs, historial o repositorio. No reemplaces permisos/accesos del propietario
por una política distinta: trabaja dentro del alcance acordado y conserva reversibilidad.

## 6. Acceso remoto

Usa OpenSSH por LAN o por tu Tailscale/Headscale. No existe relay ni conector propietario. Mantén la comprobación de huellas y las políticas de tu tailnet.
