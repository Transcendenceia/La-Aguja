"""Root-private RAM handoff for supplemental disk recovery capsules.

Metadata is safe to display. Key bytes are never returned to the console.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import recovery_keys

from profile_vault import settings_root
SOURCE = settings_root() / 'aguja-recovery.json'
ROOT = Path('/run/aguja-recovery')


def read_regular(path, private=False):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Unsafe recovery path')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 256 * 1024:
            raise ValueError('Invalid recovery file')
        if private and (info.st_uid != os.geteuid() or info.st_mode & 0o077):
            raise ValueError('Invalid recovery cache permissions')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            return stream.read(256 * 1024 + 1)
    finally:
        os.close(fd)


def cache_root(root):
    root = Path(root)
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('Unsafe recovery directory')
    root.mkdir(mode=0o700, exist_ok=True)
    info = root.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError('Invalid recovery directory permissions')
    return root


def cached(source=SOURCE, root=ROOT):
    raw = read_regular(source)
    root = cache_root(root)
    meta = json.loads(read_regular(root / 'state.json', private=True))
    keys_raw = read_regular(root / 'keys.json', private=True)
    if not isinstance(meta, dict):
        raise ValueError('Invalid recovery state')
    if meta.get('source_sha256') != hashlib.sha256(raw).hexdigest() or meta.get('keys_sha256') != hashlib.sha256(keys_raw).hexdigest():
        raise ValueError('Recovery cache is stale')
    value = json.loads(keys_raw)
    if not isinstance(value, dict) or value.get('schema') != 1:
        raise ValueError('Invalid recovery cache')
    return recovery_keys.validate(value.get('keys'))


def status(source=SOURCE, root=ROOT):
    result = {'present': False, 'loaded': False, 'locked': False,
              'source': str(source), 'private_ram': str(Path(root) / 'keys.json')}
    try:
        raw = read_regular(source)
    except FileNotFoundError:
        return result
    except (ValueError, OSError):
        return result | {'present': True, 'error': 'unavailable'}
    result['present'] = True
    try:
        e = json.loads(raw)
        if not isinstance(e, dict) or e.get('format') != recovery_keys.FORMAT or e.get('schema') != 1 or e.get('protection') not in ('plain', 'encrypted'):
            raise ValueError()
        result['protection'] = e['protection']
        result['locked'] = e['protection'] == 'encrypted'
        try:
            keys = cached(source, root)
            result.update(loaded=True, locked=False, count=len(keys))
        except (ValueError, OSError, KeyError):
            pass
    except (ValueError, TypeError):
        result['error'] = 'invalid'
    return result


def unlock(passphrase=None, source=SOURCE, root=ROOT):
    raw = read_regular(source)
    keys = recovery_keys.open_envelope(raw, passphrase)
    root = cache_root(root)
    payload = json.dumps({'schema': 1, 'keys': keys}, ensure_ascii=False).encode()
    meta = json.dumps({'source_sha256': hashlib.sha256(raw).hexdigest(),
                       'keys_sha256': hashlib.sha256(payload).hexdigest()}).encode()
    # Atomic replacement is restricted to the two owned, private cache files.
    for name, data in [('keys.json', payload), ('state.json', meta)]:
        target = root / name
        if target.exists() or target.is_symlink():
            read_regular(target, private=True)
        import tempfile
        fd, temporary = tempfile.mkstemp(prefix='.cache-', dir=root)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, 'wb') as out:
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
    return status(source, root)


def initialize():
    state = status()
    if state.get('present') and state.get('protection') == 'plain' and not state.get('error'):
        try:
            unlock()
        except (ValueError, OSError, KeyError):
            pass
