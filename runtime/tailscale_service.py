#!/usr/bin/python3
"""Opt-in tailnet enrollment. No installer, secret argv or persistent node state.

Identity lives in /run: reboot requires a new valid enrollment (reusable key for
unattended repeated boots). Local Running/Online status is not an SSH/ACL test.
"""
import ipaddress
import json
import os
import re
from pathlib import Path
import stat
import subprocess
import sys
import time
from urllib.parse import urlsplit

PLATFORM_DIR = Path('/run/aguja-platform')
PRIVATE_DIR = Path('/run/aguja-tailnet-private')
CONFIG_FILE = PRIVATE_DIR / 'config.json'
KEY_FILE = PRIVATE_DIR / 'auth.key'
STATUS_FILE = PLATFORM_DIR / 'tailscale-status.json'
RUN_DIR = Path('/run/aguja-tailscale')
SOCKET_PATH = RUN_DIR / 'tailscaled.sock'
DAEMON_UNIT = 'aguja-tailscaled.service'


def log(message):
    print('[LA AGUJA Tailnet] ' + message, flush=True)


def secure_write(path, content, mode=0o600):
    # Reuse atomic no-follow writes rather than truncate a pre-existing file.
    from profile import private_write
    path = Path(path)
    if any(parent.is_symlink() for parent in path.parents):
        raise ValueError('Destino privado no válido')
    private_write(path, content)
    path.chmod(mode)


def private_read(path):
    path = Path(path)
    if any(parent.is_symlink() for parent in path.parents):
        raise ValueError('Destino privado no válido')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'r') as stream:
        meta = os.fstat(stream.fileno())
        if not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.geteuid() or meta.st_mode & 0o077:
            raise ValueError('Configuración privada no válida')
        data = stream.read(16385)
        if len(data) > 16384:
            raise ValueError('Configuración privada demasiado grande')
        return data


def validate_config(config):
    from profile import endpoint, text
    if not isinstance(config, dict) or set(config) - {'enabled', 'auth_key', 'login_server', 'hostname', 'ssh', 'accept_routes'}:
        raise ValueError('Configuración no válida')
    if not isinstance(config.get('enabled'), bool):
        raise ValueError('Configuración no válida')
    for flag in ('ssh', 'accept_routes'):
        if not isinstance(config.get(flag, False), bool):
            raise ValueError('Configuración no válida')
    if config.get('login_server'):
        endpoint(config['login_server'])
        if urlsplit(config['login_server']).scheme != 'https':
            raise ValueError('Headscale requiere HTTPS')
    if config.get('hostname'):
        hostname = text(config['hostname'], 63)
        if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', hostname):
            raise ValueError('Configuración no válida')
    if config.get('auth_key'):
        text(config['auth_key'], 1024)
    return config


def find_binary(name):
    # Runtime binaries come exclusively from the verified image build.
    for directory in ('/usr/bin', '/usr/sbin', '/usr/local/bin', '/usr/local/sbin'):
        candidate = Path(directory) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def ensure_binaries():
    return find_binary('tailscale'), find_binary('tailscaled')


def wait_for_network(timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for family in ('-4', '-6'):
            result = subprocess.run(['ip', family, 'route', 'show', 'default'],
                                    capture_output=True, text=True, timeout=3)
            if result.returncode == 0 and result.stdout.strip():
                return True
        time.sleep(1)
    return False


def ensure_tailscaled(_binary):
    # Never adopt a daemon using another socket or a persistent /var/lib state.
    result = subprocess.run(['systemctl', 'start', DAEMON_UNIT], capture_output=True, timeout=15)
    if result.returncode:
        return False
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if SOCKET_PATH.is_socket():
            return True
        time.sleep(.25)
    return False


def cli(binary):
    return [binary, '--socket=' + str(SOCKET_PATH)]


def connect_tailscale(binary, config):
    if not KEY_FILE.is_file():
        return False, 'No hay clave de alta disponible; vuelve a preparar el perfil.'
    # Read/validate file privacy before the CLI reads it. Key never reaches argv.
    key = private_read(KEY_FILE)
    if not key or any(c in key for c in '\0\r\n'):
        return False, 'Clave de alta no válida.'
    command = cli(binary) + ['up', '--reset', '--auth-key=file:' + str(KEY_FILE),
                            '--ssh=' + str(config.get('ssh', False)).lower(),
                            '--accept-routes=' + str(config.get('accept_routes', False)).lower(),
                            '--accept-dns=false', '--timeout=40s']
    if config.get('login_server'):
        command.append('--login-server=' + config['login_server'])
    if config.get('hostname'):
        command.append('--hostname=' + config['hostname'])
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=50)
    except subprocess.TimeoutExpired:
        return False, 'Alta sin respuesta; se reintentará cuando haya conectividad.'
    # Do not print/store stderr: Headscale keys need not use a tskey- prefix.
    if result.returncode:
        return False, 'Alta rechazada o sin conectividad. Comprueba clave, URL, caducidad y aprobación del nodo.'
    return True, ''


