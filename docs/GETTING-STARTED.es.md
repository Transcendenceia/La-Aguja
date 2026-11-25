# Primeros pasos · LA AGUJA (Rescue 1.1.2 · Imager 1.2.0 · IoT ESP32 v1.4.0)

[English](GETTING-STARTED.md) · [Documentación](README.es.md) · [IoT ESP32](IOT.es.md) · [Problemas](TROUBLESHOOTING.es.md) · [Ejemplos](SHOWCASE.es.md)

**Objetivo:** preparar tu puesto de mando portátil — ya sea un USB arrancable **Rescue Disk 1.1.2** para equipos x86-64, un nodo **ESP32 IoT v1.4.0** en tu tailnet, o ambos — usando **Flash Imager 1.2.0** (Linux/Windows) o **Agent Skill 1.3.0** (sin GUI). Sin cuenta de LA AGUJA ni relay propietario. [Explora las 20 misiones](PLATFORM.es.md).

## 1. Reúne lo necesario

- **PC preparador:** equipo Windows 10/11 o Linux operativo con Internet para descargar y espacio suficiente para la imagen base, descompresión y salida privada.
- **Para Rescue Disk USB (x86-64):** equipo x86-64 capaz de arrancar por USB (BIOS/UEFI) y un pendrive de **8 GiB+** cuya capacidad real supere la imagen. Grabar reemplaza su contenido.
- **Para LA AGUJA IoT (ESP32):** cualquiera de las **11 placas ESP32 soportadas** (`ESP32-C6`, `ESP32-S3`, `ESP32-C3`, `ESP32`, `ESP32-S2`), cable USB de datos, red Wi-Fi y clave de alta (auth/pre-auth key) de tu Tailscale o Headscale.
- **Permiso y respaldos:** autorización expresa sobre equipo y red, un destino sano separado antes de recuperar datos y las claves BitLocker/LUKS del propietario si aplica. LA AGUJA nunca elude cifrado.

## 2. Descarga Flash Imager 1.2.0 y medios

