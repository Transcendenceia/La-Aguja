#!/usr/bin/python3
"""Owner-selected provisioning capsules. Never logs credential values."""
import base64
import hashlib
import ipaddress
import json
import os
import re
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = 1
MAX_CAPSULE = 4 * 1024 * 1024
from i18n import LANGUAGES, KEYBOARDS, KEYBOARD_VARIANTS, DEFAULT_LOCALE
IMPORTS = {
    'codex': {'.codex/auth.json': 'auth', '.codex/config.toml': 'codex-settings'},
    'claude': {'.claude/.credentials.json': 'auth', '.claude/settings.json': 'claude-settings', '.claude.json': 'claude-onboarding'},
    'opencode': {'.local/share/opencode/auth.json': 'auth', '.config/opencode/opencode.json': 'opencode-settings'},
    'antigravity': {'.gemini/antigravity-cli/antigravity-oauth-token': 'auth',
                    '.gemini/antigravity-cli/settings.json': 'antigravity-settings'},
}


def text(value, maxlen=8192):
    if not isinstance(value, str) or len(value.encode()) > maxlen or any(c in value for c in '\0\r\n'):
        raise ValueError('Valor privado no válido')
    return value


def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip('=')


def unb64(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise ValueError('Formato binario no válido')
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


def private_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ValueError('Destino de perfil no válido')
    fd, temporary = tempfile.mkstemp(prefix='.aguja-', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data if isinstance(data, bytes) else data.encode())
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def endpoint(value, relay=False):
    text(value, 2048)
    p = urlsplit(value)
    if p.username or p.password or p.query or p.fragment or not p.hostname:
        raise ValueError('URL de servicio no válida')
    if relay and (p.scheme != 'https' or p.port not in (None, 443) or p.path not in ('', '/')):
        raise ValueError('El túnel requiere HTTPS en el puerto 443')
    if not relay and p.scheme != 'https':
        try:
            loopback = ipaddress.ip_address(p.hostname).is_loopback
        except ValueError:
            loopback = p.hostname == 'localhost'
        if p.scheme != 'http' or not loopback:
            raise ValueError('API requiere HTTPS o un servicio local')
    return value.rstrip('/')


def validate(capsule):
    """Validate typed literal values, before any writes or process launch."""
    if not isinstance(capsule, dict) or capsule.get('schema') != SCHEMA:
        raise ValueError('Versión de perfil no compatible')
    if set(capsule) - {'schema', 'hostname', 'network', 'ssh', 'providers', 'remote', 'locale', 'tailscale'}:
        raise ValueError('Campo de perfil desconocido')
    c = json.loads(json.dumps(capsule))
    # Keep locale absent in old capsules, so they remain consumable by 0.4.1.
    if 'locale' in c:
        c['locale'] = validate_locale(c['locale'])
    hostname = text(c.setdefault('hostname', 'aguja'), 63)
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', hostname):
        raise ValueError('Nombre de equipo no válido')
    from config import DEFAULTS, parse
    wifi = c.setdefault('network', {}).setdefault('wifi', {})
    if set(c['network']) - {'wifi', 'ethernet'} or set(wifi) - {'ssid', 'password', 'security', 'country', 'hidden'}:
        raise ValueError('Red no válida')
    for name, default in [('ssid', ''), ('password', ''), ('security', 'wpa-psk'), ('country', 'ES')]:
        text(wifi.setdefault(name, default))
    if not isinstance(wifi.setdefault('hidden', False), bool):
        raise ValueError('Red oculta no válida')
    ssh = c.setdefault('ssh', {})
    if set(ssh) - {'password', 'public_key', 'port'}:
        raise ValueError('SSH no válido')
    text(ssh.setdefault('password', 'aguja'))
    text(ssh.setdefault('public_key', ''))
    port = ssh.setdefault('port', 22)
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError('Puerto SSH no válido')
    # Reuse the boot parser, including WPA and public-key validation. Values are
    # required to round-trip through its literal INI format, never source/eval.
    values = DEFAULTS | {'hostname': hostname, 'wifi_ssid': wifi['ssid'], 'wifi_password': wifi['password'],
                        'wifi_security': wifi['security'], 'wifi_country': wifi['country'],
                        'wifi_hidden': 'yes' if wifi['hidden'] else 'no', 'ssh_password': ssh['password'],
                        'ssh_public_key': ssh['public_key'], 'ssh_port': str(port)}
    if any(v != v.strip() for v in values.values()):
        raise ValueError('Los extremos del valor no pueden conservarse')
    parse('[aguja]\n' + ''.join(k + ' = ' + v + '\n' for k, v in values.items()))
    eth = c['network'].setdefault('ethernet', {'method': 'auto'})
    if set(eth) - {'method', 'address', 'prefix', 'gateway', 'dns'} or eth.get('method') not in ('auto', 'manual', 'disabled'):
        raise ValueError('Ethernet no válido')
    if eth['method'] == 'manual':
        ipaddress.IPv4Address(eth.get('address', ''))
        prefix = eth.get('prefix')
        if isinstance(prefix, bool) or not isinstance(prefix, int) or not 1 <= prefix <= 32:
            raise ValueError('Prefijo IPv4 no válido')
        if eth.get('gateway'):
            ipaddress.IPv4Address(eth['gateway'])
        dns = eth.get('dns', [])
        if not isinstance(dns, list) or len(dns) > 8:
            raise ValueError('DNS no válido')
        for value in dns:
            ipaddress.IPv4Address(value)
    providers = c.setdefault('providers', {})
    if set(providers) - set(IMPORTS):
        raise ValueError('Proveedor desconocido')
    for name, provider in providers.items():
        if not isinstance(provider, dict) or set(provider) - {'mode', 'api_key', 'base_url', 'model', 'import_paths', 'files'}:
            raise ValueError('Configuración de proveedor no válida')
        if provider.get('mode') not in ('none', 'api', 'import'):
            raise ValueError('Modo de proveedor no válido')
        for field in ('api_key', 'base_url', 'model'):
            text(provider.get(field, ''))
        if provider.get('base_url'):
            endpoint(provider['base_url'])
        if provider['mode'] == 'api' and not provider.get('api_key'):
            raise ValueError('Clave API necesaria')
        if name == 'opencode' and provider['mode'] == 'api' and provider.get('base_url') and not provider.get('model'):
            raise ValueError('Un endpoint OpenCode propio requiere modelo')
        if provider['mode'] == 'import':
            if not isinstance(provider.get('import_paths', []), list) or not isinstance(provider.get('files', {}), dict):
                raise ValueError('Importación no válida')
            if set(provider.get('files', {})) - set(IMPORTS[name]):
                raise ValueError('Archivo de proveedor no permitido')
            if name == 'antigravity':
                paths = provider.get('import_paths', [])
                auth_path = '.gemini/antigravity-cli/antigravity-oauth-token'
                if not (auth_path in provider.get('files', {}) or any(isinstance(p, str) and p.endswith('/' + auth_path) for p in paths)):
                    raise ValueError('Falta autenticación portable Antigravity')
            for filename, encoded in provider.get('files', {}).items():
                raw = unb64(encoded)
                if len(raw) > 512 * 1024:
                    raise ValueError('Archivo demasiado grande')
                sanitize_import(name, filename, raw)
    # Ignore credentials from legacy relay profiles; no account service exists.
    c['remote'] = {'enabled': False}
    tailscale = c.setdefault('tailscale', {'enabled': False})
    if not isinstance(tailscale, dict) or set(tailscale) - {'enabled', 'auth_key', 'login_server', 'hostname', 'ssh', 'accept_routes'}:
        raise ValueError('Configuración Tailscale no válida')
    if not isinstance(tailscale.get('enabled'), bool):
        raise ValueError('Tailscale no válido')
    if tailscale['enabled']:
        auth_key = text(tailscale.get('auth_key', ''), 1024)
        if not auth_key or len(auth_key) < 10:
            raise ValueError('Clave de autenticación Tailscale necesaria')
        login_server = tailscale.get('login_server', '')
        if login_server:
            endpoint(login_server)
            if urlsplit(login_server).scheme != 'https':
                raise ValueError('Headscale requiere HTTPS')
        ts_host = tailscale.get('hostname', '')
        if ts_host:
            text(ts_host, 63)
            if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', ts_host):
                raise ValueError('Nombre de equipo Tailscale no válido')
        if not isinstance(tailscale.setdefault('ssh', False), bool):
            raise ValueError('Opción SSH de Tailscale no válida')
        if not isinstance(tailscale.setdefault('accept_routes', False), bool):
            raise ValueError('Opción accept_routes de Tailscale no válida')
    else:
        # A disabled option must not revive retained keys/settings on next boot.
        c['tailscale'] = {'enabled': False}
    if len(json.dumps(c).encode()) > MAX_CAPSULE:
        raise ValueError('Perfil demasiado grande')
    return c


def sanitize_import(provider, filename, raw):
    """Export data, not executable hooks/MCP/plugins, history or host paths."""
    kind = IMPORTS[provider][filename]
    if kind == 'codex-settings':
        import tomllib
        data = tomllib.loads(raw.decode())
        allowed = {k: text(data[k], 256) for k in ('model', 'model_reasoning_effort', 'model_provider') if k in data}
        allowed['cli_auth_credentials_store'] = 'file'
        # Model provider declarations contain only known transport settings.
        for name, item in data.get('model_providers', {}).items():
            if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', name) or not isinstance(item, dict):
                raise ValueError('Configuración Codex no válida')
            clean = {k: v for k, v in item.items() if k in ('name', 'base_url', 'wire_api', 'env_key', 'requires_openai_auth')}
            for key, value in clean.items():
                if key == 'requires_openai_auth':
                    if not isinstance(value, bool):
                        raise ValueError('Configuración Codex no válida')
                else:
                    text(value, 2048)
            if clean.get('base_url'):
                endpoint(clean['base_url'])
            allowed.setdefault('model_providers', {})[name] = clean
        return toml_settings(allowed).encode()
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError):
        raise ValueError('Archivo de autenticación o configuración no válido') from None
    if not isinstance(data, dict):
        raise ValueError('Archivo JSON no válido')
    if provider == 'antigravity' and kind == 'auth':
        # Native agy OAuth file, not a keyring dump or arbitrary configuration.
        if set(data) != {'token', 'auth_method', 'id_token'} or not isinstance(data['token'], dict):
            raise ValueError('Autenticación Antigravity no válida')
        token = data['token']
        if set(token) != {'access_token', 'token_type', 'refresh_token', 'expiry'}:
            raise ValueError('Autenticación Antigravity no válida')
        for value in [*token.values(), data['auth_method'], data['id_token']]:
            text(value, 32768)
            if not value:
                raise ValueError('Autenticación Antigravity no válida')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', token['expiry']):
            raise ValueError('Fecha de autenticación Antigravity no válida')
        try:
            datetime.fromisoformat(token['expiry'].replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('Fecha de autenticación Antigravity no válida') from None
        # Expired access tokens are valid: the native CLI can refresh them.
        return json.dumps(data, separators=(',', ':')).encode()
    if kind == 'antigravity-settings':
        data = {'model': text(data['model'], 256)} if 'model' in data else {}
        # Account OAuth is selected by absence of the Gemini API switch.
        return json.dumps(data, separators=(',', ':')).encode()
    if kind == 'auth':
        # Native credential fields are deliberately kept opaque, but objects only.
        return json.dumps(data, separators=(',', ':')).encode()
    if kind == 'claude-onboarding':
        data = {k: v for k, v in data.items() if k in ('hasCompletedOnboarding', 'oauthAccount')}
    elif kind == 'claude-settings':
        data = {k: v for k, v in data.items() if k in ('model', 'language', 'effortLevel')}
    elif kind == 'opencode-settings':
        data = {k: v for k, v in data.items() if k in ('model', 'small_model', 'theme')}
    return json.dumps(data, separators=(',', ':')).encode()


def toml_settings(values):
    scalar = lambda value: 'true' if value is True else 'false' if value is False else json.dumps(value)
    out = ''.join(k + ' = ' + scalar(v) + '\n' for k, v in values.items() if k != 'model_providers')
    for name, item in values.get('model_providers', {}).items():
        out += '\n[model_providers.' + name + ']\n' + ''.join(k + ' = ' + scalar(v) + '\n' for k, v in item.items())
    return out


def read_native_import(provider, filename, home):
    """Read one canonical owned regular file; never follow parent/file symlinks."""
    directory = os.open(home, os.O_RDONLY | os.O_DIRECTORY)
    try:
        parts = Path(filename).parts
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_size > 512 * 1024:
                raise ValueError('Archivo seleccionado no permitido')
            if provider == 'antigravity':
                forbidden = 0o177 if IMPORTS[provider][filename] == 'auth' else 0o022
                if info.st_mode & forbidden or not info.st_mode & 0o400:
                    raise ValueError('Permisos privados Antigravity no válidos')
            with os.fdopen(fd, 'rb') as stream:
                fd = None
                raw = stream.read(512 * 1024 + 1)
            if len(raw) > 512 * 1024:
                raise ValueError('Archivo demasiado grande')
            return sanitize_import(provider, filename, raw)
        finally:
            if fd is not None:
                os.close(fd)
    finally:
        os.close(directory)


def discover(provider, home=None):
    if provider not in IMPORTS:
        raise ValueError('Proveedor desconocido')
    home = Path(home or Path.home()).resolve()
    paths = []
    for filename in IMPORTS[provider]:
        try:
            read_native_import(provider, filename, home)
        except (OSError, ValueError, TypeError):
            continue
        paths.append(str(home / filename))
    portable = any(IMPORTS[provider][str(Path(p).relative_to(home))] == 'auth' for p in paths)
    return {'portable': portable, 'import_paths': paths if portable else [],
            'summary': 'Credenciales nativas seleccionadas; su vigencia se comprobará en Aguja.' if portable else
                       'No hay un archivo OAuth nativo Antigravity válido y privado; usa API o autorización nativa en Aguja.' if provider == 'antigravity' else
                       'No hay un archivo de autenticación nativo portable en este usuario.'}


def materialize_imports(capsule, home=None):
    home = Path(home or Path.home()).resolve()
    c = validate(capsule)
    for name, provider in c['providers'].items():
        if provider['mode'] != 'import':
            continue
        if provider.get('files'):
            # Desktop has already materialized explicitly approved custom/WSL
            # source locations. validate() above sanitizes each canonical file;
            # never discover additional host files or retain native paths.
            if provider.get('import_paths') or not any(IMPORTS[name][p] == 'auth' for p in provider['files']):
                raise ValueError('Falta autenticación portable')
            provider['files'] = {p: b64(sanitize_import(name, p, unb64(v))) for p, v in provider['files'].items()}
            provider.pop('import_paths', None)
            continue
        files = {}
        for value in provider.get('import_paths', []):
            path = Path(value).expanduser()
            # Only this user's canonical known files; no arbitrary file export.
            try:
                relative = str(path.relative_to(home))
            except ValueError:
                raise ValueError('Archivo seleccionado no permitido') from None
            if relative not in IMPORTS[name]:
                raise ValueError('Archivo seleccionado no permitido')
            try:
                files[relative] = b64(read_native_import(name, relative, home))
            except OSError:
                raise ValueError('Archivo seleccionado no permitido') from None
        if not any(IMPORTS[name][p] == 'auth' for p in files):
            raise ValueError('Falta autenticación portable')
        provider.pop('import_paths', None)
        provider['files'] = files
    return validate(c)


def seal(capsule, protection):
    raw = json.dumps(validate(capsule), separators=(',', ':')).encode()
    mode = protection.get('mode', 'plain')
    if mode == 'plain':
        return json.dumps({'format': 'aguja-profile', 'schema': SCHEMA, 'protection': 'plain', 'capsule': json.loads(raw)}).encode()
    if mode != 'encrypted':
        raise ValueError('Protección no válida')
    passphrase = text(protection.get('passphrase', ''), 1024)
    if len(passphrase) < 1:
        raise ValueError('La frase de protección necesita entre 1 y 1024 caracteres')
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    salt, iv = os.urandom(16), os.urandom(12)
    key = Scrypt(salt=salt, length=32, n=32768, r=8, p=1).derive(passphrase.encode())
    data = AESGCM(key).encrypt(iv, raw, b'aguja-profile:1')
    return json.dumps({'format': 'aguja-profile', 'schema': SCHEMA, 'protection': 'encrypted',
                       'kdf': 'scrypt-32768-8-1', 'salt': b64(salt), 'iv': b64(iv), 'data': b64(data)}).encode()


def open_capsule(raw, passphrase=None):
    if len(raw) > MAX_CAPSULE * 2:
        raise ValueError('Perfil demasiado grande')
    envelope = json.loads(raw)
    if envelope.get('format') != 'aguja-profile' or envelope.get('schema') != SCHEMA:
        raise ValueError('Perfil no compatible')
    if envelope.get('protection') == 'plain':
        return validate(envelope['capsule'])
    if envelope.get('protection') != 'encrypted' or envelope.get('kdf') != 'scrypt-32768-8-1':
        raise ValueError('Protección no compatible')
    if passphrase is None:
        return None
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    salt, iv = unb64(envelope['salt']), unb64(envelope['iv'])
    if len(salt) != 16 or len(iv) != 12:
        raise ValueError('Protección no válida')
    key = Scrypt(salt=salt, length=32, n=32768, r=8, p=1).derive(text(passphrase, 1024).encode())
    return validate(json.loads(AESGCM(key).decrypt(iv, unb64(envelope['data']), b'aguja-profile:1')))


def validate_locale(value):
    if not isinstance(value, dict) or set(value) != {'language', 'keyboard', 'variant'}:
        raise ValueError('Idioma y teclado no válidos')
    language, keyboard, variant = value['language'], value['keyboard'], value['variant']
    if language not in LANGUAGES or keyboard not in KEYBOARDS or not isinstance(variant, str):
        raise ValueError('Idioma y teclado no compatibles')
    if variant not in KEYBOARD_VARIANTS[keyboard]:
        raise ValueError('Variante de teclado no compatible')
    return dict(value)


def locale_environment(path='/etc/default/locale'):
    """Read one allowlisted literal, never source shell syntax or client LC_*.

    LC_ALL makes the owner's choice effective over language forwarded by SSH.
    CLI launchers call this again after a protected profile is unlocked.
    """
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        return {}
    for line in lines:
        if line.startswith('LANG=') and line[5:] in LANGUAGES:
            return {'LANG': line[5:], 'LC_ALL': line[5:]}
    return {}


def apply_locale(capsule=None, root='/', runner=None, respect_override=True):
    """Apply only public owner preferences to the live system, not host input.

    An encrypted capsule has no locale until unlocked; reset to factory then.
    root is injectable for isolated tests, while runner receives literal argv.
    """
    import subprocess
    selection = validate_locale((capsule or {}).get('locale', DEFAULT_LOCALE))
    base = Path(root).resolve()
    preference = base / 'config/aguja-locale.json'
    if respect_override and preference.is_file() and not preference.is_symlink():
        try:
            selection = validate_locale(json.loads(preference.read_text()))
        except (ValueError, OSError, TypeError):
            pass
    settings = {
        'etc/default/locale': 'LANG=' + selection['language'] + '\n',
        'etc/default/keyboard': 'XKBMODEL="pc105"\nXKBLAYOUT="' + selection['keyboard'] +
            '"\nXKBVARIANT="' + selection['variant'] + '"\nXKBOPTIONS=""\nBACKSPACE="guess"\n',
    }
    for relative, content in settings.items():
        target = (base / relative).resolve()
        if not target.is_relative_to(base):
            raise ValueError('Destino de idioma y teclado no válido')
        private_write(target, content)
        target.chmod(0o644)
    (runner or subprocess.run)(['setupcon', '--keyboard-only', '--save', '--force'],
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return selection


def configuration(capsule, current):
    wifi, ssh = capsule['network']['wifi'], capsule['ssh']
    return current | {'hostname': capsule['hostname'], 'wifi_ssid': wifi['ssid'], 'wifi_password': wifi['password'],
                      'wifi_security': wifi['security'], 'wifi_country': wifi['country'],
                      'wifi_hidden': 'yes' if wifi['hidden'] else 'no', 'ssh_password': ssh['password'],
                      'ssh_public_key': ssh['public_key'], 'ssh_port': str(ssh['port'])}


def ethernet_keyfile(ethernet):
    method = ethernet['method']
    out = '[connection]\nid=aguja-ethernet\ntype=ethernet\nautoconnect=true\n[ethernet]\n[ipv4]\nmethod=' + method + '\n'
    if method == 'manual':
        out += 'address1=' + ethernet['address'] + '/' + str(ethernet['prefix']) + ',' + ethernet.get('gateway', '') + '\n'
        if ethernet.get('dns'):
            out += 'dns=' + ';'.join(ethernet['dns']) + ';\n'
    return out + '[ipv6]\nmethod=' + ('disabled' if method == 'disabled' else 'auto') + '\n'


def apply(capsule, home='/home/aguja', state='/run/aguja-platform', tailnet_state=None):
    """Write only owner auth/config files and narrow runtime state, no shell data."""
    c = validate(capsule)
    home, state = Path(home), Path(state)
    env = {}
    for name, provider in c['providers'].items():
        if provider['mode'] == 'none':
            continue
        if provider['mode'] == 'import':
            if name == 'antigravity':
                if '.gemini/antigravity-cli/antigravity-oauth-token' not in provider.get('files', {}):
                    raise ValueError('Falta autenticación portable Antigravity')
                for filename in IMPORTS[name]:
                    destination = home / filename
                    if destination.is_symlink() or any(parent.is_symlink() for parent in destination.parents):
                        raise ValueError('Destino de perfil no válido')
            for filename, encoded in provider.get('files', {}).items():
                private_write(home / filename, sanitize_import(name, filename, unb64(encoded)))
            if name == 'antigravity':
                # Also reset a prior API profile when no settings were imported.
                filename = '.gemini/antigravity-cli/settings.json'
                settings = {}
                if filename in provider['files']:
                    settings = json.loads(sanitize_import(name, filename, unb64(provider['files'][filename])))
                if provider.get('model'):
                    settings['model'] = provider['model']
                private_write(home / filename, json.dumps(settings))
            continue
        key, model, url = provider['api_key'], provider.get('model'), provider.get('base_url')
        if name == 'codex':
            private_write(home / '.codex/auth.json', json.dumps({'OPENAI_API_KEY': key}))
            cfg = {'cli_auth_credentials_store': 'file'}
            if model:
                cfg['model'] = model
            if url:
                cfg |= {'model_provider': 'aguja', 'model_providers': {'aguja': {'name': 'Aguja', 'base_url': url, 'wire_api': 'responses', 'env_key': 'OPENAI_API_KEY'}}}
            private_write(home / '.codex/config.toml', toml_settings(cfg))
            env[name] = {'OPENAI_API_KEY': key}
        elif name == 'claude':
            env[name] = {'ANTHROPIC_API_KEY': key}
            if model:
                env[name]['ANTHROPIC_MODEL'] = model
            if url:
                env[name]['ANTHROPIC_BASE_URL'] = url
            private_write(home / '.claude.json', json.dumps({'hasCompletedOnboarding': True}))
        elif name == 'antigravity':
            env[name] = {'GEMINI_API_KEY': key}
            if url:
                env[name]['GOOGLE_GEMINI_BASE_URL'] = url
            private_write(home / '.gemini/antigravity-cli/settings.json', json.dumps({'modelProvider': 'gemini'}))
        elif name == 'opencode':
            provider_id = 'aguja' if url else 'opencode'
            private_write(home / '.local/share/opencode/auth.json', json.dumps({provider_id: {'type': 'api', 'key': key}}))
            cfg = {'$schema': 'https://opencode.ai/config.json'}
            if url:
                if not model:
                    raise ValueError('Un endpoint OpenCode propio requiere modelo')
                cfg['provider'] = {'aguja': {'npm': '@ai-sdk/openai-compatible', 'name': 'Aguja', 'options': {'baseURL': url}, 'models': {model: {'name': model}}}}
            if model:
                cfg['model'] = provider_id + '/' + model if url or '/' not in model else model
            private_write(home / '.config/opencode/opencode.json', json.dumps(cfg))
    private_write(home / '.config/aguja/provider-env.json', json.dumps(env))
    # Direct native launches receive API environments too, without shell eval.
    for name in env:
        binary = {'antigravity': 'agy'}.get(name, name)
        launcher = '#!/usr/bin/python3\nimport os,sys\nsys.path.insert(0,"/usr/lib/aguja")\nfrom profile import provider_environment,locale_environment\nos.environ.update(locale_environment())\nos.environ.update(provider_environment(' + repr(name) + '))\nos.execv("/usr/local/bin/' + binary + '",["' + binary + '"]+sys.argv[1:])\n'
        target = home / '.local/bin' / binary
        private_write(target, launcher)
        target.chmod(0o700)
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    ts_conf = c.get('tailscale', {'enabled': False})
    # Keep settings and enrollment key separate; config/status never duplicates it.
    private_write(state / 'tailscale.json', json.dumps({k: v for k, v in ts_conf.items() if k != 'auth_key'}))
    (state / 'tailscale.key').unlink(missing_ok=True)  # remove legacy duplicate
    (state / 'tailscale-status.json').unlink(missing_ok=True)
    apply_tailnet(ts_conf, tailnet_state or state / 'tailnet-private')
    private_write(state / 'status.json', json.dumps({
        'loaded': True,
        'providers': {k: v['mode'] for k, v in c['providers'].items()},
        'tailscale_enabled': ts_conf.get('enabled', False)
    }))
    return env


def apply_tailnet(config, state='/run/aguja-tailnet-private'):
    """Separate root-private enrollment files from user-owned console state."""
    state = Path(state)
    if state.is_symlink() or any(parent.is_symlink() for parent in state.parents):
        raise ValueError('Destino privado no válido')
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    state.chmod(0o700)
    if os.geteuid() == 0:
        os.chown(state, 0, 0)
    key = state / 'auth.key'
    key.unlink(missing_ok=True)
    enabled = config.get('enabled') is True
    settings = {k: v for k, v in config.items() if k != 'auth_key'} if enabled else {'enabled': False}
    private_write(state / 'config.json', json.dumps(settings))
    if enabled and config.get('auth_key'):
        private_write(key, config['auth_key'])


def provider_environment(name, home=None):
    path = Path(home or Path.home()) / '.config/aguja/provider-env.json'
    if not path.exists():
        return {}
    value = json.loads(path.read_text()).get(name, {})
    allowed = {'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'ANTHROPIC_MODEL', 'ANTHROPIC_BASE_URL', 'GEMINI_API_KEY', 'GOOGLE_GEMINI_BASE_URL'}
    if set(value) - allowed:
        raise ValueError('Entorno de proveedor no válido')
    return {k: text(v) for k, v in value.items()}


def update_plain_settings(path, changes):
    """Preserve the app capsule as authority; never save protected values plaintext."""
    target = Path(path)
    original = target.read_bytes()
    envelope = json.loads(original)
    if envelope.get('protection') == 'encrypted':
        return False
    capsule = open_capsule(original)
    wifi_map = {'wifi_ssid': 'ssid', 'wifi_password': 'password', 'wifi_security': 'security', 'wifi_country': 'country', 'wifi_hidden': 'hidden'}
    ssh_map = {'ssh_password': 'password', 'ssh_public_key': 'public_key', 'ssh_port': 'port'}
    for key, value in changes.items():
        if key in wifi_map:
            capsule['network']['wifi'][wifi_map[key]] = value == 'yes' if key == 'wifi_hidden' else value
        elif key in ssh_map:
            capsule['ssh'][ssh_map[key]] = int(value) if key == 'ssh_port' else value
        elif key == 'hostname':
            capsule['hostname'] = value
        else:
            raise ValueError('Preferencia no compatible con el perfil')
    raw = seal(capsule, {'mode': 'plain'})
    if target.read_bytes() != original:
        raise ValueError('El perfil cambió durante la operación')
    private_write(target, raw)
    os.sync()
    if target.read_bytes() != raw:
        raise OSError('Lectura de perfil no coincide')
    return True
