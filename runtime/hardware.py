"""Bounded read-only preflight. No mounts, SMART self-tests or device writes."""
import json
import os
from pathlib import Path
import shutil
import subprocess


def probe(argv, timeout=8):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return p.stdout[:65536].strip() if p.returncode == 0 else ''
    except (OSError, subprocess.TimeoutExpired):
        return ''


def snapshot():
    mem = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        mem[key] = int(value.split()[0]) * 1024
    cpu = probe(['lscpu', '-J'])
    disks = probe(['lsblk', '--json', '--bytes', '-o', 'PATH,PKNAME,TYPE,SIZE,MODEL,TRAN,RM,RO,FSTYPE,LABEL,MOUNTPOINTS'])
    available = mem.get('MemAvailable', 0)
    threads = os.cpu_count() or 1
    # Budget is a ceiling to review, never a claim of dedicated free resources.
    vm_memory = min(available // 2, max(0, available - 1024**3)) // 1024**2
    locations = {}
    for name in ('/', '/run', '/data', '/data/workspace', '/config'):
        if Path(name).exists():
            usage = shutil.disk_usage(name)
            locations[name] = {'free_bytes': usage.free, 'total_bytes': usage.total}
    return {'schema': 1, 'read_only': True, 'firmware': 'uefi' if Path('/sys/firmware/efi').is_dir() else 'bios',
            'kernel': probe(['uname', '-r']), 'cpu': json.loads(cpu) if cpu else None,
            'threads': threads, 'memory_bytes': mem.get('MemTotal', 0), 'available_bytes': available,
            'virtualization': {'kvm_usable': os.access('/dev/kvm', os.R_OK | os.W_OK),
                               'tcg_available': bool(shutil.which('qemu-system-x86_64')),
                               'suggested_max_vcpus': max(1, threads // 2), 'suggested_max_memory_mib': vm_memory},
            'storage': json.loads(disks).get('blockdevices', []) if disks else [],
            'mounts': probe(['findmnt', '--json', '-o', 'TARGET,SOURCE,FSTYPE,OPTIONS']),
            'capacity': locations, 'drivers': probe(['lspci', '-nnk']),
            'usb': probe(['lsusb']), 'network': probe(['nmcli', '-t', '-f', 'DEVICE,TYPE,STATE', 'device']),
            'radio_blocks': probe(['rfkill', '-J']),
            'guides': ['/usr/share/aguja/MISSIONS.md', '/usr/share/aguja/BACKUP.md']}


def backup_options(state):
    return {'schema': 1, 'automatic_action': False, 'hardware': state,
            'required_inputs': ['mission and exact source/destination identities', 'data size and importance',
                                'disk health, encryption and acceptable downtime'],
            'options_in_preference_order': [
                {'destination': 'separate healthy internal disk', 'condition': 'not another partition on the source; enough measured free space'},
                {'destination': 'external disk', 'condition': 'owner makes it available; identify model/serial and existing data'},
                {'destination': 'NAS / SSH server', 'condition': 'owner chooses destination; check access, capacity and restore path'},
                {'destination': 'cloud', 'condition': 'ask owner first; bandwidth, quota, privacy, encryption and cost'},
                {'destination': 'Rescue USB DATA workspace', 'condition': 'owner agrees; reserve room for live generations; delete only this job backup after verified restore and owner retention check'},
                {'destination': 'temporary partition on same disk', 'condition': 'owner agrees; healthy unmounted shrinkable filesystem, verified backup of partition metadata; not protection against disk failure'},
                {'destination': 'no backup', 'condition': 'explicit informed owner choice for exact destructive operation; never inferred from silence'}],
            'next_step': 'Present feasible options with measured bytes, limitations and recommendation; do not partition or copy automatically.'}


def main(args):
    if args not in ([], ['--json'], ['plan'], ['plan', '--json']):
        raise ValueError('hardware [--json] | plan [--json]')
    data = snapshot()
    print(json.dumps(backup_options(data) if 'plan' in args else data, ensure_ascii=False, indent=2))
    return 0
