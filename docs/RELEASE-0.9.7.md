# LA AGUJA 0.9.7 · control, idioma y apoyo

## Descargas públicas

Flash Imager 0.9.7 para Windows y Linux: EXE, AppImage, DEB y TAR.GZ. Verificar cada archivo contra `SHA256SUMS.txt` o las sumas específicas de plataforma. El código de Rescue 0.9.7 está incluido en esta etiqueta.

- El Imager selecciona protección cifrada por defecto, con contraseña de fábrica editable `aguja`. El arranque directo exige selección explícita.
- Idioma y distribución de teclado importados del equipo creador, con elección manual. La configuración previa al desbloqueo requiere una imagen compatible con `locale-preunlock-v1` (Rescue 0.9.7).
- Apoyo voluntario más visible: taza/corazón, botón claro y QR local. No hay ventanas automáticas, bloqueo de funciones ni conexión a Ko-fi antes de abrir el enlace.
- El sitio web y los README incluyen accesos de apoyo visibles.

## Rescue Disk 0.9.7 completo

Centro de rescate como primera pantalla; Seguro seleccionado en cada lanzamiento de arnés; Inseguro conserva YOLO; tareas con comando, actor, resultado y salida, enmascarando credenciales; menú persistente de idioma/teclado; donación local con QR.

La imagen completa de fábrica 0.9.7 está disponible en la web oficial como IMG comprimida e ISO BIOS/UEFI. El catálogo firmado del Imager 0.9.8 descarga las partes y verifica el SHA-256 de la imagen completa. Incluye los cuatro CLI incluso sin credenciales; no contiene perfiles personales. Verifica las descargas contra `SHA256SUMS-rescue-0.9.7.txt`. Los binarios externos conservan sus licencias y condiciones; la publicación no los convierte en GPL ni acredita permisos adicionales de sus proveedores. Véase `NOTICE.md`. Descargar el Imager no actualiza un USB ya grabado: prepara y graba la nueva imagen.

- [Imagen USB 0.9.7 (.img.zst)](https://aguja.transcendenceia.net/releases/aguja-0.9.7-amd64.img.zst)
- [ISO 0.9.7 BIOS/UEFI](https://aguja.transcendenceia.net/releases/aguja-0.9.7-amd64.iso)
- [SHA256SUMS Rescue 0.9.7](https://aguja.transcendenceia.net/releases/SHA256SUMS-rescue-0.9.7.txt)

El Imager 0.9.7 conserva su catálogo antiguo (Rescue 0.9.0). Para descargar automáticamente Rescue 0.9.7, usa [Imager 0.9.8](https://github.com/Transcendenceia/La-Aguja/releases/tag/v0.9.8), que incorpora la nueva clave de firma. Alternativamente, descomprime la IMG e impórtala manualmente.

## Validación y alcance

Runtime: 166 aprobadas y una omitida. Escritorio: 99 aprobadas y diez omitidas nativas Windows. Electron Linux: 38 comprobaciones con la aplicación real; preparación y lectura de imágenes GPT/FAT directas/cifradas. Imagen personal final: BIOS y UEFI, con y sin perfil cifrado, incluidos reinicios y los cuatro CLI sin red. Idioma/teclado aplicados antes de desbloquear y cambio local conservado después del reinicio.

El EXE Windows se compiló y su contenido se verificó; no se ejecutó nuevamente en Windows en esta entrega. No se realizaron inferencias facturables ni nuevas autorizaciones con cuentas reales. No se grabó ningún USB ni se reinició la VM original.

---

## English

Public binary release of Flash Imager 0.9.7 for Windows and Linux, plus the Rescue 0.9.7 source. Encrypted profiles are selected by default with editable factory passphrase `aguja`; direct boot is explicit. Creator locale/keyboard settings can be reviewed manually. Support has a larger local coffee/heart icon and clear buttons, without automatic prompts or restricted features.

The complete factory Rescue 0.9.7 image is available from the official website as compressed IMG and BIOS/UEFI ISO, with the signed Imager catalogue and SHA-256 checksums. All four clients are preinstalled; no personal profiles are included. Third-party binaries retain their own licences and terms; publication does not grant additional redistribution rights or relicense them as GPL. See `NOTICE.md`. Installing the Imager alone does not update an existing USB: prepare and write the new Rescue image.
