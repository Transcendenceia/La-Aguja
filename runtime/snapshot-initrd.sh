#!/bin/bash
# Regenerate a staged release's initramfs in an isolated namespace only.
set -euo pipefail
root=$1
[[ $EUID == 0 && $root == /run/aguja-persistence/mount-gen-*/root && -f $root/etc/debian_version ]] || exit 1
mount --make-rprivate /
mount -t proc proc "$root/proc"
mount -t tmpfs -o mode=755,nosuid tmpfs "$root/dev"
for item in 'null 1 3' 'zero 1 5' 'random 1 8' 'urandom 1 9'; do
 read -r name major minor <<< "$item"
 mknod -m 666 "$root/dev/$name" c "$major" "$minor"
done
mount -t tmpfs -o mode=755,nosuid,nodev tmpfs "$root/run"
chroot "$root" /usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root update-initramfs -u -k all
