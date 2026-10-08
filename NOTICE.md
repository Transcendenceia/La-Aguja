# Licencias y distribución

Copyright © 2026 Transcendence IA y colaboradores de LA AGUJA.

El código propio, documentación y recursos propios de esta edición se publican
bajo **GPL-3.0-or-later**. El texto completo está en `LICENSE`. Las versiones
anteriores concedidas bajo MIT conservan esos permisos; su texto se conserva
en `licenses/MIT-previous-releases.txt`. No se revocan derechos anteriores.

Esta licencia no cambia las licencias de Debian, Linux, firmware, bibliotecas,
Electron/Chromium, Tailscale ni los clientes/modelos de terceros. LA AGUJA no
es un producto oficial de los proveedores IA ni de Tailscale/Headscale.

## Componentes externos

| Componente | Régimen / evidencia |
|---|---|
| Electron, herramientas npm del Imager | Conservar LICENSE de Electron y LICENSES.chromium.html del paquete; inventario npm en cada release. |
| Debian y kernel Linux | Licencias por paquete en `/usr/share/doc/*/copyright`; obtener fuentes correspondientes con los repositorios Debian de la versión construida. |
| Codex CLI | Apache-2.0 en su proyecto original; preservar licencia/avisos originales. |
| OpenCode | Licencia de la versión fijada en su proyecto original; preservar su archivo LICENSE. |
| Tailscale | BSD-3-Clause para el código del cliente; preservar avisos. Headscale pertenece al administrador, no está alojado en LA AGUJA. |
| Firmware de hardware | Licencias por paquete; no declarar todo el medio GPL ni completamente libre. |
| Claude Code | Software de Anthropic, no GPL. No publicar binarios sin derecho de redistribución acreditado. https://github.com/anthropics/claude-code/blob/main/LICENSE.md |
| Antigravity | Software/servicio de Google sujeto a sus condiciones; no relicenciar ni atribuir permiso de redistribución por ser descargable. https://www.antigravity.google/terms |

Los proveedores pueden exigir su propia cuenta/API y aplicar cuotas. Eso no
es una cuenta de LA AGUJA: descargar, abrir el Imager y preparar un USB no
requiere registro en LA AGUJA ni en su web.

## Publicar medios y fuentes correspondientes

No reutilizar una imagen privada de trabajo ni un USB personalizado como
release. Construir desde código público, inventariar dependencias y licencias,
incluir sumas y el código correspondiente a esa etiqueta. Los binarios sin
redistribución acreditada se instalan desde el proveedor a petición del usuario,
no se incluyen en el medio público por defecto. No subir tokens, perfiles,
claves de firma privadas, expedientes de operación ni historiales privados.

La marca LA AGUJA/Agujita identifica el proyecto: el permiso sobre código y
recursos propios no constituye respaldo oficial de forks o proveedores.
