# Harness-neutral installation

The package follows the open [Agent Skills specification](https://agentskills.io/specification): a `flash-imager/` directory containing `SKILL.md`, references, assets and executable scripts. No provider-specific tool names, hooks, permission overrides or account service are required.

Download `aguja-flash-imager-skill-1.0.0.zip` or `.tar.gz` from [the Imager release](https://github.com/Transcendenceia/La-Aguja/releases/tag/v0.9.2) and check `SHA256SUMS-flash-imager-skill-1.0.0`. Extract the **whole** `flash-imager` folder; copying only `SKILL.md` loses the execution engine. Do not overwrite another installed skill without preserving its version. Run `node <installed-folder>/scripts/imager.cjs doctor` after extraction.

## Discovery locations

These are documented discovery paths, not a claim that every product/version has been end-to-end tested. Install in one appropriate location, then check discovery in your harness. `~` means your home directory; on Windows use the equivalent user profile path.

| Harness | Folder containing `flash-imager/` | Reference |
| --- | --- | --- |
| Codex | project `.agents/skills/` | [OpenAI repository skill guidance](https://developers.openai.com/blog/skills-agents-sdk) |
| Claude Code | project `.claude/skills/` or user `~/.claude/skills/` | [Claude Code skills](https://code.claude.com/docs/en/skills) |
| OpenCode | project `.agents/skills/`, `.opencode/skills/` or user `~/.config/opencode/skills/` | [OpenCode skills](https://opencode.ai/docs/skills/) |
| Gemini CLI | project `.agents/skills/`, `.gemini/skills/` or user `~/.gemini/skills/` | [Gemini CLI skills](https://geminicli.com/docs/cli/skills/) |
| Cursor | project `.agents/skills/`, `.cursor/skills/` or user `~/.cursor/skills/` | [Cursor skills](https://cursor.com/docs/skills) |
| OpenClaw | workspace `skills/flash-imager/` or your configured extra skill directory | Follow your installation's skill catalogue and file/shell policy. |
| Antigravity, other agents, custom SDK harnesses | Manual loading, or their documented Agent Skills directory if supported by that version | Do not invent a discovery path. |

For a source checkout rather than the release bundle, leave the skill in `skills/flash-imager/` and load it manually; its script resolves the repository's `desktop/` engine. To install a standalone copy elsewhere, use the built ZIP instead. Contributors build it with `python3 scripts/package-imager-skill.py <output-directory>` after `npm ci --prefix desktop`.

## Any harness with files and shell

If native skills are unavailable, ask the agent:

> Read `/absolute/path/flash-imager/SKILL.md` and use its bundled script to prepare my La Aguja image. Create only the file; do not write any USB.

The host can expose the same executable through a process tool (argv array plus JSON stdin). Never add secrets to argv or tool descriptions. No MCP adapter is required to invoke a local executable. Browser-only agents without filesystem/shell access can explain or design the configuration but cannot execute this workflow. Hosted agents can create a downloadable file if their sandbox has Node and enough storage; that does not give them access to the user's local USB.

## Español

Descarga y descomprime la carpeta completa `flash-imager`, comprueba sus sumas y colócala en el directorio de skills de tu agente. Si no admite descubrimiento automático, dile: «Lee `/ruta/flash-imager/SKILL.md` y prepara mi imagen de La Aguja; solo el archivo, sin grabar ningún USB». Necesita Node 22+, acceso a archivos y terminal. La skill usa el motor real del Imager; no necesita Electron ni una cuenta de La Aguja. La creación del archivo no prueba que haya arrancado en tu equipo. Consulta `interface.md` para la configuración JSON y el tratamiento privado de claves.
