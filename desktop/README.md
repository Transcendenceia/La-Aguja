# LA AGUJA Flash Imager · Windows and Linux 0.9.4

[Español](README.es.md) · [User guide](https://aguja.transcendenceia.net/en/docs) · [Downloads](https://aguja.transcendenceia.net/en#application)

Prepare a Rescue Disk from a working computer: network, language/keyboard, SSH, AI tools and optional Windows BitLocker recovery keys. Optional remote access uses your own Tailscale/Headscale, not a project tunnel. No LA AGUJA account is required.

## Prepare a disk

1. Select a decompressed `.img` or use the signed catalogue. The catalogue uses Ed25519; a calculated hash alone is not proof of origin.
2. Configure Ethernet/Wi-Fi, language and keyboard. DHCP is a useful starting point.
3. Set hostname, personal SSH password or public key and port. Never paste a private key.
4. Choose API credentials, compatible portable-session import or sign-in later on the live system. A login on this PC does not automatically authenticate every rescue session.
5. Optionally enable Tailscale/Headscale with your authorised key. Empty Headscale URL selects official Tailscale; otherwise use your HTTPS server. Optional node name.
6. Review the summary and encrypt secrets. Creating a private image saves a new file; preparing and flashing USB creates it automatically.
7. Confirm the USB model, actual capacity and serial number in the native dialog. Writing replaces its contents. Wait for complete read-back verification and test booting.

Tailnet preparation requires `tailscale-profile-v1`; unsupported images are rejected. Do not alter feature markers to pretend an image has services it lacks.

## Tailnet and SSH

Private networking is off by default. When disabled, registration secrets are omitted. Legacy tunnel choices do not pair devices or copy project credentials.

Normal OpenSSH over tailnet is default; keys/passwords, selected port and network ACLs apply. Tailscale SSH is advanced, uses tailnet port 22 and requires compatible control-plane SSH policies. Accepting routes is off; the live does not announce routes or become an exit node.

The live registers after boot, network and profile unlock; the application does not enrol the preparation PC. Tailnet identity is held in RAM, so every reboot registers again. A one-use key may only permit the first boot. For repeated boots use valid, scoped reusable keys and clean up old nodes. No stable IP is promised. Your control plane and possibly DERP remain involved; this is not zero traffic or zero operational responsibility.

Capsule encryption protects locked secrets at rest, not all AGUJA_DATA or secrets against root after unlock. Revoking a registration key does not automatically remove already enrolled nodes.

## Windows

Open `aguja-flash-imager-0.9.4-win-x64.exe` as your normal user. It is portable and does not require Node.js. No recognised Authenticode signature or absence of SmartScreen prompts is promised. **UAC elevates only the USB writer**, not the Electron interface.

After consent the writer rechecks exact model, serial and capacity, rejects internal/system/boot disks and holds the verified image open. Success requires full writing, synchronisation and SHA-256 read-back of all image bytes. Cancelling UAC does not write; closing during writing can leave incomplete media.

Windows keeps AGUJA_DATA size and original partition geometry: it does not expand DATA or relocate the backup GPT to the larger physical USB's end. Unused space remains unallocated; the live does not automatically expand it. Linux has its own verified expansion phase.

**No integrated USB backup:** the option is hidden and backend rejects `backup:true` before preparing/writing. Back up externally. BitLocker key inspection/export requires available keys and permissions; it does not bypass encryption or create missing recovery keys.

## Linux

- AppImage: grant execute permission, then run as your user. If FUSE is unavailable, `--appimage-extract-and-run` is an alternative without disabling the sandbox.
- DEB: install through your package manager.
- TAR: extract the complete directory and run its application binary.
- No sudo for opening/configuration/preparation; Wi-Fi import and writing use Polkit.
- Optional verified full USB backup is off by default; it is not an internal-disk backup.

Arch/Cachy helpers: `python`, `python-cryptography`, `mtools`, `polkit`, `zstd`, `gptfdisk`, `e2fsprogs`, `util-linux`; `networkmanager` for Wi-Fi import. Debian/Ubuntu: `python3`, `python3-cryptography`, `mtools`, `pkexec`, `zstd`, `gdisk`, `e2fsprogs`, `util-linux`; `network-manager` for Wi-Fi import.

## AI and profiles

CLI login opens the official local terminal flow and you authorise it. Imports accept supported native session files and selected Windows Credential Manager entries, not complete keychains/history/hooks/MCP. Format validity does not prove a current session.

Reusable `.aguja` profiles use AES-256-GCM/scrypt and contain authorised configuration. Sessions are checked again during preparation; disabling tailnet removes its secrets from prepared/exported profiles.

On the live, `aguja login codex|claude|antigravity` supports official local browser login with the original PTY. Copying focuses the console; paste explicitly with Ctrl+Shift+V. OpenCode uses native `opencode auth login`. No QR in the current flow. SSH/serial/headless sessions keep native methods, not an automatic remote GUI or forwarded callback.

## Development

```sh
npm ci
npm test
xvfb-run -a node tests/electron-e2e.cjs
xvfb-run -a node tests/i18n-ui-e2e.cjs
xvfb-run -a node tests/flash-ui-e2e.cjs
xvfb-run -a node tests/tailnet-ui-qa.cjs
npm run build:linux
npm run build:win
```

`tests/tailnet-ui-qa.cjs` accepts `AGUJA_QA_EXECUTABLE`, `AGUJA_QA_ROOT` and `AGUJA_QA_IMAGE` for packaged execution, evidence and a compatible synthetic image. It can prepare plain/encrypted capsules through real IPC but does not enrol a tailnet, authorise accounts or flash a physical USB. Synthetic credentials remain hidden.

## Imager 0.9.3 import fixes

- Linux AppImage: privileged Wi-Fi and USB helpers are staged off FUSE into an ephemeral 0700 directory (0600 script), then removed on completion or cancellation. Only the bundled standalone script is copied, never credentials.
- Wi-Fi import reports permission cancellation, missing NetworkManager, unavailable PSK and unsupported security instead of silently accepting a missing password. Open, WPA-PSK and WPA3-SAE profiles remain supported; user keyring-only secrets may require manual entry.
- Windows recheck reads current persisted user/machine tool locations without loading shell profiles or querying credential environment variables. Lookup covers npm custom prefixes, pnpm, Bun, Scoop and NVM directories.
- Native profile imports accept BOM-marked UTF-8/UTF-16 and OpenCode JSONC; only existing allowlisted data is exported as UTF-8 to canonical Linux paths. Hooks, MCP servers, plugins, history and host paths are not copied.
- **Select profile folder** explicitly selects a custom or accessible WSL profile directory, without auto-scanning WSL users or launching WSL. This does not export a whole OS keyring. A CLI being installed or authenticated does not by itself guarantee a portable auth file or token validity.
- Failed re-imports refresh the renderer status and invalidate prepared images; file replacement with symlinks is still rejected.

The Rescue Disk image remains 0.9.0. These changes concern the desktop preparer and its bundled profile helper, not the boot image.

## Imager 0.9.4 · native Windows sessions

- Antigravity: reads its exact native `gemini` Credential Manager entry (derived from the current user profile), then exports only OAuth fields to the Linux-compatible profile. A selected folder explicitly imports its portable file instead.
- Codex: honours `cli_auth_credentials_store` (`file`, `keyring`, `auto`), custom `CODEX_HOME`, UTF-16 native keyring entries and the encrypted `secrets/codex_auth.age` backend. Only `global/CODEX_AUTH` is decrypted; MCP/general secrets are not imported. The exported config uses file storage on the rescue system.
- Claude Code: native `.claude/.credentials.json`, including `CLAUDE_CONFIG_DIR`. OpenCode: native XDG `opencode/auth.json` and JSON/JSONC settings with configured locations.
- Run the Imager as the same Windows user as the authenticated CLI. No elevation is needed to import your own session. The reader is read-only; tokens travel through a private process pipe and stay in main-process memory until image preparation or revocation. No temporary plaintext credential file is created.
- A valid imported format is not a live provider authentication check. Synthetic Windows vault and GUI regression tests do not claim real-account inference. Linux imports are unchanged.

Native backend references: [Codex storage](https://github.com/openai/codex/blob/main/codex-rs/login/src/auth/storage.rs), [Codex encrypted store](https://github.com/openai/codex/blob/main/codex-rs/secrets/src/local.rs), [Claude storage](https://code.claude.com/docs/en/authentication), [OpenCode auth](https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/auth/index.ts), [Antigravity auth](https://antigravity.google/docs/cli/install/).

## Cambios 0.9.7

El desbloqueo cifrado al arrancar es el valor inicial, con contraseña pública editable `aguja`. Arranque directo requiere selección expresa. Idioma/teclado se importan del equipo y pueden corregirse; los perfiles cifrados con idioma requieren Rescue Disk 0.9.7 para aplicarlo antes del desbloqueo. La página de apoyo usa un QR local y abre Ko-fi solo al pulsar el enlace. No incluye claves de Ko-fi.

## Cambios 0.9.9

Comprueba el espacio disponible antes de copiar la imagen privada y muestra cuánto falta. En Windows, al preparar y grabar, permite elegir otra carpeta de trabajo si el volumen inicial no tiene espacio; cancelar no inicia la grabación. Un archivo de destino existente no se sobrescribe. El catálogo ofrece Rescue Disk 0.9.9, con historial y rueda de ratón integrados en las consolas locales.
