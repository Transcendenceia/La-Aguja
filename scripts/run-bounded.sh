#!/bin/bash
# Task-local build/QA guard. Never change limits of OpenClaw or the user's apps.
set -euo pipefail
[[ $# -gt 0 ]] || { echo 'Uso: run-bounded.sh comando [argumentos]'; exit 2; }
MAX_MB=${AGUJA_JOB_MEMORY_MB:-2048}
CPU_PERCENT=${AGUJA_JOB_CPU_PERCENT:-200}
[[ $MAX_MB =~ ^[0-9]+$ && $CPU_PERCENT =~ ^[0-9]+$ ]] || exit 2
# Keep at least 2 GiB of currently available RAM out of the job budget.
AVAILABLE_MB=$(awk '/MemAvailable:/ {print int($2/1024)}' /proc/meminfo)
(( AVAILABLE_MB >= MAX_MB + 2048 )) || { echo 'Memoria disponible insuficiente: aplaza este trabajo pesado.'; exit 75; }
CPU_LIST=$(python3 - <<'PY'
import os
from pathlib import Path
groups={}
for cpu in sorted(os.sched_getaffinity(0)):
 p=Path('/sys/devices/system/cpu')/f'cpu{cpu}'/'topology'
 key=(p.joinpath('physical_package_id').read_text().strip(),p.joinpath('core_id').read_text().strip())
 groups.setdefault(key,[]).append(cpu)
# Reserve two physical cores, not merely two SMT threads, where available.
keys=list(groups);usable=keys[:-2] if len(keys)>2 else keys[:1]
print(','.join(str(cpu) for key in usable[:2] for cpu in groups[key]))
PY
)
echo "Trabajo acotado: CPU ${CPU_PERCENT}% · RAM ${MAX_MB} MiB · prioridad baja."
exec systemd-run --user --scope --quiet -p CPUQuota="${CPU_PERCENT}%" -p MemoryMax="${MAX_MB}M" \
  -p MemorySwapMax=0 -p TasksMax=256 -p IOWeight=25 \
  nice -n 10 taskset -c "$CPU_LIST" "$@"
