# Arneses

| Nombre | Binario | Modo full del launcher | Autenticación |
|---|---|---|---|
| Codex | codex | --dangerously-bypass-approvals-and-sandbox | ChatGPT o API según proveedor |
| Antigravity | agy | --dangerously-skip-permissions | Google OAuth o Gemini API según CLI |
| Claude Code | claude | --dangerously-skip-permissions | Anthropic OAuth/API según plan |
| OpenCode | opencode | permission=allow vía OPENCODE_CONFIG_CONTENT | /connect o proveedor compatible |

El launcher **no inicia acciones IA al arrancar**. Ejecuta el arnés elegido desde el menú
o `aguja agent NOMBRE`; los binarios directos siguen disponibles con opciones normales.
Desde 0.9.7 cada lanzamiento muestra **Seguro** primero y **Inseguro** después; no se recuerda una selección insegura. Seguro exige confirmación de herramientas: permisos `ask` en OpenCode/Antigravity, reglas `ask` en Claude y una puerta humana PreToolUse con broker privado en Codex. En Codex se exige una respuesta afirmativa nueva; Enter, Escape, EOF, fallo de broker o tiempo agotado deniegan la tarea. No cambia sudo ni pretende ser una frontera contra un usuario local que ejecute directamente un CLI o modifique su configuración. Inseguro conserva los modos full de la tabla.

## Preparar y autorizar: recorrido actual

El [manual con capturas](https://aguja.transcendenceia.net/docs#ia-preparacion) distingue
sesión IA, alta de tailnet y autenticación SSH (descarga sin cuenta). Son independientes.

En Flash Imager 0.9.5, selecciona **Mi sesión de este equipo**, pulsa **Iniciar sesión en
este PC**, completa el CLI oficial y vuelve para **Comprobar e importar**. Abrir el terminal
no importa una sesión. Solo se admiten archivos portables validados; un llavero ligado al
PC no se vuelve portable por copiarlo. Alternativas: **Clave API** o **Configurar después**.
La instalación local del CLI es opcional para importar; el Rescue Disk ya incluye los cuatro.

En Rescue Disk, `aguja login claude|antigravity|codex` abre el mini navegador local
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

## Instalación independiente de la autenticación

Las imágenes personales completas incluyen los cuatro ejecutables, con versiones bloqueadas
por `config/harnesses.json`. Ninguna selección «Configurar después», perfil vacío o perfil
cifrado elimina un CLI. Los binarios están en la raíz inmutable: no requieren Internet para
instalarse durante el arranque ni HOME persistente para sobrevivir al reinicio.

`aguja doctor` falla si falta cualquiera de los cuatro CLI. La construcción comprueba
`--version` con un HOME vacío, y el smoke BIOS/UEFI ejecuta los cuatro sin autenticar.

Construcción de uso propio: `sudo scripts/build-rootfs.sh`, seguida de
`sudo scripts/build-image.sh --personal`. El artefacto se llama `aguja-personal-VERSION-amd64.img`
y se marca `distribution: personal`. No se publica automáticamente ni sustituye las releases.

La imagen pública 0.9.0 anteriormente publicada contiene solo Codex y OpenCode. Las licencias
originales de Claude/Antigravity no cambian por instalarlos: mantener estos medios personales
fuera de releases públicas hasta acreditar la distribución, según `NOTICE.md`.
