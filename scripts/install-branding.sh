#!/bin/bash
# Apply only project-owned branding to an existing rootfs; never a host install.
set -euo pipefail
PROJECT=${AGUJA_PROJECT:-$(cd "$(dirname "$0")/.." && pwd)}
ROOT="$PROJECT/build/rootfs"
[[ $EUID == 0 ]] || { echo 'Ejecuta con sudo'; exit 1; }
[[ -f "$ROOT/etc/debian_version" && -x "$ROOT/usr/local/bin/agy" ]] || { echo 'Rootfs de Aguja requerida'; exit 1; }
[[ -f "$PROJECT/branding/plymouth/frame-095.png" ]] || { echo 'Genera branding: npm ci && npm run branding'; exit 1; }
THEME="$ROOT/usr/share/plymouth/themes/aguja"
install -d "$THEME" "$ROOT/usr/share/aguja/branding" "$ROOT/etc/plymouth"
install -m 644 "$PROJECT"/branding/plymouth/*.png "$PROJECT"/branding/plymouth/aguja.{script,plymouth} "$THEME/"
install -m 644 "$PROJECT/branding/mascot/aguja-mascot.png" "$PROJECT/branding/mascot/icon-256.png" "$PROJECT/branding/mascot/aguja-animated.webp" "$ROOT/usr/share/aguja/branding/"
for pose in idle blink wink surprise laugh look-left look-right mischief; do
    install -m 644 "$PROJECT/branding/mascot/$pose.png" "$ROOT/usr/share/aguja/branding/"
done
chroot "$ROOT" plymouth-set-default-theme aguja
printf '%s\n' '[Daemon]' 'Theme=aguja' 'ShowDelay=0' 'DeviceTimeout=8' > "$ROOT/etc/plymouth/plymouthd.conf"
install -m 755 "$PROJECT/runtime/aguja" "$ROOT/usr/local/bin/aguja"
install -m 644 "$PROJECT/VERSION" "$ROOT/usr/share/aguja/VERSION"
echo 'Agujita instalada en rootfs; regenera initramfs antes de empaquetar.'
