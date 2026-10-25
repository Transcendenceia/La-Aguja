# File-image interface · 1.2.0

Use Node.js >=22. The downloadable ZIP is self-contained; no npm install, Electron, root, mtools or mounts are required. From the source checkout install the existing Imager dependency with `npm ci --prefix desktop`. Preparation uses its pure-JavaScript GPT/FAT32 engine on regular `.img` files. The output parent must already exist and be private. Existing files, symlinks and device sources are refused; the factory image is preserved. Keep enough space for a full copy.

## Commands

`node <skill-dir>/scripts/imager.cjs --help`, `doctor`, `locales`, `catalog` take no JSON. `download`, `inspect`, `prepare`, `save-profile`, `profile-info` read one JSON object from stdin (8 MiB maximum). Output is JSON lines; progress records have `type:progress`, the final record has `ok`. Any failure exits nonzero and uses a credential-free generic message. Do not log stdin. `inspect` never reads profile contents into output.

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

Download: `{"version":"<version returned by catalog>","output_path":"/absolute/private/base.img"}`. Select a version actually returned by `catalog`. The official publication pin is bundled; expiry/signature failures stop downloading. This handles raw images or signed multipart raw images exactly like the desktop Imager. Manually imported `.img.zst` must first be decompressed; compressed files and ISO are not accepted by preparation.

Inspect: `{"image_path":"/absolute/base.img","image_sha256":"<trusted 64 lowercase hex>"}`. Omitting the expected hash calculates it but does not authenticate origin. Inspect reports GPT release marker capabilities and explicitly returns `signature_verified:false`.

## Prepare

See `../assets/request.example.json`. Absolute Windows paths work too; escape backslashes in JSON. Input keys:

- `image_path`, `output_path`: absolute `.img` paths, distinct; output must not exist.
- `image_sha256`: trusted expected factory SHA-256 (64 lowercase hex).
- `capsule`: schema 1; hostname, network, SSH, providers; optional locale, tailscale and extensions.
- `protection`: `{mode:"plain"}` or `{mode:"encrypted",passphrase:"..."}`. Encryption is the existing runtime-compatible scrypt + AES-256-GCM envelope. Passphrase: 12–1024 characters; enter privately, never in a public example. Protected profiles unlock at the early boot gate before SSH/agents; `aguja profile unlock` is the interactive in-session fallback. This creates an AES-GCM capsule, not a LUKS vault or encrypted DATA.
- `disk_recovery`: optional array of up to 16 entries `{type:"bitlocker"|"luks",label:"equipment/disk",identifier:"optional ID/UUID",key:"private existing key"}`. Read [recovery.md](recovery.md). Secret values enter only through private stdin; use encrypted protection. An empty list clears prior supplemental recovery content in the output copy.
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

### Extended settings · engine 1.1.0 / Rescue 1.1.1

Put these inside `capsule.extensions`, not at the request root. Check `inspect`
for `imager-profile-v2` on the exact image first. Public Rescue 1.1.1 includes it;
older images lacking it reject nonempty extensions without discarding settings.
The skill version is 1.2.0, not the selected image or engine version.

- `wifi_profiles`: ordered array, at most 16 unique SSIDs. Each item uses the same
  `ssid/password/security/country/hidden` fields as `network.wifi`. The first item
  becomes the legacy primary Wi-Fi; do not configure contradictory primary values.
  Every password-bearing entry counts as private, including secondary networks.
- `environment`: object of up to 128 variable names to literal single-line strings,
  at most 32768 UTF-8 bytes each. Names match `[A-Za-z_][A-Za-z0-9_]{0,127}`.
  Shell substitutions such as `$()` and `${HOME}` are data, not expanded/executed.
  Provider-card keys take precedence for their corresponding native agent.
  These values may contain credentials, so any nonempty environment requires
  encrypted protection unless `allow_plain_secrets:true` is explicitly authorized.
  The CLI accepts structured JSON values, not an `.env` filename or import command.