def retrieve_status(binary, login_server=''):
    state = {'enabled': True, 'connected': False, 'ipv4': '', 'tailscale_ips': [],
             'backend_state': 'Unknown', 'login_server': login_server or 'https://controlplane.tailscale.com',
             'checked_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
             'identity_storage': 'volatile', 'ssh_verified': False}
    try:
        result = subprocess.run(cli(binary) + ['status', '--json'], capture_output=True,
                                text=True, timeout=5)
        if result.returncode:
            return state
        parsed = json.loads(result.stdout)
        node = parsed.get('Self') or {}
        state['backend_state'] = str(parsed.get('BackendState', 'Unknown'))[:64]
        for value in node.get('TailscaleIPs', []):
            try:
                address = ipaddress.ip_address(value)
            except ValueError:
                continue
            state['tailscale_ips'].append(str(address))
            if address.version == 4:
                state['ipv4'] = str(address)
        state['hostname'] = str(node.get('HostName', ''))[:253]
        state['tailnet'] = str((parsed.get('CurrentTailnet') or {}).get('Name', ''))[:253]
        state['connected'] = (state['backend_state'] == 'Running' and node.get('Online') is True
                              and bool(state['tailscale_ips']))
    except (OSError, ValueError, TypeError, AttributeError, subprocess.TimeoutExpired):
        pass
    return state


def write_status(state):
    # Only nonsecret state is readable by the console/cockpit.
    secure_write(STATUS_FILE, json.dumps(state), 0o644)


def disable():
    KEY_FILE.unlink(missing_ok=True)
    # Managed daemon stops (no generic tailscaled/homelab service touched).
    subprocess.run(['systemctl', 'stop', DAEMON_UNIT], capture_output=True, timeout=15)
    write_status({'enabled': False, 'connected': False, 'ipv4': '', 'tailscale_ips': []})


def main():
    try:
        if not CONFIG_FILE.exists():
            return 0
        config = validate_config(json.loads(private_read(CONFIG_FILE)))
        if not config['enabled']:
            disable()
            return 0
        # Legacy current-source config may duplicate the key. Migrate to private
        # key file and remove it from config before doing any subprocess work.
        if config.get('auth_key'):
            secure_write(KEY_FILE, config.pop('auth_key'))
            secure_write(CONFIG_FILE, json.dumps(config))
        binary, daemon = ensure_binaries()
        if not binary or not daemon:
            write_status({'enabled': True, 'connected': False, 'error': 'La imagen no incluye Tailscale; usa una imagen compatible.'})
            return 1
        if not wait_for_network():
            write_status({'enabled': True, 'connected': False, 'error': 'Sin ruta de red; el alta se reintentará automáticamente.'})
            return 1
        if not ensure_tailscaled(daemon):
            write_status({'enabled': True, 'connected': False, 'error': 'No se pudo iniciar el daemon privado de tailnet.'})
            return 1
        current = retrieve_status(binary, config.get('login_server', ''))
        if not current['connected']:
            success, error = connect_tailscale(binary, config)
            current = retrieve_status(binary, config.get('login_server', ''))
            if not success or not current['connected']:
                current['error'] = error or 'Nodo no conectado todavía; pendiente de red o aprobación del servidor.'
                write_status(current)
                return 1
        KEY_FILE.unlink(missing_ok=True)
        write_status(current)
        log('Nodo conectado a la tailnet. SSH depende del servicio y las políticas del propietario.')
        return 0
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        # Error strings from parsers/processes can include credentials.
        try:
            write_status({'enabled': True, 'connected': False, 'error': 'Configuración o servicio no disponible; revisa el perfil.'})
        except (OSError, ValueError):
            pass
        log('No se pudo completar el alta; no se muestran datos privados.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
