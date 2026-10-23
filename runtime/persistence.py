"""Explicit global live snapshots, encrypted at rest, atomic generation activation.

Only the boot USB is writable. Passwords travel on stdin and never enter a file,
argv, environment or progress. The encrypted staging filesystem contains both
the captured tree and squashfs, so no plaintext staging is left on DATA.
"""
import argparse
import contextlib
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import sys
import time
import uuid

import updates as u

RUN = Path('/run/aguja-persistence')
# A nonrecursive root bind excludes mounted devices, including encrypted CFG.
# Volatile kernel/runtime state must be created afresh on the next boot.
EXCLUDES = ('dev/*', 'proc/*', 'sys/*', 'run/*', 'tmp/*', 'var/tmp/*',
            'data/*', 'config/*', 'mnt/*', 'media/*',
            'var/cache/apt/archives/*', 'var/cache/aguja-session-updates/*')
RUNTIME_STATE = ('aguja-storage', 'aguja-tailnet-private', 'aguja-tailscale', 'aguja-recovery')


def running_snapshot():
    return 'aguja.snapshot=1' in Path('/proc/cmdline').read_text().split()


def copy_regular_tree(source, destination):
    """Copy persistent application data, never sockets, PIDs or linked mounts."""
    for directory, dirs, files in os.walk(source, followlinks=False):
        dirs[:] = [name for name in dirs if not (Path(directory) / name).is_symlink()]
        relative = Path(directory).relative_to(source)
        target = destination / relative
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name in files:
            path = Path(directory) / name
            if path.is_file() and not path.is_symlink() and not name.endswith(('.pid', '.sock', '.lock')):
                shutil.copy2(path, target / name)
                info = path.stat()
                os.chown(target / name, info.st_uid, info.st_gid)


def capture_state(root):
    state = root / 'var/lib/aguja-snapshot-state'
    if state.exists():
        shutil.rmtree(state)
    state.mkdir(mode=0o700)
    for name in RUNTIME_STATE:
        source = Path('/run') / name
        if source.is_dir() and not source.is_symlink():
            copy_regular_tree(source, state / name)


def restore_state():
    if not running_snapshot():
        return
    state = Path('/var/lib/aguja-snapshot-state')
    for name in RUNTIME_STATE:
        source = state / name
        if source.is_dir() and not source.is_symlink():
            copy_regular_tree(source, Path('/run') / name)


def emit(stage, **values):
    print(json.dumps({'stage': stage, **values}), flush=True)


def command(argv, password=None, accepted=(0,)):
    result = subprocess.run(argv, input=password, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=1800, env=dict(os.environ,LC_ALL='C'))
    if result.returncode not in accepted:
        raise ValueError('No se completó la persistencia; el arranque anterior se conserva.')
    return result.stdout


def measured(argv, stage):
    """Consume native progress without publishing filenames or arbitrary output."""
    with subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, start_new_session=True, env=dict(os.environ,LC_ALL='C')) as proc:
        pending = b''
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(proc.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    for key, _ in selector.select(.3):
                        raw = os.read(key.fileobj.fileno(), 65536)
                        if not raw:
                            selector.unregister(key.fileobj)
                            continue
                        pieces = re.split(b'[\r\n]', pending + raw)
                        pending = pieces.pop()[-4096:]
                        for line in pieces:
                            text = line.decode(errors='replace').strip()
                            if stage == 'copy':
                                match = re.match(r'([0-9,]+)\s+\d+%', text)
                                if match:
                                    emit(stage, completed=int(match[1].replace(',', '')), unit='bytes')
                            else:
                                match = re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)%?', text)
                                if match and 0 <= float(match[1]) <= 100:
                                    emit(stage, completed=float(match[1]), total=100, unit='percent')
            if proc.wait():
                raise ValueError('La copia o compresión falló; no se activó una generación incompleta.')
        except BaseException:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
            raise


def digest(path, stage='verify'):
    size = path.stat().st_size
    hashed = 0
    value = hashlib.sha256()
    last = 0
    with path.open('rb') as stream:
        while chunk := stream.read(4 * 1024**2):
            value.update(chunk)
            hashed += len(chunk)
            if time.monotonic()-last>.15 or hashed==size:
                emit(stage, completed=hashed, total=size, unit='bytes')
                last = time.monotonic()
    return value.hexdigest()


