"""Local on-demand X11 session. Root owns VT/Xorg, never browser or GTK app."""
import fcntl
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import shlex
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import time

ACTIONS = {'home', 'browser', 'files', 'cloud', 'tailnet', 'network', 'updates', 'persist', 'power', 'guide', 'backup', 'settings'}


def apply_keyboard(path='/etc/default/keyboard', environment=None):
    """Xorg started directly does not inherit setupcon's console keymap."""
    from i18n import DEFAULT_LOCALE, KEYBOARD_VARIANTS
    try:
        entries = shlex.split(Path(path).read_text(), comments=True)
    except FileNotFoundError:
        entries = []
    values = dict(entry.split('=', 1) for entry in entries if '=' in entry)
    layout = values.get('XKBLAYOUT', DEFAULT_LOCALE['keyboard'])
    variant = values.get('XKBVARIANT', '')
    if layout not in KEYBOARD_VARIANTS or variant not in KEYBOARD_VARIANTS[layout]:
        raise ValueError('Invalid graphical keyboard selection')
    subprocess.run(['setxkbmap', '-model', 'pc105', '-layout', layout,
                    '-variant', variant, '-option', ''], check=True, timeout=5,
                   env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def apply_active_keyboards(proc='/proc'):
    """Refresh local Xorg servers when the shared console preference changes."""
    for process in Path(proc).glob('[0-9]*'):
        try:
            if (process/'comm').read_text().strip() != 'Xorg':
                continue
            args = (process/'cmdline').read_bytes().decode().split('\0')
            display = next(arg for arg in args if re.fullmatch(r':\d+', arg))
            authority = args[args.index('-auth')+1]
        except (OSError, UnicodeError, ValueError, IndexError, StopIteration):
            continue
        apply_keyboard(environment=dict(os.environ, DISPLAY=display, XAUTHORITY=authority))


def read_request(directory, uid):
    if directory.parent != Path('/tmp') or not directory.name.startswith('aguja-desk-'):
        raise ValueError('Invalid local request')
    if directory.is_symlink():
        raise ValueError('Invalid local request')
    info = directory.stat()
    if info.st_uid != uid or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('Invalid local request')
    fd = os.open(directory/'request.json', os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_size > 8192 or info.st_mode & 0o077:
            raise ValueError('Invalid local request')
        record = json.load(stream)
    if set(record) != {'action', 'pid', 'stamp', 'url'} or record['action'] not in ACTIONS:
        raise ValueError('Invalid local request')
    import auth
    if auth.process_stamp(record['pid']) != record['stamp']:
        raise ValueError('Expired local request')
    if Path('/proc', str(record['pid'])).stat().st_uid != uid:
        raise ValueError('Invalid local caller')
    return record


def run(action='home', url=None):
    if action not in ACTIONS:
        raise ValueError('Unknown Desk page')
    if os.environ.get('DISPLAY'):
        if action in ('browser','files'):
            return direct(action,url)
        return subprocess.call(['/usr/bin/python3', '/usr/lib/aguja/desk.py', action])
    import auth
    import browser
    if os.getuid() == 0 or not browser.local_console() or not sys.stdin.isatty():
        print('Graphical Desk requires the local console. SSH: aguja context / hardware / storage / tailscale.', file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory(prefix='aguja-desk-', dir='/tmp') as folder:
        directory = Path(folder)
        record = {'action': action, 'url': url, 'pid': os.getpid(), 'stamp': auth.process_stamp(os.getpid())}
        auth_path = directory/'request.json'
        auth_path.write_text(json.dumps(record)); auth_path.chmod(0o600)
        result = subprocess.call(['sudo', '-n', '/usr/bin/python3', '/usr/lib/aguja/gui_session.py', 'launch', str(directory)])
        if result:
            print(f'LA AGUJA: graphical session failed (exit {result}); returning to console.', file=sys.stderr)
        return result


def launch(directory):
    if os.getuid() != 0:
        return 1
    uid = int(os.environ.get('SUDO_UID', '0'))
    if uid == 0:
        return 1
    user = pwd.getpwuid(uid)
    record = read_request(directory, uid)
    import browser
    oldvt = browser.original_vt(record['pid'])
    lock = os.open('/run/aguja-browser.lock', os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(lock)
        return 1
    children = []
    try:
        authority = directory/'Xauthority'
        authority.touch(mode=0o600); os.chown(authority, uid, user.pw_gid)
        display = next(n for n in range(20, 40) if not Path(f'/tmp/.X11-unix/X{n}').exists() and not Path(f'/tmp/.X{n}-lock').exists())
        subprocess.run(['runuser','-u',user.pw_name,'--','xauth','-f',str(authority)],
                       input=f'add :{display} . {secrets.token_hex(16)}\n'.encode(),
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        fd = os.open('/dev/tty0', os.O_RDWR)
        try:
            vt = struct.unpack('i', fcntl.ioctl(fd, 0x5600, bytes(4)))[0]
        finally:
            os.close(fd)
        if vt <= 0 or vt == oldvt:
            raise ValueError('No spare virtual console')
        server = subprocess.Popen(['/usr/bin/Xorg', f':{display}', f'vt{vt}', '-nolisten', 'tcp',
                                   '-auth', str(authority), '-logfile', '/dev/null', '-noreset'],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        children.append(server)
        environment = dict(os.environ, DISPLAY=f':{display}', XAUTHORITY=str(authority), HOME=user.pw_dir,
                           XDG_SESSION_TYPE='x11', AGUJA_DESK_REQUEST=str(directory))
        for key in ('DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','SSH_CONNECTION','SSH_TTY'):
            environment.pop(key, None)
        for _ in range(100):
            if server.poll() is not None:
                return 1
            result = subprocess.run(['runuser','-u',user.pw_name,'--','xdpyinfo'], env=environment,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
            if result.returncode == 0:
                break
            time.sleep(.1)
        else:
            return 1
        gui = subprocess.Popen(['runuser','-u',user.pw_name,'--','dbus-run-session','--',
                                '/usr/bin/python3','/usr/lib/aguja/gui_session.py','session',str(directory)],
                               env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        children.append(gui)
        while gui.poll() is None and server.poll() is None:
            time.sleep(.2)
        return gui.returncode or 0
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired: child.kill(); child.wait()
        subprocess.run(['chvt', str(oldvt)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        os.close(lock)


def wait_window_manager(process):
    for _ in range(100):
        if process.poll() is not None:raise ValueError('Window manager did not start')
        state=subprocess.run(['xprop','-root','_NET_SUPPORTING_WM_CHECK'],capture_output=True,timeout=2)
        if b'window id #' in state.stdout:return
        time.sleep(.02)
    raise ValueError('Window manager did not become ready')


def direct(action,url=None):
    if action=='browser':
        import web
        return web.open_browser(url).wait()
    import file_manager
    return file_manager.launch('/')


def session(directory):
    record = read_request(directory, os.getuid())
    environment = dict(os.environ, BROWSER='/usr/local/bin/aguja-web', GTK_THEME='Adwaita:dark',
                       AGUJA_DESK_REQUEST=str(directory))
    window_manager = subprocess.Popen(['openbox', '--config-file', '/usr/share/aguja/desktop/openbox.xml'],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_window_manager(window_manager)
        apply_keyboard()
        os.environ.update(environment)
        if shutil.which('xsetroot'):
            subprocess.run(['xsetroot','-cursor_name','left_ptr'],env=environment,check=False)
        if record['action'] in ('browser','files'):
            return direct(record['action'],record.get('url'))
        return subprocess.call(['/usr/bin/python3','/usr/lib/aguja/desk.py',record['action']], env=environment)
    finally:
        window_manager.terminate()
        try: window_manager.wait(timeout=3)
        except subprocess.TimeoutExpired: window_manager.kill(); window_manager.wait()


if __name__ == '__main__':
    try:
        action = sys.argv[1]
        raise SystemExit(launch(Path(sys.argv[2])) if action == 'launch' else session(Path(sys.argv[2])))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        print('LA AGUJA: graphical session unavailable; return to the cockpit.', file=sys.stderr)
        raise SystemExit(1)
