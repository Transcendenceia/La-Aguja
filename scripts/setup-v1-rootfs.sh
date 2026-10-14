#!/bin/bash
# Run in a private mount/PID namespace; only the new isolated factory is changed.
set -euo pipefail
PROJECT=${AGUJA_PROJECT:-$(cd "$(dirname "$0")/.." && pwd)}
ROOT=${AGUJA_ROOT:-$PROJECT/build/rootfs}
[[ $EUID == 0 && $(realpath "$ROOT") == "$PROJECT/build/rootfs" && -f $ROOT/etc/debian_version ]] || exit 1
mount --make-rprivate /
mount -t proc proc "$ROOT/proc"
mount -t tmpfs -o mode=755,nosuid tmpfs "$ROOT/dev"
for item in 'null 1 3' 'zero 1 5' 'random 1 8' 'urandom 1 9'; do
 read -r name major minor <<< "$item";touch "$ROOT/dev/$name"
 mount --bind "/dev/$name" "$ROOT/dev/$name"
done
mount -t tmpfs -o mode=755,nosuid,nodev tmpfs "$ROOT/run"
resolver_backup="$PROJECT/build/resolver-original"
if [[ -e $ROOT/etc/resolv.conf || -L $ROOT/etc/resolv.conf ]]; then cp -a "$ROOT/etc/resolv.conf" "$resolver_backup"; fi
cleanup() {
 rm -f "$ROOT/etc/resolv.conf" "$ROOT/usr/sbin/policy-rc.d"
 if [[ -e $resolver_backup || -L $resolver_backup ]]; then mv "$resolver_backup" "$ROOT/etc/resolv.conf"; fi
}
trap cleanup EXIT
if [[ -L $ROOT/etc/resolv.conf ]]; then unlink "$ROOT/etc/resolv.conf"; fi
cp /etc/resolv.conf "$ROOT/etc/resolv.conf"
printf '#!/bin/sh\nexit 101\n' > "$ROOT/usr/sbin/policy-rc.d";chmod 755 "$ROOT/usr/sbin/policy-rc.d"
chroot "$ROOT" /usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root DEBIAN_FRONTEND=noninteractive dpkg --configure -a
chroot "$ROOT" /usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root DEBIAN_FRONTEND=noninteractive apt-get update
chroot "$ROOT" /usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends squashfs-tools xorriso
AGUJA_PROJECT="$PROJECT" AGUJA_ROOT="$ROOT" bash "$PROJECT/scripts/install-runtime.sh"
chroot "$ROOT" /usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root update-initramfs -u -k all