[Página oficial de descargas](https://aguja.transcendenceia.net/es) · [Flash Imager 1.2.0](https://github.com/Transcendenceia/La-Aguja/releases/tag/v1.2.0) · [Rescue Disk 1.1.2](https://github.com/Transcendenceia/La-Aguja/releases/tag/v1.1.2) · [Agent Skill 1.3.0](https://github.com/Transcendenceia/La-Aguja/releases/tag/flash-imager-skill-v1.3.0)

| Archivo | Función |
| --- | --- |
| `aguja-flash-imager-1.2.0-win-x64.exe` / AppImage / DEB / `.tar.gz` | Ejecuta Flash Imager (modos USB Rescue + ESP32 IoT; integra los 6 firmwares ESP32 v1.4.0 y `esptool.exe` en Windows) |
| `aguja-1.1.2-amd64.img.zst` | Imagen USB Rescue Disk comprimida; descomprime antes de importar manualmente |
| `aguja-1.1.2-amd64.iso` | ISO BIOS/UEFI para pruebas en VM o medio óptico (no es una IMG configurable) |
| `.aguja` | Perfil cifrado reutilizable para preparación USB |
| `aguja-flash-imager-skill-1.3.0.zip` | Paquete autónomo Agent Skills (Node 22+, sin Electron ni Python) para `.img` y NVS v2 ESP32 |

Prefiere el catálogo firmado de Flash Imager: verifica firma Ed25519, partes y SHA-256 completo automáticamente. Para descarga manual: [Rescue 1.1.2 `.img.zst`](https://aguja.transcendenceia.net/releases/aguja-1.1.2-amd64.img.zst), [ISO](https://aguja.transcendenceia.net/releases/aguja-1.1.2-amd64.iso) y [SHA256SUMS en GitHub](https://github.com/Transcendenceia/La-Aguja/releases/download/v1.1.2/SHA256SUMS).

Abre Flash Imager como usuario normal; solo grabar USB físico (o importar Wi-Fi en Linux) pide UAC/Polkit. La versión Windows es portátil y no necesita Node.js ni Python. Véase [desktop/README.es.md](../desktop/README.es.md).

## 3. Vía A — Prepara tu USB Rescue Disk 1.1.2

Recorre los 7 pasos del modo USB en Flash Imager 1.2.0:

1. **Imagen:** selecciona Rescue Disk `1.1.2` desde el catálogo firmado (o una `.img` local descomprimida).
2. **Red e idioma:** define idioma, teclado/variante del live, Ethernet DHCP/estático y hasta 16 redes Wi-Fi con prioridad (`imager-profile-v2`).
3. **Acceso SSH:** elige hostname y contraseña SSH propia o clave pública (nunca pegues la privada). Sustituye las credenciales de fábrica `aguja`/`aguja`.
4. **Herramientas IA y extensiones:** configura opcionalmente Codex CLI, Claude Code, Antigravity u OpenCode, destinos NAS/nube (Drive, OneDrive, Dropbox, S3, SFTP, SMB, WebDAV) y variables de entorno literales.
5. **Red privada (Tailscale / Headscale):** añade opcionalmente tu clave de alta y URL HTTPS de Headscale (vacía para Tailscale oficial). Desde Rescue `1.0.2` / `1.1.2` la identidad tailnet persiste limpiamente entre reinicios.
6. **Discos cifrados:** incluye opcionalmente claves de recuperación BitLocker/LUKS (en Windows, BitLocker local aparece arriba de las claves manuales).
7. **Crear disco:** elige protección cifrada (**Desbloquear al arrancar**) si hay secretos, confirma modelo/serie/capacidad exactos del USB y espera la verificación completa SHA-256 de lectura.

Fuera del asistente, **Perfiles y USB** guarda/abre plantillas `.aguja` cifradas o edita el `CFG` de un USB sin regrabar, y **Actualizaciones** consulta versiones firmadas del Imager.

## 4. Arranca, desbloquea y verifica el USB

Arranca desde el USB con el menú del firmware, desbloquea el perfil si está cifrado y ejecuta:

```sh
aguja profile unlock   # solo perfiles cifrados
aguja status
aguja doctor
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS
findmnt
```

- Inicia un agente con `aguja login codex|claude|antigravity` (u `opencode auth login`) y `aguja agent codex` (Codex Seguro usa sandbox `workspace-write` con aprobación humana por herramienta).
- Gestiona actualizaciones en RAM o persistentes con `aguja update menu` / `aguja update rollback`.
- Guarda resultados fuera de RAM antes de apagar; usa las acciones verificadas de persistir y apagar/reiniciar cuando trabajes con persistencia global cifrada.

## 5. Vía B — Flashea tu primer nodo ESP32 IoT

Cambia el selector lateral de **Flash Imager 1.2.0** a **IoT · MCU** y sigue los 4 pasos:

1. **Placa y autodetección USB:** conecta cualquier placa ESP32 soportada (`ESP32-C6`, `ESP32-S3`, `ESP32-C3`, `ESP32`, `ESP32-S2`) y pulsa **Detectar placa** — el Imager sondea el silicio por USB (`esptool`), detecta flash/PSRAM y selecciona automáticamente el firmware `v1.4.0` correcto.
2. **Redes Wi-Fi:** añade de 1 a 8 redes Wi-Fi ordenadas por prioridad. El **SoftAP viene desactivado por defecto** (activable manualmente si quieres un AP NAT local).
3. **Proxy Tailscale / Headscale:** introduce nombre del nodo, servidor de control (Tailscale oficial o tu Headscale + clave Noise de 64 hex + región DERP), auth key, opciones de exit node / subnet router / DNS relay y token API del agente (se genera automáticamente si queda vacío).
4. **Flashear y verificar:** revisa el mapa exacto de flash (`0x0`/`0x1000` bootloader, `0x8000` particiones, `0x9000` NVS v2 en JS puro, `0x15000` otadata, `0x20000` firmware), pulsa **Flashear placa** y observa la verificación serie en vivo. Usa **Borrar flash** cuando quieras dejar la placa limpia.

Cuando el nodo entre en tu tailnet, contrólalo a distancia con [iot/cli/aguja-iot.py](../iot/cli/aguja-iot.py) o su interfaz web oscura (`http://<ip-tailnet>/`). Más detalle en [IOT.es.md](IOT.es.md).

## 6. Vía C — Preparación headless con Agent Skill 1.3.0

Descomprime `aguja-flash-imager-skill-1.3.0.zip` (Node.js 22+, sin Electron ni Python):

```sh
node /ruta/flash-imager/scripts/imager.cjs doctor
node /ruta/flash-imager/scripts/imager.cjs iot-boards
node /ruta/flash-imager/scripts/imager.cjs iot-nvs < /privado/iot-request.json
node /ruta/flash-imager/scripts/imager.cjs prepare < /privado/usb-request.json
```

La skill se detiene en archivos locales `.img` / `.bin` verificados (`device_written: false`) y nunca escribe USBs físicos ni puertos serie automáticamente. Consulta [harnesses.md](../skills/flash-imager/references/harnesses.md) e [iot.md](../skills/flash-imager/references/iot.md).

Siguiente: [20 misiones de la plataforma](PLATFORM.es.md) · [Arquitectura IoT](IOT.es.md) · [Problemas](TROUBLESHOOTING.es.md) · [Notas de Imager 1.2.0](RELEASE-IMAGER-1.2.0.md).
