# Rescate con LA AGUJA

Guía práctica actual: [manual por niveles y capturas](https://aguja.transcendenceia.net/docs).
Primer diagnóstico: [entender antes de reparar](https://aguja.transcendenceia.net/docs#primer-diagnostico).
Este documento resume el trabajo técnico en **Rescue Disk 0.8.0**, preparado con **Flash Imager 0.8.2**.

## Paso 1 · Arrancar el entorno correcto

Selecciona el pendrive en el menú del fabricante. Comprueba arquitectura x86-64, modo de
arranque y política de firmware; no se promete una cadena Secure Boot firmada universal.
No cambies firmware sin acuerdo del propietario y claves de recuperación disponibles.

Si la cápsula está cifrada, ejecuta en consola local:

```sh
aguja profile unlock
aguja status
aguja doctor
```

El sistema interno no se monta ni repara automáticamente. Doctor comprueba el live,
no la salud completa del almacenamiento interno ni la vigencia de una sesión IA.

## Paso 2 · Red y acceso

Ethernet puede obtener dirección por DHCP. Wi-Fi guardado se aplica con el perfil disponible;
`aguja wifi` permite configurarlo localmente. Sin Internet siguen disponibles las herramientas locales.

En el equipo de asistencia, conecta a la IP actual y al puerto configurado:

```sh
ssh aguja@IP_MOSTRADA
ssh -p PUERTO_CONFIGURADO aguja@IP_MOSTRADA
```

Sustituye los marcadores antes de ejecutar. Compara la huella SSH con el panel.
`aguja.local` es una alternativa solo si el cliente y la LAN admiten mDNS.
La contraseña pública de fábrica es `aguja`; personaliza el acceso para tu intervención.

El recorrido remoto actual usa **tu Tailscale/Headscale opcional**: se registra al arrancar
con red, clave válida y perfil cargado. El técnico necesita ruta y permisos en la misma
red privada. La identidad vive en RAM y se reinscribe tras reiniciar. Una IP privada
sin LAN/VPN no crea acceso por Internet. No se abren puertos del router por este recorrido.
No hay cuenta de LA AGUJA: las descargas son públicas en GitHub. Las cuentas IA y la administración de la tailnet son independientes.

## Paso 3 · Evidencia y dispositivos

```sh
aguja context
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS
findmnt
aguja tools
```

Identifica USB de rescate, origen y destino externo. `/dev/sda` no identifica siempre el mismo disco.
Si el almacenamiento muestra errores o desaparece, evita escaneos repetidos: puede convenir
una imagen con ddrescue y mapa en almacenamiento sano, seguida de trabajo sobre la copia.

No uses `/data` como destino de un rescate mayor que su espacio libre. Recuperar archivos
sobre el mismo origen puede sobrescribir lo que todavía necesitas recuperar.
BitLocker/LUKS requieren claves legítimas; LA AGUJA no rompe su cifrado.

## Paso 4 · Lectura, reparación o copia: elegir, no mezclar

- Para copiar documentos, verifica la partición y usa opciones de lectura apropiadas al filesystem.
  `aguja mount-ro` no equivale a un bloqueador físico de escritura ni una garantía forense.
- No fuerces Windows hibernado a escritura ni ejecutes reparación de filesystem sobre un montaje activo.
- Antes de escribir, conserva copia/evidencia, acuerda destino exacto, procedimiento y reversión.
- `sudo -n` es acceso root completo. «Solo lectura» en un prompt orienta al agente, no lo limita técnicamente.
- IA en nube requiere red y cuenta propias; valida lo propuesto contra el estado real de esa máquina.

## Paso 5 · Verificar y cerrar

Comprueba archivos utilizables, conexión desde el cliente o arranque del sistema interno,
según el objetivo. Un comando con exit code 0 no sustituye esa prueba observable.
Guarda un informe autorizado fuera de la RAM, retira accesos temporales, revisa montajes,
sincroniza y apaga coordinadamente antes de retirar el USB. `tmux` mantiene una sesión
tras desconectar SSH, no tras apagar el live.
