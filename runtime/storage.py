"""Cloud/NAS credential plumbing. No remote is contacted by metadata/status."""
import json
import os
from pathlib import Path
import subprocess


def configuration():
    from profile_vault import private_root
    root = private_root()
    # Never persist new storage credentials unencrypted by default.
    if root is None:
        root = Path('/run/aguja-storage')
    return root / 'storage' / 'rclone.conf'


def status():
    path = configuration()
    try:
        configured = path.is_file()
    except PermissionError:
        configured = None
    return {'schema': 1, 'credential_values_displayed': False, 'configured': configured,
            'config_path': str(path), 'persistent': str(path).startswith('/config/private/'),
            'providers': ['Google Drive', 'OneDrive', 'Dropbox', 'S3-compatible', 'WebDAV', 'SFTP', 'SMB/NAS'],
            'guide': '/usr/share/aguja/BACKUP.md', 'network_contacted': False}


def main(args):
    if args in ([], ['status'], ['status', '--json']):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    if args != ['configure']:
        raise ValueError('storage status [--json] | storage configure')
    if os.geteuid() != 0:
        return subprocess.call(['sudo', '-n', '/usr/local/bin/aguja', 'storage', 'configure'])
    if not os.isatty(0):
        raise ValueError('Use an interactive terminal for storage credentials')
    path = configuration()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    print('LUKS: credenciales persistentes.' if status()['persistent'] else 'Sin bóveda LUKS: credenciales solo en RAM; se pierden al apagar.')
    # Native rclone handles OAuth and remote choice; no application logs/argv secrets.
    previous = os.umask(0o077)
    try:
        return subprocess.call(['rclone', '--config', str(path), 'config'])
    finally:
        os.umask(previous)
        if path.is_file():
            path.chmod(0o600)
