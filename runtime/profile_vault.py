"""File-backed LUKS2 profile, opened before owner access is configured.

Only the current boot medium's CFG is considered. Never scan/open target disks.
Plain Imager profiles are deliberately supported. Legacy AES capsules use the same
boot gate, but are never described as LUKS. No secret is passed via argv or logged.
"""
import getpass
import fcntl
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import termios
import time

CFG = Path('/config')
VAULT = CFG / 'aguja-profile.luks'
PRIVATE = CFG / 'private'
MAPPING = 'aguja-profile'
FILES = ('aguja.conf', 'aguja-profile.json', 'aguja-recovery.json', 'aguja-tailnet-identity.json')


def command(argv, **kwargs):
    return subprocess.run(argv, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)


def regular(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Unsafe profile path')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('Invalid profile file')
    return path


def private_root():
    mounted = os.path.ismount(PRIVATE)
    # Root mutations require the real mount; a public marker is metadata only.
    if os.geteuid() == 0:
        return PRIVATE if mounted else None
    return PRIVATE if mounted or Path('/run/aguja-vault-open').is_file() else None


def settings_root():
    root = private_root()
    if os.geteuid() == 0 and VAULT.exists() and root is None:
        raise ValueError('Protected profile is not unlocked')
    return root or CFG


def ask(prompt):
    # A running Plymouth daemon does not prove its password label is visible
    # on the physical display. Reveal a dedicated local VT before requesting
    # input; never route the question to the last kernel console (often serial).
    for argv in (['plymouth', 'quit'], ['chvt', '1']):
        try:
            subprocess.run(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=5, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
    # systemd services can be session leaders: a normal open would silently
    # acquire tty1 for the parent and make the child's TIOCSCTTY fail (EPERM).
    descriptor = os.open('/dev/tty1', os.O_RDWR | os.O_NOCTTY)
    with os.fdopen(descriptor, 'r+b', buffering=0) as console:
        # Explicit KD_TEXT also handles a splash which left the VT in graphics.
        fcntl.ioctl(console, 0x4B3A, 0)  # KDSETMODE, KD_TEXT
        console.write((
            '\x1b[2J\x1b[H\n'
            '  LA AGUJA | DESBLOQUEAR PERFIL / UNLOCK PROFILE\n'
            '  ========================================================\n\n'
            '  Tu perfil esta cifrado. Introduce su contrasena y pulsa Enter.\n'
            '  Your profile is encrypted. Enter its password and press Enter.\n\n'
            '  La entrada se oculta. / Your password will not be shown.\n'
            '  El panel y SSH se abriran despues. / Access opens afterwards.\n\n'
        ).encode('utf-8'))
        # Run with an explicit controlling terminal, not a password-agent race.
        # Only stdout carries the secret; stderr/prompt stay on the local VT.
        result = subprocess.run(
            ['systemd-ask-password', '--timeout=0', '--echo=masked', prompt],
            stdin=console, stdout=subprocess.PIPE, stderr=console,
            start_new_session=True,
            preexec_fn=lambda: fcntl.ioctl(0, termios.TIOCSCTTY, 0), check=True)
    return result.stdout.rstrip(b'\n').decode('utf-8')


def open_vault(password):
    regular(VAULT)
    if private_root():
        return
    PRIVATE.mkdir(mode=0o700, exist_ok=True)
    if PRIVATE.is_symlink() or any(PRIVATE.iterdir()):
        raise ValueError('Vault mountpoint is not empty')
    command(['cryptsetup', 'open', '--type', 'luks', '--key-file', '-', str(VAULT), MAPPING], input=password.encode())
    try:
        command(['mount', '-t', 'ext4', '-o', 'nosuid,nodev,noexec', '/dev/mapper/' + MAPPING, str(PRIVATE)])
        os.chmod(PRIVATE, 0o700)
        Path('/run/aguja-vault-open').write_text('open\n')
        Path('/run/aguja-vault-open').chmod(0o644)
    except BaseException:
        command(['cryptsetup', 'close', MAPPING])
        raise


def gate():
    """Return capsule/path/passphrase/protection; fail closed, no menu fallback."""
    import profile
    password = None
    if VAULT.exists():
        while not private_root():
            password = ask('LA AGUJA · LUKS · desbloquear perfil / unlock profile:')
            if not password:
                raise ValueError('Profile unlock cancelled')
            try:
                open_vault(password)
            except subprocess.CalledProcessError:
                print('LUKS: no se abrió el perfil. Reintenta en esta pantalla.', flush=True)
                time.sleep(.5)
    root = settings_root()
    path = root / 'aguja-profile.json'
    capsule = None
    protection = 'luks2' if private_root() else 'none'
    if path.is_file():
        raw = regular(path).read_bytes()
        try:
            capsule = profile.open_capsule(raw, password)
        except Exception:
            capsule = None
        # Existing Imager encrypted capsules still boot, without an Imager change.
        while capsule is None:
            if not private_root():
                protection = 'legacy-aes'
            password = ask('LA AGUJA · perfil cifrado heredado / legacy profile:')
            if not password:
                raise ValueError('Profile unlock cancelled')
            try:
                capsule = profile.open_capsule(raw, password)
            except Exception:
                print('Perfil: frase no válida; reintenta.', flush=True)
                time.sleep(.5)
        if protection == 'none':
            protection = 'automatic'
    return capsule, path, password, protection


def migration_payload(files):
    """Normalize old envelopes only in RAM, so LUKS needs a single boot phrase."""
    import profile
    payload = {path.name: path.read_bytes() for path in files}
    old_password = None
    raw = payload.get('aguja-profile.json')
    if raw is not None and json.loads(raw).get('protection') == 'encrypted':
        old_password = getpass.getpass('Frase del perfil anterior (solo para migrar): ')
        capsule = profile.open_capsule(raw, old_password)
        if capsule is None:
            raise ValueError('Previous profile did not unlock')
        payload['aguja-profile.json'] = profile.seal(capsule, {'mode': 'plain'})
    raw = payload.get('aguja-recovery.json')
    if raw is not None and json.loads(raw).get('protection') == 'encrypted':
        import recovery_keys
        try:
            keys = recovery_keys.open_envelope(raw, old_password)
        except ValueError:
            password = getpass.getpass('Frase del resguardo anterior (solo para migrar): ')
            keys = recovery_keys.open_envelope(raw, password)
        payload['aguja-recovery.json'] = json.dumps({'format': recovery_keys.FORMAT, 'schema': 1,
                                                     'protection': 'plain', 'keys': keys}).encode()
    raw = payload.get('aguja-tailnet-identity.json')
    if raw is not None and json.loads(raw).get('protection') == 'encrypted':
        import tailnet_identity
        settings = tailnet_identity.settings()
        native = tailnet_identity.decode(raw, settings)
        payload['aguja-tailnet-identity.json'] = tailnet_identity.encode(native, settings | {'protection': 'plain'})
    return payload


def protect():
    """Explicit local migration; never run by ordinary boot or a remote command."""
    if os.geteuid() != 0 or not os.isatty(0) or os.environ.get('SSH_CONNECTION'):
        raise ValueError('Protect requires a local root console')
    if VAULT.exists() or not os.path.ismount(CFG):
        raise ValueError('Requires mounted CFG with no existing vault')
    files = [regular(CFG / name) for name in FILES if (CFG / name).exists()]
    if not files:
        raise ValueError('No settings to protect')
    print('Crear bóveda LUKS2 de 128 MiB en CFG; mover perfil, configuración y claves dentro. DATA/workspace no se cifra.')
    print('No es borrado seguro de rastros previos en flash. Conserva un respaldo privado fuera del USB.')
    if input('Escribe PROTEGER para continuar: ') != 'PROTEGER':
        return 130
    payload = migration_payload(files)
    password = getpass.getpass('Nueva frase LUKS: ')
    if len(password) < 12 or password != getpass.getpass('Repetir frase LUKS: '):
        raise ValueError('Invalid passphrase confirmation')
    if shutil.disk_usage(CFG).free < 144 * 1024**2:
        raise ValueError('Insufficient free CFG space')
    temporary = CFG / 'aguja-profile.luks.pending'
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        # Allocate actual space before formatting, avoiding a late ENOSPC.
        os.posix_fallocate(stream.fileno(), 0, 128 * 1024**2)
        os.fsync(stream.fileno())
    mapped = False
    mounted = False
    try:
        command(['cryptsetup', 'luksFormat', '--type', 'luks2', '--batch-mode', '--pbkdf', 'argon2id',
                 '--pbkdf-memory', '65536', '--pbkdf-parallel', '1', '--key-file', '-', str(temporary)], input=password.encode())
        command(['cryptsetup', 'open', '--key-file', '-', str(temporary), MAPPING], input=password.encode())
        mapped = True
        command(['mkfs.ext4', '-q', '-m', '0', '/dev/mapper/' + MAPPING])
        PRIVATE.mkdir(mode=0o700, exist_ok=True)
        if PRIVATE.is_symlink() or any(PRIVATE.iterdir()):
            raise ValueError('Vault mountpoint is not empty')
        command(['mount', '-o', 'nosuid,nodev,noexec', '/dev/mapper/' + MAPPING, str(PRIVATE)])
        mounted = True
        os.chmod(PRIVATE, 0o700)
        from profile import private_write
        for source in files:
            raw = payload[source.name]
            private_write(PRIVATE / source.name, raw)
            if (PRIVATE / source.name).read_bytes() != raw:
                raise ValueError('Profile readback failed')
        command(['sync', '-f', str(PRIVATE)])
        command(['umount', str(PRIVATE)])
        mounted = False
        command(['cryptsetup', 'close', MAPPING])
        mapped = False
        # Prove key/header after close, before activation or deleting source files.
        command(['cryptsetup', 'open', '--test-passphrase', '--key-file', '-', str(temporary)], input=password.encode())
        os.rename(temporary, VAULT)
        from config_transaction import syncdir
        syncdir(CFG)
        for source in files:
            source.unlink()
        syncdir(CFG)
        print('Bóveda verificada y activada para el próximo arranque. No se reinició. Revisa copias históricas sin cifrar.')
        return 0
    finally:
        if mounted:
            command(['umount', str(PRIVATE)])
        if mapped:
            command(['cryptsetup', 'close', MAPPING])
        # Failed .pending remains for diagnosis; originals are unchanged until activation.
