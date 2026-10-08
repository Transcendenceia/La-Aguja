# LA AGUJA 0.9.0 · apertura del proyecto

- GPL-3.0-or-later para el código y recursos propios, conservando avisos de
  terceros y los permisos MIT otorgados en versiones anteriores.
- Sin cuentas de LA AGUJA, verificación de correo ni sesiones para descargar,
  abrir el Imager o preparar un USB.
- Web informativa: documentación y descargas públicas directas de GitHub.
  Retirados servidor de cuentas, consola WebSocket, relay y conector propios.
- Acceso remoto por tu LAN o Tailscale/Headscale y SSH; no se modifica la tailnet
  del propietario ni se genera una cuenta adicional.
- Catálogo Ed25519 fijado al repositorio y descarga multipart con SHA-256 de
  cada parte y de la imagen completa, sin enviar cabeceras de cuenta.
- Codex y OpenCode incluidos. Claude Code y Antigravity siguen integrados como
  proveedores opcionales, instalados desde el proveedor, no redistribuidos.
- Conservados perfil cifrado, red, idiomas/teclados, controles de identidad USB,
  grabación verificada y BitLocker con autorización nativa.

## Qué archivo descargar

Windows: EXE portátil. Linux: AppImage, DEB o TAR con la carpeta completa.
El Imager descarga la IMG por partes y las une. Para importación manual,
descomprimir `.img.zst` y comprobar su SHA-256. ISO permite probar arranque;
la IMG incorpora las particiones de configuración y datos para el USB.

No grabar una parte sola. Una clave API/IA o tailnet sigue perteneciendo al
usuario y al proveedor, no al sitio. La imagen de fábrica no contiene perfiles,
sesiones OAuth, identidades tailnet ni claves SSH personales.

La comprobación de un archivo no acredita compatibilidad con todo hardware;
preparación, escritura física, arranque y login/inferencia son pruebas distintas.
