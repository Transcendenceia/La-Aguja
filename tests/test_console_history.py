import os
import fcntl
from pathlib import Path
import pty
import re
import select
import shutil
import signal
import subprocess
import struct
import sys
import time
import termios
import unittest
from unittest.mock import patch

RUNTIME = Path(__file__).resolve().parents[1] / 'runtime'
sys.path.insert(0, str(RUNTIME))
import console_history
import console_mouse
import harness


class HistoryBoundaryTests(unittest.TestCase):
    def test_wheel_filter_never_forwards_keyboard_buttons_or_coordinates(self):
        event = console_mouse.EVENT.pack
        data = event(0,0,1,30,1) + event(0,0,1,272,1) + event(0,0,2,0,100) + event(0,0,2,1,-30)
        self.assertEqual(console_mouse.wheel_delta(data), 0)
        self.assertEqual(console_mouse.wheel_delta(data + event(0,0,2,8,2)), 2)
        self.assertEqual(console_mouse.wheel_delta(event(0,0,2,8,-1)), -1)

    def test_ssh_noninteractive_and_existing_tmux_unchanged(self):
        for environment in ({'SSH_CONNECTION': 'fixture'}, {'TMUX': 'fixture'}, {}):
            with patch.dict(os.environ, environment, clear=True), patch.object(os, 'isatty', return_value=False):
                self.assertIsNone(console_history.run(['never-run']))
        with patch.dict(os.environ, {'AGUJA_LOCAL_CONSOLE': '1', 'AGUJA_CONSOLE_TTY': '/dev/tty1'}, clear=True), \
             patch.object(os, 'isatty', return_value=True), patch.object(os, 'ttyname', return_value='/dev/pts/1'):
            self.assertEqual(console_history.local_vt(), '/dev/tty1')

    def test_codex_inline_preserves_safe_and_unsafe_permission_modes(self):
        with patch.dict(os.environ, {'TMUX': 'fixture', 'AGUJA_LOCAL_CONSOLE': '1'}):
            for mode in ('safe', 'unsafe'):
                _, args, _ = harness.invocation('codex', mode)
                self.assertIn('--no-alt-screen', args)
                if mode == 'safe':
                    self.assertIn('hooks.PreToolUse=', ' '.join(args))
                else:
                    self.assertIn('--dangerously-bypass-approvals-and-sandbox', args)


@unittest.skipUnless(shutil.which('tmux'), 'real tmux required')
class ActualHistoryTests(unittest.TestCase):
    def test_real_scrollback_keyboard_exit_code_and_no_transcript(self):
        fixture = 'import os,sys; print("\\x1b[?1049h",end=""); [print("SCROLL-LINE-%04d"%i) for i in range(350)]; print("QA_SOCKET="+os.environ["TMUX"].split(",")[0],flush=True); input(); sys.exit(7)'
        pid, fd = pty.fork()
        if pid == 0:
            fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack('4H', 24, 80, 0, 0))
            environment = dict(os.environ, TMPDIR='/tmp', TERM='linux', AGUJA_LOCAL_CONSOLE='1', AGUJA_CONSOLE_TTY='/dev/tty1')
            environment.pop('SSH_CONNECTION', None)
            environment.pop('TMUX', None)
            os.execvpe(sys.executable, [sys.executable, str(RUNTIME/'console_history.py'), sys.executable, '-c', fixture], environment)
        data = b''
        socket = None
        try:
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                if select.select([fd], [], [], .1)[0]:
                    try:
                        data += os.read(fd, 65536)
                    except OSError:
                        break
                match = re.search(rb'QA_SOCKET=(/tmp/aguja-console-[a-zA-Z0-9_-]+/tmux.sock)', data)
                if match:
                    socket = match[1].decode()
                    break
            self.assertIsNotNone(socket, data[-1000:])
            def tmux(*args):
                return subprocess.check_output(['tmux', '-S', socket, *args], text=True, timeout=3).strip()
            history = tmux('capture-pane', '-p', '-S', '-')
            self.assertIn('SCROLL-LINE-0000', history)
            self.assertIn('SCROLL-LINE-0349', history)
            self.assertEqual(tmux('show-options', '-gv', 'history-limit'), '10000')
            self.assertEqual(tmux('show-options', '-gwv', 'alternate-screen'), 'off')
            os.write(fd, b'\x1b[5~')  # Real PageUp key bytes, not tmux send-keys.
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and tmux('display-message', '-p', '#{pane_in_mode}') != '1':
                time.sleep(.05)
            self.assertEqual(tmux('display-message', '-p', '#{pane_in_mode}'), '1')
            initial = int(tmux('display-message', '-p', '#{scroll_position}'))
            self.assertGreater(initial, 0)
            os.write(fd, b'\x1b[5~')
            time.sleep(.08)
            upper = int(tmux('display-message', '-p', '#{scroll_position}'))
            self.assertGreater(upper, initial)
            os.write(fd, b'\x1b[6~')
            time.sleep(.08)
            self.assertLess(int(tmux('display-message', '-p', '#{scroll_position}')), upper)
            os.write(fd, b'\x1b')
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and tmux('display-message', '-p', '#{pane_in_mode}') != '0':
                time.sleep(.05)
            self.assertEqual(tmux('display-message', '-p', '#{pane_in_mode}'), '0')
            console_history.scroll(socket, 2)
            self.assertEqual(tmux('display-message', '-p', '#{pane_in_mode}'), '1')
            self.assertEqual(int(tmux('display-message', '-p', '#{scroll_position}')), 6)
            console_history.scroll(socket, -2)
            self.assertEqual(tmux('display-message', '-p', '#{pane_in_mode}'), '0')
            self.assertEqual(sorted(p.name for p in Path(socket).parent.iterdir()), ['tmux.sock'])
            os.write(fd, b'finish\n')
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                exited, status = os.waitpid(pid, os.WNOHANG)
                if exited:
                    self.assertEqual(os.waitstatus_to_exitcode(status), 7)
                    self.assertFalse(Path(socket).parent.exists())
                    pid = None
                    break
                if select.select([fd], [], [], .1)[0]:
                    try: os.read(fd, 65536)
                    except OSError: pass
            self.assertIsNone(pid, 'console wrapper did not finish')
        finally:
            if socket and Path(socket).exists():
                subprocess.run(['tmux', '-S', socket, 'kill-server'], capture_output=True)
            if pid:
                try: os.kill(pid, signal.SIGTERM)
                except ProcessLookupError: pass
                os.waitpid(pid, 0)
            os.close(fd)


if __name__ == '__main__':
    unittest.main()
