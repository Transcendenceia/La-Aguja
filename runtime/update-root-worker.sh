#!/bin/bash
# Executed only in an isolated mount+PID namespace by updates.py.
set -euo pipefail
ulimit -c 0
root=$1
packages=$2
[[ $packages == yes || $packages == no || $packages == verify ]] || exit 1
[[ $EUID == 0 && $root == /data/updates/gen-*/root && -f $root/etc/debian_version ]] || exit 1
mount --make-rprivate /
mount -t proc proc "$root/proc"
mount -t tmpfs -o mode=755,nosuid tmpfs "$root/dev"
for item in 'null 1 3' 'zero 1 5' 'random 1 8' 'urandom 1 9'; do
 read -r name major minor <<< "$item"
 touch "$root/dev/$name"
 mount --bind "/dev/$name" "$root/dev/$name"
done
mount -t tmpfs -o mode=755,nosuid,nodev tmpfs "$root/run"
# The build needs current DNS temporarily, not the next computer's DNS.
resolver_backup="$root/var/tmp/aguja-update-resolver-original"
if [[ -e $root/etc/resolv.conf || -L $root/etc/resolv.conf ]]; then
 cp -a "$root/etc/resolv.conf" "$resolver_backup"
fi
restore_build_settings() {
 rm -f "$root/etc/resolv.conf" "$root/usr/sbin/policy-rc.d"
 if [[ -e $resolver_backup || -L $resolver_backup ]]; then mv "$resolver_backup" "$root/etc/resolv.conf"; fi
}
trap restore_build_settings EXIT
# No daemon on the installed host may be started by a staging maintainer script.
printf '#!/bin/sh\nexit 101\n' > "$root/usr/sbin/policy-rc.d"
chmod 755 "$root/usr/sbin/policy-rc.d"
if [[ -L $root/etc/resolv.conf ]]; then unlink "$root/etc/resolv.conf"; fi
cp /etc/resolv.conf "$root/etc/resolv.conf"
if [[ $packages == yes ]]; then
 chroot "$root" /usr/bin/env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=1 update
 # Bound staging growth before installing anything; keep room for another root.
 plan=$(chroot "$root" /usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root LC_ALL=C DEBIAN_FRONTEND=noninteractive apt-get -y --with-new-pkgs --print-uris upgrade)
 download_bytes=$(printf '%s\n' "$plan" | awk '/^\047https?:/ {sum+=$3} END {printf "%.0f",sum}')
 free_bytes=$(df -PB1 "$root" | awk 'NR==2 {print $4}')
 [[ $free_bytes -ge $((download_bytes * 4 + 3 * 1024 * 1024 * 1024)) ]] || { echo 'Espacio insuficiente para instalar y empaquetar'; exit 1; }
 chroot "$root" /usr/bin/env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root DEBIAN_FRONTEND=noninteractive apt-get -y --with-new-pkgs -o Dpkg::Options::=--force-confold upgrade
fi
if [[ $packages != verify ]]; then
 chroot "$root" /usr/bin/env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root update-initramfs -u -k all
fi
if [[ $packages == verify ]]; then
 python3 - "$root" <<'PYVERSIONS'
import json,re,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);expected=json.loads((root/'usr/share/aguja/installed-harnesses.json').read_text())['providers']
paths={'codex':'/opt/aguja/agents/codex/x86_64-unknown-linux-musl/bin/codex','claude':'/opt/aguja/agents/claude/claude','antigravity':'/opt/aguja/agents/antigravity/agy','opencode':'/opt/aguja/agents/opencode/opencode'}
actual={}
for name,item in expected.items():
 raw=subprocess.check_output(['chroot',str(root),'/usr/bin/env','-i','PATH=/usr/local/bin:/usr/bin:/bin','HOME=/nonexistent','AGY_CLI_DISABLE_AUTO_UPDATE=true','DISABLE_AUTOUPDATER=1',paths[name],'--version'],timeout=30).decode(errors='replace')
 match=re.search(r'\d+\.\d+\.\d+',raw)
 if not match or match.group()!=item['version']:raise ValueError('Native version mismatch')
 actual[name]=match.group()
print(json.dumps(actual))
PYVERSIONS
else
 for name in codex agy claude opencode; do
  chroot "$root" /usr/bin/env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root AGY_CLI_DISABLE_AUTO_UPDATE=true "$name" --version
 done
fi
# Fresh staging /root may have only package caches; exclude it entirely from
# persisted generations. User HOME and profile values never came into this root.
rm -f "$root/usr/sbin/policy-rc.d"
