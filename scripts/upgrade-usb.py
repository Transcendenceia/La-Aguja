#!/usr/bin/python3
"""Exact USB upgrade with verified full backup and preservation of configuration/data."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'runtime'))
from config import load

spec = importlib.util.spec_from_file_location('flash_usb', PROJECT / 'scripts/flash-usb.py')
flash = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flash)
LEGACY_GUIDE = 'efd5778bc2d9d428ff5c57c7e9d6dffacbad2c06df60b1084d522e6c99bc4c2b'


def run(*args):
    return subprocess.run(args, check=True, capture_output=True)


def topology():
    return json.loads(run('lsblk', '--tree', '-b', '-J', '-o', 'PATH,TYPE,SIZE,TRAN,RM,SERIAL,LABEL,MOUNTPOINTS').stdout)['blockdevices']


def parts(device, serial):
    matches = [d for d in topology() if d['path'] == device and d.get('serial') == serial]
    if len(matches) != 1 or matches[0]['tran'] != 'usb' or not matches[0]['rm']:
        raise ValueError('El USB no coincide con la identidad autorizada')
    result = {}
    for label in ('AGUJA_CFG', 'AGUJA_DATA'):
        candidates = [p for p in matches[0].get('children', []) if p.get('label') == label]
        if len(candidates) != 1:
            raise ValueError('Falta una partición única del medio LA AGUJA')
        result[label] = candidates[0]['path']
    return result


def internal_disks():
    return [disk for disk in topology() if disk.get('tran') == 'nvme']


def mount(partition, target, data=False, readonly=True):
    options = ('ro,' if readonly else 'rw,') + 'nosuid,nodev,noexec'
    if data and readonly:
        options += ',noload'
    if not data:
        options += ',umask=0077'
    run('mount', '-o', options, partition, str(target))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('device')
    parser.add_argument('--serial', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--backup-dir', type=Path, required=True)
    parser.add_argument('--confirm', required=True)
    args = parser.parse_args()
    if os.geteuid() != 0 or args.confirm != 'FLASH:' + args.serial:
        raise ValueError('Root e identidad autorizada requeridos')
    os.umask(0o077)
    disk = flash.identify(args.device, args.serial)
    with args.image.open('rb') as f:
        if flash.hash_stream(f) != args.sha256:
            raise ValueError('La imagen no coincide con su SHA256')
    before_internal = internal_disks()
    original = parts(args.device, args.serial)
    # Stage only a clean filesystem; never replay a journal on the original USB.
    run('e2fsck', '-f', '-n', original['AGUJA_DATA'])
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder = args.backup_dir / ('upgrade-' + args.serial + '-' + stamp)
    folder.mkdir(parents=True, mode=0o700)
    backing = run('findmnt', '-n', '-o', 'SOURCE', '--target', str(folder)).stdout.decode().strip()
    if backing.startswith(args.device):
        raise ValueError('El respaldo no puede estar en el USB')
    free = os.statvfs(folder)
    if free.f_bavail * free.f_frsize < disk['size'] * 2:
        raise ValueError('Espacio insuficiente para preservar datos y respaldo completo')
    with tempfile.TemporaryDirectory(prefix='aguja-upgrade-', dir='/run') as temporary:
        base = Path(temporary)
        cfg, data = base / 'cfg', base / 'data'
        cfg.mkdir(); data.mkdir()
        mounted = []
        try:
            mount(original['AGUJA_CFG'], cfg)
            mounted.append(cfg)
            configuration = (cfg / 'aguja.conf').read_bytes()
            settings = load(cfg / 'aguja.conf')
            (folder / 'aguja.conf').write_bytes(configuration)
            mount(original['AGUJA_DATA'], data, data=True)
            mounted.append(data)
            archive = folder / 'data.tar'
            run('tar', '--acls', '--xattrs', '--sparse', '-cpf', str(archive), '-C', str(data), '.')
            run('tar', '--acls', '--xattrs', '-df', str(archive), '-C', str(data))
            for target in reversed(mounted):
                run('umount', str(target))
            mounted.clear()
            flash.identify(args.device, args.serial)
            print('Configuración y datos preservados y comparados; comienza respaldo completo y grabación.', flush=True)
            subprocess.run([sys.executable, str(PROJECT / 'scripts/flash-usb.py'), str(args.image), args.device,
                            '--serial', args.serial, '--sha256', args.sha256, '--backup-dir', str(args.backup_dir),
                            '--confirm', args.confirm], check=True)
            updated = parts(args.device, args.serial)
            mount(updated['AGUJA_CFG'], cfg, readonly=False)
            mounted.append(cfg)
            candidate = cfg / '.aguja-upgrade.conf'
            candidate.write_bytes(configuration)
            load(candidate)
            os.replace(candidate, cfg / 'aguja.conf')
            assert (cfg / 'aguja.conf').read_bytes() == configuration
            mount(updated['AGUJA_DATA'], data, data=True, readonly=False)
            mounted.append(data)
            run('tar', '--acls', '--xattrs', '--same-owner', '-xpf', str(archive), '-C', str(data))
            run('tar', '--acls', '--xattrs', '-df', str(archive), '-C', str(data))
            guide_updates = 0
            workspace = data / 'workspace'
            if workspace.is_dir() and not workspace.is_symlink():
                for name in ('AGENTS.md', 'CLAUDE.md', 'GEMINI.md'):
                    target = workspace / name
                    if target.is_file() and not target.is_symlink() and hashlib.sha256(target.read_bytes()).hexdigest() == LEGACY_GUIDE:
                        # Refresh only the exact unedited previous autogenerated guide.
                        target.write_bytes((PROJECT / 'runtime/AGENT-CONTEXT.md').read_bytes())
                        guide_updates += 1
            os.sync()
            assert (cfg / 'aguja.conf').read_bytes() == configuration
            for target in reversed(mounted):
                run('umount', str(target))
            mounted.clear()
            run('blockdev', '--flushbufs', args.device)
            flash.identify(args.device, args.serial)
            start = int(Path('/sys/class/block/' + Path(updated['AGUJA_CFG']).name + '/start').read_text()) * 512
            # GPT relocation affects the first 34 sectors, not the live boot payload.
            length = start - 34 * 512
            with args.image.open('rb') as source, open(args.device, 'rb', buffering=0) as actual:
                source.seek(34 * 512); actual.seek(34 * 512)
                assert flash.hash_stream(source, length) == flash.hash_stream(actual, length)
            assert internal_disks() == before_internal
            report = {'result': 'verified', 'version': (PROJECT / 'VERSION').read_text().strip(),
                      'usb_serial': args.serial, 'configuration_preserved': True,
                      'wifi_preconfigured': bool(settings['wifi_ssid']), 'data_restored_and_compared': True,
                      'agent_guides_refreshed': guide_updates, 'live_region_readback_verified': True,
                      'internal_disk_topology_unchanged': True, 'preservation_backup': str(folder),
                      'usb_unmounted': True, 'physical_boot_of_new_version_tested': False}
            (folder / 'verified.json').write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps(report), flush=True)
        finally:
            for target in reversed(mounted):
                subprocess.run(['umount', str(target)], capture_output=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, AssertionError, subprocess.SubprocessError) as exc:
        print('Actualización no completada: ' + type(exc).__name__ + '. Los respaldos se conservan; no se muestran credenciales.', file=sys.stderr)
        sys.exit(1)
