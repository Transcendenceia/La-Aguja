#!/usr/bin/python3
"""SSH ForceCommand: preserve transport, mirror only sanitized volatile activity.

Interactive PTYs retain job control and window size. No stdin is ever recorded.
Protocols bypass interception; login/exec uses the account's original shell.
"""
import base64
import fcntl
import os
import pwd
import pty
import select
import shlex
import signal
import subprocess
import sys
import termios
import tty
import uuid

import activity


def protocol(command):
    try:
        words = shlex.split(command)
    except ValueError:
        return None
    if not words:
        return None
    executable = os.path.basename(words[0])
    if (executable=='aguja' and words[1:] in (['activity'],['activity','--json'])) or words==['cat','/run/aguja-activity/snapshot.json']:
        return 'observer'
    if executable in ('internal-sftp', 'sftp-server'):
        return 'sftp'
    if executable == 'scp' and any(option.startswith('-') and ('t' in option or 'f' in option) for option in words[1:]):
        return 'scp'
    if executable == 'rsync' and '--server' in words[1:]:
        return 'rsync'
    return None


def command_argv(command, shell, mode):
    if mode == 'sftp':
        words = shlex.split(command)
        if words and words[0] == 'internal-sftp':
            return ['/usr/lib/openssh/sftp-server'] + words[1:]
    return [shell, '-c', command] if command else [shell, '-l']


def stream(data):
    # Bytes go unmodified to SSH. Only a transient local datagram goes to the
    # root sanitizer; daemon ignores it unless a safe command is active.
    activity.emit('output', chunk=base64.b64encode(data).decode('ascii'))


def write_all(fd, data):
    while data:
        try:
            written = os.write(fd, data)
            if written <= 0:
                raise OSError('SSH stream made no progress')
            data = data[written:]
        except InterruptedError:
            continue


def resize(master):
    try:
        size = fcntl.ioctl(0, termios.TIOCGWINSZ, bytes(8))
        fcntl.ioctl(master, termios.TIOCSWINSZ, size)
    except OSError:
        pass


def relay_pty(argv):
    attributes = termios.tcgetattr(0)
    size = fcntl.ioctl(0, termios.TIOCGWINSZ, bytes(8))
    pid, master = pty.fork()
    if pid == 0:
        termios.tcsetattr(0, termios.TCSANOW, attributes)
        fcntl.ioctl(0, termios.TIOCSWINSZ, size)
        os.execvpe(argv[0], argv, os.environ)
    old_resize = signal.signal(signal.SIGWINCH, lambda *_: resize(master))
    old_signals = {}
    for signum in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT, signal.SIGQUIT):
        def forward(sig, frame):
            try:
                os.killpg(pid, sig)
            except ProcessLookupError:
                pass
        old_signals[signum] = signal.signal(signum, forward)
    try:
        # SSH may have already delivered a piped command before startup.
        # tty.setraw defaults to TCSAFLUSH and would silently drop that input.
        tty.setraw(0, when=termios.TCSANOW)
        inputs = [0, master]
        while master in inputs:
            ready, _, _ = select.select(inputs, [], [])
            for fd in ready:
                try:
                    data = os.read(fd, 4096)
                except OSError:
                    data = b''
                if not data:
                    inputs.remove(fd)
                    if fd == 0:
                        # Parent SSH disconnect: don't leave the rescue shell
                        # behind and don't inject a literal EOT into raw apps.
                        try:
                            os.killpg(pid, signal.SIGHUP)
                        except ProcessLookupError:
                            pass
                    continue
                if fd == master:
                    write_all(1, data)
                    stream(data)
                else:
                    # Signal only that input happened, never its contents.
                    # Suppress local mirror before the slave can echo input.
                    activity.emit('input_activity')
                    write_all(master, data)
        _, status = os.waitpid(pid, 0)
        return os.waitstatus_to_exitcode(status)
    finally:
        termios.tcsetattr(0, termios.TCSADRAIN, attributes)
        signal.signal(signal.SIGWINCH, old_resize)
        for signum, handler in old_signals.items():
            signal.signal(signum, handler)
        os.close(master)


def relay_pipes(argv, mirror=True):
    # Pass stdin directly, no relay/read/logging of script or password input.
    # New process group forwards disconnect/signals to descendants.
    child = subprocess.Popen(argv, stdin=None, stdout=subprocess.PIPE if mirror else None,
                             stderr=subprocess.PIPE if mirror else None, start_new_session=True)
    handlers = {}
    for signum in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT, signal.SIGQUIT):
        def forward(sig, frame):
            try:
                os.killpg(child.pid, sig)
            except ProcessLookupError:
                pass
        handlers[signum] = signal.signal(signum, forward)
    try:
        if mirror:
            streams = {child.stdout.fileno(): 1, child.stderr.fileno(): 2}
            while streams:
                ready, _, _ = select.select(list(streams), [], [])
                for fd in ready:
                    data = os.read(fd, 4096)
                    if not data:
                        del streams[fd]
                        continue
                    write_all(streams[fd], data)
                    stream(data)
        return child.wait()
    finally:
        if child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGHUP)
                child.wait(timeout=1)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            except ProcessLookupError:
                child.wait()
        for signum, handler in handlers.items():
            signal.signal(signum, handler)


def main():
    from profile import locale_environment
    os.environ.update(locale_environment())
    command = os.environ.get('SSH_ORIGINAL_COMMAND', '')
    shell = pwd.getpwuid(os.getuid()).pw_shell or '/bin/sh'
    sid = uuid.uuid4().hex[:24]
    os.environ['AGUJA_SESSION_ID'] = sid
    mode = protocol(command)
    peer = os.environ.get('SSH_CONNECTION', '').split()
    local = os.environ.get('AGUJA_LOCAL_CONSOLE') == '1'
    activity.emit('session_start', command or 'Shell interactiva', session=sid,
                  peer='Consola local' if local else (peer[0] + ':' + peer[1]) if len(peer) >= 2 else 'desconocido',
                  transport='local' if local else 'ssh',
                  sensitive=not (activity.safe_output(command) or activity.safe_task_output(command)), mode=mode or ('interactive' if not command else 'exec'),
                  probe=activity.probe_context(command), label=activity.task_label(command))
    argv = command_argv(command, shell, mode)
    code = 255
    try:
        if mode:
            # Binary protocols and the observer get their original bytes.
            # Never journal the journal into itself (unbounded feedback).
            code = relay_pipes(argv, mirror=False)
            if mode=='observer':
                stream(('Consulta de actividad entregada · código '+str(code)+'\n').encode())
        elif local and os.isatty(0):
            # Capture task output in a PTY while preserving the validated real
            # VT for framebuffer/mouse access when the panel is reopened.
            # Input is forwarded, never recorded.
            os.environ.setdefault('AGUJA_CONSOLE_TTY', os.ttyname(0))
            code = relay_pty(argv)
        elif os.isatty(0):
            code = relay_pty(argv)
        else:
            code = relay_pipes(argv, mirror=True)
    except (OSError, ValueError):
        # Fixed error only: exceptions may contain confidential argv/paths.
        try:
            os.write(2, b'LA AGUJA Rescue Disk: no se pudo iniciar la sesion.\n')
        except OSError:
            pass
    finally:
        activity.emit('session_end', session=sid, exit=code)
    if code < 0:
        signum = -code
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)
        return 128 + signum
    return code


if __name__ == '__main__':
    sys.exit(main())
