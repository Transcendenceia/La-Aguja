# Arneses

| Nombre | Binario | Modo full del launcher | Autenticación |
|---|---|---|---|
| Codex | codex | --dangerously-bypass-approvals-and-sandbox | ChatGPT o API según proveedor |
| Antigravity | agy | --dangerously-skip-permissions | Google OAuth o Gemini API según CLI |
| Claude Code | claude | --dangerously-skip-permissions | Anthropic OAuth/API según plan |
| OpenCode | opencode | permission=allow vía OPENCODE_CONFIG_CONTENT | /connect o proveedor compatible |

El launcher **no inicia acciones IA al arrancar**. Ejecuta el arnés elegido desde el menú
o `aguja agent NOMBRE`; los binarios directos siguen disponibles con opciones normales.
Cambiar agent_mode a ask conserva sus políticas normales y el acceso sudo.

## Preparar y autorizar: recorrido actual

El [manual con capturas](https://aguja.transcendenceia.net/docs#ia-preparacion) distingue
sesión IA, alta de tailnet y autenticación SSH (descarga sin cuenta). Son independientes.

En Flash Imager 0.8.2, selecciona **Mi sesión de este equipo**, pulsa **Iniciar sesión en
este PC**, completa el CLI oficial y vuelve para **Comprobar e importar**. Abrir el terminal
no importa una sesión. Solo se admiten archivos portables validados; un llavero ligado al
PC no se vuelve portable por copiarlo. Alternativas: **Clave API** o **Configurar después**.
La instalación local del CLI es opcional para importar; el Rescue Disk ya incluye los cuatro.

En Rescue Disk 0.8.0, `aguja login claude|antigravity|codex` abre el mini navegador local
compatible y mantiene el callback oficial y la misma PTY. Autoriza tú en el dominio oficial.
Si requiere copiar un código, el foco vuelve a la consola y tú pegas con Ctrl+Shift+V.
Cerrar devuelve al terminal original. OpenCode conserva `opencode auth login` nativo.
**El nuevo recorrido no usa QR.** El [informe OAuth 0.3.2](oauth-0.3.2/RESULT.md)
se conserva como evidencia histórica, no como instrucciones actuales.

Para SSH interactivo utiliza `ssh -t aguja@IP` y `tmux new -s rescate`.
Codex ofrece `codex login --device-auth` para un terminal sin navegador local; comprueba los
requisitos de la cuenta en su documentación oficial.
Si el proveedor necesita callback local, usa su modo de autenticación para dispositivo/SSH
o un túnel del puerto real indicado por el CLI; no expongas callbacks en todas las interfaces.
No copies tokens de otra máquina indiscriminadamente. Con persistent_home=no se pierden al reiniciar.

Fuentes oficiales verificadas para instalación:
- [Codex CLI](https://learn.chatgpt.com/docs/codex/cli)
- [Claude Code setup](https://code.claude.com/docs/en/setup)
- [Antigravity CLI](https://antigravity.google/docs/cli/install/)
- [OpenCode](https://opencode.ai/docs/)

Licencias, planes, cuotas, regiones y métodos de autenticación siguen siendo responsabilidad
del proveedor. LA AGUJA no incluye una suscripción ni saldo.

## Proveedores opcionales en el medio público

Codex y OpenCode se incluyen con sus licencias. Claude Code y Antigravity **no se redistribuyen** en el medio público; los paneles permiten configurar sus credenciales para una instalación del proveedor, no prometen que el binario venga preinstalado.

Instala la versión del proveedor desde su documentación oficial antes de `aguja login` / `aguja agent`: [Claude Code](https://code.claude.com/docs/en/setup), [Antigravity](https://antigravity.google/). Comprueba las condiciones y el artefacto oficial; no ejecutes un instalador tomado de un fork ni mezcles la identidad de LA AGUJA con la del proveedor. Las versiones usadas en pruebas anteriores se indican en `config/harnesses.json`, no se descargan en el arranque.

En una sesión live una instalación en RAM desaparece al reiniciar. Si necesitas conservarla, usa un entorno personalizado de uso propio y evita publicar sus credenciales/binarios.
