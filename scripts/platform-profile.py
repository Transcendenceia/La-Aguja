#!/usr/bin/python3
"""Structured private desktop helper: JSON stdin, safe metadata JSON lines stdout."""
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from profile import MAX_CAPSULE, discover, materialize_imports, seal


def emit(value):
    print(json.dumps(value, separators=(',', ':')), flush=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def config_partition(image):
    """Read verified GPT bounds/CRC. Never guess offsets or attach/mount disks."""
    size = Path(image).stat().st_size
    with open(image, 'rb') as stream:
        stream.seek(512)
        header = bytearray(stream.read(512))
        if header[:8] != b'EFI PART':
            raise ValueError('La imagen requiere GPT')
        header_size = struct.unpack_from('<I', header, 12)[0]
        crc = struct.unpack_from('<I', header, 16)[0]
        if not 92 <= header_size <= 512:
            raise ValueError('GPT no válida')
        struct.pack_into('<I', header, 16, 0)
        if zlib.crc32(header[:header_size]) != crc:
            raise ValueError('GPT dañada')
        first, last, table_lba, count, entry_size, table_crc = struct.unpack_from('<QQ16xQIII', header, 40)
        if not 1 <= count <= 4096 or entry_size != 128 or table_lba * 512 + count * entry_size > size:
            raise ValueError('Tabla GPT fuera de límites')
        stream.seek(table_lba * 512)
        table = stream.read(count * entry_size)
        if zlib.crc32(table) != table_crc:
            raise ValueError('Tabla GPT dañada')
        matches = []
        for index in range(count):
            entry = table[index * entry_size:(index + 1) * entry_size]
            if entry[:16] == b'\0' * 16:
                continue
            start, end = struct.unpack_from('<QQ', entry, 32)
            label = entry[56:128].decode('utf-16-le').rstrip('\0')
            if label == 'AGUJA_CFG':
                if start < first or end > last or start > end or (end + 1) * 512 > size:
                    raise ValueError('Partición de configuración fuera de límites')
                matches.append((start * 512, (end - start + 1) * 512))
        if len(matches) != 1:
            raise ValueError('Falta una partición AGUJA_CFG única')
        offset, length = matches[0]
        stream.seek(offset)
        boot = stream.read(512)
        if boot[510:] != b'\x55\xaa' or boot[82:90] != b'FAT32   ':
            raise ValueError('La configuración necesita FAT32')
        return offset, length


def prepare(request):
    source, output = Path(request['image_path']), Path(request['output_path'])
    if not source.is_file() or source.is_symlink() or source.resolve() == output.resolve() or output.exists():
        raise ValueError('Selecciona una imagen y un destino nuevo diferente')
    expected = request['image_sha256']
    if not isinstance(expected, str) or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
        raise ValueError('Hash de imagen no válido')
    output.parent.mkdir(parents=True, exist_ok=True)
    if not shutil.which('mcopy'):
        raise ValueError('Instala mtools para preparar la imagen')
    emit({'type': 'progress', 'stage': 'verify', 'message': 'Verificando imagen original'})
    if sha256(source) != expected:
        raise ValueError('La imagen no coincide con su huella')
    offset, _ = config_partition(source)
    with tempfile.TemporaryDirectory(prefix='aguja-capability-') as work:
        marker = Path(work) / 'release.json'
        subprocess.run(['mcopy', '-i', str(source) + '@@' + str(offset), '::/release.json', str(marker)], check=True, capture_output=True)
        release = json.loads(marker.read_bytes())
        if request['capsule'].get('tailscale', {}).get('enabled') and 'tailscale-profile-v1' not in release.get('features', []):
            return {'ok': False, 'error': 'La imagen no admite alta automática Tailscale/Headscale; descarga una imagen compatible.'}
        if 'locale' in request['capsule'] and 'locale-profile-v1' not in release.get('features', []):
            return {'ok': False, 'error': 'La imagen no admite idioma y teclado personalizados; descarga una versión compatible (0.4.3 o posterior).'}
        locale = request['capsule'].get('locale', {})
        public_locale = 'locale-preunlock-v1' in release.get('features', [])
        if locale and request.get('protection', {}).get('mode') == 'encrypted' and not public_locale:
            return {'ok': False, 'error': 'El teclado antes de desbloquear necesita Rescue Disk 0.9.7 o posterior.'}
        if (locale.get('language') in ('zh_CN.UTF-8', 'ja_JP.UTF-8') or locale.get('keyboard') in ('cn', 'jp')) and 'i18n-catalog-v1' not in release.get('features', []):
            return {'ok': False, 'error': 'La imagen no admite este idioma o teclado; descarga LA AGUJA 0.7.0 o posterior.'}
        if any(name == 'antigravity' and item.get('mode') == 'import' for name, item in request['capsule'].get('providers', {}).items()) and 'antigravity-oauth-file-v1' not in release.get('features', []):
            return {'ok': False, 'error': 'La imagen no admite OAuth portable Antigravity; descarga una versión compatible (0.4.1 o posterior).'}
        if 'platform-profile-v1' not in release.get('features', []):
            raise ValueError('La imagen no admite perfiles de la aplicación')
    capsule = materialize_imports(request['capsule'])
    protection = request.get('protection', {'mode': 'plain'})
    sealed = seal(capsule, protection)
    if len(sealed) > MAX_CAPSULE * 2:
        raise ValueError('Perfil demasiado grande')
    original_stat = source.stat()
    # No destination overwrite, no root privileges and no block device access.
    fd, temp = tempfile.mkstemp(prefix='.aguja-image-', dir=output.parent)
    os.close(fd)
    try:
        emit({'type': 'progress', 'stage': 'copy', 'message': 'Creando imagen privada'})
        subprocess.run(['cp', '--reflink=auto', '--sparse=always', '--', str(source), temp], check=True, capture_output=True)
        os.chmod(temp, 0o600)
        with tempfile.TemporaryDirectory(prefix='aguja-profile-') as work:
            profile = Path(work) / 'profile.json'
            profile.write_bytes(sealed)
            os.chmod(profile, 0o600)
            emit({'type': 'progress', 'stage': 'profile', 'message': 'Aplicando configuración privada'})
            subprocess.run(['mcopy', '-o', '-i', temp + '@@' + str(offset), str(profile), '::/aguja-profile.json'], check=True, capture_output=True)
            readback = Path(work) / 'readback.json'
            subprocess.run(['mcopy', '-i', temp + '@@' + str(offset), '::/aguja-profile.json', str(readback)], check=True, capture_output=True)
            if readback.read_bytes() != sealed:
                raise OSError('Verificación del perfil no coincide')
            if public_locale and capsule.get('locale'):
                selection = Path(work) / 'locale.json'
                selection.write_text(json.dumps(capsule['locale']))
                subprocess.run(['mcopy', '-o', '-i', temp + '@@' + str(offset), str(selection), '::/aguja-locale.json'], check=True, capture_output=True)
                checked = Path(work) / 'locale-readback.json'
                subprocess.run(['mcopy', '-i', temp + '@@' + str(offset), '::/aguja-locale.json', str(checked)], check=True, capture_output=True)
                if checked.read_bytes() != selection.read_bytes():
                    raise OSError('Verificación del idioma y teclado no coincide')

        current_stat = source.stat()
        if (current_stat.st_size, current_stat.st_mtime_ns, current_stat.st_ino) != (original_stat.st_size, original_stat.st_mtime_ns, original_stat.st_ino):
            raise ValueError('La imagen original cambió')
        with open(temp, 'rb') as stream:
            os.fsync(stream.fileno())
        emit({'type': 'progress', 'stage': 'hash', 'message': 'Verificando imagen preparada'})
        digest = sha256(temp)
        # link is atomic and fails if another process created output meanwhile.
        os.link(temp, output)
        directory = os.open(output.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return {'ok': True, 'output_path': str(output), 'sha256': digest, 'bytes': output.stat().st_size,
                'protection': protection.get('mode', 'plain'), 'profile_verified': True}
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main():
    raw = sys.stdin.buffer.read(MAX_CAPSULE * 2 + 1)
    if len(raw) > MAX_CAPSULE * 2:
        raise ValueError('Solicitud demasiado grande')
    request = json.loads(raw)
    if request.get('op') == 'prepare':
        return prepare(request)
    if request.get('op') == 'import-provider':
        return {'ok': True, **discover(request['provider'])}
    raise ValueError('Operación desconocida')


if __name__ == '__main__':
    try:
        emit(main())
    except Exception:
        # Exceptions from native tools/parsers could embed private values.
        emit({'ok': False, 'error': 'No se completó la operación. Comprueba imagen, destino, perfil y dependencias.'})
        sys.exit(1)