- `storage`: at most 32 unique named destinations, each `{name,type,fields}`;
  optional `files` and `obscured`. Supported types and allowed fields:

  | Type | `fields` keys |
  | --- | --- |
  | `smb` | `host,user,pass,domain,port` |
  | `sftp` | `host,user,port,pass,key_file,key_file_pass,known_hosts_file` |
  | `webdav` | `url,vendor,user,pass,bearer_token` |
  | `s3` | `provider,access_key_id,secret_access_key,region,endpoint` |
  | `drive` | `client_id,client_secret,token,scope,root_folder_id,service_account_file` |
  | `onedrive` | `client_id,client_secret,token,drive_id,drive_type` |
  | `dropbox` | `client_id,client_secret,token` |

  Field values are literal single-line strings. OAuth `token`, when nonempty,
  is a string containing a JSON object, never a request to log in. File fields
  (`key_file`, `known_hosts_file`, `service_account_file`) require their bytes as
  base64 in `files` under the same field key (nonempty, at most 256 KiB decoded per file); no host-file paths are auto-read.
  Keep `obscured:false` for manually supplied passwords; `true` denotes existing
  rclone-obscured values, which are not secure encryption. Unknown types/fields,
  duplicate names and arbitrary rclone hooks are rejected. All nonempty storage
  settings require encrypted protection unless plain storage is explicitly chosen.
  Preparation does not connect, mount, enroll, upload or test these accounts.
- `tailscale`: advanced options supplement the separate `capsule.tailscale`
  enrollment block. Boolean flags: `accept_dns`, `exit_node_allow_lan_access`,
  `advertise_exit_node`, `shields_up`, `snat_subnet_routes`, `forwarding`.
  Defaults are false except `snat_subnet_routes:true`. Text fields: `exit_node`,
  comma-separated `advertise_routes` (CIDRs), `advertise_tags` (`tag:name`),
  `netfilter_mode` (`""`, `on`, `off`, `nodivert`). Omitting the entire extensions
  block preserves legacy behavior; explicit advanced flags take effect in the
  live only. Do not enable routing/forwarding or advertise an exit node by default.

See `../assets/request.extended.example.json` for placeholders, not a ready-to-run
credential request. The complete normalized extensions payload is limited to
768 KiB. Image/profile passwords, SSH password, Wi-Fi passwords and cloud keys
are separate inputs. If the owner requests a shared phrase, set the requested
SSH/profile/output fields privately; no `shared_password` schema field exists.
Saved profiles preserve extensions but do not copy native OAuth account sessions.

Legacy project relay/account fields are not supported. No BitLocker harvesting, USB backup/writing, provider installation or full distro rebuild is performed by this interface. Use the existing desktop for its platform-specific flows.

## Result and verification

Preparation returns `output_path`, `sha256`, `bytes`, `profile_verified:true`, `recovery_verified:true`, `recovery_count`, `source_unchanged:true`, `device_written:false`, and `protection`. It uses the existing engine's FAT32 readback, additionally opens the encrypted profile in memory, hashes the output, checks the original hash again and atomically creates the final file without replacement. This verifies file preparation, not physical boot or service health.

POSIX staging/output are 0700/0600. Node mode bits do **not** enforce Windows ACLs: use a private user directory, and encryption for credentials. macOS/Windows execution support follows the Node engine but must be tested in your own environment; Linux functional QA alone is not a cross-OS certificate.

## Reusable encrypted profiles

`save-profile`: private stdin `{capsule,disk_recovery,passphrase,output_path}`; creates a new `.aguja` file, never overwrites or emits its contents. `profile-info`: `{profile_path}`; metadata only, no password required. For `prepare`, use `profile_path` and `profile_passphrase` instead of `capsule`/`disk_recovery`; preserve the existing image/output/hash/protection fields. The saved profile's password opens the file; the output image protection is a separate explicit choice. Existing import-mode settings still require explicitly approved `import_providers`. Never put either password in argv or chat.
