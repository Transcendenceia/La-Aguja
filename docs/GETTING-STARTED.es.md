# Primeros pasos · LA AGUJA 0.9.9

[English](GETTING-STARTED.md) · [Documentación](README.es.md) · [Problemas](TROUBLESHOOTING.es.md) · [Ejemplos](SHOWCASE.es.md)

**Objetivo:** preparar un USB, arrancar el Linux independiente e identificar equipo, recursos y discos antes de elegir misión. Puedes construir, configurar, experimentar, migrar o recuperar; este primer hito no necesita cuenta IA. [Explora la plataforma](PLATFORM.es.md).

## 1. Reúne lo necesario

- Un PC Windows o Linux operativo, Internet para descargar y espacio para la descarga, la base descomprimida y una nueva imagen privada. El respaldo USB completo necesita espacio adicional según todo el dispositivo, no solo los archivos ocupados.
- Un equipo destino x86-64 capaz de arrancar por USB. BIOS/UEFI no significa Secure Boot universal ni certificación de hardware.
- Un USB cuya **capacidad real** supere la requerida por la imagen. Grabar sustituye su contenido.
- Autorización para examinar el equipo y un **destino sano separado** si luego recuperas datos. Respaldar el USB de rescate no respalda el equipo averiado.
- Claves BitLocker/LUKS del propietario cuando correspondan. LA AGUJA no rompe el cifrado.

Si el original hace clics, se desconecta repetidamente o contiene datos irremplazables, evita escaneos reiterados y considera recuperación profesional antes de seguir encendiéndolo. No cambies firmware ni cifrado a la ligera; conserva claves de recuperación y autorización.

## 2. Descarga preparador e imagen

