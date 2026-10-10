# Troubleshooting · 0.9.9

[Español](TROUBLESHOOTING.es.md) · [Getting started](GETTING-STARTED.md)

Locate the failing layer before changing anything. Record the version, platform, exact action and redacted error. A healthy `aguja doctor` is not proof of disk health, successful recovery or provider authentication.

| Symptom | Check first | Next action |
| --- | --- | --- |
| Catalogue/download fails | Connectivity, clock, signature and exact filename | Retry from the official catalogue; never bypass a signature/hash failure |
| ENOSPC while preparing | Space on the work volume for base + private copy, and full-device backup if enabled | Choose a larger work folder on Windows or another output filesystem; keep the original base |
| Local image is rejected | Is it still `.img.zst`, an ISO or incomplete download? | Verify the published checksum, decompress and select the IMG |
| USB absent or rejected | Model/serial/capacity, connection, device ownership and OS disk role | Stop if identity is uncertain; do not disable internal/system-disk protection |
| UAC/Polkit cancelled | Was local writer elevation approved? | Reattempt only after checking the exact USB; cancelled consent is not a write |
| Interrupted flash | Write and full read-back did not complete | Preserve evidence and prepare again after diagnosis; do not label media ready |
| Firmware will not boot | Architecture, USB boot menu, image identity and read-back | Check vendor guidance; VM BIOS/UEFI tests do not certify Secure Boot or this hardware |
| Unlock phrase rejected | Keyboard layout, Caps Lock and the profile phrase—not SSH password | Enter locally with the correct layout; encrypted secrets cannot be restored without their phrase |
| No network | Link, DHCP, Wi-Fi credentials and NetworkManager | Inspect `ip -br address`; use Ethernet as a simpler first test |
| SSH unavailable | Actual live IP, configured port, unlock, SSH credentials and host fingerprint | Test LAN first; do not expose a public port as a default workaround |
| Tailnet absent after reboot | Unlock/network, key validity/one-use consumption and control-plane ACLs | Use your valid scoped registration key; remove stale nodes under your own administration |
| AI installed but login fails | Provider account, network, quota and supported native auth | Authenticate separately; imported files are not evidence of valid sessions |
| SSH OAuth callback fails | Callback points to the remote machine's localhost | Follow provider-native headless methods; automatic callback forwarding is not provided |
| Files are encrypted/hibernated | Correct owner's recovery key and filesystem state | Do not bypass encryption or force a write mount of hibernated Windows |
| Read errors increase | Physical instability and value of the original | Stop repeated scanning; consider a conservative ddrescue image or a specialist |
| Wheel history seems missing | New local console, RAM history, full-screen application's own navigation | Scroll to prompt or press Esc; SSH uses its client terminal and old lost output is not recovered |
| Tokens survive a reboot | Was unencrypted persistent HOME enabled? | Review persistence deliberately; a capsule does not encrypt all AGUJA_DATA |

For encrypted profiles the boot runtime forces `persistent_home=no`. Older/plaintext configurations can still retain HOME unencrypted. Do not confuse RAM console history with a saved intervention report.

## Report a reproducible problem

Use the [issue tracker](https://github.com/Transcendenceia/La-Aguja/issues) with image/Imager version, OS, expected result, observed result, minimal steps and whether this is a VM or physical hardware. Include only redacted diagnostics. Exclude private images, `.aguja` profiles, tokens, passwords, recovery keys and personal file contents. Preserve the original and backups while investigating.

[USB reference](USB.md) · [Release evidence](RELEASE-0.9.9.md) · [Workflow ideas](SHOWCASE.md)
