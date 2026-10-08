# LA AGUJA Flash Imager · Windows and Linux 0.9.2

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

Open `aguja-flash-imager-0.9.2-win-x64.exe` as your normal user. It is portable and does not require Node.js. No recognised Authenticode signature or absence of SmartScreen prompts is promised. **UAC elevates only the USB writer**, not the Electron interface.

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

CLI login opens the official local terminal flow and you authorise it. Imports accept only supported native portable session files, not complete keychains/history/hooks/MCP. Format validity does not prove a current session.

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
