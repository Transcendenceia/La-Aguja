#!/usr/bin/python3
"""Small owner console UI. Passphrase stays on private stdin, never argv/logs."""
import getpass
import json
import os
import subprocess
from pathlib import Path


def main(args):
    if args == ['unlock']:
        if os.geteuid() != 0:
            return subprocess.call(['sudo', '-n', '/usr/local/bin/aguja', 'profile', 'unlock'])
        if not os.isatty(0):
            print('Desbloquea el perfil desde una consola interactiva local.')
            return 1
        import profile
        try:
            password = getpass.getpass('Frase del perfil protegido: ')
            capsule = profile.open_capsule(Path('/config/aguja-profile.json').read_bytes(), password)
            if capsule is None:
                raise ValueError('Perfil no abierto')
            import boot
            boot.main(profile_override=capsule)
        except Exception:
            print('No se abrió el perfil; comprueba la frase y la configuración.')
            return 1
        print('Perfil desbloqueado. Red, SSH y proveedores aplicados; la red privada conserva tu elección.')
        return 0
    if args not in ([], ['status'], ['status', '--json']):
        raise ValueError('profile status [--json] | profile unlock')
    path = Path('/run/aguja-profile-status.json')
    value = json.loads(path.read_text()) if path.exists() else {'present': False, 'locked': False, 'loaded': False}
    print(json.dumps(value) if '--json' in args else 'Perfil: ' + ('protegido, pendiente de desbloquear' if value['locked'] else 'cargado' if value['loaded'] else 'configuración de fábrica'))
    return 0
