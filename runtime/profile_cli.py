#!/usr/bin/python3
"""Small owner console UI. Passphrase stays on private stdin, never argv/logs."""
import getpass
import json
import os
import subprocess
from pathlib import Path


def main(args):
    if args == ['protect']:
        if os.geteuid() != 0:
            return subprocess.call(['sudo', '-n', '/usr/local/bin/aguja', 'profile', 'protect'])
        import profile_vault
        return profile_vault.protect()
    if args == ['unlock']:
        print('El perfil se desbloquea antes de iniciar Rescue, en la pantalla de arranque; no desde el menú.')
        return 1
    if args not in ([], ['status'], ['status', '--json']):
        raise ValueError('profile status [--json] | profile protect')
    path = Path('/run/aguja-profile-status.json')
    value = json.loads(path.read_text()) if path.exists() else {'present': False, 'locked': False, 'loaded': False}
    print(json.dumps(value) if '--json' in args else 'Perfil: ' + ('protegido, pendiente de desbloquear' if value['locked'] else 'cargado' if value['loaded'] else 'configuración de fábrica') + ' · ' + value.get('protection', 'unknown'))
    return 0
