# User guide · LA AGUJA

[Website](https://aguja.transcendenceia.net/en/docs) · [English](../en/USER-GUIDE.md) · [Español](../es/USER-GUIDE.md)


## A launchpad, not just a lifeboat.

Give an advanced agent an objective, not just a repair command. It can inspect the available hardware, choose tools, generate and run scripts within your authorised scope, and check the result. The installed OS does not need to start — or even exist.

The live session uses a writable RAM overlay over the read-only USB image. It is Linux, not firmware, and the entire USB is not copied to RAM. Internal disks stay untouched at startup; writes happen when you choose to use them.

Included: root-capable AI clients, SSH, Python, Git, storage tools, debootstrap and arch-install-scripts. Extend the session with compatible packages: QEMU/KVM, container engines or build tools need additional installation, enough RAM/storage and hardware support. Save important outputs deliberately; RAM state is temporary. Cloud AI requires networking and your own account, not an included local model.

[↗](https://aguja.transcendenceia.net/en/docs#que-es)

## Your first USB

Back up a USB whose actual capacity exceeds the image size. Download Flash Imager, select the public Rescue Disk image through the signed catalogue and leave Ethernet on automatic DHCP. Set the rescue hostname, language, keyboard and your own SSH password or public key. For the first test, you can leave AI preparation and tailnet access disabled.

Review the protection mode. If the configuration contains secrets, choose encrypted protection and keep the unlock phrase outside the USB. Find the USB, compare its model, capacity and serial number, then prepare and flash it only after confirming the exact device. Wait for read-back verification. Boot from the USB using the computer’s firmware menu; unlock the profile if necessary. Run the status and disk-inventory commands below. Seeing the panel and identifying the disks completes this first test; you do not need to recover a file or sign in to an AI provider.

```sh
aguja status
aguja doctor
lsblk -o NAME,SIZE,MODEL,FSTYPE,LABEL,MOUNTPOINTS
```

[↗](https://aguja.transcendenceia.net/en/docs#primer-usb)

## Terms you will encounter

Live means an operating system booted without installing it on the internal disk. An image (.img or ISO) represents media, not a photograph: the configurable IMG is used by the Imager, while the ISO is useful for VM boot tests. A disk is the whole device; a partition is a region of it; mounting makes its files accessible. Device names such as /dev/sda can change.

DHCP assigns network addresses automatically. SSH provides an encrypted terminal connection; its host fingerprint identifies the server. Root/sudo means administrator access, not a read-only sandbox. A tailnet is an authorised private device network. A node-registration key, an AI API key, an SSH password and a profile-unlock phrase have different purposes. SHA-256 checks bytes, not universal boot compatibility. BitLocker/LUKS protect disk volumes; the USB profile phrase does not unlock them.

[↗](https://aguja.transcendenceia.net/en/docs#glosario)

## Before starting: hardware, permission and backup

Use x86-64 hardware and verify firmware and USB boot support. BIOS and UEFI paths are tested, but ARM, all Wi-Fi chipsets and a universal signed Secure Boot chain are not promised. Obtain permission to examine the computer and its data. Choose the source disk and a separate recovery destination before beginning. If a failing disk disappears, makes unusual noises or shows read errors, avoid repeated repair attempts on the original; consider imaging it first.

Flashing replaces the selected USB’s contents. Windows has no integrated USB backup yet: make an external backup before flashing. Linux offers an optional verified full-device backup, disabled by default, requiring space and permissions. Neither option backs up the internal disk being rescued. Have the owner’s BitLocker/LUKS keys when needed. LA AGUJA does not bypass disk encryption.

[↗](https://aguja.transcendenceia.net/en/docs#preparacion)

## Download and open Flash Imager

Use the official download page: Windows 10/11 EXE, Linux AppImage, Debian/Ubuntu DEB or portable Linux archive. Keep the original filename and check the published SHA-256. Launch the Imager on the working preparation computer; do not flash its EXE or AppImage to the USB. Downloading the project does not require a LA AGUJA account.

Windows packages do not currently have a recognised Authenticode signature. Linux may need executable permission for the AppImage; the portable archive is an alternative. Local elevated permission is needed for device-writing operations. A successful launch is not proof that a USB has been prepared or can boot.

[↗](https://aguja.transcendenceia.net/en/docs#descargas)

## Step 1 · Choose a compatible image

Use the signed public catalogue or select a local .img. The catalogue verifies its Ed25519 signature and image hashes; split downloads are joined into one verified image. A manually downloaded .img.zst must be decompressed before import. The ISO and IMG are not interchangeable in the preparation flow.

A private preparation creates a new image with your configuration; it does not change the public factory image. The current Imager is 0.9.2 and the rescue image is 0.9.0. Options depend on the image’s supported features: images lacking tailscale-profile-v1 are rejected when preparing tailnet registration. Check actual required capacity rather than a USB’s marketing label.

[↗](https://aguja.transcendenceia.net/en/docs#imagen)

## Step 2 · Network, language and hostname

Select the live system’s language, keyboard layout and variant; the Imager interface language is a separate setting. Give the rescue computer a recognisable hostname. Automatic Ethernet DHCP is the simplest initial route. Saved Wi-Fi can connect at boot; without networking the local panel offers interactive selection. Corporate Wi-Fi and captive portals may require manual NetworkManager configuration.

Wi-Fi credentials imported from the preparation computer may require local permission. They become part of the private profile, not a website account. If online sign-in or tailnet registration fails, check network connectivity, DNS, HTTPS and time independently. Local disk diagnostics can remain available without Internet.

[↗](https://aguja.transcendenceia.net/en/docs#red)

## Step 3 · SSH access

Choose a unique SSH password or paste the public key of the authorised operator. Never paste a private SSH key into the public-key field. The default port is 22; changing a port does not replace authentication or network policy. Connect using the live system’s actual IP and compare the host fingerprint before trusting it.

The factory username is aguja and its public factory password is aguja. A personal password overrides the default. A blank password with a public key enables key-only access; without a key it preserves factory access for compatibility. The account has unrestricted sudo. Use aguja password to persist a new SSH password on the USB; sudo passwd aguja only changes the running session.

```sh
ssh aguja@IP
```

[↗](https://aguja.transcendenceia.net/en/docs#ssh)

## Step 4 · Prepare AI tools

Flash Imager integrates with Codex CLI, OpenCode, Claude Code and Antigravity. Choose a provider and supported authentication method: your API key, a selectively imported portable session, or later sign-in on the live system. A CLI installation check is not a successful login or inference test. Not every credential store can be transferred.

The Imager does not copy your entire keychain, history, hooks or MCP configuration. A portable file may already be expired. Provider costs, quotas and submitted data depend on your own account and terms. You can prepare the USB without AI credentials and authenticate after boot; cloud AI is not promised to work offline.

[↗](https://aguja.transcendenceia.net/en/docs#ia-preparacion)

## Step 5 · Your Tailscale or Headscale

Remote access is optional. Enable private networking, provide an authorised auth/pre-auth key and optionally a node name. An empty Headscale URL selects official Tailscale; otherwise provide your own HTTPS Headscale endpoint. The live system registers at boot after networking and profile unlock. This does not enrol the preparation PC or create a proprietary LA AGUJA tunnel.

Your connecting client must belong to the same authorised tailnet and satisfy its policies. A registration key is not an SSH password or AI API key. Registration alone does not prove that ACLs allow SSH; verify a real connection from the authorised client. The live identity is kept in RAM and must register again after reboot.

[↗](https://aguja.transcendenceia.net/en/docs#tailnet)

## OpenSSH and Tailscale SSH are different

The default route is normal OpenSSH carried over the tailnet. SSH keys/passwords and host fingerprints still apply, while network ACLs must allow the connection. Tailscale SSH is an advanced alternative with compatible server support and explicit SSH policies; merely enabling it does not authorise every client.

When a connection fails, separate registration, node reachability, TCP port access and SSH authentication. Do not open public firewall ports or weaken broad ACLs to hide an authentication problem. Follow the documentation for the versions deployed on your own Tailscale/Headscale infrastructure.

[↗](https://aguja.transcendenceia.net/en/docs#politicas)

## Secrets and the limits of encryption

The private profile may contain Wi-Fi passwords, SSH settings, AI credentials and tailnet registration keys. Encrypt its capsule and store the unlock phrase separately from the USB. At boot, unlock locally before private settings are loaded. A saved .aguja template is another sensitive artefact; protect it and its backups.

Capsule encryption does not encrypt all of AGUJA_DATA and does not protect loaded secrets from root after unlock. With persistent_home=no, HOME and session tokens disappear on reboot; persistent_home=yes stores them unencrypted on the USB. Plain aguja.conf values are readable to anyone with physical access. Do not upload private images, profiles or secrets to public issues or source repositories.

[↗](https://aguja.transcendenceia.net/en/docs#secretos)

## Windows · Understanding BitLocker

BitLocker encrypts Windows volumes. Booting Linux does not remove that protection: obtain the matching recovery key from the owner and identify the correct volume. The USB profile phrase and SSH password are not BitLocker recovery keys. LA AGUJA can use appropriate recovery tools with the supplied key, but does not break encryption.

On Windows, Flash Imager can inspect available recovery keys and optionally include selected keys in a private image. Inclusion must be explicit; protect the profile and keep another recovery copy outside the USB. Viewing a key or preparing a profile does not prove that the target volume has been unlocked. The published Windows screenshot is historical 0.8.1 evidence, not a new 0.9.2 native execution.

[↗](https://aguja.transcendenceia.net/en/docs#bitlocker)

## Step 6 · Prepare, flash and verify

Review the image, protection mode and configuration summary. Creating a private image prepares a file; preparing and flashing a USB additionally writes the selected device. Compare model, serial number and real capacity in the native confirmation. Cancel if the identity is uncertain. Grant local UAC/Polkit permission only for the operation you intend.

Wait for writing and complete read-back verification; do not disconnect the device while it is working. Check the reported result, not just the absence of an error popup. Read-back verifies bytes, not compatibility with all firmware. Test booting on your intended hardware. Windows USB backup must be performed externally; do not assume it is included in the write operation.

[↗](https://aguja.transcendenceia.net/en/docs#grabar)

## Boot, unlock and connect

Select the USB in the manufacturer’s firmware boot menu. The live panel should display current networking and SSH information. If the profile is encrypted, run aguja profile unlock in the local console before using private settings. A graphical cockpit may fall back to an adaptable text console when hardware requires it.

Use the actual IP shown by the live system. The advertised .local hostname depends on working mDNS/multicast and may change after a name collision. SSH can work over LAN without a tailnet. Verify the host fingerprint, authenticate, then check status and disks. No internal disk is mounted or repaired automatically just because the panel appears.

```sh
aguja profile unlock
aguja status
```

[↗](https://aguja.transcendenceia.net/en/docs#arranque)

## Reboots: tailnet identity is temporary

The live tailnet state is stored in RAM. Rebooting loses the enrolled identity and requires a fresh registration after network availability and profile unlock. A one-use key may be consumed by the first boot and cannot guarantee subsequent boots. For repeated boots, use a valid, appropriately scoped reusable key under your own administration.

This temporary tailnet identity is separate from the USB’s SSH host key and from optional HOME persistence. Remove obsolete nodes and revoke registration keys when the rescue job ends. Do not interpret a previous successful connection as proof that today’s node is registered or allowed by the current policy.

[↗](https://aguja.transcendenceia.net/en/docs#reinicios)

## AI sign-in with the local browser

From the local console, aguja login codex, aguja login claude or aguja login antigravity can open a sandboxed Chromium browser on the official sign-in flow with a console attached to the original PTY. Copying a code only focuses the console; paste explicitly using Ctrl+Shift+V. Closing the browser returns to the original terminal. This route does not use QR codes or grant consent automatically.

OpenCode keeps its native opencode auth login flow. SSH, serial and headless sessions retain provider-native URLs/methods; do not assume a remote localhost callback is forwarded. API credentials and portable-session imports are separate authentication paths. Synthetic browser screenshots demonstrate interface behaviour, not actual provider consent or successful AI inference.

```sh
aguja login codex
aguja login claude
aguja login antigravity
opencode auth login
```

[↗](https://aguja.transcendenceia.net/en/docs#ia-login)

## First diagnosis: understand before repairing

Begin with a concrete question and collect status, device identity, filesystem types and mount state. Run aguja doctor and the read-only inventory below before choosing a target. Distinguish the preparation USB, the internal source and the recovery destination by model, size and identifiers, not by an assumed /dev/sdX letter.

When examining files, use an appropriate read-only path and verify the actual mount options. Even a read-only file access workflow can require care with filesystem journal recovery. Save observations before changing anything. Failing hardware may need an image and a ddrescue map rather than repeated attempts at filesystem repair.

```sh
aguja doctor
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS
findmnt
```

[↗](https://aguja.transcendenceia.net/en/docs#primer-diagnostico)

## Working with an agent

Specify the objective, exact computer and disk, authorised actions, backup destination and stopping conditions. Ask the agent to inspect live state, explain its findings and keep evidence before proposing changes. Starting an agent does not itself complete a rescue. Check the resulting files or boot behaviour independently.

Codex Safe in 0.9.10 uses a workspace-write sandbox with networking disabled. Each tool requires fresh human confirmation; leaving the sandbox requires human approval. The OS account retains sudo outside the sandbox. Other clients keep their own confirmation mechanisms; YOLO remains unrestricted. Choose through aguja agent NAME; Escape cancels. No mode authorises actions beyond your request.

[↗](https://aguja.transcendenceia.net/en/docs#trabajo-ia)

## Rescue tools and orientation commands

aguja tools lists installed tools by category. GNU ddrescue supports imaging unstable media with a map; TestDisk/PhotoRec support recovery workflows; rsync copies files. smartctl and nvme-cli help inspect hardware. Filesystem, LUKS, LVM, RAID and BitLocker tooling require the right target and, where applicable, keys.

Use the orientation commands below to collect evidence. Do not run formatting, bootloader installation, partition writes or repair commands against a guessed device. Consult each tool’s manual and work on a copy when appropriate. Traditional diagnostics do not require cloud AI. Tool availability is not a promise of recovering every file or every damaged device.

```sh
aguja tools
aguja status --disks
aguja status --json
aguja context
aguja help
```

[↗](https://aguja.transcendenceia.net/en/docs#herramientas)

## What could you build from boot?

Build on the included Linux tools or add the dependencies your project needs. These are adaptable missions, not one-click features or claims that every scenario has already been tested.

[↗](https://aguja.transcendenceia.net/en/docs#casos)

## Professional workflow: evidence and repeatability

Record permission, hardware identity, image version/hash, initial state, target disks and the recovery plan. Work from a copy when possible, label collected evidence and retain the mapping between the original and its image. For unstable media, capture the imaging map and stop when continued reading is likely to worsen the situation.

Keep changes incremental and document each command’s purpose and observed result. Validate restored data or boot behaviour, not just exit codes. A reusable .aguja profile may reduce preparation work but must be encrypted and reviewed for stale credentials. Do not reuse a customer’s keys or personal data in a public issue or demonstration.

[↗](https://aguja.transcendenceia.net/en/docs#profesional)

## Troubleshooting by layer

No boot: check x86-64 support, media integrity, firmware selection and graphical fallback. No network: separate link/Wi-Fi, DHCP, DNS, HTTPS and time. No SSH: inspect the actual IP/port, listener, policy and authentication. No tailnet: check the registration key, server URL, expiry and whether a one-use key was already consumed.

No AI login: check the provider method, account eligibility, Internet and callback location. Profile not loaded: verify image feature support and unlock state. Disk not visible: inspect the controller and inventory before any writes. A healthy local doctor report is not an end-to-end proof of DNS, ACLs, provider authentication or hardware compatibility.

[↗](https://aguja.transcendenceia.net/en/docs#problemas)

## Finish without leaving forgotten access

Summarise observations, changes and verified results. Close sessions and finish writing to the recovery destination before a clean shutdown. Safely disconnect media and confirm that recovered files remain readable from the destination. Keep the original evidence and backup until the owner accepts the result.

Remove temporary tailnet nodes, revoke no-longer-needed keys and dispose of private profiles/images through an approved recoverable process. Check whether HOME persistence left tokens on the USB. Do not revoke unrelated owner access or erase evidence as part of housekeeping. Report unresolved limitations and the next concrete step.

[↗](https://aguja.transcendenceia.net/en/docs#terminar)

## What is tested, and what cannot be inferred

The public edition removes LA AGUJA accounts and the proprietary relay. Published preparation, package and VM tests support the documented flows; they do not certify every physical computer. Imager 0.9.2 fixes the headline in seven interface languages without changing the rescue image 0.9.0. Previous-version screenshots remain historical evidence and synthetic examples are labelled.

Read-back is not universal boot validation. A panel, CLI version or portable session file does not prove provider login or inference. Local registration status does not prove a remote SSH policy. Windows lacks integrated USB backup and a recognised Authenticode signature. There is no universal signed Secure Boot chain. Treat version-specific results as evidence with limits, not a blanket compatibility claim.

[↗](https://aguja.transcendenceia.net/en/docs#validacion)

## References and next steps

Use the downloads and source links in the header. The extended Spanish reference retains the original 26-chapter manual and detailed examples; this operational guide covers the same workflow stages in your chosen language. Screenshots retain their real historical version and synthetic-test provenance. Print this page to save a PDF in the current language; the separately published historical PDF is Spanish.

Consult the official documentation for OpenSSH, Tailscale/Headscale, GNU ddrescue, TestDisk and Microsoft BitLocker for the version you actually use. Project code is GPL-3.0-or-later; third-party components retain their own licences and terms. Bug reports should include version, redacted symptoms and reproducible steps, never passwords, tokens, private keys or private disk images.

[↗](https://aguja.transcendenceia.net/en/docs#referencias)
