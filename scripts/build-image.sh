#!/bin/bash
set -euo pipefail
PROJECT=$(cd "$(dirname "$0")/.." && pwd)
ROOT=$(realpath "$PROJECT/build/rootfs")
ISO_TREE="$PROJECT/build/iso"
DIST="$PROJECT/dist"
VERSION=$(cat "$PROJECT/VERSION")
# This complete image contains provider-owned clients, not GPL project assets.
# Keep personal media out of public release pipelines until distribution is cleared.
[[ ${1:-} == --personal && $# == 1 ]] || { echo "Usa --personal para la imagen completa de uso propio; no es una entrega pública."; exit 1; }
[[ $EUID == 0 ]] || { echo 'Ejecuta con sudo'; exit 1; }
AGUJA_ROOT="$ROOT" bash "$PROJECT/scripts/verify-required-clis.sh"
cmp -s "$PROJECT/VERSION" "$ROOT/usr/share/aguja/VERSION" || { echo 'Instala la versión actual en rootfs antes de empaquetar'; exit 1; }
cmp -s "$PROJECT/runtime/aguja" "$ROOT/usr/local/bin/aguja" || { echo 'Instala el diagnóstico actual antes de empaquetar'; exit 1; }
# Reject unprivileged copies that strip ownership/setuid from the factory.
[[ $(stat -c '%u:%g:%a' "$ROOT/usr/bin/sudo") == 0:0:4755 ]] || { echo 'Restaura propietarios y permisos de la rootfs (sudo)'; exit 1; }
[[ $(stat -c '%u:%a' "$ROOT/usr/lib/dbus-1.0/dbus-daemon-launch-helper") == 0:4754 ]] || { echo 'Restaura propietarios y permisos de la rootfs (D-Bus)'; exit 1; }
# Public images must never ship a live node identity or enrollment key.
[[ ! -e "$ROOT/run/aguja-platform/tailscale.key" ]] || { echo 'Rootfs contiene una clave tailnet privada; usa una raíz limpia'; exit 1; }
for private_tree in run/aguja-tailnet-private run/aguja-tailscale var/lib/tailscale; do
    if [[ -d "$ROOT/$private_tree" && -n $(find "$ROOT/$private_tree" -type f -print -quit) ]]; then
        echo 'Rootfs contiene estado tailnet privado; usa una raíz limpia'
        exit 1
    fi
done
# Refuse a capability marker if bundled daemon/browser support is absent.
TAILSCALE_VERSION=$(jq -r .version "$PROJECT/config/tailscale.json")
[[ -x "$ROOT/usr/bin/tailscale" && -x "$ROOT/usr/sbin/tailscaled" ]] || { echo 'Incluye Tailscale verificado antes de empaquetar'; exit 1; }
[[ $("$ROOT/usr/bin/tailscale" version | head -1) == "$TAILSCALE_VERSION" ]] || { echo 'Tailscale no coincide con el lock'; exit 1; }
for tailnet_binary in tailscale tailscaled; do
    tailnet_path="usr/bin/$tailnet_binary"
    [[ $tailnet_binary != tailscaled ]] || tailnet_path="usr/sbin/$tailnet_binary"
    tailnet_hash=$(jq -r --arg name "$tailnet_binary" '.binaries[$name]' "$PROJECT/config/tailscale.json")
    printf '%s  %s\n' "$tailnet_hash" "$ROOT/$tailnet_path" | sha256sum -c -
done
for unit in aguja-tailscale.service aguja-tailscaled.service aguja-network-check.service aguja-network-check.timer; do
    cmp -s "$PROJECT/runtime/$unit" "$ROOT/etc/systemd/system/$unit" || { echo 'Instala las unidades tailnet actuales'; exit 1; }
done
for helper in browser-session; do
    cmp -s "$PROJECT/runtime/$helper" "$ROOT/usr/lib/aguja/$helper" || { echo 'Instala el navegador OAuth actual'; exit 1; }
done
cmp -s "$PROJECT/runtime/browser-launch" "$ROOT/usr/local/bin/aguja-browser-launch" || { echo 'Instala el launcher del navegador'; exit 1; }
for browser_binary in chromium Xorg openbox xclip xterm xdotool; do
    chroot "$ROOT" /bin/sh -c 'command -v "$1" >/dev/null' sh "$browser_binary" || { echo 'Falta un componente del navegador OAuth'; exit 1; }
done
[[ $(stat -c '%u:%g:%a' "$ROOT/usr/lib/chromium/chrome-sandbox") == 0:0:4755 ]] || { echo 'Incluye chromium-sandbox con sus permisos oficiales'; exit 1; }
# A release capability must describe the packed runtime, never only this script.
for runtime in "$PROJECT/runtime/"*.py "$PROJECT/runtime/locale-catalog.json" "$PROJECT/runtime/console-history.conf"; do
    cmp -s "$runtime" "$ROOT/usr/lib/aguja/$(basename "$runtime")" || { echo 'Instala el runtime actual antes de empaquetar'; exit 1; }
done
cmp -s "$PROJECT/runtime/locale.sh" "$ROOT/etc/profile.d/aguja-locale.sh" || { echo 'Instala el soporte de idioma antes de empaquetar'; exit 1; }
AVAILABLE_LOCALES=$(chroot "$ROOT" locale -a)
while IFS= read -r language; do
    [[ $'\n'"$AVAILABLE_LOCALES"$'\n' == *$'\n'"${language/.UTF-8/.utf8}"$'\n'* ]] || { echo 'Genera todos los idiomas compatibles en rootfs con locale-gen'; exit 1; }
done < <(python3 -c 'import json,sys; c=json.load(open(sys.argv[1])); print("\n".join(x["value"] for x in c["languages"]))' "$PROJECT/runtime/locale-catalog.json")
# Refuse retired project relay; required provider clients are installed independently of auth.
for retired in usr/lib/aguja/remote.py usr/lib/aguja/tunnel.py usr/lib/aguja/access.py etc/systemd/system/aguja-tunnel.service; do
    [[ ! -e "$ROOT/$retired" && ! -L "$ROOT/$retired" ]] || { echo 'Rootfs contiene componentes retirados'; exit 1; }
done
mkdir -p "$ISO_TREE/live" "$ISO_TREE/boot/grub" "$DIST"
mkdir -p "$ISO_TREE/boot/grub/themes/aguja"
cp "$PROJECT/branding/grub/"* "$ISO_TREE/boot/grub/themes/aguja/"
grub-mkfont -s 18 -o "$ISO_TREE/boot/grub/themes/aguja/menu.pf2" /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
cp "$(find "$ROOT/boot" -maxdepth 1 -name 'vmlinuz-*' | sort -V | tail -1)" "$ISO_TREE/live/vmlinuz"
cp "$(find "$ROOT/boot" -maxdepth 1 -name 'initrd.img-*' | sort -V | tail -1)" "$ISO_TREE/live/initrd.img"
# These directories must exist in the live root for initramfs mount handover.
# build-rootfs unmounts all bind mounts before this stage.
for p in dev proc sys; do
    if mountpoint -q "$ROOT/$p"; then echo "Desmonta rootfs/$p antes de empaquetar"; exit 1; fi
done
mksquashfs "$ROOT" "$ISO_TREE/live/filesystem.squashfs" -noappend -comp zstd -Xcompression-level 10 -processors 2 -mem 256M -root-uid 0 -root-gid 0 -no-progress -wildcards -e 'tmp/*' 'var/tmp/*' var/cache/apt var/lib/apt/lists root/.npm root/.cache root/.local
# Compare the actual required executable bytes, not only their presence in rootfs.
for binary in codex agy claude opencode; do
    executable=$(realpath "$ROOT/usr/local/bin/$binary" 2>/dev/null || true)
    # Absolute links are rooted in the guest, not in the build host.
    if [[ -L "$ROOT/usr/local/bin/$binary" ]]; then executable="$ROOT$(readlink "$ROOT/usr/local/bin/$binary")"; fi
    [[ -x "$executable" ]] || { echo "Falta CLI empaquetable: $binary"; exit 1; }
    relative=${executable#"$ROOT/"}
    [[ $(unsquashfs -cat "$ISO_TREE/live/filesystem.squashfs" "$relative" | sha256sum | cut -d ' ' -f 1) == $(sha256sum "$executable" | cut -d ' ' -f 1) ]] || { echo "CLI empaquetado no coincide: $binary"; exit 1; }
done
# Verify the packed filesystem too: mksquashfs must not silently pack a
# symlink to a factory root instead of its contents.
unsquashfs -cat "$ISO_TREE/live/filesystem.squashfs" usr/share/aguja/VERSION | cmp -s "$PROJECT/VERSION" - || { echo 'Versión empaquetada no coincide'; exit 1; }
unsquashfs -cat "$ISO_TREE/live/filesystem.squashfs" usr/local/bin/aguja | cmp -s "$PROJECT/runtime/aguja" - || { echo 'Diagnóstico empaquetado no coincide'; exit 1; }
for runtime in "$PROJECT/runtime/"*.py "$PROJECT/runtime/locale-catalog.json"; do
    unsquashfs -cat "$ISO_TREE/live/filesystem.squashfs" "usr/lib/aguja/$(basename "$runtime")" | cmp -s "$runtime" - || { echo 'Runtime empaquetado no coincide'; exit 1; }
done
# Non-Python helpers, service units and pinned network binaries must survive
# the squashfs stage too; a matching marker alone does not prove support.
for unit in aguja-tailscale.service aguja-tailscaled.service aguja-network-check.service aguja-network-check.timer; do
    unsquashfs -cat "$ISO_TREE/live/filesystem.squashfs" "etc/systemd/system/$unit" | cmp -s "$PROJECT/runtime/$unit" - || { echo 'Unidad tailnet empaquetada no coincide'; exit 1; }
done
for tailnet_binary in tailscale tailscaled; do
    tailnet_path="usr/bin/$tailnet_binary"
    [[ $tailnet_binary != tailscaled ]] || tailnet_path="usr/sbin/$tailnet_binary"
    tailnet_hash=$(jq -r --arg name "$tailnet_binary" '.binaries[$name]' "$PROJECT/config/tailscale.json")
    [[ $(unsquashfs -cat "$ISO_TREE/live/filesystem.squashfs" "$tailnet_path" | sha256sum | cut -d ' ' -f 1) == "$tailnet_hash" ]] || { echo 'Binario tailnet empaquetado no coincide'; exit 1; }
done
unsquashfs -cat "$ISO_TREE/live/filesystem.squashfs" usr/lib/aguja/browser-session | cmp -s "$PROJECT/runtime/browser-session" - || { echo 'Sesión navegador empaquetada no coincide'; exit 1; }
unsquashfs -cat "$ISO_TREE/live/filesystem.squashfs" usr/local/bin/aguja-browser-launch | cmp -s "$PROJECT/runtime/browser-launch" - || { echo 'Launcher navegador empaquetado no coincide'; exit 1; }
cp "$PROJECT/config/aguja.conf" "$ISO_TREE/aguja.conf"
cat > "$ISO_TREE/boot/grub/grub.cfg" <<'EOF'
set timeout=5
set default=0
set color_normal=light-gray/black
set color_highlight=black/light-cyan
if loadfont /boot/grub/themes/aguja/menu.pf2; then
    insmod all_video
    insmod gfxterm
    insmod gfxmenu
    insmod png
    set gfxmode=1024x768,auto
    set gfxpayload=keep
    terminal_output gfxterm
    set theme=/boot/grub/themes/aguja/theme.txt
    export theme
fi
menuentry 'LA AGUJA Rescue Disk' {
    linux /live/vmlinuz boot=live components quiet splash plymouth.ignore-serial-consoles console=tty0 console=ttyS0,115200n8
    initrd /live/initrd.img
}
menuentry 'Rescue Disk · Diagnostico (mensajes de arranque)' {
    linux /live/vmlinuz boot=live components console=tty0 console=ttyS0,115200n8
    initrd /live/initrd.img
}
menuentry 'Rescue Disk · Compatibilidad grafica (nomodeset)' {
    linux /live/vmlinuz boot=live components nomodeset console=tty0 console=ttyS0,115200n8
    initrd /live/initrd.img
}
menuentry 'Apagar' { halt; }
menuentry 'Reiniciar' { reboot; }
EOF
ISO="$DIST/aguja-personal-$VERSION-amd64.iso"
grub-mkrescue -o "$ISO" "$ISO_TREE" -- -volid AGUJA_LIVE -hfsplus off
# Build hybrid image entirely with files: no loop devices or host-disk mutations.
IMG="$DIST/aguja-personal-$VERSION-amd64.img"
cp --reflink=auto "$ISO" "$IMG"
ISO_SECTORS=$(( ($(stat -c %s "$ISO") + 511) / 512 ))
CFG_START=$(( (ISO_SECTORS / 2048 + 1) * 2048 ))
CFG_SECTORS=$((256 * 1024 * 1024 / 512))
DATA_START=$((CFG_START + CFG_SECTORS))
DATA_SECTORS=$((2 * 1024 * 1024 * 1024 / 512))
TOTAL_SECTORS=$((DATA_START + DATA_SECTORS + 2048))
truncate -s "$((TOTAL_SECTORS * 512))" "$IMG"
sgdisk -e "$IMG"
sgdisk -n "4:$CFG_START:+${CFG_SECTORS}S" -t 4:0700 -c 4:AGUJA_CFG \
       -n "5:$DATA_START:+${DATA_SECTORS}S" -t 5:8300 -c 5:AGUJA_DATA "$IMG"
sgdisk -t 1:8300 -t 3:8300 -c 3:AGUJA_LIVE "$IMG"
CFG="$PROJECT/build/config.fat"
truncate -s "$((CFG_SECTORS * 512))" "$CFG"
mkfs.vfat -F 32 -n AGUJA_CFG "$CFG"
mcopy -i "$CFG" "$PROJECT/config/aguja.conf" ::aguja.conf
python3 - "$VERSION" "$PROJECT/build/release.json" <<'PYPROFILE'
import json,sys
from pathlib import Path
Path(sys.argv[2]).write_text(json.dumps({'version':sys.argv[1],'distribution':'personal','required_clis':['codex','agy','claude','opencode'],'features':['platform-profile-v1','antigravity-oauth-file-v1','locale-profile-v1','i18n-catalog-v1','tailscale-profile-v1','browser-oauth-v1','locale-preunlock-v1']}))
PYPROFILE
mcopy -i "$CFG" "$PROJECT/build/release.json" ::release.json
printf 'LA AGUJA Rescue Disk\r\nSSH de fabrica: usuario aguja, password aguja.\r\nPersonaliza Wi-Fi/SSH en aguja.conf (sin comillas).\r\nAl arrancar: Centro de rescate. Wi-Fi/idioma/teclado disponibles en el menu.\r\nEn consola: aguja help / aguja wifi / aguja password.\r\nPara el agente SSH: aguja context / aguja tools.\r\n' > "$PROJECT/build/LEEME.txt"
mcopy -i "$CFG" "$PROJECT/build/LEEME.txt" ::LEEME.txt
dd if="$CFG" of="$IMG" bs=512 seek="$CFG_START" conv=notrunc status=none
DATA="$PROJECT/build/data.ext4"
truncate -s "$((DATA_SECTORS * 512))" "$DATA"
mkfs.ext4 -q -F -L AGUJA_DATA -E lazy_itable_init=0,lazy_journal_init=0 "$DATA"
dd if="$DATA" of="$IMG" bs=512 seek="$DATA_START" conv=notrunc,sparse status=none
sgdisk -v "$IMG"
cp "$PROJECT/config/harnesses.json" "$DIST/harnesses.json"
chroot "$ROOT" dpkg-query -W > "$DIST/packages.tsv"
(cd "$DIST" && sha256sum "aguja-personal-$VERSION-amd64.iso" "aguja-personal-$VERSION-amd64.img" packages.tsv harnesses.json > SHA256SUMS)
echo "Construidas: $ISO y $IMG"
