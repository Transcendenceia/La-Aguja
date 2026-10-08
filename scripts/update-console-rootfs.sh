#!/bin/bash
# Upgrade only LA AGUJA runtime/console in a previously built rootfs.
set -euo pipefail
PROJECT=$(cd "$(dirname "$0")/.." && pwd)
ROOT="$PROJECT/build/rootfs"
[[ $EUID == 0 && -f "$ROOT/etc/debian_version" && -f "$ROOT/usr/local/bin/agy" ]] || { echo 'Rootfs previa requerida'; exit 1; }
cleanup() {
    for p in dev/pts dev proc sys; do
        if mountpoint -q "$ROOT/$p"; then umount -R "$ROOT/$p"; fi
    done
    ln -sfn /run/NetworkManager/resolv.conf "$ROOT/etc/resolv.conf"
    if [[ -f "$ROOT/usr/sbin/policy-rc.d" ]]; then unlink "$ROOT/usr/sbin/policy-rc.d"; fi
}
trap cleanup EXIT
for p in dev proc sys; do
    mountpoint -q "$ROOT/$p" || mount --rbind "/$p" "$ROOT/$p"
    mount --make-rslave "$ROOT/$p"
done
printf '#!/bin/sh\nexit 101\n' > "$ROOT/usr/sbin/policy-rc.d"
chmod +x "$ROOT/usr/sbin/policy-rc.d"
install -m 644 /etc/resolv.conf "$ROOT/etc/resolv.conf.build"
mv -f "$ROOT/etc/resolv.conf.build" "$ROOT/etc/resolv.conf"
chroot "$ROOT" /bin/bash -e <<'EOF'
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends zsh zsh-autosuggestions zsh-syntax-highlighting avahi-daemon avahi-utils libnss-mdns python3-pil
apt-get clean
EOF
AGUJA_PROJECT="$PROJECT" AGUJA_ROOT="$ROOT" bash "$PROJECT/scripts/install-runtime.sh"
AGUJA_PROJECT="$PROJECT" bash "$PROJECT/scripts/install-branding.sh"
chroot "$ROOT" zsh -n /usr/share/aguja/zshrc
chroot "$ROOT" zsh -n /usr/local/share/zsh/site-functions/_aguja
chroot "$ROOT" update-initramfs -u -k all
chroot "$ROOT" dpkg-query -W > "$PROJECT/dist/packages.tsv"
echo 'Rootfs de consola actualizada; arneses preservados.'
