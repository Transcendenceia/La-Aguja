"""Bounded, RAM-only scrollback for local CLI consoles, independent of X/GUI.

Keep the tmux server in the foreground under this VT-owning process: the
existing browser/console helpers can still validate the original VT ancestry.
Only an exit code is written temporarily; no terminal transcript or input log.
"""
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time


def local_vt():
    if os.environ.get('SSH_CONNECTION') or os.environ.get('TMUX'):
        return None
    if not (os.isatty(0) and os.isatty(1)):
        return None
    current = os.ttyname(0)
    if re.fullmatch(r'/dev/tty[1-9][0-9]*', current):
        return current
    original = os.environ.get('AGUJA_CONSOLE_TTY', '')
    if os.environ.get('AGUJA_LOCAL_CONSOLE') == '1' and re.fullmatch(r'/dev/tty[1-9][0-9]*', original):
        return original
    return None


def run(argv):
    vt = local_vt()
    if not vt or not shutil.which('tmux'):
        return None
    config = Path(__file__).with_name('console-history.conf')
    if not config.is_file():
        return None
    environment = dict(os.environ, AGUJA_LOCAL_CONSOLE='1', AGUJA_CONSOLE_TTY=vt)
    with tempfile.TemporaryDirectory(prefix='aguja-console-') as directory:
        socket = str(Path(directory) / 'tmux.sock')
        status = Path(directory) / 'exit-code'
        base = ['tmux', '-S', socket]
        server = subprocess.Popen(base + ['-f', str(config), '-D'],
            env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        handlers = {}
        mouse = None
        mouse_thread = None
        try:
            for sig in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT, signal.SIGQUIT):
                handlers[sig] = signal.signal(sig, lambda s, _: server.send_signal(s) if server.poll() is None else None)
            deadline = time.monotonic() + 5
            while not Path(socket).exists() and server.poll() is None and time.monotonic() < deadline:
                time.sleep(.02)
            if not Path(socket).exists():
                return None  # No child has been launched; safe native fallback.
            mouse, mouse_thread = start_mouse(socket, vt)
            command = base + ['new-session', '-s', 'rescate', '-n', 'consola',
                '/usr/bin/python3', str(Path(__file__).resolve()), '--child', str(status)] + list(argv)
            client_code = subprocess.call(command, env=environment)
            if not status.exists() and server.poll() is None:
                # Detaching keeps the running CLI intact. Reattach from another
                # terminal; this VT-owning parent stays alive until it finishes.
                print('\nConsola separada; sigue activa. Volver: tmux -S ' + socket + ' attach', flush=True)
                server.wait()
            if status.exists():
                return int(status.read_text())
            return client_code or 1
        finally:
            if mouse is not None:
                mouse.stdin.close()
                try:
                    mouse.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    mouse.terminate()
                    mouse.wait(timeout=2)
                mouse.stdout.close()
            if mouse_thread is not None:
                mouse_thread.join(timeout=1)
            for sig, handler in handlers.items():
                signal.signal(sig, handler)
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


def scroll(socket, delta):
    """Navigate terminal memory; never send keystrokes/commands to the CLI."""
    base = ['tmux', '-S', socket]
    def command(*args):
        return subprocess.run(base + list(args), capture_output=True, text=True, timeout=2)
    mode = command('display-message', '-p', '#{pane_in_mode}')
    if mode.returncode:
        return
    if delta > 0 and mode.stdout.strip() == '0':
        command('copy-mode')
    if delta > 0 or mode.stdout.strip() != '0':
        command('send-keys', '-X', '-N', str(3*min(16, abs(delta))),
                'scroll-up' if delta > 0 else 'scroll-down')
        if delta < 0 and command('display-message', '-p', '#{scroll_position}').stdout.strip() == '0':
            command('send-keys', '-X', 'cancel')


def start_mouse(socket, vt):
    helper = Path(__file__).with_name('console_mouse.py')
    if not helper.is_file() or not shutil.which('sudo'):
        return None, None
    process = subprocess.Popen(['sudo', '-n', '/usr/bin/python3', str(helper), str(os.getpid()), vt],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    def consume():
        try:
            for line in process.stdout:
                if re.fullmatch(r'-?[0-9]+\s*', line):
                    delta = int(line)
                    if delta and abs(delta) <= 16:
                        scroll(socket, delta)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
    thread = threading.Thread(target=consume, name='aguja-wheel', daemon=True)
    thread.start()
    return process, thread


def child(status, argv):
    process = subprocess.Popen(argv)
    previous = {}
    for sig in (signal.SIGINT, signal.SIGQUIT):
        # The terminal already signals the foreground group; don't end the
        # supervising Python before the native CLI handles Ctrl+C itself.
        previous[sig] = signal.signal(sig, lambda *_: None)
    try:
        code = process.wait()
        code = code if code >= 0 else 128 - code
        Path(status).write_text(str(code))
        return code
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    if len(sys.argv) >= 4 and sys.argv[1] == '--child':
        raise SystemExit(child(sys.argv[2], sys.argv[3:]))
    if len(sys.argv) >= 2:
        result = run(sys.argv[1:])
        if result is None:
            os.execvp(sys.argv[1], sys.argv[1:])
        raise SystemExit(result)