[Descargas oficiales](https://aguja.transcendenceia.net/es) · [Imager 0.9.9](https://github.com/Transcendenceia/La-Aguja/releases/tag/v0.9.9)

| Archivo | Función |
| --- | --- |
| EXE Windows / AppImage, DEB o archivo portátil Linux | Ejecuta Flash Imager en el PC preparador |
| Rescue `.img.zst` | Imagen USB comprimida; descomprime antes de importar manualmente |
| Rescue `.img` | Base que Imager personaliza y graba |
| ISO Rescue | Pruebas VM/arranque tipo medio óptico; no es el recorrido de preparación IMG configurable |
| `.aguja` | Perfil privado reutilizable, no imagen de sistema operativo |

Prefiere el catálogo firmado del Imager: verifica firma Ed25519, partes descargadas y hash completo. Para descarga manual: [imagen 0.9.9](https://aguja.transcendenceia.net/releases/aguja-0.9.9-amd64.img.zst), [ISO](https://aguja.transcendenceia.net/releases/aguja-0.9.9-amd64.iso) y [sumas publicadas](https://aguja.transcendenceia.net/releases/SHA256SUMS-rescue-0.9.9.txt). Compara el hash del nombre exacto. Calcular un hash sin referencia fiable no acredita procedencia.

Abre Imager como usuario normal. Grabar USB pide elevación local. Windows no ofrece firma Authenticode reconocida: revisa procedencia en vez de ignorar avisos rutinariamente. En Linux, da permiso de ejecución al AppImage; si falta FUSE usa el archivo portátil o la extracción documentada, no opciones para desactivar el sandbox. Véase la [guía de implementación](../desktop/README.es.md).

![Imager 0.9.9 real en español](../server/public/docs-images/099/imager.png)

*Aplicación Linux empaquetada real. No es una ejecución Windows ni resultado de grabación USB.*

## 3. Configura un primer perfil sencillo

1. Elige imagen del catálogo o IMG local descomprimida. Conserva intacta la base.
2. Selecciona **idioma y teclado del live**, independientes del idioma de la aplicación. Comprueba el teclado antes de escribir una nueva frase de desbloqueo.
3. Usa Ethernet DHCP en el primer arranque si puedes. Wi-Fi personal guardado es opcional; autenticación empresarial y portales cautivos pueden necesitar NetworkManager manual.
4. Elige hostname reconocible y contraseña SSH única para esta intervención, o clave **pública** del operador autorizado. Nunca pegues la privada.
5. Deja IA y red privada sin configurar si aún no las necesitas. La imagen completa 0.9.9 sigue incluyendo los cuatro CLI.

Usuario SSH y contraseña pública de fábrica: `aguja`. Contraseña vacía con clave pública permite solo clave; sin clave conserva acceso de fábrica. Después, `aguja password` cambia y conserva la contraseña; `sudo passwd aguja` solo afecta a la sesión actual.

![Red e idioma y teclado independientes en el Imager](../server/public/docs-images/099/imager-network-en.png)

*Interfaz real con inglés seleccionado. El teclado español de la captura es una opción independiente real, no una traducción de la imagen. Elige tu distribución.*

## 4. Protege los secretos antes de guardar

Selecciona **Desbloquear al arrancar** si el perfil contiene secretos. La frase inicial es pública (`aguja`): cámbiala y conserva una copia de recuperación fuera del USB. Contraseña SSH, frase del perfil, clave API y clave de recuperación del disco son credenciales distintas.

- La cápsula cifra su **perfil bloqueado**. No cifra todo AGUJA_DATA, todo el USB ni secretos cargados y accesibles a root.
- El perfil cifrado fuerza `persistent_home=no` al arrancar; HOME persistente corresponde a configuraciones antiguas/en texto plano.
- `persistent_home=no` descarta HOME y tokens al reiniciar. `persistent_home=yes` los conserva **sin cifrar** en el USB.
- `aguja.conf` en texto plano, imagen privada, perfil exportado o respaldo pueden contener información sensible. No los adjuntes a incidencias ni los compartas como imagen pública.
- Un perfil reutilizable cifrado facilita otra preparación, pero no renueva sesiones ni claves de registro caducadas.

![Protección del perfil y opciones USB en Imager](../server/public/docs-images/099/imager-protection-en.png)

*Interfaz Linux real con inglés seleccionado y algunas etiquetas españolas. No hay imagen ni USB seleccionados: muestra opciones, no finalización. El respaldo visible es exclusivo de Linux.*

## 5. Respalda y graba solo el USB confirmado

**Grabar sustituye el contenido del USB seleccionado.** Haz primero un respaldo recuperable. Linux ofrece copia completa verificada opcional, desactivada inicialmente. Windows **no tiene respaldo USB integrado**: usa una herramienta externa antes de continuar.

Compara modelo, serie y capacidad real del dispositivo físico con la confirmación nativa. Cancela ante cualquier duda. «Crear imagen privada» guarda un archivo nuevo; «Preparar y grabar USB» también escribe el dispositivo seleccionado. La skill para agentes solo prepara un archivo y no graba automáticamente.

Espera escritura, sincronización y verificación completa de lectura. En 0.9.9 Imager comprueba espacio antes de copiar; Windows permite otra carpeta de trabajo si hace falta. No sobrescribas la base ni uses un destino existente como atajo. No desconectes durante la escritura. Un proceso fallido o interrumpido no deja un medio listo para arrancar.

La lectura verificada demuestra coincidencia de bytes, no compatibilidad con todo firmware. Windows conserva la geometría AGUJA_DATA de la imagen sin ampliarla automáticamente en USB mayores. Instalar otro Imager no actualiza un USB ya grabado. Revisa [respaldo y actualización USB](USB.md) antes de modificar medios existentes.

## 6. Arranca, desbloquea y alcanza el primer hito

Usa el menú de arranque del fabricante y selecciona el USB. No inicies una instalación sobre el disco interno. El cockpit puede recurrir a texto si lo requiere la pantalla.

Desde consola local:

```sh
aguja profile unlock   # solo perfiles cifrados; introduce la frase interactivamente
aguja status
aguja doctor
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS
findmnt
```

Identifica **USB de rescate, origen original y destino separado** por modelo/serie/tamaño, no por una letra recordada. Estos comandos orientan: doctor correcto no prueba salud del disco interno ni cuenta IA funcional. Revisa números de serie, huellas y rutas personales antes de publicar resultados.

**Primer hito:** ves el cockpit, identificas versión, consultas estado y distingues discos. No hace falta reparación interna ni login en nube. Arrancar no monta, repara, instala ni escribe automáticamente en discos internos.

Las consolas locales 0.9.9 conservan hasta 10.000 líneas en RAM. Rueda arriba revisa salida; baja al prompt o Esc vuelve. Una consola nueva no recupera texto ya perdido y algunas aplicaciones de pantalla completa tienen navegación propia. No es una transcripción guardada. SSH conserva su terminal habitual.

## 7. Conecta opcionalmente desde otro equipo

Sustituye los marcadores por dirección real y puerto configurado:

```sh
ssh aguja@IP_REAL_DEL_LIVE
# Si elegiste un puerto distinto:
ssh -p PUERTO_CONFIGURADO aguja@IP_REAL_DEL_LIVE
```

Compara la huella con la consola antes de confiar en el servidor. `aguja.local` depende de mDNS, multicast y colisiones; la IP real es la alternativa. `10.0.2.15` en las capturas es una dirección de prueba QEMU, no tu equipo.

**Tu Tailscale/Headscale opcional:** configura auth/pre-auth key autorizada, nombre de nodo opcional y URL HTTPS Headscale propia (vacía selecciona Tailscale oficial). La imagen debe admitir `tailscale-profile-v1`. El live se registra después de tener red y perfil desbloqueado, no el PC preparador. Cliente y ACL deben permitir acceso.

La ruta predeterminada es OpenSSH normal por red privada; Tailscale SSH es diferente y necesita políticas SSH compatibles. La identidad tailnet vive en RAM y se registra otra vez al reiniciar. Una clave de un uso puede consumirse en el primer arranque; varios arranques necesitan claves reutilizables vigentes y limitadas. Retira nodos/claves obsoletos después; revocar el registro no elimina todos los nodos ya inscritos.

## 8. Autoriza opcionalmente un cliente IA

Elige **un** comando de login según proveedor, no todos:

```sh
aguja login codex
aguja login claude
aguja login antigravity
opencode auth login
```

El login local compatible abre el flujo oficial en Chromium con sandbox y PTY original. Tú das consentimiento. Copiar enfoca la consola; pega expresamente con Ctrl+Shift+V. Cerrar devuelve al terminal original. OpenCode mantiene login nativo; el nuevo navegador local no utiliza QR.

SSH/serie/sin pantalla usan métodos nativos del proveedor. El callback localhost remoto no se reenvía automáticamente. API e importación selectiva de sesiones portables son alternativas; instalación o archivo importado no prueban autenticación. No se copia todo el llavero, historial, hooks ni MCP. Comprueba cuenta, red, cuota, precio y política de datos del proveedor; no se promete inferencia en nube sin Internet.

Abre el cliente elegido desde el launcher, por ejemplo:

```sh
aguja agent codex
```

Elige **Seguro** para confirmar tareas; Inseguro/YOLO es explícito. **Ambos mantienen sudo/root ilimitado. Seguro no es sandbox ni bloqueador forense de escritura.** Empieza con un [prompt de diagnóstico acotado](SHOWCASE.es.md#first-diagnosis), revisa comandos y detente antes de escrituras no autorizadas.

**Actualización del código:** Codex Seguro ahora añade sandbox `workspace-write` y aprobación humana; la imagen descargable 0.9.9 permanece sin cambios. [Política y alcance](HARNESSES.md#corrección-de-codex-seguro--2026-10-10).

## 9. Verifica y cierra la intervención

En un primer arranque, registra versión, procedencia verificada de la imagen y límites observados de hardware/arranque. En un rescate posterior, abre muestras en destino y comprueba el resultado acordado, no solo el código de salida. Guarda evidencia autorizada fuera de RAM, sin secretos. El historial de consola no es un informe.

Termina transferencias, desmonta limpiamente volúmenes de recuperación y apaga antes de retirar medios. Retira solo accesos temporales creados para el trabajo, revoca claves innecesarias y revisa HOME persistente por tokens restantes. Conserva originales y copias hasta la aceptación del propietario. No borres accesos ajenos ni evidencia al limpiar.

Siguiente: [ocho recorridos prácticos](SHOWCASE.es.md) · [problemas](TROUBLESHOOTING.es.md) · [evidencia de versión](RELEASE-0.9.9.md).