def excluded(relative):
    return any(relative == item[:-2] or relative.startswith(item[:-1]) for item in EXCLUDES)


def tree_bytes(root):
    total = count = 0
    seen = set()
    for directory, dirs, files in os.walk(root, followlinks=False):
        base = Path(directory).relative_to(root)
        dirs[:] = [name for name in dirs if not excluded(str(base / name))]
        for name in files:
            path = Path(directory) / name
            if excluded(str(base / name)):
                continue
            info = path.lstat()
            if path.is_file() and not path.is_symlink():
                inode = (info.st_dev, info.st_ino)
                if inode not in seen:
                    total += info.st_size
                    seen.add(inode)
            count += 1
            if count % 1000 == 0:
                emit('scan', completed=count, unit='files')
    emit('scan', completed=count, unit='files')
    return total


def status():
    try:
        target = u.verify_persistent_target()
        return {'ok': True, 'available': True, 'target': target,
                'free_bytes': shutil.disk_usage(u.DATA).free,
                'state': u.state(), 'running_generation': u.running_generation()}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {'ok': True, 'available': False,
                'message': 'Se necesita el pendrive de arranque de LA AGUJA con CFG y DATA; un CD/ISO no permite persistir.'}


def pending_release():
    path = u.RUN / 'pending-release.json'
    if not path.exists():
        return None
    value = u.metadata(path)
    folder = Path(value['folder'])
    if folder.parent != Path('/var/cache/aguja-session-updates') or not re.fullmatch('release-[a-f0-9]{32}', folder.name):
        raise ValueError('La imagen pendiente no es válida.')
    if any(p.is_symlink() for p in (folder, *folder.parents)):
        raise ValueError('La imagen pendiente no es válida.')
    for name in ('vmlinuz', 'initrd.img', 'filesystem.squashfs'):
        if (folder / 'live' / name).is_symlink() or u.hashfile(folder / 'live' / name) != value['files'][name]:
            raise ValueError('La imagen pendiente no superó la verificación.')
    return folder / 'live'


