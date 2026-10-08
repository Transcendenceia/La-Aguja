#!/bin/bash
set -euo pipefail
PROJECT=${AGUJA_PROJECT:-$(cd "$(dirname "$0")/.." && pwd)}
ROOT="$PROJECT/build/rootfs"
[[ $EUID == 0 ]] || { echo 'Ejecuta con sudo'; exit 1; }
mkdir -p "$PROJECT/build" "$PROJECT/dist"
[[ -d "$ROOT/etc" ]] || debootstrap --variant=minbase --arch=amd64 trixie "$ROOT" https://deb.debian.org/debian
cleanup() {
    for p in dev/pts dev proc sys; do
        if mountpoint -q "$ROOT/$p"; then umount -R "$ROOT/$p" || true; fi
    done
}
trap cleanup EXIT
for p in dev proc sys; do
    mountpoint -q "$ROOT/$p" || mount --rbind "/$p" "$ROOT/$p"
    mount --make-rslave "$ROOT/$p"
done
cat > "$ROOT/etc/apt/sources.list" <<'EOF'
deb https://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb https://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
deb https://deb.debian.org/debian trixie-updates main contrib non-free non-free-firmware
EOF
printf '#!/bin/sh\nexit 101\n' > "$ROOT/usr/sbin/policy-rc.d"
chmod +x "$ROOT/usr/sbin/policy-rc.d"
install -m 644 /etc/resolv.conf "$ROOT/etc/resolv.conf.build"
mv -f "$ROOT/etc/resolv.conf.build" "$ROOT/etc/resolv.conf"
python3 - "$PROJECT/runtime/locale-catalog.json" "$ROOT/etc/aguja-locales.build" <<'PY_LOCALES'
import json,sys
from pathlib import Path
catalog=json.loads(Path(sys.argv[1]).read_text())
Path(sys.argv[2]).write_text(''.join(item['value']+' UTF-8\n' for item in catalog['languages']))
PY_LOCALES
chroot "$ROOT" /bin/bash -e <<'EOF'
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends ca-certificates
apt-get update -qq
apt-get install -y --no-install-recommends linux-image-amd64 live-boot systemd-sysv dbus udev \
  openssh-server sudo network-manager wpasupplicant iw rfkill wireless-regdb \
  firmware-realtek firmware-iwlwifi firmware-atheros firmware-brcm80211 firmware-mediatek firmware-misc-nonfree \
  curl wget git jq ripgrep tmux nano less bash-completion zsh zsh-autosuggestions zsh-syntax-highlighting \
  avahi-daemon avahi-utils libnss-mdns python3 python3-pil python3-qrcode python3-cryptography nodejs npm \
  gddrescue testdisk smartmontools nvme-cli hdparm pciutils usbutils lshw \
  parted gdisk dosfstools e2fsprogs btrfs-progs xfsprogs ntfs-3g exfatprogs \
  cryptsetup lvm2 mdadm dislocker wimtools debootstrap arch-install-scripts \
  grub-pc-bin grub-efi-amd64-bin efibootmgr rsync zstd xz-utils unzip iproute2 iputils-ping dnsutils \
  locales kbd console-setup plymouth plymouth-themes fonts-dejavu-core fonts-noto-cjk \
  chromium chromium-sandbox xserver-xorg-core xserver-xorg-input-libinput xserver-xorg-video-all \
  xinit openbox xclip x11-utils xauth dbus-x11 xterm xdotool
getent passwd aguja >/dev/null || useradd -m -s /bin/bash -G sudo aguja
printf 'aguja ALL=(ALL:ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/aguja
chmod 440 /etc/sudoers.d/aguja
passwd -l root
echo aguja > /etc/hostname
# The shared catalog, installed by the build host below, is the sole allowlist.
cat /etc/aguja-locales.build > /etc/locale.gen
locale-gen
rm /etc/aguja-locales.build
echo 'LANG=es_ES.UTF-8' > /etc/default/locale
systemctl enable NetworkManager ssh
systemctl set-default multi-user.target
systemctl mask systemd-networkd.service systemd-networkd.socket systemd-networkd-wait-online.service
EOF
AGUJA_PROJECT="$PROJECT" AGUJA_ROOT="$ROOT" bash "$PROJECT/scripts/install-runtime.sh"
# Version locks: do not silently upgrade agents in release builds.
NODE_VERSION=$(jq -r .node.version "$PROJECT/config/harnesses.json")
NODE_HASH=$(jq -r .node.sha256 "$PROJECT/config/harnesses.json")
curl --fail --location --retry 3 "https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-x64.tar.xz" -o "$PROJECT/build/node.tar.xz"
printf '%s  %s\n' "$NODE_HASH" "$PROJECT/build/node.tar.xz" | sha256sum -c -
tar -xJf "$PROJECT/build/node.tar.xz" -C "$PROJECT/build" "node-v$NODE_VERSION-linux-x64/bin/node" "node-v$NODE_VERSION-linux-x64/LICENSE"
install -m 755 "$PROJECT/build/node-v$NODE_VERSION-linux-x64/bin/node" "$ROOT/usr/local/bin/node"
install -m 644 "$PROJECT/build/node-v$NODE_VERSION-linux-x64/LICENSE" "$ROOT/usr/share/aguja/node-LICENSE"
CODEX=$(jq -r .codex "$PROJECT/config/harnesses.json")
OPENCODE=$(jq -r .opencode "$PROJECT/config/harnesses.json")
chroot "$ROOT" npm install -g "@openai/codex@$CODEX" "opencode-ai@$OPENCODE"
for binary in codex opencode; do chroot "$ROOT" "$binary" --version; done
AGUJA_PROJECT="$PROJECT" bash "$PROJECT/scripts/pack-native.sh"
chroot "$ROOT" apt-get purge -y npm nodejs
chroot "$ROOT" apt-get autoremove -y --purge
chroot "$ROOT" dpkg-query -W > "$PROJECT/dist/packages.tsv"
chroot "$ROOT" apt-get clean
# Package indexes are regenerable and need not occupy the rescue image.
find "$ROOT/var/lib/apt/lists" -type f -delete
find "$ROOT/etc/ssh" -maxdepth 1 -name 'ssh_host_*' -type f -delete
truncate -s 0 "$ROOT/etc/machine-id"
[[ ! -f "$ROOT/var/lib/dbus/machine-id" ]] || truncate -s 0 "$ROOT/var/lib/dbus/machine-id"
rm -f "$ROOT/usr/sbin/policy-rc.d"
AGUJA_PROJECT="$PROJECT" bash "$PROJECT/scripts/install-branding.sh"
chroot "$ROOT" update-initramfs -u -k all
ln -sf /run/NetworkManager/resolv.conf "$ROOT/etc/resolv.conf"
cleanup
trap - EXIT
echo 'Rootfs lista. Continúa con scripts/build-image.sh'
