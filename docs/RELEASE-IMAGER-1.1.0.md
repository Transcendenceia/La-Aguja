# LA AGUJA Flash Imager 1.1.0 · Windows and Linux

Flash Imager is the preparation application; Rescue Disk remains 1.1.1. This
release publishes the previously local alignment work and the Windows blank-disk
writer fix. New extended fields require Rescue 1.1.1 with imager-profile-v2;
older images are rejected before preparation, without silently dropping settings.

## Changes

- Up to 16 ordered Wi-Fi networks and priority controls.
- Portable NAS/cloud destinations: SMB, SFTP, WebDAV/Nextcloud, S3, Drive,
  OneDrive and Dropbox; manual setup and authorized rclone configuration import.
  Preparation does not connect to or mount a remote account.
- Expanded Tailscale/Headscale options for DNS, routes, tags, exit-node/LAN,
  shields up, forwarding, SNAT and netfilter. Applied in Rescue, not on this PC.
- Shared password by default for SSH/console and profile encryption, with an
  explicit option to separate it. Wi-Fi and remote-account passwords stay separate.
- Literal custom environment variables and .env/JSON import; values do not run
  as shell code or expand host variables. Provider-card API keys take precedence.
- Extended encrypted profiles and USB editing preserve those settings.
- Windows writer handles blank RAW/GPT virtual USB disks without mistaking
  Get-Partition ObjectNotFound for a populated-disk error.
- Spectrum/graphite UI, local Inter font, eight steps and compact-window support;
  reduced progress IPC, transfer speed/ETA and download cancellation.
- Clear Linux feedback when an older Rescue image lacks extended-profile support.

Preparation encryption is the interoperable AES-GCM capsule. LUKS conversion is
an explicit Rescue action; the Imager does not claim to create a LUKS vault.
New UI text is Spanish/English; other supported app languages retain their
translations and use English fallback for the new text where not yet translated.

## Distribution and provenance

EXE, AppImage, DEB and portable Linux TAR are accompanied by SHA-256 inventories,
source and VALIDATION-IMAGER-1.1.0.md. The corresponding Imager source is the
separate immutable flash-imager-v1.1.0 tag. Assets are added to the existing
v1.1.0 release URL namespace because already-published Imager updaters require
/release/download/v<version>/ paths; the older Rescue v1.1.0 source tag and image
files are not replaced. Rescue v1.1.1 remains repository Latest.

## Español

Se publica Flash Imager 1.1.0 para Windows y Linux: varias redes Wi-Fi ordenadas,
NAS/cloud, tailnet ampliada, contraseña común opcional, variables literales,
perfiles ampliados y corrección de grabación Windows sobre discos vacíos.
Los ajustes nuevos funcionan con la imagen pública Rescue 1.1.1. No se
reconstruye Rescue ni se modifica ningún pendrive físico para esta publicación.
No se conectan cuentas ni se importan sesiones del propietario en los paquetes.
Las pruebas finales y las pruebas nativas Windows históricas se distinguen en
VALIDATION; las sumas permiten comprobar cada instalador.
