# File-image interface · 1.0.0

Use Node.js >=22. The downloadable ZIP is self-contained; no npm install, Electron, root, mtools or mounts are required. From the source checkout install the existing Imager dependency with `npm ci --prefix desktop`. Preparation uses its pure-JavaScript GPT/FAT32 engine on regular `.img` files. The output parent must already exist and be private. Existing files, symlinks and device sources are refused; the factory image is preserved. Keep enough space for a full copy.

## Commands

`node <skill-dir>/scripts/imager.cjs --help`, `doctor`, `locales`, `catalog` take no JSON. `download`, `inspect`, `prepare` read one JSON object from stdin (8 MiB maximum). Output is JSON lines; progress records have `type:progress`, the final record has `ok`. Any failure exits nonzero and uses a credential-free generic message. Do not log stdin. `inspect` never reads profile contents into output.

Pass a JSON file on POSIX/cmd with stdin redirection:

```sh
node "/path/flash-imager/scripts/imager.cjs" prepare < "/private/request.json"
```

PowerShell uses a UTF-8 pipe, not POSIX `<`:

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Get-Content -Raw -Encoding UTF8 'C:\private\request.json' | node 'C:\skills\flash-imager\scripts\imager.cjs' prepare
```

A harness process API can send the JSON bytes directly to stdin. Avoid command strings containing secret values.

## Download / inspect

Download: `{"version":"0.9.0","output_path":"/absolute/private/base.img"}`. Select a version actually returned by `catalog`. The official publication pin is bundled; expiry/signature failures stop downloading. This handles raw images or signed multipart raw images exactly like the desktop Imager. Manually imported `.img.zst` must first be decompressed; compressed files and ISO are not accepted by preparation.

Inspect: `{"image_path":"/absolute/base.img","image_sha256":"<trusted 64 lowercase hex>"}`. Omitting the expected hash calculates it but does not authenticate origin. Inspect reports GPT release marker capabilities and explicitly returns `signature_verified:false`.

## Prepare

See `../assets/request.example.json`. Absolute Windows paths work too; escape backslashes in JSON. Input keys:

- `image_path`, `output_path`: absolute `.img` paths, distinct; output must not exist.
- `image_sha256`: trusted expected factory SHA-256 (64 lowercase hex).
- `capsule`: schema 1; hostname, network, SSH, providers; optional locale and tailscale.
- `protection`: `{mode:"plain"}` or `{mode:"encrypted",passphrase:"..."}`. Encryption is the existing runtime-compatible scrypt + AES-256-GCM envelope. Passphrase: 12–1024 characters; enter privately, never in a public example. Encrypted profiles require `aguja profile unlock` after boot.
- `import_providers`: names explicitly authorised for selective local portable-session import. Each listed provider must have `mode:"import"`, and every import-mode provider must be listed. No arbitrary import paths are accepted. File portability does not prove authentication validity.
- `allow_plain_secrets:true`: optional explicit override for a caller who deliberately accepts unencrypted credentials; otherwise such a request is rejected. Do not infer this consent.

### Capsule settings

- `hostname`: lowercase letters, digits, hyphens; 1–63 chars, start/end alphanumeric.
- `locale`: `language`, `keyboard`, `variant`, exactly as returned by `locales`. The base image must advertise the relevant locale features.
- `network.ethernet`: `{method:"auto"}` or `{method:"manual",address:"192.0.2.10",prefix:24,gateway:"192.0.2.1",dns:["192.0.2.1"]}`. Use actual authorised values, not example IPs.
- Optional `network.wifi`: `ssid`, `password`, `security` (`wpa-psk`, `sae`, `open`), two-letter uppercase `country`, boolean `hidden`.
- `ssh`: integer `port` 1–65535, `password` string, `public_key` string. At least one authentication field must be nonempty. Use the user's public key, never a newly invented key that locks them out.
- `providers`: any subset of `codex`, `claude`, `antigravity`, `opencode`. Each has `mode` (`none`, `api`, `import`), optional `api_key`, `base_url` (HTTPS without embedded credentials/query), `model`. Custom OpenCode API endpoints need a model. Auth imports are read only after explicit selection; prefer native login after boot when portability is unavailable.
- `tailscale`: `{enabled:false}` or `{enabled:true,auth_key:"...",login_server:"https://headscale.example",hostname:"my-aguja",ssh:false,accept_routes:false}`. Key required when enabled; omit `login_server` for Tailscale. Do not enrol the preparation host, change ACLs or enable Tailscale SSH/routes by default. Registration occurs on live boot after network/profile unlock, not during file creation. Base needs `tailscale-profile-v1`.

Legacy project relay/account fields are not supported. No BitLocker harvesting, USB backup/writing, provider installation or full distro rebuild is performed by this interface. Use the existing desktop for its platform-specific flows.

## Result and verification

Preparation returns `output_path`, `sha256`, `bytes`, `profile_verified:true`, `source_unchanged:true`, `device_written:false`, and `protection`. It uses the existing engine's FAT32 readback, additionally opens the encrypted profile in memory, hashes the output, checks the original hash again and atomically creates the final file without replacement. This verifies file preparation, not physical boot or service health.

POSIX staging/output are 0700/0600. Node mode bits do **not** enforce Windows ACLs: use a private user directory, and encryption for credentials. macOS/Windows execution support follows the Node engine but must be tested in your own environment; Linux functional QA alone is not a cross-OS certificate.
