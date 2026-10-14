#!/usr/bin/python3
"""Standalone companion for manual recovery keys; compatible with Rescue 0.9.11.

No key in command arguments, logs or a plaintext USB file in encrypted mode.
This supplemental capsule leaves the existing boot/profile format unchanged.
"""
import argparse
import base64
import getpass
import json
import os
from pathlib import Path
import re
import stat
import subprocess

FORMAT = 'aguja-disk-recovery'
AAD = b'aguja-disk-recovery:1'

def validate(keys):
    if not isinstance(keys, list) or len(keys) > 16:
        raise ValueError('Invalid recovery key list / Lista de claves no válida')
    result = []
    for item in keys:
        if not isinstance(item, dict) or set(item) != {'type', 'label', 'identifier', 'key'}:
            raise ValueError('Invalid recovery entry / Clave de recuperación no válida')
        if item['type'] not in ('bitlocker', 'luks'):
            raise ValueError('Unsupported encryption type / Tipo de cifrado no admitido')
        for field, limit in [('label', 128), ('identifier', 128), ('key', 4096)]:
            value = item[field]
            if not isinstance(value, str) or len(value.encode()) > limit or re.search(r'[\x00-\x1f\x7f]', value):
                raise ValueError('Invalid recovery field / Campo de recuperación no válido')
        if not item['label'] or not item['key']:
            raise ValueError('Missing recovery field / Falta un campo de recuperación')
        if item['type'] == 'bitlocker' and (not re.fullmatch(r'(?:\d{6}-){7}\d{6}', item['key']) or any(int(g) > 720885 or int(g) % 11 for g in item['key'].split('-'))):
            raise ValueError('Invalid BitLocker recovery key / Clave BitLocker no válida')
        result.append(dict(item))
    return result

def open_envelope(raw, passphrase=None):
    if len(raw) > 256 * 1024:
        raise ValueError('Recovery file too large / Archivo demasiado grande')
    envelope = json.loads(raw)
    if envelope.get('format') != FORMAT or envelope.get('schema') != 1:
        raise ValueError('Invalid recovery format / Formato de recuperación no válido')
    if envelope.get('protection') == 'plain':
        return validate(envelope['keys'])
    if envelope.get('protection') != 'encrypted' or envelope.get('kdf') != 'scrypt-32768-8-1':
        raise ValueError('Invalid recovery protection / Protección no válida')
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    def decode(value):
        return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))
    try:
        salt, iv, data = (decode(envelope[k]) for k in ('salt', 'iv', 'data'))
        if len(salt) != 16 or len(iv) != 12 or len(data) < 16:
            raise ValueError()
        key = Scrypt(salt=salt, length=32, n=32768, r=8, p=1).derive(passphrase.encode())
        value = json.loads(AESGCM(key).decrypt(iv, data, AAD))
    except Exception:
        raise ValueError('Wrong password or altered recovery file / Contraseña incorrecta o archivo alterado') from None
    if value.get('schema') != 1:
        raise ValueError('Invalid recovery version / Versión de recuperación no válida')
    return validate(value['keys'])

def export_keys(keys, root=Path('/run/aguja-recovery')):
    if root.is_symlink() or any(p.is_symlink() for p in root.parents):
        raise ValueError('Unsafe recovery directory / Directorio no seguro')
    root.mkdir(mode=0o700, exist_ok=True)
    os.chmod(root, 0o700)
    path = root / 'keys.json'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as out:
        json.dump({'schema': 1, 'keys': validate(keys)}, out)
    return path

def main():
    parser = argparse.ArgumentParser(description='LA AGUJA manual BitLocker / LUKS recovery keys')
    parser.add_argument('action', choices=['list', 'export', 'open'])
    parser.add_argument('index', nargs='?', type=int)
    parser.add_argument('device', nargs='?')
    parser.add_argument('--file', type=Path, default=Path('/config/aguja-recovery.json'))
    parser.add_argument('--writable', action='store_true')
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise ValueError('Run with sudo / Ejecuta con sudo')
    raw = args.file.read_bytes()
    envelope = json.loads(raw)
    password = getpass.getpass('Image unlock password / Contraseña de la imagen: ') if envelope.get('protection') == 'encrypted' else None
    keys = open_envelope(raw, password)
    if args.action == 'list':
        for n, item in enumerate(keys, 1):
            print(f"{n}. {item['type']} · {item['label']} · {item['identifier']} · [hidden / oculta]")
    elif args.action == 'export':
        print(export_keys(keys))
    else:
        if args.index is None or not 1 <= args.index <= len(keys) or not args.device:
            raise ValueError('Choose a key number and exact device / Elige número de clave y dispositivo exacto')
        device = Path(args.device).resolve(strict=True)
        if not str(device).startswith('/dev/') or not stat.S_ISBLK(device.stat().st_mode):
            raise ValueError('Select a block device / Selecciona un dispositivo de bloques')
        item = keys[args.index - 1]
        if item['type'] == 'luks' and re.fullmatch(r'[0-9a-fA-F-]{36}', item['identifier']):
            uuid = subprocess.check_output(['cryptsetup', 'luksUUID', str(device)], text=True).strip()
            if uuid.lower() != item['identifier'].lower():
                raise ValueError('LUKS UUID does not match / El UUID LUKS no coincide')
        command = ['cryptsetup', 'open', '--type', 'bitlk' if item['type'] == 'bitlocker' else 'luks', '--key-file', '-']
        if not args.writable:
            command.append('--readonly')
        command += [str(device), f'aguja-recovery-{args.index}']
        subprocess.run(command, input=item['key'].encode(), check=True)

if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError):
        print('Recovery operation failed. Check the selected key, password, disk and permissions. / No se completó la recuperación. Revisa clave, contraseña, disco y permisos.')
        raise SystemExit(1)
