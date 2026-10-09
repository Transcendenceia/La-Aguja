# LA AGUJA 0.9.7 · control, idioma y apoyo

## Descargas públicas

Flash Imager 0.9.7 para Windows y Linux: EXE, AppImage, DEB y TAR.GZ. Verificar cada archivo contra `SHA256SUMS.txt` o las sumas específicas de plataforma. El código de Rescue 0.9.7 está incluido en esta etiqueta.

- El Imager selecciona protección cifrada por defecto, con contraseña de fábrica editable `aguja`. El arranque directo exige selección explícita.
- Idioma y distribución de teclado importados del equipo creador, con elección manual. La configuración previa al desbloqueo requiere una imagen compatible con `locale-preunlock-v1` (Rescue 0.9.7).
- Apoyo voluntario más visible: taza/corazón, botón claro y QR local. No hay ventanas automáticas, bloqueo de funciones ni conexión a Ko-fi antes de abrir el enlace.
- El sitio web y los README incluyen accesos de apoyo visibles.

## Fuente Rescue 0.9.7 e imagen personal

Centro de rescate como primera pantalla; Seguro seleccionado en cada lanzamiento de arnés; Inseguro conserva YOLO; tareas con comando, actor, resultado y salida, enmascarando credenciales; menú persistente de idioma/teclado; donación local con QR.

La imagen completa personal incluye los cuatro CLI incluso sin credenciales. No se adjunta a esta release pública: contiene binarios de Claude Code y Antigravity cuyo permiso de redistribución no está acreditado; véase `NOTICE.md`. La imagen pública descargable continúa en 0.9.0 y no recibe estos cambios por descargar solo el Imager. No se anuncia una imagen nueva que no esté disponible.

## Validación y alcance

Runtime: 166 aprobadas y una omitida. Escritorio: 99 aprobadas y diez omitidas nativas Windows. Electron Linux: 38 comprobaciones con la aplicación real; preparación y lectura de imágenes GPT/FAT directas/cifradas. Imagen personal final: BIOS y UEFI, con y sin perfil cifrado, incluidos reinicios y los cuatro CLI sin red. Idioma/teclado aplicados antes de desbloquear y cambio local conservado después del reinicio.

El EXE Windows se compiló y su contenido se verificó; no se ejecutó nuevamente en Windows en esta entrega. No se realizaron inferencias facturables ni nuevas autorizaciones con cuentas reales. No se grabó ningún USB ni se reinició la VM original.

---

## English

Public binary release of Flash Imager 0.9.7 for Windows and Linux, plus the Rescue 0.9.7 source. Encrypted profiles are selected by default with editable factory passphrase `aguja`; direct boot is explicit. Creator locale/keyboard settings can be reviewed manually. Support has a larger local coffee/heart icon and clear buttons, without automatic prompts or restricted features.

The complete Rescue 0.9.7 image remains personal because redistribution permission for its Claude Code/Antigravity binaries has not been established. The downloadable public Rescue image remains 0.9.0. Installing this Imager alone does not update the Rescue runtime; encrypted pre-unlock locale requires Rescue 0.9.7 compatibility. See `NOTICE.md` and the Spanish validation details above.
