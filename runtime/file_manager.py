"""One root Thunar window with its own D-Bus session, never automount at boot."""
import os
from pathlib import Path
import subprocess


def spawn(path='/'):
    return subprocess.Popen(['sudo', '-n', 'env', 'DISPLAY='+os.environ.get('DISPLAY',''),
                            'XAUTHORITY='+os.environ.get('XAUTHORITY',''),
                            'LANG='+os.environ.get('LANG','en_US.UTF-8'),
                            '/usr/bin/python3', __file__, path])


def launch(path='/'):
    return spawn(path).wait()


def main(path='/'):
    if os.geteuid() != 0 or not os.environ.get('DISPLAY') or not Path(path).is_dir():
        return 1
    runtime = Path('/run/aguja-files')
    runtime.mkdir(mode=0o700, exist_ok=True)
    if runtime.is_symlink() or runtime.stat().st_uid != 0:
        return 1
    runtime.chmod(0o700)
    env = {'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
           'HOME': '/root', 'USER': 'root', 'LOGNAME': 'root',
           'DISPLAY': os.environ['DISPLAY'], 'XAUTHORITY': os.environ['XAUTHORITY'],
           'XDG_RUNTIME_DIR': str(runtime), 'GTK_THEME': 'Adwaita:dark',
           'LANG': os.environ.get('LANG', 'en_US.UTF-8')}
    # Root has owner-authorized access; its bus avoids using the browser's bus.
    return subprocess.call(['dbus-run-session', '--', 'thunar', '--window', path], env=env)


if __name__ == '__main__':
    import sys
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else '/'))