@contextlib.contextmanager
def package_locks():
    with contextlib.ExitStack() as stack:
        for path in ('/var/lib/dpkg/lock-frontend', '/var/lib/dpkg/lock'):
            file = stack.enter_context(open(path, 'a+b'))
            try:
                fcntl.lockf(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('Hay una instalación en curso. Termínala antes de persistir.') from None
        yield


def save(password):
    if not isinstance(password, str) or not 8 <= len(password) <= 1024 or '\0' in password:
        raise ValueError('Usa una clave de persistencia de al menos 8 caracteres.')
    if 'boot=live' not in Path('/proc/cmdline').read_text().split():
        raise ValueError('Solo se puede persistir desde el live de LA AGUJA.')
    # The worker owns a private mount namespace, never the caller's mounts.
    command(['mount', '--make-rprivate', '/'])
    RUN.mkdir(mode=0o700, exist_ok=True)
    if RUN.is_symlink() or RUN.stat().st_uid != 0:
        raise ValueError('Área de persistencia no válida.')
    with u.lock(), package_locks():
        target = u.verify_persistent_target()
        generation = 'gen-' + uuid.uuid4().hex
        folder = u.ROOT / generation
        live = folder / 'live'
        live.mkdir(mode=0o700, parents=True)
        view = RUN / ('view-' + generation)
        encrypted = RUN / ('mount-' + generation)
        base_view = RUN / ('base-' + generation)
        merged = RUN / ('merged-' + generation)
        view.mkdir(mode=0o700)
        encrypted.mkdir(mode=0o700)
        mapping = 'aguja-save-' + generation[4:20]
        device = '/dev/mapper/' + mapping
        image = live / 'filesystem.squashfs'
        opened = mounted = viewed = rebased = base_mounted = False
        key = password.encode()
        password = None
        try:
            command(['mount', '--bind', '/', str(view)])
            viewed = True
            emit('scan')
            size = tree_bytes(view)
            pending = pending_release()
            if pending:
                base_view.mkdir(mode=0o700)
                command(['mount', '-t', 'squashfs', '-o', 'loop,ro', str(pending / 'filesystem.squashfs'), str(base_view)])
                base_mounted = True
                size = max(size, tree_bytes(base_view))
            # Staged tree and compressed image coexist, both inside encryption.
            reserve = size * (3 if pending else 2) + 1024**3
            u.capacity(reserve)
            emit('encrypt')
            with image.open('xb') as file:
                os.fchmod(file.fileno(), 0o600)
                file.truncate(reserve)
            command(['cryptsetup', 'luksFormat', '--batch-mode', '--type', 'luks2',
                     '--pbkdf', 'argon2id', '--pbkdf-memory', '65536', '--iter-time', '300',
                     '--key-file', '-', str(image)], key)
            metadata = json.loads(command(['cryptsetup', 'luksDump', '--dump-json-metadata', str(image)]))
            offset = int(metadata['segments']['0']['offset'])
            command(['cryptsetup', 'open', '--key-file', '-', str(image), mapping], key)
            opened = True
            command(['mkfs.ext4', '-q', '-F', '-m', '0', '-E', 'lazy_itable_init=0,lazy_journal_init=0', device])
            command(['mount', '-t', 'ext4', '-o', 'nosuid,nodev', device, str(encrypted)])
            mounted = True
            root = encrypted / 'root'
            root.mkdir()
            snapshot_source = view
            if pending:
                options = command(['findmnt', '-n', '-o', 'OPTIONS', '/']).decode().strip().split(',')
                upper = next((Path(x.split('=', 1)[1]) for x in options if x.startswith('upperdir=')), None)
                if upper is None or not str(upper).startswith('/run/live/overlay/') or not upper.is_dir():
                    raise ValueError('No se pudo combinar la imagen nueva con los cambios de esta sesión.')
                cloned_upper = encrypted / 'upper'
                cloned_upper.mkdir()
                work = encrypted / 'work'
                work.mkdir()
                measured(['rsync', '-aHAXx', '--numeric-ids', '--no-inc-recursive', '--info=progress2',
                          str(upper) + '/', str(cloned_upper) + '/'], 'copy')
                merged.mkdir(mode=0o700)
                command(['mount', '-t', 'overlay', '-o',
                         f'lowerdir={base_view},upperdir={cloned_upper},workdir={work}', 'overlay', str(merged)])
                rebased = True
                snapshot_source = merged
            emit('copy')
            measured(['rsync', '-aHAXx', '--numeric-ids', '--no-inc-recursive', '--info=progress2',
                      *['--exclude=/' + x for x in EXCLUDES], str(snapshot_source) + '/', str(root) + '/'], 'copy')
            if rebased:
                command(['umount', str(merged)])
                rebased = False
                shutil.rmtree(cloned_upper)
                shutil.rmtree(work)
                u.refresh_manager(root)
                main = root / 'usr/lib/live/boot/9990-main.sh'
                text = main.read_text()
                call = '\taguja_verify_generation "${livefs_root}"\n'
                if call not in text:
                    text = text.replace('\tVerify_checksums "${livefs_root}"', call + '\tVerify_checksums "${livefs_root}"', 1)
                if call not in text:
                    raise ValueError('La nueva imagen no permite el arranque de cambios cifrados.')
                main.write_text(text)
            # Rebuild from the captured root, not an initramfs inherited from
            # the boot medium or generated for a different installed kernel.
            emit('initramfs')
            command(['unshare', '--mount', '--pid', '--fork', '--propagation', 'private',
                     '/usr/lib/aguja/snapshot-initrd.sh', str(root)])
            capture_state(root)
            # A machine identity and live runtime sockets are not portable state.
            (root / 'etc/machine-id').write_bytes(b'')
            dbus_id = root / 'var/lib/dbus/machine-id'
            if dbus_id.exists() or dbus_id.is_symlink():
                dbus_id.unlink()
            dbus_id.symlink_to('/etc/machine-id')
            for path in ('dev', 'proc', 'sys', 'run', 'tmp', 'var/tmp', 'data', 'config', 'mnt', 'media'):
                (root / path).mkdir(parents=True, exist_ok=True)
            (root / 'tmp').chmod(0o1777)
            (root / 'var/tmp').chmod(0o1777)
            kernel, initrd = u.boot_pair(root)
            version = (root / 'usr/share/aguja/VERSION').read_text().strip()
            shutil.copy2(kernel, live / 'vmlinuz')
            shutil.copy2(initrd, live / 'initrd.img')
            emit('compress')
            squash = encrypted / 'system.squashfs'
            measured(['nice', '-n', '10', 'mksquashfs', str(root), str(squash), '-noappend',
                      '-processors', '1', '-mem', '128M', '-comp', 'zstd', '-Xcompression-level', '3',
                      '-percentage', '-progress'], 'compress')
            command(['unsquashfs', '-s', str(squash)])
            inner_hash = digest(squash)
            shutil.rmtree(root)
            emit('sync')
            command(['sync', '-f', str(encrypted)])
            command(['umount', str(encrypted)])
            mounted = False
            command(['e2fsck', '-fy', device], accepted=(0, 1))
            emit('compact')
            command(['resize2fs', '-M', device])
            header = command(['dumpe2fs', '-h', device]).decode()
            blocks = int(re.search(r'^Block count:\s+(\d+)', header, re.M)[1])
            block_size = int(re.search(r'^Block size:\s+(\d+)', header, re.M)[1])
            command(['cryptsetup', 'close', mapping])
            opened = False
            with image.open('r+b') as file:
                file.truncate(offset + blocks * block_size)
                file.flush()
                os.fsync(file.fileno())
            emit('verify')
            command(['cryptsetup', 'open', '--readonly', '--key-file', '-', str(image), mapping], key)
            opened = True
            command(['mount', '-t', 'ext4', '-o', 'ro,noload', device, str(encrypted)])
            mounted = True
            if digest(encrypted / 'system.squashfs') != inner_hash:
                raise ValueError('La instantánea no superó la verificación; no se activó.')
            command(['umount', str(encrypted)])
            mounted = False
            command(['cryptsetup', 'close', mapping])
            opened = False
            files = {name: digest(live / name) for name in ('vmlinuz', 'initrd.img', 'filesystem.squashfs')}
            u.atomic(folder / 'manifest.json', {'schema': 1, 'version': version, 'kind': 'snapshot-luks2',
                     'files': files, 'created_at': int(time.time()), 'inner_sha256': inner_hash})
            # Reobserve the real boot medium immediately before the commit point.
            if u.verify_persistent_target() != target:
                raise ValueError('El pendrive cambió durante el guardado; no se activó.')
            emit('activate')
            active = u.activate(generation)
            emit('done', result={'ok': True, 'generation': generation, 'state': active,
                 'encrypted': True, 'reboot_required': True})
            return 0
        finally:
            key = None
            if rebased:
                subprocess.run(['umount', str(merged)], capture_output=True)
            if base_mounted:
                subprocess.run(['umount', str(base_view)], capture_output=True)
            if mounted:
                subprocess.run(['umount', str(encrypted)], capture_output=True)
            if opened:
                subprocess.run(['cryptsetup', 'close', mapping], capture_output=True)
            if viewed:
                subprocess.run(['umount', str(view)], capture_output=True)
            for directory in (encrypted, view, merged, base_view):
                try:
                    directory.rmdir()
                except OSError:
                    pass


def main(argv=None):
    actual = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog='aguja persist')
    parser.add_argument('operation', nargs='?', default='status', choices=('status', 'save', 'worker'))
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(actual)
    if args.operation == 'save':
        password = getpass.getpass('Clave para cifrar y desbloquear los cambios: ')
        if password != getpass.getpass('Repite la clave: '):
            print('Las claves no coinciden.', file=sys.stderr)
            return 1
        process = subprocess.run(['sudo', '-n', 'unshare', '--mount', '--propagation', 'private',
                                  '/usr/bin/python3', __file__, 'worker'],
                                 input=json.dumps({'password': password}).encode())
        return process.returncode
    if os.geteuid() != 0:
        return subprocess.call(['sudo', '-n', '/usr/bin/python3', __file__, *actual])
    try:
        if args.operation == 'status':
            print(json.dumps(status(), ensure_ascii=False))
            return 0
        # Unshare is mandatory; changing mount propagation in the host namespace
        # would affect the desktop and unrelated services.
        if os.readlink('/proc/self/ns/mnt') == os.readlink('/proc/1/ns/mnt'):
            raise ValueError('El guardado necesita su propio espacio de montajes.')
        request = json.loads(sys.stdin.buffer.read(8192))
        return save(request.get('password'))
    except Exception as error:
        message = str(error) if isinstance(error, ValueError) else 'No se completó la persistencia; el arranque anterior se conserva.'
        emit('failed', error=message)
        return 1


if __name__ == '__main__':
    sys.exit(main())
