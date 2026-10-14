# LA AGUJA Flash Imager · Windows and Linux 1.0.0

[Español](README.es.md) · [User guide](https://aguja.transcendenceia.net/en/docs) · [Downloads](https://aguja.transcendenceia.net/en#application)

Prepare a Rescue Disk from a working computer: network, language/keyboard, SSH, AI tools and optional Windows BitLocker recovery keys. Optional remote access uses your own Tailscale/Headscale, not a project tunnel. No LA AGUJA account is required.

## 1.0 profiles, existing USBs and updates

The numbered preparation flow has seven steps and ends at **Create disk**. **Profiles and USB** and **Updates** are separate, unnumbered tools below the preparation steps; they have no wizard Back/Continue controls. Returning restores the previous preparation step and settings. On Windows, **BitLocker on this PC** appears above manually supplied disk recovery keys.

- **Encrypted disks** is a separate step before Create disk; manual BitLocker/LUKS keys and detected BitLocker use the same protected recovery capsule.
- **Profiles and USB** saves/loads encrypted `.aguja` templates. Templates are portable configuration, not a copy of every local login: imported provider sessions are checked and explicitly selected again during preparation.
- Select an exact LA AGUJA USB, read/decrypt its CFG, change settings in the normal sections, then return and save. Reading never writes edits. Saving confirms identity, rejects stale snapshots, preserves original stored bytes in a backup, verifies all replacements and leaves workspace/boot generations/unrelated files alone. An interrupted edit is recovered before boot consumes the capsule.
- **Imager updates** checks a signed catalog and downloads the platform-specific SHA-256-verified app only when requested. Cancel leaves no success message; nothing runs or replaces the current application automatically.
- In the live, `aguja update menu` offers OS packages, native harnesses and signed Rescue releases. Updates are stored as verified generations on DATA and become active on the next boot; factory and previous are retained. [Offline procedure](../runtime/UPDATES.md).

## Imager 1.0.0 · languages, exclusive USB access and recovery keys

All sections, live status messages and native confirmations follow the selected application language. Language/keyboard option labels also refresh; user-entered values, keys, disk identities and selected layouts stay unchanged.

Windows closes only Explorer windows on the confirmed USB and uses Restart Manager to request an orderly close from eligible applications holding its files. Services, critical processes, the writer and unrelated applications are not force-killed. Every target volume must be locked/dismounted and an exclusive raw handle acquired before partition erasure. If a remaining lock cannot be released, flashing stops with an error. PowerShell workers are hidden; the normal Windows UAC consent remains visible.

**Disk recovery keys** accepts BitLocker recovery passwords and LUKS1/LUKS2 passphrases/recovery keys from another computer on either Windows or Linux. A label identifies each computer/disk; UUID/recovery ID is optional. BitLocker groups are validated; LUKS whitespace is preserved. The selected image-protection mode also protects these keys. Plain mode intentionally stores plaintext credentials.

A supplemental recovery capsule and tool are added to the private image’s AGUJA_CFG partition, leaving the Rescue 0.9.11 boot/profile schema intact. On the target computer:

```sh
sudo python3 /config/aguja-recovery.py list
sudo python3 /config/aguja-recovery.py export
sudo python3 /config/aguja-recovery.py open 1 /dev/DEVICE
```

Encrypted keys prompt for the image unlock password. `list` hides key values. `export` creates `/run/aguja-recovery/keys.json` in private RAM (0600); reboot removes it. `open` requires an explicit key number and block device, defaults to read-only and checks a supplied LUKS UUID. `--writable` is explicit. There is no automatic target selection, decryption, mounting, rekeying or local BitLocker suspension. BitLocker operations for the preparation PC remain separate.

Exported encrypted reusable profiles retain manual recovery keys; importing restores them without exposing them in status text.

## Imager 0.9.12 · completion dialogs

Rescue Disk 1.0 adds persistent updates. Existing older USB configurations can be edited, but configuration editing does not upgrade their boot infrastructure. Use a newly prepared 1.0 image for generation updates.

After flashing, a native window confirms that the USB is ready **only after successful read-back verification**. Eject it in your operating system before unplugging it. Failed preparation, denied permissions, writing or verification show a native error window with the public failure reason; the USB is not marked ready. Canceling the confirmation shows neither success nor error. The existing inline status remains available after closing the dialog. All supported application languages are included.

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

Open `aguja-flash-imager-1.0.0-win-x64.exe` as your normal user. It is portable and does not require Node.js. No recognised Authenticode signature or absence of SmartScreen prompts is promised. **UAC elevates only the USB writer**, not the Electron interface.

After consent the writer rechecks exact model, serial and capacity, rejects internal/system/boot disks and holds the verified image open. Success requires full writing, synchronisation and SHA-256 read-back of all image bytes. Cancelling UAC does not write; closing during writing can leave incomplete media.

Windows writes the original DATA geometry. Fresh 1.0 media initializes and expands DATA once on its own removable boot USB at first boot, preserving the partition GUID. The CFG editor never creates that initialization marker on existing USBs. Linux has its own verified expansion phase.

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

Historical 0.9.3 import changes concerned the desktop preparer, not the then-current Rescue 0.9.0. The current catalogue provides Rescue Disk 0.9.9.

## Imager 0.9.4 · native Windows sessions

- Antigravity: reads its exact native `gemini` Credential Manager entry (derived from the current user profile), then exports only OAuth fields to the Linux-compatible profile. A selected folder explicitly imports its portable file instead.
- Codex: honours `cli_auth_credentials_store` (`file`, `keyring`, `auto`), custom `CODEX_HOME`, UTF-16 native keyring entries and the encrypted `secrets/codex_auth.age` backend. Only `global/CODEX_AUTH` is decrypted; MCP/general secrets are not imported. The exported config uses file storage on the rescue system.
- Claude Code: native `.claude/.credentials.json`, including `CLAUDE_CONFIG_DIR`. OpenCode: native XDG `opencode/auth.json` and JSON/JSONC settings with configured locations.
- Run the Imager as the same Windows user as the authenticated CLI. No elevation is needed to import your own session. The reader is read-only; tokens travel through a private process pipe and stay in main-process memory until image preparation or revocation. No temporary plaintext credential file is created.
- A valid imported format is not a live provider authentication check. Synthetic Windows vault and GUI regression tests do not claim real-account inference. Linux imports are unchanged.

Native backend references: [Codex storage](https://github.com/openai/codex/blob/main/codex-rs/login/src/auth/storage.rs), [Codex encrypted store](https://github.com/openai/codex/blob/main/codex-rs/secrets/src/local.rs), [Claude storage](https://code.claude.com/docs/en/authentication), [OpenCode auth](https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/auth/index.ts), [Antigravity auth](https://antigravity.google/docs/cli/install/).

## 0.9.7 changes retained

Unlock-at-boot encryption is initially selected, with the public editable phrase `aguja`. Direct boot requires an explicit choice. Imported language/keyboard can be corrected; encrypted language profiles require Rescue 0.9.7+ to apply them before unlock. Support uses a local QR and opens Ko-fi only on a click; no Ko-fi secrets are bundled.

## 0.9.9 changes

Checks available space before copying the private image and reports the shortfall. Windows preparation/flashing can choose another working folder if the initial volume is full; cancelling does not start writing. Existing output files are not overwritten. The catalogue provides Rescue Disk 0.9.9 with mouse-wheel history in local consoles. Encrypted profiles force `persistent_home=no` at boot; capsule protection does not encrypt all AGUJA_DATA.
