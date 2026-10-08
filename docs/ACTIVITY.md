# LA AGUJA Rescue Disk · trazabilidad SSH y consola local

La pantalla local aprovecha el framebuffer del equipo para presentar actividad remota,
red, sesiones, procesos, consumo y Agujita animada. No es un escritorio: no necesita X,
Wayland, navegador ni conexión a Internet para dibujar la interfaz.

## Uso

- Arranque normal: mantiene autologin, Wi-Fi/DHCP, SSH y descubrimiento `.local`.
- Cada sesión SSH autenticada y shell local instrumentada anuncia conexión y desconexión.
- La vista inicial presenta hasta 100 tareas con nombre, estado, resultado y duración.
- ↑↓ seleccionan una tarea; Enter o clic despliega su detalle; Esc o clic derecho lo pliega.
- En detalle, ↑↓/rueda desplazan, PgUp/PgDn cambian página, Inicio/Fin recorren el texto;
  ←→ cambia de comando. La selección se mantiene aunque lleguen tareas nuevas.
- S filtra por sesión; F muestra fallos e interrupciones; B incluye sondeos técnicos.
- L/End vuelve al directo; P pausa la vista; PgUp/PgDn recorren el historial acotado.
- Tab alterna tareas, terminal de actividad, procesos y ayuda. H abre ayuda/herramientas.
- W/2 abre Wi-Fi; Q/1 vuelve a Zsh; `aguja` abre el panel otra vez.
- Sesiones y procesos siguen actualizándose durante la pausa de la vista.
- Agujita parpadea, mira y cambia de expresión según conexión y trabajo activo.
- `3`: guía; `4`–`7`: agentes; `8`: diagnóstico; `9`: contraseña SSH.
- `aguja activity --json`: vista temporal estructurada para agentes.

La vista gráfica usa `/dev/fb0` solo desde una VT local visible, con formatos truecolor
24/32 bits RGB/BGR compatibles y memoria/pitch/offset validados. Usa fuentes DejaVu
instaladas y las ocho poses originales de Agujita. Restablece el modo texto al salir.
Sin framebuffer, formato compatible, permisos de vídeo o Pillow, cae a texto curses
a todo el ancho. Las conexiones SSH y la consola serie no cambian su dispositivo de vídeo.

## Tareas con nombre y resultados auténticos

    aguja run --label "Memoria" -- free -h
    aguja run --label "Revisar hardware" -- sudo -n python3 -

El comando recibe su stdin y entrega stdout/stderr/código de salida sin alterarlos.
La etiqueta no debe contener secretos. Solo los diagnósticos permitidos reflejan salida;
scripts, configuración, autenticación y transferencias permanecen privados por defecto.
Cada tarea puede seleccionarse para ver detalle y salida permitida asociada a su ID.
Las entradas se acotan a 100 tareas y no sobreviven al reinicio. La duración no inventa
porcentaje de progreso ni tiempo restante. Seleccionar una tarea nunca la ejecuta.

### Sondeos Git 128/129

En la notebook se observaron pares cada 30 s enviados por un cliente/editor remoto:
consultas de rama/commit y diff sobre una carpeta sin `.git`. Se reconocen únicamente
secuencias generadas de entorno/cd y consultas Git de solo lectura, incluidas alternativas
`git … || git …`, tras comprobar directorio y ancestros sin repositorio. No se inicializa
un repo ficticio ni se modifica la orden del cliente. Se agrupan por defecto; B permite
inspeccionarlas como «Sondeo Git · carpeta sin repositorio (código N)».

No se ocultan errores de tareas Git normales ni se convierten códigos fallidos en cero.
Tuberías, órdenes desconocidas, escrituras y repositorios reales no se clasifican como
estos sondeos. Las desconexiones y señales reales se distinguen de errores de comando.
Los códigos siguen disponibles por SSH y en `aguja activity --json`.

## Qué se muestra y qué no

La privacidad forma parte de la presentación: no es una grabación indiscriminada.

- Nunca se registran bytes de teclado/stdin ni el contenido de scripts enviados por stdin.
- Los comandos conservan argumentos, rutas, comillas, tuberías y scripts en `-c`/`-e`.
  Los valores de credenciales conocidas, flags/asignaciones de secretos, claves privadas
  y credenciales en URLs se enmascaran; no se oculta el resto de la orden por su nombre.
  El límite de 16384 caracteres por comando se indica explícitamente si se alcanza.
