# LA AGUJA · Manual para usuarios

8 de octubre de 2026 · versión pública 0.9.0 en preparación.

[Manual navegable con capturas, búsqueda e impresión](https://aguja.transcendenceia.net/es/docs). [PDF del manual](https://github.com/Transcendenceia/La-Aguja/releases/download/v0.9.0/LA-AGUJA-Manual-usuarios-20261007.pdf). Acceso privado conservado.

## Mucho más que un disco de rescate: un centro móvil de operaciones.

LA AGUJA reúne un Linux arrancable para cualquier PC, nodos ESP32 de bolsillo para tu red privada, un grabador multiplataforma y una skill para agentes IA: todo sobre tu hardware y tu propia tailnet.

Dale a un agente avanzado un objetivo, no solo un comando de reparación. Puede analizar el hardware disponible, elegir herramientas, generar y ejecutar scripts dentro del alcance que autorices y comprobar el resultado. El sistema del disco no necesita arrancar, ni siquiera existir.

La sesión live usa una capa de escritura en RAM sobre la imagen de solo lectura del USB. Es Linux, no firmware, y no se copia todo el USB a RAM. Los discos internos permanecen intactos al inicio; escribes en ellos cuando decides usarlos.

Incluye clientes IA con acceso root, SSH, Python, Git, herramientas de discos, debootstrap y arch-install-scripts. Amplía la sesión con paquetes compatibles: Desde 0.9.11 se incluyen QEMU x86, qemu-img/qemu-nbd, OVMF y SeaBIOS; usa KVM si está disponible o TCG, más lento, como alternativa. Los motores de contenedores y las herramientas de compilación siguen siendo adicionales; comprueba RAM, almacenamiento y compatibilidad. Guarda los resultados importantes explícitamente; el estado en RAM es temporal. La IA en nube requiere red y tu cuenta, no un modelo local incluido.

## Tu primer USB, sin complicarte

Objetivo de esta primera vuelta: **ver el panel de LA AGUJA y conocer tu equipo**. No vamos a reparar, formatear ni instalar el sistema interno. La única escritura necesaria para prepararlo es la del pendrive elegido.

Necesitas un PC Windows x64 o Linux x86-64 para preparar el USB, un pendrive vacío o respaldado que supere el tamaño real de la imagen y un equipo compatible donde probarlo. Para esta ruta usa cable Ethernet si puedes. Internet ayuda a descargar; con una imagen local y los componentes necesarios, preparar no exige cuenta web.

- **Descarga Flash Imager para tu sistema.** Ábrelo como usuario normal. Es la app preparadora, no el sistema de rescate. [Ver los formatos y su comprobación](https://aguja.transcendenceia.net/es/docs#descargas).

- **Elige la imagen de Rescue Disk.** Pulsa Buscar versión estable sin registrarte, o Seleccionar imagen si ya tienes la `.img`. Un EXE o un AppImage no se graba en el USB.

- **Deja Ethernet en Automática (DHCP).** En Red, usa un nombre como `rescate-ejemplo`, elige idioma y teclado. Wi-Fi puede quedar vacío si usarás cable. [Qué significa cada campo](https://aguja.transcendenceia.net/es/docs#red).

- **Personaliza SSH.** En Acceso SSH, usa Crear una contraseña única o pega una clave pública propia. Conserva el puerto 22 si no necesitas otro. Esa contraseña sirve para entrar al live, no para desbloquear Windows.

- **Deja IA sin preconfigurar y red privada desactivada para esta prueba.** No necesitas ninguna de ellas para arrancar y consultar el equipo. Podrás iniciar sesión en IA después.

- **En Crear disco, revisa el resumen y la protección.** Si hay secretos, elige Desbloquear al arrancar y guarda la frase fuera del USB. La necesitarás físicamente en el equipo de rescate.

- **Busca el USB y confirma su identidad.** Pulsa Buscar USB disponibles, selecciona tu pendrive y luego Preparar y grabar USB. Compara modelo, capacidad y serie en la confirmación. Si dudas, cancela; no lo averigües grabando.

- **Espera el resultado de lectura verificada.** Autoriza UAC/Polkit cuando lo pida la operación. No retires el USB mientras trabaja. Ahora tienes un medio preparado; aún falta probar que arranque en tu equipo.

- **Arranca desde el USB.** Usa el menú de arranque del fabricante. Si cifraste el perfil, abre la consola local y ejecuta `aguja profile unlock`. [Ver arranque y desbloqueo](https://aguja.transcendenceia.net/es/docs#arranque).

- **Comprueba que llegaste al live.** Debes ver el panel de LA AGUJA; en su consola ejecuta los comandos de abajo. Identifica el USB y los discos internos sin montarlos. Después puedes apagar el live y volver a tu sistema normal.

```
# En el Rescue Disk, no en PowerShell del PC preparador
aguja status
aguja doctor
lsblk -o NAME,SIZE,MODEL,FSTYPE,LABEL,MOUNTPOINTS
```

### Así sabes que la primera vuelta terminó

Viste el panel, comprobaste el estado y reconociste el USB frente al almacenamiento interno. **No necesitas recuperar un archivo ni autenticar cuatro proveedores** para completar este aprendizaje. Si no hay Internet, el inventario local sigue disponible.

**Dos roles:** el PC preparador crea el pendrive; el equipo de rescate lo arranca. Pueden ser el mismo equipo en momentos distintos, pero no confíes en poder preparar el USB dentro de un Windows que ya no inicia: prepáralo antes o utiliza otro PC.

## Las palabras que vas a encontrar

No tienes que memorizar estas palabras: vuelve aquí cuando un paso te resulte confuso.

| Palabra | En lenguaje cotidiano | En LA AGUJA |
| --- | --- | --- |
| Live / Rescue Disk | Un sistema que puedes arrancar sin instalarlo en tu disco interno. | El Linux del pendrive. Su raíz usa RAM y sus datos pueden vivir en el USB. |
| Flash Imager | La aplicación que prepara el pendrive. | Se abre en Windows/Linux; no repara por sí misma el PC averiado. |
| Imagen .img / ISO | Un archivo que representa un medio completo, no una foto. | La IMG es el disco configurable del Imager; la ISO sirve para recorridos de arranque como VMs. No son intercambiables aquí. |
| Disco / partición / montaje | El dispositivo completo / una zona de él / hacer accesibles sus archivos. | /dev/sda puede ser un disco y /dev/sda1 una partición; esas letras cambian. Se identifican, no se adivinan. |
| IP / puerto / DHCP | Dirección de red / puerta de un servicio / asignación automática de dirección. | SSH usa la IP actual y su puerto. DHCP evita inventar una dirección de otra red. |
| Terminal / CLI | Una ventana donde escribes órdenes y lees respuestas. | El Imager abre un terminal para el CLI oficial de IA; el live también tiene consola propia. |
| SSH / huella | Conexión cifrada para manejar otra consola / identidad comprobable del servidor. | La cuenta es aguja. Compara la huella antes de confiar en la primera conexión. |
| Root / sudo | Permiso de administrador del Linux. | Control completo. No significa «solo lectura» ni evita equivocarte de disco. |
| Tailnet / Headscale | Red privada de dispositivos autorizados / servidor propio para administrarla. | Opcional para soporte remoto; necesita alta, conectividad y política compatible. |
| Auth key / API key / OAuth | Clave para registrar un nodo / clave de un servicio / consentimiento de inicio de sesión. | Son tres cosas distintas. Ninguna sustituye la contraseña SSH o la frase del perfil. |
| Cápsula / perfil .aguja | Configuración que viaja dentro de la imagen / plantilla reutilizable cifrada. | La cápsula se carga al arrancar. El archivo .aguja se abre en el Imager para repetir una preparación. |
| SHA-256 / verificación | Una huella de los bytes / comparación de lo leído con lo esperado. | Ayuda a detectar archivos o grabaciones distintos. No garantiza que el hardware pueda arrancarlos. |
| BitLocker / LUKS | Cifrado de volúmenes. | Leerlos requiere la clave apropiada. La frase del perfil del USB no descifra el disco interno. |

## Antes de empezar: equipo, permisos y respaldo

- **Confirma el equipo.** La imagen es x86-64. El proyecto contempla arranque BIOS y UEFI; ARM, todos los controladores Wi-Fi y cualquier firmware no están garantizados. No se ofrece una cadena Secure Boot firmada universal: revisa el firmware y la política del propietario antes de cambiarlo.

- **Elige un USB cuya capacidad real supere el tamaño de la imagen.** Compruébalo en el catálogo y la aplicación. «16 GB» comerciales y GiB mostrados no son la misma medida. Guarda fuera del USB lo que quieras conservar: la grabación lo reemplaza.

- **Obtén permiso sobre el equipo y los datos.** Define qué disco se investigará, qué datos se pueden copiar, qué proveedor IA se usará y cuándo hay que detenerse. Un propietario de la máquina no siempre es el titular de todos sus datos.

- **Prepara conectividad.** Ethernet DHCP suele ser el camino más simple. Guarda Wi-Fi si hace falta. Para alta en tailnet y OAuth necesitas red, DNS, HTTPS y hora correcta; el rescate local sigue siendo posible sin Internet.

- **Prepara una copia o destino de recuperación.** Debe ser distinto del dispositivo que falla. Si el disco hace ruidos, desaparece o acusa errores de lectura, evita reparaciones repetidas sobre el original: puede convenir una imagen primero y trabajo sobre la copia.

No necesitas tener instalado el sistema del disco interno para leer sus particiones desde el live. Sí necesitas las claves correctas de BitLocker/LUKS cuando haya cifrado: LA AGUJA no lo rompe ni evita la autorización.

### Respaldo de USB: Windows y Linux no ofrecen lo mismo

**Windows:** el respaldo previo integrado todavía no está implementado. La opción no se ofrece y el backend rechaza una solicitud de respaldo antes de escribir. Copia los archivos o haz una imagen con tu herramienta de respaldo antes de grabar. **Linux:** hay respaldo completo opcional con verificación, desmarcado por defecto; exige espacio suficiente y permisos. El respaldo del USB no es un respaldo del disco interno del equipo que vas a rescatar.

## Flash Imager 1.2.0: descargas, perfiles USB, IoT ESP32 y Agent Skill 1.3.0

Descarga el EXE portátil de Windows o AppImage, DEB o archivo portátil Linux de la release oficial v1.2.0. Ábrelo como usuario normal; solo las operaciones físicas sobre USB piden UAC/Polkit. La versión Windows incluye esptool.exe oficial y no necesita Python para flashear ESP32.

En modo USB, Perfiles y USB guarda y abre plantillas .aguja cifradas (incluyendo ajustes ampliados imager-profile-v2 de Wi-Fi, NAS/nube, variables literales y tailnet) y edita el CFG de un USB existente sin regrabar. En modo IoT · MCU, Flash Imager 1.2.0 detecta automáticamente el chip ESP32 por USB, integra 6 firmwares v1.4.0 precompilados para 11 placas, genera particiones NVS v2 de 48 KiB en JS puro (SoftAP desactivado por defecto), verifica el arranque por serie y permite borrar la flash en 1 clic.

Para automatización sin ventana ni Electron, Agent Skill 1.3.0 ofrece el mismo motor GPT/FAT32 y generador ESP32 NVS v2 (iot-boards, iot-nvs) con Node 22+, deteniéndose en archivos verificados. Actualizaciones del Imager consulta el catálogo firmado y solo descarga cuando tú eliges.

## Paso 1 · Elegir una imagen compatible

En **Imagen**, usa el catálogo o **Seleccionar imagen**. El Imager trabaja con `.img` sin comprimir. Si recibiste `.img.zst`, descomprímelo primero en una carpeta con espacio suficiente. Una ISO no sustituye el disco configurable AGUJA_CFG/AGUJA_DATA del recorrido del Imager.

```
# Descomprimir un archivo recibido; no escribe ningún USB
zstd -d aguja-0.8.0-amd64.img.zst
```

![Flash Imager: selección de imagen y comprobación manual](../server/public/docs-images/linux-01-imagen.png)

Captura del paquete Linux 0.9.0 real con estado de ejemplo. ① Seleccionar imagen calcula su SHA. ② Buscar versión estable consulta el catálogo firmado. ③ Comprobación manual es opcional. No representa un login ni una autorización de proveedor.

El estado distingue **versión oficial verificada**, **SHA comparado** e **imagen local de origen no comprobado**. Si la comprobación manual no coincide, no se usa la nueva selección. No ignores esa diferencia para un medio que tendrá acceso completo a tus discos.

Para alta automática de tailnet, la imagen debe anunciar `tailscale-profile-v1`. Una imagen antigua se rechaza antes de preparar el perfil; actualizar solo el EXE/AppImage no añade Tailscale a un live ya construido. Mantén Imager e imagen compatibles. También existen guardas de idioma/teclado e importación OAuth Antigravity.

### Qué debes ver al terminar este paso

La app debe mostrar el archivo seleccionado, su tamaño y el resultado de la comprobación. Si no coincide con el SHA esperado, detente y descarga de nuevo desde la fuente correcta. Un nombre con «oficial» no prueba procedencia. Para el USB final y una imagen privada intermedia necesitas espacio libre suficiente; el espacio del PC y la capacidad del pendrive son dos comprobaciones distintas.

## Paso 2 · Red, idioma y nombre del equipo

- Elige idioma, distribución y variante de teclado. El idioma de la app es independiente del teclado que tendrá el disco. Prueba los signos de tu contraseña antes de depender de una consola remota.

- Da al equipo un nombre simple con minúsculas, números y guiones. Evita incluir el nombre completo de una persona o información de un cliente.

- Usa Ethernet automático (DHCP), salvo que conozcas dirección, prefijo, puerta de enlace y DNS correctos de esa red. Una IP estática de otra red puede impedir conectarte.

- Si necesitas Wi-Fi, escribe SSID, seguridad y contraseña; marca red oculta solo si corresponde. Importar desde tu PC evita errores de escritura, pero no garantiza que el hardware del equipo rescatado tenga ese controlador.

![Flash Imager: conectividad, idioma y teclado](../server/public/docs-images/linux-02-red.png)

Captura Linux 0.9.0 con nombre de equipo de ejemplo. Revisa idioma/teclado antes de SSH; DHCP y Wi-Fi son configuraciones distintas. La app puede pedir permisos locales para importar una contraseña Wi-Fi existente.

Una interfaz con IP no garantiza salida a Internet. Una tailnet necesita acceso al plano de control y, según la topología, a relés de transporte. Prueba DNS y conectividad en el live cuando arranque. El Imager no inscribe tu PC personal ni reemplaza su cliente VPN al guardar estos datos.

### Ejemplo sencillo, campo por campo

- **Nombre del equipo:** `rescate-ejemplo`; aparecerá en la red. No es el nombre de tu cuenta.

- **Ethernet → Automática (DHCP):** el router asigna la dirección. No escribas una IP fija salvo que conozcas esa red.

- **Nombre de la red Wi-Fi:** el SSID exacto, respetando mayúsculas. La contraseña puede ser distinta de la de administración del router.

- **Idioma de la aplicación:** cambia lo que ves en el Imager. **Idioma del sistema / teclado:** cambia el live que prepararás. Son ajustes separados.

**Resultado esperado:** el resumen refleja el nombre y el tipo de red. Todavía no has conectado el equipo de rescate: eso se comprobará después de arrancar.

## Paso 3 · SSH: tu puerta de entrada

Selecciona una contraseña sólida o pega la **clave pública** de quien asistirá. La clave privada permanece en su equipo: nunca la pegues en el Imager. Puedes usar un puerto diferente de 22 si tu política de red lo contempla. Esa configuración vale para OpenSSH, tanto en la LAN como por la IP privada de la tailnet.

![Flash Imager: contraseña o clave pública y puerto SSH](../server/public/docs-images/linux-03-ssh.png)

Captura con contraseña sintética oculta y puerto 50222 de ejemplo. La contraseña del perfil no aparece en el resumen. Un puerto distinto no sustituye la autenticación ni las reglas de acceso.

```
# En el equipo del técnico; solo lee una clave pública ya existente
cat ~/.ssh/id_ed25519.pub

# PowerShell equivalente
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

Si no existe una clave, genera una en tu equipo con tu herramienta SSH y protégela según tu política. No compartas `id_ed25519` sin `.pub`. El disco de fábrica puede tener acceso conocido para puesta en marcha: **personaliza SSH antes de llevarlo a una red compartida**.

Al conectar por primera vez, compara la huella anunciada en la pantalla del Rescue Disk con la de tu cliente SSH. Si cambió tras regrabar o cambiar de USB, verifica la causa; no desactives `StrictHostKeyChecking` para hacer desaparecer el aviso. La dirección de tailnet puede cambiar entre registros.

## Paso 4 · Preparar IA en el Imager

Abre **Herramientas IA**. Encontrarás Codex CLI, Antigravity CLI, Claude Code y OpenCode. Puedes preparar uno, varios o ninguno; las herramientas locales de diagnóstico no requieren tenerlos todos autenticados.

![Herramientas IA de Flash Imager Linux 0.8.2](../server/public/docs-images/imager-ia.png)

Paquete Linux real 0.9.0. Las tarjetas muestran comprobación/instalación, modo y acciones de sesión. No se autorizó ninguna cuenta en esta captura; Linux y Windows comparten este recorrido, pero esta no es una captura Windows.

| Quiero… | Elijo… | Qué pasa realmente |
| --- | --- | --- |
| Aprender primero, sin configurar IA | Configurar después | El live arranca; puedes iniciar sesión después si tienes red y cuenta. |
| Usar una clave de servicio autorizada | Clave API | La clave viaja en la cápsula. Modelo/endpoint deben corresponder al proveedor; cuotas y costes son suyos. |
| Llevar una sesión compatible del PC | Mi sesión de este equipo | Se validan solo archivos portables admitidos. Un llavero ligado al sistema no se convierte automáticamente en sesión portable. |

### Importar una sesión, paso a paso

- En la tarjeta del proveedor, comprueba si su CLI está disponible en **este PC preparador**. Si debes instalarlo, utiliza la acción ofrecida y verifica el resultado. No es una comprobación de Internet ni de tu suscripción.

- Selecciona **Mi sesión de este equipo**. Si todavía no tienes sesión local, pulsa **Iniciar sesión en este PC**. Se abre un terminal real del proveedor: completa allí su autorización oficial.

- Comprueba el dominio y la cuenta antes de consentir. Si cierras sin terminar o el CLI falla, no has iniciado sesión. El mensaje «se abrió el CLI» solo confirma que se abrió el terminal.

- Vuelve al Imager y pulsa **Comprobar e importar** en la tarjeta. Aún no se ha importado significa exactamente eso: el lanzamiento anterior no terminó la importación por ti.

- Comprueba el estado que devuelve la app. Si dice que el formato no es portable, utiliza API si corresponde o inicia sesión directamente en el live; no copies todo el llavero como atajo.

- Revisa el resumen y cifra la cápsula antes de prepararla. Al arrancar, verifica que el proveedor puede trabajar: un archivo aceptado puede contener una sesión caducada.

**Tres autorizaciones independientes:** proveedor IA, alta Tailscale/Headscale y SSH. LA AGUJA no solicita una cuarta cuenta para descargas.

No publiques API keys, códigos o URLs de autorización en capturas. La IA en nube necesita Internet y puede enviar al proveedor las instrucciones, resultados y archivos que uses; elige los datos conforme a tu tarea.

## Paso 5 · Tu Tailscale o Headscale

El acceso remoto es opcional. Activa la red privada y facilita una clave de alta autorizada. Una URL Headscale vacía selecciona Tailscale oficial; de lo contrario usa tu servidor HTTPS. El cliente de acceso debe pertenecer a la misma red y cumplir sus políticas; comprueba una conexión SSH real.

Desde Rescue Disk 1.0.2, el USB recupera su identidad Tailscale/Headscale guardada antes de conectar. La clave de alta sirve para el primer registro, no para crear un nodo en cada reinicio. El estado idéntico no se reescribe; los cambios se guardan atómicamente y se verifican. El perfil automático no añade desbloqueo; el cifrado conserva el suyo. Siguen aplicándose la caducidad y revocación del servidor. Los nodos LA AGUJA IoT (ESP32 v1.4.0) también se unen a tu mismo Tailscale o Headscale por WireGuard/DERP como exit node de bolsillo, subnet router dinámico y DNS relay, controlables a distancia por API REST o aguja-iot.py sin relay de LA AGUJA.

## SSH normal y Tailscale SSH no son lo mismo

**La ruta recomendada es OpenSSH sobre tailnet.** Tailscale transporta la conexión privada; el servidor OpenSSH autentica con tu contraseña o clave pública. La ACL/grant de red debe permitir el puerto. La auth key solo inscribe el nodo, no concede acceso universal a cualquier persona.

**Tailscale SSH** es la opción avanzada distinta: intercepta el puerto 22 en la IP de tailnet y utiliza identidad y políticas SSH del plano de control. Requiere autorización de red y reglas SSH compatibles; no usa de la misma forma la contraseña o `authorized_keys` de OpenSSH. El puerto personalizado de OpenSSH no se convierte en puerto de Tailscale SSH. En Headscale, revisa la compatibilidad y la política de tu versión. [Referencia oficial de Tailscale SSH](https://tailscale.com/docs/features/tailscale-ssh).

```
# Desde el equipo de asistencia YA conectado a la misma tailnet
# IP de EJEMPLO: sustitúyela por la mostrada en el Rescue Disk
ssh aguja@100.64.0.10

# Si configuraste OpenSSH en otro puerto
ssh -p 50222 aguja@100.64.0.10
```

Windows puede usar su cliente OpenSSH en PowerShell; Linux puede usar el mismo comando desde terminal. MagicDNS o un nombre Headscale depende de DNS y configuración: la IP mostrada es la referencia para diagnosticar. No compartas la auth key para que un técnico entre; inscribe y autoriza su propio dispositivo en tu organización.

La aceptación de rutas de subred es opcional y no anuncia nuevas rutas: el Rescue Disk no se convierte automáticamente en router, exit node ni acceso completo a la LAN. Mantén esa opción apagada salvo necesidad explícita.

## Secretos: qué se guarda y qué protege el cifrado

| Dato | Destino | Decisión del propietario |
| --- | --- | --- |
| Wi-Fi, acceso SSH, API keys, auth key de tailnet | Cápsula privada del USB y memoria del live al cargarla. | Cifrar la cápsula; restringir uso, vigencia y custodia del USB. |
| Sesión OAuth nativa importada | Solo archivos portables permitidos, dentro de la cápsula. | Importar si es necesario; comprobar vigencia y retirar permisos al terminar. |
| Identidad de tailnet | Estado propio del USB desde 1.0.2. | Recupera el nodo guardado; caducidad y revocación siguen bajo el control del servidor. |
| Workspace, informes, clave SSH del USB | AGUJA_DATA si está disponible. | El cifrado de la cápsula no cifra todo este volumen. |

En **Crear disco**, el modo cifrado usa AES-256-GCM y scrypt. Introduce una frase de al menos 12 caracteres; no la guardes junto al USB. Un perfil reutilizable `.aguja` también se guarda cifrado, pero es distinto de la cápsula dentro de la imagen.

![Flash Imager: elegir cifrado y revisar el resumen](../server/public/docs-images/linux-05-perfil-cifrado.png)

Captura con contraseña sintética oculta. El resumen enumera equipo, red, SSH e IA sin revelar claves. Seleccionar cifrado exige desbloquear en el arranque antes de cargar los datos privados.

La cápsula cifrada protege los secretos en reposo mientras está bloqueada. No protege de root ni de un agente con permisos completos una vez desbloqueada. Tampoco cifra automáticamente tus informes, los discos internos ni todo AGUJA_DATA. No uses el pendrive como almacén universal de contraseñas.

Usa placeholders al compartir instrucciones: `<AUTH_KEY>`, `<IP_TAILNET>`, `<PARTICION_ORIGEN>`. No pegues claves en nombres de máquina, etiquetas de tareas, capturas, argumentos de shell, historial, tickets o mensajes. El estado público omite secretos conocidos; no asumas que cualquier cadena desconocida puede filtrarse mágicamente.

### Tres botones que no hacen lo mismo

- **Guardar perfil cifrado:** guarda una plantilla `.aguja` para abrirla en el Imager más adelante. No graba un USB ni garantiza que las claves sigan vigentes.

- **Crear imagen privada:** genera un archivo de disco configurado. La imagen fuente se conserva; ese nuevo archivo también necesita custodia.

- **Preparar y grabar USB:** prepara la configuración necesaria y escribe sobre el pendrive confirmado. Es el paso que borra el contenido anterior del USB.

**Para reutilizar:** pulsa Abrir perfil, introduce su frase, selecciona la imagen actual y vuelve a revisar red, claves, sesiones y destinos. El perfil no es una copia de seguridad de tus documentos ni un archivo de recuperación de BitLocker universal.

## Windows · BitLocker explicado sin confusiones

BitLocker cifra datos de Windows. Arrancar un Linux externo no elimina ese cifrado. Para acceder al volumen necesitas una clave válida del propietario y un procedimiento compatible. **Comprobar, ver una clave y suspender la protección son acciones distintas.**

![Flash Imager Windows 0.8.1 con un volumen BitLocker protegido](../server/public/docs-images/windows-bitlocker.png)

Captura nativa real de Windows 0.8.1: volumen protegido, clave no mostrada y copia a la imagen desmarcada. 0.8.2 conserva este flujo; no se presenta como una nueva ejecución Windows 0.8.2. No se suspendió BitLocker para obtenerla.

- En **Crear disco**, localiza **Protección BitLocker**. Solo aparece en Windows. Si muestra autorización pendiente, no significa «el disco no está cifrado».

- Pulsa **Comprobar BitLocker** y autoriza UAC cuando corresponda. Se eleva la consulta necesaria, no toda la aplicación. Cancelar permite volver a intentarlo.

- Selecciona la unidad y lee protección, porcentaje y método. Esa consulta no muestra ni exporta la contraseña de recuperación.

- Si tu tarea lo requiere, **Ver clave de recuperación** la muestra de forma explícita; **Guardar en archivo (.txt)** crea una copia sensible. No guardes esa copia junto al disco cifrado ni la fotografíes para soporte.

- **Mandar clave de recuperación a la imagen** permite incluir una clave disponible en la configuración privada. Está desmarcado por defecto. Cifra la cápsula y verifica volumen/clave en el procedimiento de rescate. Incluirla no implica que el disco interno se monte automáticamente al arrancar.

- **Suspender BitLocker (1 reinicio)** cambia la protección del Windows actual y requiere una decisión específica. No descifra el disco ni es un requisito general para crear el pendrive. Antes de tocar firmware o arranque, conserva una clave recuperable y consulta el procedimiento del equipo.

Si la clave no está disponible en ese Windows, el Imager no la inventa: recupérala por el canal del propietario o su administrador. El identificador de protector no es la clave numérica de 48 dígitos. El cifrado de la cápsula del USB tampoco sustituye BitLocker.

Referencia oficial: [Microsoft · recuperación de BitLocker](https://learn.microsoft.com/windows/security/operating-system-security/data-protection/bitlocker/recovery-overview). Los cambios de entorno de arranque pueden activar recuperación; no atribuyas todo aviso al pendrive.

## Paso 6 · Preparar, grabar y verificar

- Revisa el resumen y el modo de protección. **Crear imagen privada** guarda un archivo nuevo configurado sin tocar un USB.

- Para grabar, pulsa **Buscar USB disponibles** y elige la unidad extraíble correcta. Compara modelo, capacidad, dispositivo y serie. Las unidades internas no se ofrecen para ese recorrido.

- En Linux, marca respaldo previo solo si lo deseas y elige un destino distinto del USB. En Windows, realiza tu respaldo fuera de la app antes de continuar.

- **Preparar y grabar USB** crea la imagen privada automáticamente si hace falta. Si cambiaste configuración, se vuelve a preparar.

- Confirma la ventana nativa de borrado. Cancelar conserva el dispositivo. Autoriza Polkit/UAC para la operación de grabación.

- Espera escritura y verificación de lectura. Un mensaje de éxito significa bytes leídos verificados, no compatibilidad de arranque probada en todo el hardware.

No retires el USB durante la escritura. Conserva fuera del medio el hash, versión e informe de entrega. Una copia de imagen privada también contiene tus secretos: aplica la misma custodia que al USB, incluso si era un archivo intermedio.

![Imager Linux empaquetado 0.8.0 después de preparar una imagen privada de prueba](../server/public/docs-images/linux-06-imagen-preparada.png)

Captura histórica real del paquete 0.8.0; la captura es evidencia histórica, no una nueva prueba 0.9.0. Se prepararon imágenes en claro y cifradas con datos sintéticos y el lector real de Rescue Disk abrió ambas. Esto no es una grabación física de USB ni un alta en una tailnet personal. Elige el dispositivo solo después de comprobar su identidad y capacidad.

### Qué cambia entre Windows y Linux

| Operación | Windows | Linux |
| --- | --- | --- |
| Permiso para escribir USB | UAC para el grabador. | Polkit para la operación. |
| Respaldo previo dentro de la app | No implementado; respalda externamente primero. | Opcional, completo y verificado; necesita espacio en otro destino. |
| Espacio sobrante del USB | Conserva la geometría de la IMG; no amplía AGUJA_DATA ni recoloca GPT al final físico. | El grabador tiene una fase propia de ampliación verificada. |
| BitLocker | Consulta y acciones explícitas sobre Windows. | No aparece ese panel Windows; el live conserva herramientas de cifrado. |

**Si se interrumpe:** no confíes en un USB parcial. Conserva el error y vuelve a preparar/grabar tras identificar otra vez el destino. Un 100 % de escritura sin lectura verificada no es el resultado final esperado.

## Arrancar, desbloquear y conectarse

- Con el equipo apagado o siguiendo su procedimiento seguro, conecta el USB y elige ese medio en el menú de arranque del firmware. No cambies el orden o la seguridad del firmware sin permiso.

- Arranca la entrada apropiada de LA AGUJA. Si la presentación gráfica falla, conserva la consola o prueba el modo de arranque de respaldo disponible. No presupongas que un fallo de vídeo indica disco dañado.

- Si la cápsula está cifrada, desbloquéala en la consola local. Sin ese paso no están disponibles sus credenciales de red/SSH/IA ni el alta preconfigurada.

- Comprueba IP, puerto SSH y estado real. Si habilitaste tailnet y hay red, el disco intenta registrarse con tus datos; la app no lo había inscrito durante la preparación.

- Desde el equipo autorizado en esa misma red privada, conecta a la IP actual y compara la huella SSH. Si no hay tailnet, usa consola local o LAN autorizada.

```
# En la consola local del Rescue Disk
aguja profile unlock
aguja status --json
aguja doctor
aguja tailscale status
aguja tailscale status --json
ip -br addr
ip route
```

`aguja doctor` comprueba herramientas y servicios, no garantiza salud del disco interno ni una cuenta IA operativa. Un perfil bloqueado, un nodo esperando aprobación o un proveedor sin sesión son estados distintos. Consulta el apartado de diagnóstico para aislarlos.

![Pantalla real del rescate en VM con red privada y estado de SSH](../server/public/docs-images/rescue-panel.png)

Arranque real en una VM de QA, sin discos internos conectados. La dirección y el servidor pertenecen a una tailnet aislada sintética. El estado local no demuestra por sí solo las ACL: en esta prueba se verificó además una sesión OpenSSH desde el otro nodo.

### La primera pantalla y las teclas

El cockpit muestra Agujita, estado de red e información para conectar. En los menús utiliza flechas, números y Enter según las opciones visibles. No es un escritorio de Windows: la consola es el lugar donde ejecutas órdenes. Si tu hardware no permite la vista gráfica, la consola de texto sigue siendo el camino de respaldo.

La tecla del menú de arranque depende del fabricante; consulta su manual. Selecciona el pendrive, no una entrada de instalación del disco interno. No hay una tecla ni una política Secure Boot universal para todos los equipos.

### Cuatro comprobaciones separadas

**Arrancó:** ves el live. **Perfil cargado:** tus ajustes están disponibles. **Red disponible:** hay una ruta útil, no solo una IP. **Asistencia disponible:** el cliente autorizado puede entrar por SSH. Pasar una no prueba las otras.

## Actualizaciones interactivas del live

Abre Actualizaciones en el panel o ejecuta aguja update menu. Primero pulsa Comprobar actualizaciones: la lista muestra la versión instalada y la disponible. No se instala nada automáticamente.

En cada fila elige No, Sí · RAM o Sí persistente. No no cambia nada. RAM actualiza solo esta sesión y se pierde al reiniciar. Persistente guarda un sistema limpio y verificado en DATA de este pendrive para el próximo arranque.

Selecciona con ratón, flechas y Espacio. A abre la revisión con los recuentos y el destino persistente exacto; Enter aplica. La release completa de Rescue Disk requiere persistencia y se actualiza por separado de los componentes.

Verás bytes de descarga o progreso APT cuando se pueden medir, y las fases de preparación, instalación, guardado en USB, verificación y selección de arranque. Las fases sin total medible muestran actividad, no porcentajes inventados. Espera a que termine antes de retirar el USB.

El resultado final permanece hasta pulsar Volver al menú. No hay reinicio automático. Un fallo o resultado parcial no se anuncia como éxito. Fábrica y la generación anterior siguen disponibles; aguja update rollback cambia el próximo arranque.

En la 1.0.2, el arranque normal evita recalcular el hash del sistema completo. Las comprobaciones se ejecutan en segundo plano y avisan sin instalar nada. Los trabajos confirmados continúan al salir con Escape o cerrar SSH; vuelve a Actualizaciones para recuperar progreso y resultado. No retires el USB durante una escritura activa.

Necesitas un USB escribible compatible con 1.0, espacio libre en DATA y RAM suficiente. La generación pendiente se conserva como base; los secretos del perfil y el workspace no se copian al sistema. Editar solo CFG no actualiza un USB antiguo.

```sh
aguja update menu
aguja update status --json
aguja update check --json
aguja update rollback
```

![Lista · No / RAM / persistente](../../server/public/docs-images/101/updates-list.png)

![Revisión del destino persistente](../../server/public/docs-images/101/updates-review.png)

![Progreso medido de descarga](../../server/public/docs-images/101/updates-download.png)

![Guardando en el pendrive](../../server/public/docs-images/101/updates-save.png)

![Finalización verificada](../../server/public/docs-images/101/updates-done.png)

![Resultado RAM · solo esta sesión](../../server/public/docs-images/101/updates-ram.png)

Capturas reales de la VM; QA con una versión oficial anterior de Codex controlada. La demostración de paquetes es sintética. Las versiones mostradas no prometen actualizaciones disponibles hoy.

## Autenticar IA con el mini navegador local

Hay tres caminos distintos: **clave API**, **importación de una sesión portable** ya existente y **login oficial en el live**. El Imager no autoriza automáticamente un proveedor y LA AGUJA no concede acceso a OpenAI, Google, Anthropic u OpenCode.

### API o importación en Flash Imager

Elige proveedor y modo. Una API key puede tener coste y alcance propios; configura endpoint/modelo si procede. Importar valida únicamente archivos nativos permitidos: no traslada por defecto historial, hooks, plugins, MCP ni el llavero completo del PC. Algunas sesiones no son portables; otras pueden estar caducadas aunque su formato sea válido. El login del CLI en tu PC sirve para esa sesión local, no equivale a una inferencia desde el disco.

### Login en el Rescue Disk

![Navegador local y consola gráfica unida al mismo CLI; prueba sintética, no login de proveedor](../server/public/docs-images/rescue-browser.png)

Captura real de una VM UEFI arrancada con Rescue Disk 0.8.0: página y código sintéticos, no una cuenta ni autorización de un proveedor. ① Callback local de prueba. ② Copiar cambia el foco. ③ Ctrl+Shift+V pega explícitamente en la misma consola. El resultado no certifica un login OAuth real.

- Desde la consola local, inicia el flujo oficial del arnés. El asistente reconoce las URLs de autorización permitidas y abre Chromium mínimo como usuario normal, con su sandbox.

- Comprueba el dominio y autentícate tú. No se sustituye la página del proveedor por un formulario que capture tu contraseña.

- Si el proveedor usa retorno `localhost`, la misma instancia del CLI sigue viva y conserva su callback, `state` y PKCE.

- Si requiere copiar un código, usa el botón de copiar del proveedor. La consola gráfica toma el foco al cambiar el propietario de la selección; el asistente no lee su contenido.

- Pega explícitamente con Ctrl + Shift + V en la consola que está esperando. Está unida a la **misma PTY**, no a un segundo login. Comprueba el resultado que muestra el CLI.

- Cerrar navegador o consola gráfica devuelve al terminal original sin matar el CLI. Ctrl + ] permite abrir una URL pendiente capturada o cerrar el asistente activo.

```
# Flujos asistidos oficiales desde consola local
aguja login codex
aguja login claude
aguja login antigravity

# OpenCode utiliza su recorrido nativo; no se promete el asistente para todos sus proveedores
opencode auth login
```

En SSH, serie o una sesión sin pantalla compatible no se abre por magia un navegador local. La URL y el método nativo permanecen disponibles. Si un callback escucha en localhost del live, abrir la URL en tu PC no redirige automáticamente ese puerto: utiliza un método remoto oficial o un reenvío explícito apropiado a ese flujo, entendiendo `state`/PKCE. No inventes códigos, no registres URLs privadas y no desactives TLS para completar una sesión.

No hay QR en el nuevo recorrido. El navegador sirve para autorizar, no para convertir la IA en dueña de tus cuentas. Su perfil es privado y temporal en `/run`, retirado al cerrar; el token resultante que guarda el CLI tiene su propio ciclo de vida. Login real e inferencia de cada proveedor deben comprobarse por separado.

![Consola de la VM después del pegado explícito en la misma PTY](../server/public/docs-images/rescue-console.png)

Prueba gráfica en la imagen final: callback local y copia sintéticos, foco en la consola y pegado explícito. «MISMA PTY: OK» comprueba que recibió el código el proceso original. Cerrar la prueba devolvió la consola de texto. No se realizó consentimiento, login ni inferencia en una cuenta de IA.

## Tu primera tarea: entender antes de reparar

Empieza con una pregunta concreta: «¿por qué no arranca este equipo?» o «¿puedo copiar mis documentos?». No con «arregla todo». El resultado útil de una primera sesión puede ser un diagnóstico claro y un plan, incluso sin modificar nada.

- **Comprueba dónde estás.** Ejecuta `aguja status` y lee la guía `aguja context`. Confirma versión, conectividad y que estás en el live correcto.

- **Identifica cada disco.** Consulta el inventario siguiente. Separa USB de rescate, disco interno y destino externo. Tamaño, modelo y serie importan más que la letra `sda`.

- **Describe el síntoma.** Anota el error exacto y qué ocurrió antes: actualización, corte de energía, cambio de firmware, espacio lleno. No conviertas una sospecha en diagnóstico.

- **Decide el siguiente paso con evidencia.** Si hay lecturas fallidas o desconexiones, considera una imagen del original antes de reparar. Si hay cifrado, verifica la disponibilidad de su clave.

- **Deja un resumen entendible.** «Observamos X; falta comprobar Y; proponemos Z; antes de escribir necesitamos copia y destino». Si cambia algo, verifica el efecto real después.

```
# Inventario inicial en el Rescue Disk
aguja status --disks
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS
findmnt
ip -br addr
aguja tools
```

Estos comandos consultan estado. No montan automáticamente particiones ni reparan el sistema de archivos. Leer un disco muy deteriorado también puede exigir prudencia: no repitas pruebas extensas sin criterio.

### Ejemplo de mensaje para tu agente

Estoy en LA AGUJA y el sistema interno no inicia. Primero identifica USB, disco interno y sus particiones con datos reales. No montes en escritura, no repares y no cambies el arranque todavía. Explica los hallazgos en palabras sencillas, indica qué falta comprobar y propón un plan con destino de respaldo. Antes de cualquier cambio, describe exactamente qué dispositivo tocarías y cómo verificaríamos el resultado.

Este mensaje orienta el trabajo; **no reduce los permisos técnicos del agente**. El operador sigue controlando decisiones y destinos. Nunca pegues la recovery key o una API key en un prompt para «dar contexto».

### Qué ves mientras trabaja alguien por SSH

El panel puede mostrar sesiones y tareas. Selecciona una tarea con ↑/↓ y Enter; según la vista, S filtra sesión, F fallos, B sondeos y L vuelve al directo. El detalle permite revisar comando, resultado y salida filtrada. No es una grabación íntegra del teclado ni un informe permanente.

```
# Etiqueta una consulta remota para reconocerla en el panel
aguja run --label "Inventario inicial" -- lsblk -o NAME,SIZE,MODEL,FSTYPE
```

## Usar un agente: objetivo, evidencia y límites

El agente puede leer salidas, escribir scripts, comparar configuraciones y ejecutar herramientas que ya están en el live. Su valor no es solo «ver una pantalla»: puede encadenar observaciones y ayudarte a justificar una decisión. Su mayor riesgo es poder hacer rápidamente un cambio incorrecto con acceso de administrador.

```
# Primero, orientarse en el live
aguja context
aguja tools
lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS
findmnt

# Ejemplo de un diagnóstico etiquetado en el panel
aguja run --label "Inventario de discos" -- lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS

# Abrir el arnés elegido, después de configurar su autenticación
aguja agent codex
```

Puedes elegir `claude`, `antigravity`, `opencode` o `shell`. El modo completo puede omitir aprobaciones del CLI y `sudo` está disponible: no lo confundas con un modo técnico de observación. No se configura un agente para reparar automáticamente cada máquina sin diagnóstico.

### Un encargo útil y verificable

Quiero identificar por qué el equipo no arranca. Primero muestra discos, montajes y estado del hardware sin repararlos. No montes el disco en escritura, no ejecutes fsck, no cambies particiones ni cargador. Resume evidencia y dudas, propone comandos y confirma conmigo el disco y el respaldo antes de cualquier escritura. No envíes archivos personales ni secretos al proveedor.

Esta petición orienta al modelo; no garantiza obediencia ni aislamiento. Acompáñala de una política externa de permisos, un operador atento y copias verificadas. Si necesitas una restricción forense de escritura, usa barreras técnicas adecuadas fuera del simple prompt.

### La información puede ser hostil

Un README, una página web o la salida de un proceso pueden contener instrucciones maliciosas dirigidas al modelo. Trátalos como datos, no como autorización del propietario. Revisa las órdenes propuestas, no solo la explicación. No entregues dumps, cookies, claves, historiales o archivos de clientes por comodidad. Lo que se envía al proveedor puede salir del equipo y estar sujeto a sus condiciones.

El panel de actividad sirve para observar tareas y comandos redactados durante la sesión; no es un control de acceso, una transcripción forense completa ni una garantía de ocultar un secreto que el agente divulgue. Costes, cuotas, latencia y capacidades dependen del proveedor y de tu cuenta.

## Herramientas de rescate y comandos de orientación

`aguja tools` presenta el inventario disponible del arranque actual. Puede indicar un binario ausente: no sustituyas el estado vivo por esta tabla. Los comandos siguientes son de orientación o lectura; la letra `XXX` es un marcador que debes reemplazar tras identificar el dispositivo.

| Categoría | Herramientas | Uso y límite |
| --- | --- | --- |
| Discos y montajes | lsblk, blkid, findmnt, parted, sgdisk | Identificar estructura; comandos de crear/borrar particiones sí modifican el disco. |
| Hardware | smartctl, nvme, lshw, lspci, lsusb | Inventario y señales de salud. SMART sin errores no prueba que todo el hardware esté sano. |
| Recuperación | ddrescue, ddrescuelog, testdisk, photorec | Imagen con mapa, análisis y recuperación. Destino separado; no garantizan recuperar todos los archivos o nombres. |
| Sistemas de archivos | e2fsck, btrfs, xfs_repair, ntfs-3g | Cada sistema tiene reglas. Reparar o forzar montaje puede escribir; no hay un comando universal seguro. |
| Cifrado y volúmenes | cryptsetup, dislocker, lvm, mdadm | Necesitan claves y topología correctas. Ensamblar/importar mal un RAID puede agravar el problema. |
| Red | nmcli, nmtui, ip, ssh, scp, rsync | Configurar red y transferir. Comprueba destino, permisos y qué datos estás enviando. |
| Instalación/arranque | debootstrap, pacstrap, grub-install, efibootmgr, wimlib-imagex | Capacidad avanzada disponible; modificar firmware, bootloader o instalar exige plan y respaldo. |
| Sesiones y scripts | tmux, zsh, nano, rg, jq, python3 | Continuidad y automatización. No ejecutes scripts desconocidos como root sin revisar. |

```
# En el Rescue Disk, orientar antes de escribir
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS
findmnt
ip -br addr
ip route
sudo -n smartctl -a /dev/XXX

# Mantener una tarea remota tras reconectar
# No uses el mismo nombre si ya existe una sesión de otra persona
tmux new -s rescate
# Más tarde:
tmux attach -t rescate
```

### Montar para leer no equivale a una garantía forense

`aguja mount-ro` solicita `ro,nosuid,nodev,noexec`. Identifica primero una partición, no el disco completo, y comprueba el montaje. Determinados sistemas pueden necesitar opciones adicionales contra reproducción del journal; no es un bloqueador físico de escritura. No fuerces un Windows hibernado en escritura.

```
# Sustituye la partición tras verificar modelo, serie y lsblk
aguja mount-ro /dev/PARTICION_ORIGEN /mnt/target
findmnt /mnt/target
```

### ddrescue: pensar el destino antes de copiar

El dispositivo origen averiado se lee; la imagen destino se escribe en almacenamiento sano diferente; el mapa permite retomar. Verifica espacio y correspondencia antes de ejecutar. No se da una receta de clonado hacia `/dev/sda` que alguien pueda pegar y destruir su disco. Obtén primero `ddrescue --help` y un plan específico con origen, destino y mapa.

## Qué puedes lograr: diez recorridos concretos

Los ejemplos siguientes son **procedimientos que puedes adaptar**, no historias inventadas de clientes recuperados ni promesas de éxito. La IA ayuda a leer evidencias y ordenar pasos; el operador verifica que corresponden a la máquina real.

CASO 01 · LECTURA

### El sistema no inicia y necesitas documentos

Arranca el USB, identifica la partición, comprueba si está cifrada y monta en lectura con las opciones apropiadas. Copia a otro destino autorizado y verifica archivos. El agente puede sugerir rutas y excluir contenido innecesario.

**No promete:** descifrar sin clave, superar un SSD averiado ni preservar todas las fechas/ACL sin elegir un método adecuado.

CASO 02 · DIAGNÓSTICO

### Dudas entre disco, arranque y hardware

Reúne estructura de discos, estado SMART/NVMe y configuración de arranque. Separa síntoma de causa. Un informe puede justificar hacer una imagen antes de reparar.

**No promete:** atribuir un fallo de E/S a daño físico sin evidencias. Una VM puede fallar por almacenamiento virtual o su host.

CASO 03 · SOPORTE AUTORIZADO

### El técnico está lejos

El propietario prepara la tailnet, arranca y entrega la IP actual. Un equipo autorizado conecta por SSH con su clave. El operador observa tareas y revoca el nodo al terminar.

**No promete:** entrar sin autorización, Internet o política compatible; no instala Tailscale en el sistema interno por hacerlo en el live.

CASO 04 · BITLOCKER

### Necesitas leer un Windows cifrado

Obtén del propietario la recovery key válida. En Windows, el Imager puede consultar/exportar una clave disponible con los permisos necesarios e incluirla si se solicita. En el live, comprueba volumen y herramienta antes de desbloquear.

**No promete:** recuperar una clave inexistente, eludir TPM/cifrado ni resolver corrupción. Suspender BitLocker es una acción separada sobre Windows y no es necesario para cualquier lectura.

CASO 05 · CAMBIO CONTROLADO

### Reparar cargador o sistema de archivos

Primero evidencia, copia verificable y destino confirmado. Después un procedimiento específico al sistema BIOS/UEFI y filesystem. Guarda el antes/después y prueba arranque sin el USB.

**No promete:** un comando universal `fsck -y` o reinstalación de GRUB correcta en todas las máquinas. Escribir sobre el original puede impedir otra recuperación.

CASO 06 · AUTOMATIZACIÓN

### Inventariar una flota de equipos

Una política de claves/nodos y scripts revisados pueden recopilar inventarios y diagnósticos al arrancar. Separa recogida permitida de reparación. Una IA puede comparar los informes después de redactar datos sensibles.

**No promete:** gestión de flota SaaS ya implementada, políticas multiusuario completas ni reparación autónoma segura de todo hardware.

### De la idea al procedimiento: ejemplos para practicar

### 1. Rescatar documentos de un sistema que no arranca

**Por qué sirve:** el live no necesita que el Windows/Linux interno inicie. **Necesitas:** disco legible, claves si está cifrado y destino sano distinto del origen.

- Identifica disco, partición y cifrado; no confundas el USB con el disco interno.

- Si hay señales de deterioro, decide primero si crear una imagen.

- Abre la partición con un montaje de lectura adecuado a su filesystem y confirma con `findmnt`.

- Copia solo las carpetas autorizadas al destino separado; revisa espacio y método para conservar metadata cuando sea necesaria.

- Abre archivos representativos desde la copia y coteja integridad cuando corresponda. No declares recuperación solo porque una carpeta tiene nombres.

**Resultado comprobable:** documentos utilizables fuera del disco original. No repara necesariamente el arranque.

### 2. Diagnosticar si falla el disco, la red o el arranque

**Por qué sirve:** tienes un sistema independiente para comparar el síntoma. Recoge inventario, montajes y señales de salud apropiadas al dispositivo; en una VM, incluye el almacenamiento del host. Consulta DNS, rutas y hora si falla HTTPS.

**Resultado comprobable:** hipótesis sustentadas y siguientes pruebas, no «hardware sano» solo por ver SMART sin alertas. Evita pruebas largas sobre un disco que se desconecta.

### 3. Recibir ayuda de un técnico que está en otra ciudad

- Prepara SSH y una tailnet propia antes de la visita si habrá Internet.

- Arranca, desbloquea y confirma que el nodo de este arranque fue autorizado.

- El técnico entra desde su equipo autorizado con la IP actual y compara huella.

- Observa las tareas, confirma los cambios previstos y guarda un resumen.

- Al terminar, cierra la sesión y administra nodo/clave temporal en el control plane.

**Lo sorprendente:** el sistema instalado puede seguir averiado mientras la consola del live es accesible. No hace falta abrir por este recorrido un puerto público del router.

### 4. Leer un volumen BitLocker con su clave legítima

Obtén la clave por el canal autorizado; identifica el volumen y verifica compatibilidad de la herramienta. Si preparas desde Windows y su clave está disponible, puedes incluirla explícitamente en una cápsula cifrada. Desbloquea y monta según el procedimiento específico; verifica los datos copiados.

**Resultado comprobable:** acceso autorizado a un volumen compatible. No se rompe BitLocker ni se promete salvar un volumen corrupto.

### 5. Recuperar archivos borrados trabajando sobre una copia

Evita seguir escribiendo en el origen. Valora una imagen y trabaja sobre ella con TestDisk/PhotoRec u otra herramienta apropiada; el destino de lo recuperado debe ser otro almacenamiento. Valida contenido, no solo extensión.

**Resultado comprobable:** archivos recuperados que realmente abren. TRIM, sobrescritura, cifrado y daño físico pueden impedir la recuperación; nombres/carpetas originales no siempre sobreviven.

### 6. Reparar un arranque después de una actualización

Comprueba BIOS/UEFI, esquema de particiones, ESP y sistema instalado. Conserva evidencias/copia y elige un procedimiento específico del sistema. Solo entonces modifica el cargador o su configuración. Para Windows pueden ser necesarias herramientas de recuperación del fabricante.

**Resultado comprobable:** el sistema interno arranca sin el USB y sus datos permanecen accesibles. Instalar GRUB sin error no demuestra eso.

### 7. Crear una imagen de un disco con errores y retomar después

Con almacenamiento sano suficiente, ddrescue puede copiar a una imagen y usar un archivo de mapa para retomar. Primero confirma origen, imagen destino y mapa; consulta su ayuda/manual y adapta los intentos al estado real. Trabaja después sobre la copia.

**Resultado comprobable:** mapa conservado, zonas leídas/faltantes identificadas y una copia de trabajo. No garantiza leer sectores físicamente perdidos.

### 8. Preparar una migración o instalación sin improvisar

Inventaría hardware, exporta datos autorizados y claves de recuperación, elige distribución/licencia e imagen oficial y prepara un segundo USB instalador si corresponde. Conserva intacto el de rescate. Usa el instalador apropiado; una ISO Windows no se vuelve arrancable por cualquier copia cruda.

**Resultado comprobable:** respaldo recuperable y medio de instalación correcto. LA AGUJA no incluye Windows, WinPE ni licencias, ni un asistente universal de instalación.

### 9. Repetir tu configuración sin volver a escribir todo

Guarda una plantilla `.aguja` cifrada y ábrela en el Imager cuando prepares otro medio. Actualiza claves, red y sesiones, escoge la imagen y verifica el nuevo USB. No traslada automáticamente una sesión caducada ni autoriza clonar una identidad tailnet en varios USB concurrentes.

**Resultado comprobable:** configuración coherente y revisada, con menos errores de escritura. No es gestión de flota ya implementada.

### 10. Convertir un diagnóstico técnico en una explicación entendible

Un agente puede ordenar salidas permitidas, distinguir hallazgos de hipótesis, escribir una lista de próximos pasos y generar un informe adaptado al propietario. El técnico coteja cada afirmación con resultados reales y elimina datos sensibles antes de compartir.

**Resultado comprobable:** informe con evidencia, cambios, límites y verificación. Una explicación convincente no demuestra por sí sola que la reparación funcionó.

## Ruta profesional: control, evidencia y repetibilidad

LA AGUJA también sirve como entorno de trabajo técnico. Su valor es facilitar una entrada independiente y automatizable al equipo; el procedimiento, la custodia de datos y la comprobación final siguen siendo tuyos.

- **Delimita la intervención.** Propietario, síntoma, equipos, datos autorizados y resultado esperado. Separa diagnóstico de escritura.

- **Registra la línea base.** Versión de imagen, identidad del USB y origen/destino, modo de arranque, montajes, red y estado relevante. No incluyas secretos en inventarios.

- **Elige la estrategia.** Lectura directa si procede; imagen/copia antes de reparaciones cuando haya degradación o necesidad de preservar el original. No escanees una y otra vez un medio inestable.

- **Mantén la sesión.** Usa `tmux` para tareas remotas y `aguja run --label` para identificarlas. La sesión mantiene procesos en ese live; no sobrevive al apagado por usar tmux.

- **Ejecuta cambios acotados.** Identifica dispositivo por modelo/serie y topología actual. No reutilices `/dev/sdX` de una sesión anterior. Comprueba si el filesystem está montado antes de repararlo.

- **Verifica el resultado observable.** Copia de archivos abre; conexión externa funciona; sistema interno arranca; servicio responde. El exit code se registra, pero no sustituye esas verificaciones.

- **Entrega y cierra.** Informe breve, copia validada, tareas pendientes, rollback y retirada de accesos temporales. El panel de actividad en RAM no sustituye ese informe.

### Contexto y estado para automatización

```
# En el Rescue Disk; consulta de contratos del propio producto
aguja context
aguja status --json
aguja profile status --json
aguja tailscale status --json
aguja activity --json
aguja doctor --json
```

Un consumidor de JSON debe comprobar código de salida y campos reales de esa versión. Un estado healthy del live no equivale a filesystem interno sano ni a sesión IA vigente. Revisa/redacta los informes antes de guardarlos o enviarlos.

### ¿Puedo usar un agente desde fuera?

Sí: un técnico o agente con cliente SSH y credenciales autorizadas puede entrar por LAN o tailnet. Empieza leyendo `aguja context` y el estado actual; no necesitas instalar OpenClaw en el pendrive para que un controlador externo trabaje por SSH. Un agente local se inicia con `aguja agent codex`, `aguja agent claude`, `aguja agent antigravity` o `aguja agent opencode` tras preparar su autenticación.

Esta versión no incluye relay, túneles propios ni el conector MCP propietario. Usa las herramientas SSH de tu elección en tu LAN o tailnet.

### Permisos, modo ask y persistencia

El modo de agente `full` habilita mecanismos de acceso amplio del arnés. La configuración avanzada `agent_mode=ask` conserva las aprobaciones propias del arnés; no quita el sudo del propietario ni convierte el sistema en sandbox. Comprueba el modo efectivo antes de trabajar.

`persistent_home=no` mantiene HOME temporal; `persistent_home=yes` puede conservar HOME y tokens en el USB **sin cifrar**. La cápsula cifrada no cifra ese HOME ni los informes de AGUJA_DATA. Desde Rescue Disk 1.0.2, el USB recupera su identidad Tailscale/Headscale guardada antes de conectar. La clave de alta sirve para el primer registro, no para crear un nodo en cada reinicio. El estado idéntico no se reescribe; los cambios se guardan atómicamente y se verifican. El perfil automático no añade desbloqueo; el cifrado conserva el suyo. Siguen aplicándose la caducidad y revocación del servidor. Define estas decisiones por intervención, no por comodidad accidental.

### Mini plantilla de entrega

Objetivo y equipo: …
Versión y dispositivos comprobados: …
Evidencia antes: …
Copia y reversión disponibles: …
Cambios autorizados realizados: …
Verificación real después: …
Datos recuperados y límites: …
Accesos temporales retirados / pendientes: …

## Si algo falla: separar las capas

| Síntoma | Primera comprobación | Siguiente acción segura |
| --- | --- | --- |
| No hay IP | ip -br addr, aguja network. | Revisar cable/SSID, DHCP y controlador. aguja wifi permite configurar Wi-Fi localmente. |
| Imagen «no admite Tailscale» | Versión y tailscale-profile-v1. | Usar imagen compatible; no editar un marcador para fingir que contiene el servicio. |
| Perfil bloqueado | Estado local y contraseña correcta. | aguja profile unlock. Si olvidaste la frase, volver a preparar con datos válidos; no se promete recuperarla. |
| Alta rechazada/caducada | aguja tailscale status --json; control plane. | Revisar clave, vigencia, tipo de un uso, DNS, TLS y hora; no mostrar la clave en logs. |
| Nodo esperando aprobación | Consola Tailscale/Headscale y nodo de este arranque. | Que el administrador autorice según política. No llamar «conectado» solo porque apareció una IP antigua. |
| SSH tarda hasta timeout | Misma tailnet, IP actual y ACL del puerto. | Separar ruta/control plane de OpenSSH; revisar política sin abrir todo el acceso para probar. |
| SSH responde pero rechaza autenticación | Usuario aguja, clave/contraseña y modo SSH. | Revisar OpenSSH frente a Tailscale SSH; una auth key no es una contraseña SSH. |
| Huella SSH distinta | Huella local, identidad del USB y regrabación. | Confirmar el motivo antes de actualizar known_hosts; no desactivar comprobación. |
| No abre navegador | Consola local gráfica, herramientas y URL permitida. | Usar flujo nativo/URL original. SSH/serie no ofrecen el mismo navegador; Ctrl+] abre una URL pendiente local. |
| Copié pero el CLI espera | Foco de la consola gráfica de esa PTY. | Pegar explícitamente con Ctrl+Shift+V. Copiar no entrega el código automáticamente. |
| Callback OAuth ocupado/falla | Error del CLI y puerto localhost solicitado. | Resolver conflicto o reiniciar el flujo oficial; no reutilizar URLs/code/state antiguos. |
| USB no elegible o ocupado | Unidad extraíble, identidad y montajes. | Revisar destino y cerrar uso del USB. No seleccionar un disco interno como atajo. |
| Respaldo Windows no disponible | Función no implementada. | Respaldar antes con herramienta externa; no se inició una escritura por rechazar esa opción. |
| Windows/VM registra HTTPS o E/S intermitente | Red del invitado, almacenamiento virtual y eventos. | Diagnosticar la VM por separado. 0xC0000006 observado en pruebas anteriores no certifica un disco físico dañado ni una solución automática. |

Si compartes un informe, retira IPs privadas identificables, nombres de clientes y cualquier token. `aguja doctor --json` y los estados públicos están diseñados para no incluir claves, pero revisa el contenido antes de enviarlo.

### Preguntas frecuentes, sin dar nada por sabido

### ¿Tengo que saber Linux para usarla?

No para preparar el USB y recorrer el inventario inicial. Reparar particiones, cifrado o arranque sí puede requerir criterio técnico. Empieza por la ruta guiada y pide ayuda para tareas que no puedas validar.

### ¿Necesito pagar cuatro servicios de IA?

No necesitas autenticar los cuatro, y puedes usar herramientas locales sin IA. Si eliges un proveedor, sus cuentas, planes, cuotas y términos son independientes de LA AGUJA. La app no incluye créditos ni una suscripción a todos ellos.

### ¿Funciona sin Internet?

Puede arrancar, inventariar y usar herramientas locales. Descargar, autorizar o consultar IA en nube y registrar una tailnet necesitan conectividad. Haber importado una sesión no convierte un modelo en nube en modelo offline.

### ¿Me borra Windows al arrancar?

No instala, repara ni monta automáticamente el disco interno al inicio. La grabación del Imager sí borra el USB confirmado; comandos de reparación/instalación posteriores pueden modificar el disco interno cuando se ejecutan.

### ¿La contraseña del USB desbloquea BitLocker?

No. La frase de la cápsula protege sus datos; contraseña SSH permite entrar al live; recovery key BitLocker desbloquea el volumen correspondiente. No son intercambiables.

### ¿Por qué no aparece mi USB?

El recorrido exige un dispositivo elegible y desmontado. Confirma conexión, identidad y si otra app lo está usando; revisa el mensaje exacto. No elijas un disco interno ni fuerces filtros para continuar.

### ¿Puedo usarla en cualquier Mac o placa ARM?

La imagen actual es x86-64; no se promete Apple Silicon, ARM, cualquier firmware o todos los controladores. Verifica arquitectura, arranque y política del equipo.

### ¿Por qué el soporte remoto falla en el segundo arranque?

La identidad tailnet es temporal. Una clave de un uso puede haber quedado consumida, otra caducada o el nuevo nodo pendiente de aprobación. Comprueba el registro de este arranque y su IP actual.

### ¿Puedo quitar el USB cuando aparece el panel?

No lo retires como método habitual: puede contener configuración, workspace o datos en uso. Cierra tareas, verifica montajes, sincroniza y apaga coordinadamente antes de retirarlo.

## Cerrar una tarea sin dejar accesos olvidados

- Resume qué se observó, qué cambió y qué se comprobó. Un código de salida 0 no equivale a que el sistema interno arranque ni a que todos los archivos sean recuperables.

- Copia los informes autorizados a un destino externo y verifica que estén completos. La raíz RAM se perderá; AGUJA_DATA no está cifrada por el simple hecho de cifrar la cápsula.

- Cierra sesiones IA y retira permisos temporales según la política de su propietario. No borres a ciegas autenticaciones compartidas.

- Cierra la asistencia SSH; retira el nodo de este arranque del control plane y revoca la clave de alta cuando ya no se necesite. Actualiza el USB si iba a usarse con otra finalidad.

- Verifica montajes y procesos en uso, sincroniza y apaga coordinadamente. No retires un USB mientras escribe ni cortes energía a un disco que todavía guarda cambios.

- Prueba el resultado en el sistema interno cuando corresponda; conserva evidencia y rollback hasta que el propietario lo acepte.

```
# Inspección final antes de desmontar/apagar de forma coordinada
findmnt
sync
# El apagado termina todas las sesiones; ejecútalo solo al cerrar la tarea
sudo -n systemctl poweroff
```

## Validación de Rescue 1.1.2, Imager 1.2.0 e IoT ESP32

La documentación de validación cubre Rescue Disk 1.1.2 (arranques BIOS/UEFI, desbloqueo LUKS, generaciones persistentes, rollback e identidad tailnet), Flash Imager 1.2.0 en Linux y Windows (perfiles USB, edición CFG y flasheo real de ESP32-C6 y ESP32-S3-WROOM-1 N16R8 con esptool.exe sin Python en Windows) y paquetes deterministas de Agent Skill 1.3.0.

Las capturas conservan sus versiones históricas indicadas y datos sintéticos de QA. Las pruebas físicas IoT cubren Seeed Studio XIAO ESP32-C6 y ESP32-S3-WROOM-1 N16R8; el resto de subfamilias ESP32 incluyen firmwares v1.4.0 compilados y empaquetados pendientes de ensayo físico individual. Estas comprobaciones no garantizan compatibilidad universal de hardware, Secure Boot ni cuentas IA externas.

## Referencias y lectura siguiente

Este manual describe la candidata pública 0.9.0 y distingue la evidencia de versiones anteriores. Para políticas o herramientas externas, consulta la documentación del fabricante de la versión que uses:

- [Tailscale CLI](https://tailscale.com/docs/reference/tailscale-cli) · estados y opciones del cliente.

- [Tailscale SSH](https://tailscale.com/docs/features/tailscale-ssh) · diferencia respecto a OpenSSH y políticas.

- [Headscale · primeros pasos](https://headscale.net/stable/usage/getting-started/) · alta con claves de administrador.

- [GNU ddrescue](https://www.gnu.org/software/ddrescue/manual/ddrescue_manual.html) · lectura, mapa y estrategias de recuperación.

- [TestDisk](https://www.cgsecurity.org/wiki/TestDisk) · alcance de la herramienta y recuperación.

- [Manual OpenSSH](https://man.openbsd.org/ssh) · conexión, claves y reenvíos explícitos.

- [Microsoft · recuperación de BitLocker](https://learn.microsoft.com/windows/security/operating-system-security/data-protection/bitlocker/recovery-overview) · claves y procedimientos del propietario.

[Obtener Flash Imager](https://aguja.transcendenceia.net/#application) · [Código y releases](https://github.com/Transcendenceia/La-Aguja) · [Privacidad](https://aguja.transcendenceia.net/privacy)
