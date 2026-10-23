#!/bin/bash
# Temporary updates only: root must be a live RAM overlay; USB views readonly.
set -euo pipefail
ulimit -c 0
plan=$1
[[ $EUID == 0 && $plan == /var/cache/aguja-session-updates/session-*/packages.json && -f $plan && ! -L $plan ]] || exit 1
python3 - <<'PYRAM'
import sys
sys.path.insert(0,'/usr/lib/aguja')
from update_tasks import verify_live_ram
verify_live_ram()
PYRAM
mount --make-rprivate /
private=$(dirname "$plan")
mkdir -m700 "$private/devices"
for name in null zero random urandom; do touch "$private/devices/$name"; mount --bind "/dev/$name" "$private/devices/$name"; done
mount -t tmpfs -o mode=755,nosuid tmpfs /dev
for name in null zero random urandom; do touch "/dev/$name"; mount --bind "$private/devices/$name" "/dev/$name"; done
mkdir -p /dev/pts
mount -t devpts -o newinstance,ptmxmode=0666,mode=0620 devpts /dev/pts
ln -s pts/ptmx /dev/ptmx
ln -s /proc/self/fd /dev/fd
mount -t proc proc /proc
for view in /data /config /run/live/medium; do
 if mountpoint -q "$view"; then mount --bind "$view" "$view"; mount -o remount,bind,ro "$view"; fi
done
policy=/usr/sbin/policy-rc.d
if [[ -e $policy || -L $policy ]]; then cp -a "$policy" "$private/policy.before"; fi
restore_policy() {
 rm -f "$policy"
 if [[ -e $private/policy.before || -L $private/policy.before ]]; then mv "$private/policy.before" "$policy"; fi
}
trap restore_policy EXIT
rm -f "$policy"
printf '#!/bin/sh\nexit 101\n' > "$policy"
chmod 755 "$policy"
python3 - "$plan" <<'PYPACKAGES'
import json,os,re,subprocess,sys
from pathlib import Path
plan=Path(sys.argv[1]);items=json.loads(plan.read_text());assert isinstance(items,list) and 0<len(items)<=4096
args=[]
for item in items:
 assert set(item)=={'name','version'} and re.fullmatch(r'[a-z0-9][a-z0-9+.-]*(?::[a-z0-9][a-z0-9-]*)?',item['name']) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.+:~_-]{0,199}',item['version'])
 args.append(item['name']+'='+item['version'])
env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/nonexistent','LC_ALL':'C','DEBIAN_FRONTEND':'noninteractive','NEEDRESTART_MODE':'l'}
cache=plan.parent/'apt-cache';cache.mkdir();(cache/'archives').mkdir();(cache/'archives/partial').mkdir()
opts=['-o','Dir::State::lists=/run/aguja-updates/checks/lists','-o','Dir::Cache='+str(cache),'-o','Acquire::Retries=1']
preview=subprocess.check_output(['apt-get',*opts,'--print-uris','-y','install',*args],env=env,text=True)
size=sum(int(m[1]) for line in preview.splitlines() if (m:=re.match(r"^'https?://[^']+' \S+ (\d+) ",line)))
stat=os.statvfs('/');available=stat.f_bavail*stat.f_frsize
if available<size*4+256*1024**2:raise ValueError('Not enough RAM for package staging')
subprocess.run(['apt-get',*opts,'-y','-o','APT::Status-Fd=1','-o','Dpkg::Options::=--force-confold','install',*args],env=env,check=True)
PYPACKAGES