- El detalle muestra ID/sesión, origen, hora, duración, resultado y salida permitida.
  Las líneas largas se ajustan al ancho y se recorren sin perder el final.
- La salida solo se refleja para una lista conservadora de diagnósticos simples.
  Lectura arbitraria de archivos/configuración, intérpretes, pipelines, autenticación,
  herramientas de red y transferencias no publican sus contenidos. `sudo` tampoco
  habilita automáticamente el reflejo de salida.
- No se interpreta ni ejecuta texto recibido para dibujar; ANSI, controles y dirección
  de texto engañosa se neutralizan.
- El filtrado no es una garantía DLP frente a secretos arbitrarios; el agente debe evitar
  imprimirlos o introducirlos en argumentos desde el principio.

El cliente SSH recibe sus bytes originales incluso cuando la pantalla local oculta
un contenido. Una línea oculta no significa que haya fallado el comando.

## Arquitectura y límites

`sshd` entrega sesiones a `/usr/lib/aguja/ssh_session.py` mediante `ForceCommand`.
El wrapper conserva la shell original, PTY/tamaño de terminal, señales, stdin y códigos
de salida. SFTP/SCP/rsync conservan sus protocolos sin intercepción de contenido.
Los hooks `preexec`/`precmd` de Zsh anuncian comandos y resultados por stdin al helper,
sin poner su texto en el argv del propio observador.

`aguja` inicia una shell local instrumentada al salir
del panel, conservando la VT real para volver a abrir el framebuffer y el ratón.
En esa shell local se registran comandos/resultados; su salida se entrega directamente
a la consola y no se replica automáticamente en el monitor.
El lector de ratón solo abre dispositivos con botones y ejes de puntero;
no emite teclas, se ejecuta únicamente mientras el panel local está abierto y renuncia
a la elevación después de abrir los dispositivos. No cambia grupos ni permisos globales.

`aguja-activity.service` verifica credenciales locales del socket, PID/ascendencia y
tiempo de nacimiento del proceso. La vista se publica de forma atómica en
`/run/aguja-activity/snapshot.json`, con sesiones activas, eventos y procesos asociados.
No se escriben transcripciones en `/data` ni se incluye historial de otra máquina.
La vista se vacía al reiniciar y se acota en número/tamaño de eventos, sesiones y procesos.
Un reinicio del monitor conserva el historial filtrado de esa sesión de arranque.

El observador es una ayuda visual, **no un registro forense completo**: el muestreo de
`/proc` puede omitir procesos muy breves; no reconstruye instrucciones internas de
Python/Bash por stdin ni todos los builtins de shells alternativas. Procesos desacoplados
y reparentados, como servidores tmux ya existentes, pueden salir de la ascendencia de la
conexión. Los comandos interactivos detallados corresponden a los hooks de Zsh estándar.

El monitor no modifica permisos de los agentes, no autoriza operaciones y no monta ni
repara discos internos. Si no está disponible, SSH conserva su funcionamiento; el panel
indica que falta el observador y `aguja doctor` comprueba el servicio.

## Verificación de esta versión

Los resultados de la imagen final y las capturas reales de VM se registran en
`docs/activity-0.3.0/`. Las imágenes renderizadas de diseño, separadas del arranque real,
están en `operations/dashboard-0.3.0/`. No confundir una preview PNG con una consola que
haya entrado en modo gráfico. La grabación del USB y la prueba en el portátil requieren
su propia evidencia y no se realizan implícitamente al desarrollar estas funciones.

El 2026-10-04 se grabó y verificó 0.3.0 en el Transcend físico, conservando
configuración/Wi-Fi y datos; quedó sincronizado y desmontado. Véase
[la evidencia de grabación](../operations/release-0.3.0/usb-upgrade-verified.json).
El arranque UEFI/Wi-Fi/SSH de 0.3.0 se comprobó en el portátil. Las lecturas iniciales
del framebuffer no probaban la salida visible: el propietario solo veía el login.
El [hotfix de refresco Intel](../operations/display-hotfix-0.3.0/RESULT.md) corrigió
la salida en vivo, fue confirmado visualmente por Marlon y quedó persistido en el USB.
[Informe físico](activity-0.3.0/physical-laptop/verification.json) ·
[Captura física](activity-0.3.0/physical-laptop/ssh-activity.png).

Contratos utilizados: [OpenSSH ForceCommand](https://man.openbsd.org/sshd_config.5),
[hooks de Zsh](https://zsh.sourceforge.io/Doc/Release/Functions.html).
