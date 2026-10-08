# LA AGUJA Flash Imager · Windows y Linux 0.9.2

Prepara y graba tu Rescue Disk desde un PC. Conserva Agujita, herramientas IA, red, idioma/teclado, acceso SSH y soporte BitLocker Windows. La nueva conexión remota usa **tu propia Tailscale o Headscale**, no un túnel de nuestra plataforma.

[Manual por niveles con capturas, glosario y primer USB](https://aguja.transcendenceia.net/es/docs) · [Copia del manual](../docs/USER-GUIDE.md) · [Aplicación y biblioteca](https://aguja.transcendenceia.net/).
La web es pública e informativa. Descargar y preparar no requiere registro en LA AGUJA.

## Preparar un disco

1. Elige una imagen `.img` sin comprimir. Comprueba procedencia y SHA completo; el catálogo oficial se verifica con su firma Ed25519. Un SHA calculado no prueba procedencia.
2. Configura Ethernet/Wi-Fi, idioma y teclado. DHCP es el punto de partida si tu red no exige otra cosa.
3. Define nombre del equipo, contraseña SSH o clave pública y puerto. Nunca pegues la clave privada.
4. Elige herramientas IA: API, sesión portable importada o login pendiente en el disco. Instalar/iniciar sesión del CLI en este PC no autentica automáticamente todas las sesiones de rescate.
5. Opcionalmente activa **Red privada Tailscale / Headscale**. Pega la auth/pre-auth key; URL vacía selecciona Tailscale oficial, URL HTTPS propia selecciona Headscale. Nombre de nodo opcional.
6. Revisa el resumen. Cifra la cápsula del USB cuando incluya secretos. **Crear imagen privada** guarda un archivo nuevo; **Preparar y grabar USB** lo prepara automáticamente.
7. Comprueba modelo, capacidad, dispositivo y serie del USB en la ventana nativa. La grabación borra el contenido. Cancelar no prepara ni escribe. Espera verificación de lectura.

Imágenes con alta automática requieren `tailscale-profile-v1`. Una imagen antigua se rechaza antes de preparar el perfil, en Windows y Linux. No edites el marcador para fingir que el live contiene servicios que no tiene.

## Tailnet y SSH: diferencias importantes

- La opción está **apagada por defecto**. Desactivada, el perfil no incluye la auth key. Una selección legacy de túnel no crea, vincula ni copia credenciales a nuevas imágenes.
- **OpenSSH normal por tailnet es el valor predeterminado**: usa tu contraseña/clave pública y el puerto elegido. El técnico debe estar en la misma tailnet y su política debe permitir ese puerto.
- **Tailscale SSH** es avanzado y distinto: intercepta el puerto 22 de la IP de tailnet y requiere políticas SSH del control plane. No basta la clave de alta; no es necesario activarlo para transportar OpenSSH.
- **Aceptar rutas** está apagado. No anuncia rutas, ni convierte el disco en router o exit node.
- La app no inscribe tu PC personal. El live hace el alta al arrancar con red, opción habilitada y perfil disponible/desbloqueado.
- Estado/identidad de tailnet en RAM: cada reinicio reinscribe. Una clave de un uso solo permite el primer registro. Para repetir sin regrabar, usa una clave reutilizable válida y limitada; gestiona nodos antiguos en tu control plane. No se promete IP estable.
- El SSH no pasa por nuestro relay de consola. Tailscale/Headscale todavía necesita control plane y, según la red, DERP: no significa cero tráfico, coste ni responsabilidad para su operador.

La clave queda dentro de la cápsula. Cifrarla protege secretos en reposo mientras esté bloqueada, **no frente a root/agente completo una vez desbloqueada**, ni cifra todo AGUJA_DATA. Revocar una clave de alta no elimina automáticamente todos los nodos ya inscritos.

## Windows

Flash Imager **0.9.2** es la candidata pública. Publicación y comprobaciones nativas se registran por separado; no se atribuyen a esta versión las pruebas de otras versiones.

Abre `aguja-flash-imager-0.9.2-win-x64.exe` como tu usuario. Es portátil; no necesitas Node.js. No se promete instalador firmado ni ausencia de avisos SmartScreen. La app no necesita ejecutarse como administrador: **UAC eleva únicamente el grabador de USB**, no toda la interfaz Electron.

Tras confirmar el borrado y autorizar UAC, el grabador vuelve a comprobar **serie, capacidad y modelo exactos** del USB y rechaza discos internos, de sistema o de arranque. Conserva abierto el archivo de imagen verificado durante la escritura. El éxito exige grabación completa, sincronización y **lectura SHA-256 de todos los bytes de la imagen desde el USB**; no basta con que el proceso termine sin errores. Cancelar UAC no graba; cerrar la app durante una grabación puede dejar el USB incompleto y obliga a repetirla.

**Capacidad de datos:** Windows conserva el tamaño de `AGUJA_DATA` y la geometría de particiones de la IMG. **No amplía DATA para ocupar un USB mayor ni reubica su GPT secundaria al final físico del USB**; el espacio sobrante queda sin asignar. El arranque del Rescue Disk tampoco hace esa ampliación automáticamente. El grabador Linux tiene su propia fase de ampliación verificada.

**Respaldo previo integrado no disponible:** se oculta esa opción y el backend rechaza `backup:true` antes de confirmar, preparar o escribir. Respalda fuera de la app antes de grabar. BitLocker sigue independiente: consultar/exportar la recovery key exige que Windows la tenga disponible y permisos; no elude el cifrado ni crea claves inexistentes.

## Linux

- AppImage: `chmod +x aguja-flash-imager-0.9.2-x86_64.AppImage`, después ábrelo como tu usuario. Si falta FUSE, usa `--appimage-extract-and-run`; no desactiva el sandbox.
- DEB: instala el paquete local con tu gestor de paquetes.
- TAR: extrae la carpeta completa y ejecuta el binario de la aplicación.
- No necesitas sudo para abrir, configurar o preparar la imagen. Importar Wi-Fi/grabar solicita Polkit.
- Respaldo USB completo opcional y verificado, desmarcado por defecto. Un respaldo del USB no respalda el disco interno que vas a rescatar.

Helpers Arch/Cachy: `python`, `python-cryptography`, `mtools`, `polkit`, `zstd`, `gptfdisk`, `e2fsprogs`, `util-linux`; `networkmanager` para importar Wi-Fi. Debian/Ubuntu: `python3`, `python3-cryptography`, `mtools`, `pkexec`, `zstd`, `gdisk`, `e2fsprogs`, `util-linux`; `network-manager` para importar Wi-Fi.

## Autenticación IA y perfiles

El inicio de sesión de un CLI del PC abre el terminal oficial; tú autorizas. La importación permite solo archivos nativos portables validados del usuario, no llavero completo, historial, hooks o MCP. Un formato válido no prueba vigencia. El producto no crea sesiones ni tokens de LA AGUJA.

Un perfil reutilizable `.aguja` va cifrado AES-256-GCM/scrypt; incluye red/SSH/API y tailnet habilitada, no credenciales desconocidas inyectadas por el renderer. Las sesiones OAuth se comprueban otra vez al preparar. Desactivar tailnet retira sus secretos del perfil preparado/exportado.

En el Rescue Disk, `aguja login codex|claude|antigravity` abre el mini navegador local para un flujo oficial compatible. Callback nativo y misma PTY; copiar cambia foco y tú pegas explícitamente con Ctrl+Shift+V. OpenCode utiliza `opencode auth login` nativo. No QR en el nuevo recorrido. SSH/serie/sin pantalla conserva la URL y su método nativo, no abre una GUI mágica.

## Desarrollo y verificación

```bash
npm ci
npm test
xvfb-run -a node tests/electron-e2e.cjs
xvfb-run -a node tests/i18n-ui-e2e.cjs
xvfb-run -a node tests/flash-ui-e2e.cjs
xvfb-run -a node tests/tailnet-ui-qa.cjs
npm run build:linux
npm run build:win
```

`tests/tailnet-ui-qa.cjs` acepta `AGUJA_QA_EXECUTABLE` para un binario empaquetado, `AGUJA_QA_ROOT` para capturas/informe y `AGUJA_QA_IMAGE` para una imagen sintética compatible. Con esta última prepara cápsulas tailnet en claro y cifradas mediante IPC real; **no inscribe una tailnet, no autoriza cuentas ni graba un USB físico**. Las capturas mantienen claves sintéticas ocultas.

`windows-profile.test.cjs` prepara GPT/FAT32 real con el escritor Windows JS; mtools lee el perfil y el lector Python real lo abre en ambos modos. También prueba el rechazo de imagen sin capacidad tailnet y la conservación de la fuente. Esta prueba corre en Linux con herramientas FAT, no certifica el sistema de E/S de cualquier Windows.

Las pruebas Electron pueden usar `--no-sandbox` solo en el contenedor de QA que no admite namespaces; esa opción no forma parte del producto entregado. El renderer mantiene `contextIsolation:true`, `sandbox:true`, `nodeIntegration:false`, navegación bloqueada y CSP local. CLI, USB físico, login/inferencia real y arranque de hardware se verifican por separado en el informe de entrega.
