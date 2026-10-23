"""Native live recovery interface: metadata on stdout, keys only in private RAM."""
import argparse
import getpass
import json
import os
import subprocess
from pathlib import Path
import recovery_keys
import recovery_state


def main(args):
    parser = argparse.ArgumentParser(prog='aguja recovery')
    parser.add_argument('action', choices=['status', 'list', 'unlock', 'export', 'open'], nargs='?', default='status')
    parser.add_argument('index', type=int, nargs='?')
    parser.add_argument('device', nargs='?')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--writable', action='store_true')
    a = parser.parse_args(args)
    if os.geteuid() != 0:
        import subprocess
        return subprocess.call(['sudo', '-n', '/usr/local/bin/aguja', 'recovery', *args])
    try:
        state = recovery_state.status()
        if a.action == 'status':
            print(json.dumps(state) if a.json else 'Recovery: ' + ('loaded in private RAM' if state['loaded'] else 'locked; use sudo aguja recovery unlock (profile unlock is at boot)' if state['locked'] else 'available' if state['present'] else 'not configured'))
            return 0
        if not state['present'] or state.get('error'):
            raise ValueError()
        if not state['loaded']:
            password = None
            if state['locked']:
                if a.action != 'unlock' or not os.isatty(0):
                    print('Recovery is locked. Use an interactive console: sudo aguja recovery unlock.')
                    return 1
                password = getpass.getpass('Image unlock password / Contraseña de la imagen: ')
            state = recovery_state.unlock(password)
        if a.action == 'unlock':
            print(json.dumps(state) if a.json else 'Recovery keys are available in private RAM; no disk was opened.')
            return 0
        keys = recovery_state.cached()
        if a.action == 'list':
            rows = [{'index': n, 'type': item['type'], 'label': item['label'], 'identifier': item['identifier']} for n, item in enumerate(keys, 1)]
            if a.json:
                print(json.dumps({'keys': rows}, ensure_ascii=False))
            else:
                for row in rows:
                    print(f"{row['index']}. {row['type']} · {row['label']} · {row['identifier']} · [hidden / oculta]")
        elif a.action == 'export':
            print(recovery_state.ROOT / 'keys.json')
        else:
            if a.index is None or not 1 <= a.index <= len(keys) or not a.device:
                raise ValueError()
            recovery_keys.open_device(keys[a.index - 1], a.device, a.index, a.writable)
        return 0
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError):
        print('Recovery operation failed. Check state, selected disk and permissions; no key is displayed.')
        return 1
